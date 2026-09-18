# 06-deployment - 部署

## 用途
存放打包、发布、安装相关产物（EXE 打包配置、Release 发布记录）与**环境地基清单**。

## 内容清单
- env-baseline_v1.md — 环境地基清单（2026-09-18 12:15 初版，12:32 修订）：硬件 / 工具链绝对路径 / Python 包版本 / 可复现安装与卸载命令 / 验收证据 / 环境坑 A-D / 回滚依据 / **P2-2 迁移顺序修正版 7 步** / env_probe 调用方式澄清 / 56 测试三个时点
- 配套回滚快照：`F:\自动化验证工具\08-env-baseline\pip_before_20260918.txt`（pip 安装前全量快照，106 行）

## 相关文档
- local-dev-environment 技能"阶段封板流程"（打 tag + 准备 RELEASE_NOTES + 打包资产 + gh release create + 验证）
- RELEASE_NOTES_INDEX.md（根目录 Release 索引）
