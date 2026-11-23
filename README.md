# LFMC 独立测试站

测试站仓库使用独立 GitHub 组织的公开 Pages 域名。它从公开的 LFMC 仓库读取 PR、CI 和固定 SHA 的源码 ZIP。打包只读取 LFMC 静态文件，不检出或执行该 PR 的工作流、测试脚本或构建脚本。

## 初始化

1. 将此目录提交到测试仓库的默认分支，保留 .github/workflows/publish.yml。
2. 从初始提交创建并推送 preview-snapshots 分支。工作流向该分支追加快照，分支规则需要允许测试仓库的 GitHub Actions 写入。
3. 在测试仓库的 Settings → Pages → Build and deployment 中选择 GitHub Actions。允许工作流写入测试仓库内容，并让 github-pages 环境仅接受默认分支的部署。
4. 在 Actions → Publish LFMC preview → Run workflow 中填写 PR 编号、完整 head SHA 和预期版本。首次使用 163、2850510d4f48fe2762300d2497ad5360000746f7、2026.11.23-99。

## 核验

- 打开 /latest/，确认跳转到 /pr-163/2850510d4f48fe2762300d2497ad5360000746f7/。
- 检查页首的 PR、完整 SHA、版本、部署时间和 PR 链接。相同信息可从该目录下的 preview.json 核验。
- 检查 app.js?v=2026.11.23-99 返回 HTTP 200，页脚显示 v2026.11.23-99，再从手机选择测试附加包、转换并下载。
- 每次发布都包含历史快照和新的 /latest/ 指向。只有 Pages 部署成功才会切换公开入口。保留全部历史会持续增长，需要监控 Pages 站点体积上限。
