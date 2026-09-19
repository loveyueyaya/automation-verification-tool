# 07-operations - 运维

## 用途
存放运行维护、监控、日志巡检相关文档，以及仓库同步等日常运维脚本。

## 内容清单（逐文件）

| 文件 | 作用 |
|---|---|
| `operations-index.md` | 本目录索引 |
| `git-sync.ps1` | 项目自动同步到 GitHub 的 PowerShell 脚本：无变更不提交、无领先不推送；用 `$LASTEXITCODE` 判成败（09-18 修复：不再把 git 正常 stderr 当异常；push 用 Token 禁止明文密码） |
| `sync-to-github.bat` | `git-sync.ps1` 的双击包装入口（2026-09-19 由根目录归位并英文化命名） |
| （待填充） | 运行环境复检、时间线会话检查、性能基线等运维文档，待后续阶段产出 |

## 相关文档
- `06-deployment\`（发布与 Release 资产）
- `08-review-logs\`（审查日志）、`09-feedback\`（反馈日志）
- GitHub 仓库：https://github.com/loveyueyaya/automation-verification-tool （main；本地=远端 `c66e5d9`）
