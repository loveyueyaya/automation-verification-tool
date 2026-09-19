# 06-deployment - 部署

## 用途
存放打包、发布、安装相关产物（EXE 打包配置、Release 发布记录）。当前为 P1/P1-patch1 的发布档案 + 本地大体积备份。

## 内容清单（逐文件）

| 文件 | 作用 | 入库 |
|---|---|---|
| `deployment-index.md` | 本目录索引 | ✅ |
| `RELEASE_NOTES_INDEX.md` | Release 索引：P1（`ui-toolbox-P1-20260916`）/ P1-patch1（`ui-toolbox-P1-patch1-20260917`），对应 GitHub Release 清单 | ✅ |
| `RELEASE_NOTES_v1.md` | P1 Release 说明全文（含 MIGRATION 初始版快照；**历史文档**——正文中的旧路径保留原文，末尾有勘误注记指向现位置） | ✅ |
| `P1_patch1_release_notes.md` | P1-patch1 Release 说明：字符串字面量复核（文心 AI 误报，5 来源铁证 0 命中） | ⬜ 本地副本不入库 |
| `P1-pyc-cache-backup\` | P1 期 pyc 重建备份（12,834 文件 / 156.8 MB）：含 AppData 清理事故中被删源码的 .pyc（cookie_sync / 测试控制台 / GitHubCodeAnalyzer / P1 全套）——**AppData 被清后的恢复路径证据** | ⬜ 本地副本不入库（.gitignore） |

## 相关文档
- `07-operations\git-sync.ps1` / `sync-to-github.bat`（仓库同步脚本）
- local-dev-environment 技能"阶段封板流程"（打 tag + RELEASE_NOTES + 打包资产 + gh release create + 验证）
- 原环境地基清单 `env-baseline_v1.md` 已迁至 `10-env-baseline\`（09-18 编号去冲突）
