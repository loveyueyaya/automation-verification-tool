# 04-implementation - 代码实现

## 用途
项目代码权威源目录。**P2-2 起分两个目录**：`P2-layers/` 为七层骨架目标位置（contracts 横切 + 各层），
`P1-toolbox-legacy/` 为 P1 遗留目录（scripts / tests / 证据 / MIGRATION.md + contracts shim），逐步腾空。

## 内容清单
- **P2-layers/contracts/** — 契约层（横切区，不按层分配）：enums / flow / models / stable_id / state_hash / validators / errors / version
  - P2-2 由 `git mv` 从 P1 迁入（保留 git 历史）；`state_hash.py` / `stable_id.py` / `models.py` / `enums.py` 按架构 v3.2 必修 1 留在 contracts
- **P2-layers/env_adapter/** — 层2 环境适配：env_probe / env_cache / input_router / capture_router / focus_manager / fallback_policy
  - P2-2 整目录 git mv 迁入；实测当前**零引用**（BUG-2，留待 P2-2 后续处理）
- **P1-toolbox-legacy/contracts/__init__.py** — 迁移 shim（方案 B）：不含实现，
  用 `sys.modules` 替换把 `contracts` 指向 `P2-layers/contracts`，旧 import 写法零改动
  - 删除时机：7 步法第 7 步（所有调用方 import 改到新路径后）
- P1-toolbox-legacy/contracts/ — 契约层（enums / flow / models / stable_id / state_hash / validators / errors / version）
- P1-toolbox-legacy/env_adapter/ — 环境适配层（env_probe / env_cache / input_router / capture_router / focus_manager / fallback_policy）
- P1-toolbox-legacy/scripts/ — 脚本（env / locate / uitool / timeline / shot / cache / ocr / sendinput）
- P1-toolbox-legacy/tests/ — 56 个单测（test_rebuild_equiv / test_select_flow / test_stable_id / test_state_hash）
- P1-toolbox-legacy/timeline/ — 时间线会话记录（shots 截图）
- P1-toolbox-legacy/evidence/ — 重建与审计证据（compare_pyc / diff_pyc / full_dis_out.txt / 审计日志）
- P1-toolbox-legacy/MIGRATION.md — 迁移说明与已知偏差
- P1-toolbox-legacy/自查报告.md — P1 自查报告

## 相关文档
- 01-requirements/（需求）、02-architecture/（架构）、05-tests/（验收证据）


> **2026-09-19 19:5x 收尾完成**：#1 调用方 import 已指向 P2-layers（7 文件，含 UITOOL_CONTRACTS_SOURCE=p1/p2 flag）｜#2 shim 已删｜#3 本目录改名 P1-toolbox-legacy｜#4 restore_p1_shim.py + flag 闭环已验证｜#5 BUG-2 接线（uitool see → env_profile 入审计）+ BUG-4 修复（FRAMEWORK_RULES 声明式）。全程 56 单测 5 次全绿。已随提交 `028ffc2` 推送（文档笔 `f2bf819`、取证笔 `a580e75`，远端 main = a580e75）。`timeline\_test_bug2\` 为 BUG-2 接线的实跑验证证据。
