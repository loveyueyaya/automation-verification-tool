# 10-env-baseline - 环境地基基线

## 用途

存放本机开发环境地基基线的**证据与清单**：工具链版本、Python 包版本、可复现安装/卸载命令、验收证据、环境坑规避、未验证路径清单、pip 安装前快照（回滚依据）。

与相邻目录的边界：

| 目录 | 放什么 |
|---|---|
| **10-env-baseline**（本目录） | 环境基线的**可复现事实**（版本、命令、证据、快照） |
| 08-review-logs | AI 审查记录与误报/分歧案例库 |
| 09-feedback | 过程日志（问题/解决/遗留/timeline 事件流） |

## 内容清单

- `env-baseline_v1.md` — 环境地基清单（2026-09-18 12:15 初版，12:32 修订，13:1x 路径修订）：硬件 / 工具链绝对路径 / Python 包版本 / 可复现安装与卸载命令 / 验收证据 / 环境坑 A-D / 回滚依据 / **P2-2 迁移顺序修正版 7 步** / env_probe 调用方式澄清 / 56 测试三个时点
- `pip_before_20260918.txt` — pip 安装前全量快照（106 行，2348 B，sha256 `a9ea9fdaffbbfdb815efe5a41cc090e6a5291900d64b3aaf8c34e29dcc8500ec`），回滚依据
- `unverified-paths_20260918.md` — 未验证路径清单（SendInput / dxcam 主路径 + comtypes COM 初始化间接路径；本机 `security=wujie` 降级导致主路径从未真机验证）

## 目录编号说明

- 原为 `08-env-baseline`，与既有 `08-review-logs` **编号冲突**，2026-09-18 经用户拍板改名 `10-env-baseline`
- 迁移方式：`git mv`（保留历史，未用复制）
- 同时把 `06-deployment\env-baseline_v1.md` 一并迁入本目录，使环境基线归位一处

## 相关文档

- 部署索引：`F:\自动化验证工具\06-deployment\deployment-index.md`（地基清单原在此，已迁出并注明）
- 技能索引：`F:\自动化验证工具\00-doubao-llm-prerequisites\doubao-prerequisites-index.md`
- 平台实测坑 A-E：`local-dev-environment` 技能 SKILL.md（权威源 + AppData 副本双份）
- 未验证路径的行动项：P3 smoke 必须含"关闭远程软件验证主路径"用例
