"""Build a GitHub Pages artifact from a verified, fixed LFMC commit."""
import html
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from zipfile import ZipFile

REPO = "zanesu154-rgb/tianji-turn-addon"
API = f"https://api.github.com/repos/{REPO}"
ROOT_FILES = {"index.html", "app.js", "style.css"}
STATIC_DIRS = {"src", "vendor"}


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lfmc-preview"}
    with urlopen(Request(API + path, headers=headers), timeout=30) as response:
        return json.load(response)


def verify(pr, sha):
    pull = api(f"/pulls/{pr}")
    if (pull["state"] != "open" or pull["merged"]
            or pull["base"]["repo"]["full_name"] != REPO
            or pull["base"]["ref"] != "main" or pull["head"]["sha"] != sha):
        raise ValueError("PR must be open and match the requested SHA and base")
    runs = api(f"/actions/workflows/tests.yml/runs?event=pull_request&head_sha={sha}")
    for run in runs["workflow_runs"]:
        if (run["head_sha"] == sha and run["event"] == "pull_request"
                and any(item["number"] == pr and item["base"]["repo"]["id"] == pull["base"]["repo"]["id"]
                        for item in run["pull_requests"])):
            if run["status"] != "completed" or run["conclusion"] != "success":
                raise ValueError("The most recent matching LFMC Tests run has not passed")
            return run["html_url"]
    raise ValueError("No LFMC Tests run associated with this PR and head SHA")


def extract_static(archive, destination):
    with ZipFile(io.BytesIO(archive)) as bundle:
        for member in bundle.infolist():
            parts = PurePosixPath(member.filename).parts[1:]
            if not parts or member.is_dir():
                continue
            if not ((len(parts) == 1 and parts[0] in ROOT_FILES) or (len(parts) > 1 and parts[0] in STATIC_DIRS)):
                continue
            mode = stat.S_IFMT(member.external_attr >> 16)
            if mode not in (0, stat.S_IFREG) or any(p in ("..", ".", "/") or "\\" in p for p in parts):
                raise ValueError("Invalid static archive entry")
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
    if not all((destination / name).is_file() for name in ROOT_FILES):
        raise ValueError("Missing LFMC site entry files")


def annotate(snapshot, pr, sha, expected_version, ci):
    page = snapshot / "index.html"
    source = page.read_text(encoding="utf-8")
    version_match = re.search(r'<script\s+src="app\.js\?v=([0-9.]+-[0-9]+)"', source)
    if not version_match or version_match[1] != expected_version:
        raise ValueError("LFMC asset version does not match the expected version")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pr_url = f"https://github.com/{REPO}/pull/{pr}"
    metadata = dict(pr=pr, sha=sha, version=expected_version, deployed_at=timestamp,
                    pr_url=pr_url, ci_url=ci)
    banner = (
        '<aside aria-label="LFMC 测试部署" style="padding:0.65rem;overflow-wrap:anywhere;'
        'background:#fef3c7;color:#222;font:14px system-ui">'
        f'<strong>LFMC 测试站 · PR #{pr} · v{html.escape(expected_version)}</strong><br>'
        f'提交 <code>{sha}</code> · 部署时间 <time>{timestamp}</time> · '
        f'<a href="{pr_url}">查看 PR</a></aside>'
    )
    output, count = re.subn(r"<body(?:\s[^>]*)?>", lambda match: match[0] + banner, source,
                            count=1, flags=re.IGNORECASE)
    if count != 1:
        raise ValueError("Missing LFMC page body")
    page.write_text(output, encoding="utf-8")
    (snapshot / "preview.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main():
    pr_text, sha, version, history_dir, site_dir = sys.argv[1:]
    if not re.fullmatch(r"[1-9][0-9]*", pr_text) or not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("Expected a PR number and the full lowercase head SHA")
    if not re.fullmatch(r"[0-9.]+-[0-9]+", version):
        raise ValueError("Expected an LFMC version such as 2026.11.23-99")
    pr = int(pr_text)
    ci = verify(pr, sha)
    history = Path(history_dir)
    site = Path(site_dir)
    relative = Path(f"pr-{pr}", sha)
    archived = history / "snapshots" / relative
    if not archived.exists():
        with urlopen(f"https://codeload.github.com/{REPO}/zip/{sha}", timeout=60) as response:
            extract_static(response.read(), archived)
        annotate(archived, pr, sha, version, ci)
    if json.loads((archived / "preview.json").read_text())["version"] != version:
        raise ValueError("Existing immutable snapshot has a different version")
    verify(pr, sha)
    shutil.copytree(history / "snapshots", site)
    latest_link = f"../{relative.as_posix()}/"
    latest = site / "latest"
    latest.mkdir()
    (latest / "index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><title>LFMC 最新测试版</title>'
        f'<meta http-equiv="refresh" content="0;url={latest_link}">'
        f'<a href="{latest_link}">打开最新测试版</a>\n', encoding="utf-8")
    shutil.copyfile(archived / "preview.json", latest / "preview.json")


if __name__ == "__main__":
    main()
