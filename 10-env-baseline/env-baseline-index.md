# 10-env-baseline - 环境地基基线

## 用途

存放本机开发环境地基基线的**证据与清单**：工具链版本、Python 包版本、可复现安装/卸载命令、验收证据、环境坑规避、未验证路径清单、pip 安装前快照（回滚依据）。

> 📌 **新模型快速入口**：当前环境"长什么样"读 `env-baseline_v1.md`（地基清单）；环境出过什么事读三份 09-19 报告（见下）；本目录 `_tools\` 里 40+ 脚本全部可独立复跑（`python 脚本名`，无需参数的占多数）。

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
- `env-verify_20260919.md` — **环境验证报告（2026-09-19）**：按要求清理 paddlepaddle CPU 版；实测取证并覆盖法修复包文件丢失事故（paddle/dxcam 整目录 + 14 包元数据 + 5 包部分文件 + comtypes.client/colorama.init 子模块）；对照《开发前盘点》§5.3 逐条代码验证（①②③④⑤⑥⑦⑧ 全通过）；偏差记录：屏幕分辨率经复验与基线一致（2560×1440；此前 3200×1440 系切屏瞬时读数，已更正）、C 盘剩余 109→72 GB
- `env-incident_20260919_root-cause.md` — **文件丢失根因取证报告（2026-09-19）**：删除经 `genie-trash` 逐个进回收站（审计事件 4663 实证）→ 实测 47~126 ms/文件 vs `cmd del` 0.74 ms/文件（慢 64~170 倍）→ 大包 `pip uninstall`/`--force-reinstall` 超时被强杀（`killed=true` 28 次，时刻与删除潮末点精确重合）→ 包半删（`~pkg` 残留）→ 5,187 文件缺失、5,186 可从回收站恢复（132.1 MB）。含取证手段、可复现工具清单、审计回滚命令与处置建议
- `env-damage-assessment_20260919.md` — **环境损失评估报告（2026-09-19，对照《开发前盘点》）**：项目源码树**零损伤**（P2-layers 16/16、tests 4/4 行数与基线一致；shot.py/ocr.py 差异为 P2-1 已知修复）；环境侧真实缺失 3,804 个中**核心文件仅 1 个**（opencv 5.0 遗留 ffmpeg DLL，与当前 4.10 无关），其余为 `.pyc` 3220（自动重建）/空目录条目 571/`.pyi` 6/`.txt` 4；44 个涉及包**全部可导入**；结论 **不恢复**（附可选动作与防复发硬规则）
- **审计保留（用户 2026-09-19 裁定）**：文件系统审核策略 + `C:\Program Files\Python313` 的 Delete SACL **长期保留**，用于后续同类事件的进程级归因
- `env-api-and-conflict-check_20260919.md` — **API 逐一验证 + 冲突/缺失/功能异常全面检测报告（2026-09-19）**：46 项 Win32 API 实跑（42 通过 / 4 仅解析 / **0 失败**，含 UIPI 判定链、DPI、消息注入无副作用实跑）；23 个 Python 库功能实跑全通过；3 个外部命令正常（nvidia-smi 147 ms vs pynvml 21 ms、WgcCapture.exe 缺失属已知）；冲突检测发现 C1 僵尸 `opencv_python-5.0.0.93.dist-info`、C2 `pynvml` 元数据缺失（详见 `09-feedback\issues\issue_003_env-metadata-residue.md`）；端到端 7 项全通过。原始输出 `F:\自动化验证工具\10-env-baseline\_evidence\10_env_full_check.txt`

## 2026-09-19 后置处置（用户批准）

| 项 | 处置 | 复验 |
|---|---|---|
| C1 僵尸 `opencv_python-5.0.0.93.dist-info` | 已删除（进回收站可回滚） | `pip list` 与 `importlib.metadata` 视图一致；`cv2 4.10.0` 正常 |
| C2 `nvidia-ml-py3 7.352.0` 元数据缺失 | 从回收站**原样恢复** 6 个文件（未下载 wheel，保证版本一致） | `pip list` 显示 `nvidia-ml-py3 7.352.0`；`pip check` 无新增告警 |
| 目录树整理 | 见下表 | 全树中文目录数 = 0；根目录仅 README.md + LICENSE |

### 本目录新增子目录（2026-09-19 归位）

| 子目录 | 内容 |
|---|---|
| `_tools/` | 本目录取证实效工具（**逐脚本已编译+实跑验证**）：`verify_reorg.py`（整理结果全量逐项验证，12 类检查）、`recycle_forensics.py`（回收站删除时间线）、`damage_check.py`（缺失判定）、`analyze_waves.py` / `attribute_waves.py`（波次归因）、`final_assessment.py` / `assess_damage.py` / `list_core_damage.py` / `verify_packages.py` / `sample_noext.py`（损失评估）、`verify_win32_api.py` / `probe_symbols.py`（API 验证）、`verify_env_full.py` / `check_metadata.py` / `verify_e2e.py`（环境与元数据检测）、`watch_files.py`（文件数采样）、`restore_from_wheels.py`（覆盖法修复）、`restore_from_recycle.py`（回收站恢复）、`update_refs.py` / `update_refs2.py` / `update_refs3.py` / `reorganize_root.py` / `reorganize_batch2.py` / `reorganize_batch3.py`（归位与引用同步） |
| `_tools/legacy_repair/` | 09-18~19 事故期的修复与探针脚本（保留可复现性），逐脚本：`_probe_step3.py`（盘点实测探针，只读）｜`probe_libs.py`（依赖实测性能，支撑复用/薄封装/自研决策）｜`probe_ocr_tuning.py`（OCR 误识别率量化 + 官方调优参数实测）｜`probe_uia_deep.py`（env_probe 耗时 + UIA 树深度遍历）｜`probe_uia_foreground.py`（前台窗口 UIA 遍历 + wujie 误判核查）｜`repair_env.py`~`repair_env5_autofix.py`（五轮覆盖式修复：wheel 补缺→CUDA DLL→dist-info 元数据→通用自愈，全程只补不删）｜`reorganize_batch2.py`（盘点v2/任务txt/取证工具归位）｜`p21`、`repair_env6`、`restore_cuda_and_test`、`restore_missing_dists`（无扩展名脚本：CUDA 恢复与元数据补齐）｜`_restore_reqs.txt` / `_repair_reqs.txt` / `_repair_small.txt`（版本清单） |
| `_evidence/` | 原始输出（**逐字证据，不改写**）：`10_env_full_check.txt`（全面检测原始输出）、`01_defender.txt` ~ `09_commands.txt`（取证过程原始记录）、`_watch_log.jsonl`（5 分钟文件数采样）、`reorg-verify_20260919.txt`（整理结果逐项验证报告） |
| `_local_assets/` | 本地大体积资产（**不入库**，见 .gitignore）：`_wheels/`（官方源 wheel 归档 54 文件，用于覆盖法修复）、`_backup_opencv_stale/`（旧版 opencv 包备份 1,028 文件） |

**目录树整理（2026-09-19）**：根目录 `决策日志/` 并入技能决策日志权威源后移除；`01-requirements/env-report/` → `env-report/`；`04-implementation/P1-contracts-env-adapter/evidence/` → `evidence/`；`07-operations/sync-to-github.bat` → `07-operations/sync-to-github.bat`；`11-management/project-phase-progress.xlsx` → `11-management/project-phase-progress.xlsx`；本目录 `env-incident_20260919_root-cause.md` → `env-incident_20260919_root-cause.md`。活文档引用已同步（24 处 / 14 个文件），历史文档（RELEASE_NOTES_v1 / 05-tests 验收证据）保留原文并加勘误注记。
**根目录归位（同日）**：`06-deployment/RELEASE_NOTES_INDEX.md` / `06-deployment/RELEASE_NOTES_v1.md` / `06-deployment/P1_patch1_release_notes.md` / `06-deployment/P1-pyc-cache-backup/` → `06-deployment/`；`05-tests/P1_acceptance_evidence.zip` → `05-tests/`；`07-operations/git-sync.ps1` / `07-operations/sync-to-github.bat` → `07-operations/`；`11-management/HANDOVER.md` / `11-management/project-phase-progress.xlsx` → `11-management/`。根目录仅保留 GitHub 要求的 README.md 与 LICENSE。

## 目录编号说明

- 原为 `08-env-baseline`，与既有 `08-review-logs` **编号冲突**，2026-09-18 经用户拍板改名 `10-env-baseline`
- 迁移方式：`git mv`（保留历史，未用复制）
- 同时把 `06-deployment\env-baseline_v1.md` 一并迁入本目录，使环境基线归位一处

## 相关文档

- 部署索引：`F:\自动化验证工具\06-deployment\deployment-index.md`（地基清单原在此，已迁出并注明）
- 技能索引：`F:\自动化验证工具\00-doubao-llm-prerequisites\doubao-prerequisites-index.md`
- 平台实测坑 A-E：`local-dev-environment` 技能 SKILL.md（权威源 + AppData 副本双份）
- 未验证路径的行动项：P3 smoke 必须含"关闭远程软件验证主路径"用例
