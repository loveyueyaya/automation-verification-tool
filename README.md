# 自动化验证工具 - 项目总说明

## 项目定位（一句话）
本地离线运行的 UI 自动化验证工具箱：感知层输出 target_hwnd、动作层强制 locate（拒绝裸坐标）、审计层记录"坐标来源+置信度+回退链"，三层自动闭环（失败→诊断→重试），全程可回放、可审计、可对比基线。

## 目录结构（00~10）

| 目录 | 内容 |
|---|---|
| 00-doubao-llm-prerequisites | AI 技能前置文件（五技能权威源：local-dev-environment / parallel-serial-decider / cache-manager / feedback-logger / computer-use-automation） |
| 01-requirements | 需求分析（需求规格 v0.1~v0.3 + `env-report/` 运行环境报告） |
| 02-architecture | 架构设计（v3 / v3.1 / v3.2） |
| 03-detailed-design | 详细设计（v1 / v1.1） |
| 04-implementation | **代码实现**：`P1-contracts-env-adapter/`（scripts 8 + tests 4 + evidence + MIGRATION/SKILL/自查报告）、`P2-layers/`（contracts 9 + env_adapter 7，P2-2 分层迁移产物） |
| 05-tests | 测试与验收证据（P1 验收证据 + P2-1/P2-2 验收报告 + 验收证据包） |
| 06-deployment | 部署与发布（RELEASE_NOTES 索引与说明、P1-patch1 说明、pyc 重建备份） |
| 07-operations | 运维（仓库同步脚本 07-operations/git-sync.ps1 / 07-operations/sync-to-github.bat；运维文档待填充） |
| 08-review-logs | 审查日志（含误报/分歧案例库） |
| 09-feedback | 反馈日志（timeline 事件流 + 日报 + 遗留问题 issues 001~003） |
| 10-env-baseline | **环境地基与事故证据**（env-baseline_v1 / pip 快照 / 4 份 09-19 报告 / `_tools/` 取证工具 / `_evidence/` 原始输出） |
| 11-management | **项目管理与规划**（交接文档、阶段进度表、开发前盘点 v2、10 轮任务规划） |

> 目录约定：编号目录 00~11 各司其职，**根目录仅保留 README.md 与 LICENSE**（GitHub 要求的两个文件）；其余文档一律归入对应编号目录，各目录均以 `*-index.md` 自述内容清单。

## 当前阶段（2026-09-19）

- **P1 已封板**：56/56 单测通过 + pyc 备份 + tag `ui-toolbox-P1-20260916`（补丁 tag `ui-toolbox-P1-patch1-20260917`）。
- **P2-1 已完成**：OpenCV 收敛为 2 包（`opencv-python` + `opencv-contrib-python`，均 4.10.0.84）、显存监控改 pynvml、BUG-1（区域截图）与 BUG-3（OCR 单例）已修。
- **P2-2 已完成**：contracts / env_adapter 分层迁移至 `04-implementation/P2-layers`（P1 侧留 shim，56 单测全绿）。
- **环境事故已处置**：site-packages 包文件批量丢失 → 根因定位（工具层删除逐个进回收站 → 大包卸载超时被强杀 → 包半删）→ 覆盖法修复 + 损失评估（结论：不恢复）→ 环境全面检测（Win32 API 46 项 0 失败、23 库功能全通过）。
- **状态：开发暂停中**，等待用户指示再开工。

## 权威源位置与硬规则

- 项目权威源：`F:\自动化验证工具\`（**禁止**依赖 AppData 副本）
- **绝对规则**：一切判断建立在本地代码的真实执行结果上；文件/包存在性只用执行验证；先取证再动手；破坏性操作必须可回滚。
- **高危操作禁令**：不在本环境对大包执行 `pip uninstall` / `pip install --force-reinstall`（删除经 `genie-trash` 逐个进回收站，实测 47~126 ms/文件、比 `cmd del` 慢 64~170 倍，必然超时被强杀）；修环境一律用「覆盖法」。
- 详见 `10-env-baseline/env-incident_20260919_root-cause.md` 与技能 `local-dev-environment/SKILL.md`。

## Release 索引

- P1：`ui-toolbox-P1-20260916`（P1 契约+环境适配层）
- P1 patch 1：`ui-toolbox-P1-patch1-20260917`（字符串字面量复核，误报确认）

详见 `06-deployment/RELEASE_NOTES_INDEX.md`（含 2026-09-19 目录整理注记）。

## 相关文档链接

- 架构设计 v3.2：`02-architecture/架构设计_v3.2.md`
- 详细设计 v1.1：`03-detailed-design/详细设计_v1.1.md`
- 迁移记录：`04-implementation/P1-contracts-env-adapter/MIGRATION.md`
- 环境地基：`10-env-baseline/env-baseline_v1.md`
- 根因取证：`10-env-baseline/env-incident_20260919_root-cause.md`
- GitHub：https://github.com/loveyueyaya/automation-verification-tool
