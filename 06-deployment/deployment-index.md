# 06-deployment - 部署

## 用途
存放打包、发布、安装相关产物（EXE 打包配置、Release 发布记录）。

## 内容清单
- RELEASE_NOTES_INDEX.md — Release 索引（P1 / P1-patch1；2026-09-19 由根目录归位至此）
- RELEASE_NOTES_v1.md — P1 Release 说明（历史文档，正文路径保留原文 + 末尾勘误注记）
- P1_patch1_release_notes.md — P1-patch1 Release 说明（**本地副本，不入库**）
- P1-pyc-cache-backup/ — P1 期 pyc 重建备份（12,834 文件 / 156.8 MB，**本地副本，不入库**）
- 原环境地基清单 `env-baseline_v1.md` 已于 2026-09-18 迁至 `F:\自动化验证工具\10-env-baseline\`（原因：08 编号与 `08-review-logs` 冲突）

## 相关文档
- local-dev-environment 技能"阶段封板流程"（打 tag + 准备 RELEASE_NOTES + 打包资产 + gh release create + 验证）
- RELEASE_NOTES_INDEX.md（本目录，Release 索引）
- 07-operations/（仓库同步脚本 07-operations/git-sync.ps1 / 07-operations/sync-to-github.bat）
