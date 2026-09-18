# 自动化验证工具 - 项目总说明

## 项目定位（一句话）
本地离线运行的 UI 自动化验证工具箱：感知层输出 target_hwnd、动作层强制 locate（拒绝裸坐标）、审计层记录"坐标来源+置信度+回退链"，三层自动闭环（失败→诊断→重试），全程可回放、可审计、可对比基线。

## 目录结构（00~10）
- 00-doubao-llm-prerequisites — 豆包技能前置文件（本地开发环境 + 并行/串行判定技能权威源）
- 01-requirements — 需求分析（需求规格 + 运行环境报告）
- 02-architecture — 架构设计（v3：7 层 MVP + select_flow 5 流 + 契约化）
- 03-detailed-design — 详细设计（待 P2 填充）
- 04-implementation — 代码实现（P1 权威源：contracts + env_adapter + scripts + tests）
- 05-tests — 测试与验收证据
- 06-deployment — 部署（打包/发布，待填充）
- 07-operations — 运维（待填充）
- 08-review-logs — 审查日志（AI 审查记录 + 误报/分歧案例库）
- 09-feedback — 反馈日志（问题/解决/遗留/不清晰记录）
- 10-env-baseline — 环境地基基线（工具链/包版本/可复现命令/验收证据/未验证路径/pip 快照）

## 当前阶段
P1 已封板（56/56 测试通过 + pyc 备份 + tag），准备 P2。

## 权威源位置
F 盘：`F:\自动化验证工具\`（项目代码权威源，禁止依赖 AppData 工作区）

## Release 索引
- P1：ui-toolbox-P1-20260916（P1 契约+环境适配层）
- P1 patch 1：ui-toolbox-P1-patch1-20260917（字符串字面量复核，误报确认）
详见 RELEASE_NOTES_INDEX.md

## 相关文档链接
- 架构设计 v3：`02-architecture/本地离线自动化测试_修订版架构设计_v3.md`
- MIGRATION：`04-implementation/P1-contracts-env-adapter/MIGRATION.md`
- GitHub：https://github.com/loveyueyaya/automation-verification-tool
