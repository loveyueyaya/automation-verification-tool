# 04-implementation - 代码实现

## 用途
项目代码权威源目录。当前为 P1 阶段产物：contracts 契约层 + env_adapter 环境适配层 + scripts 脚本 + tests 测试。

## 内容清单
- P1-contracts-env-adapter/contracts/ — 契约层（enums / flow / models / stable_id / state_hash / validators / errors / version）
- P1-contracts-env-adapter/env_adapter/ — 环境适配层（env_probe / env_cache / input_router / capture_router / focus_manager / fallback_policy）
- P1-contracts-env-adapter/scripts/ — 脚本（env / locate / uitool / timeline / shot / cache / ocr / sendinput）
- P1-contracts-env-adapter/tests/ — 56 个单测（test_rebuild_equiv / test_select_flow / test_stable_id / test_state_hash）
- P1-contracts-env-adapter/timeline/ — 时间线会话记录（shots 截图）
- P1-contracts-env-adapter/证据/ — 重建与审计证据（compare_pyc / diff_pyc / full_dis_out.txt / 审计日志）
- P1-contracts-env-adapter/MIGRATION.md — 迁移说明与已知偏差
- P1-contracts-env-adapter/自查报告.md — P1 自查报告

## 相关文档
- 01-requirements/（需求）、02-architecture/（架构）、05-tests/（验收证据）
