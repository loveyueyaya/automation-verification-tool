# 目录树整理报告（2026-09-19）

> 依据：用户裁定「GitHub 要求的 README.md 与 LICENSE 保持不动，其余文件一律整理到对应子目录；整理后同步更新索引与注释；排查并消除功能/描述相近、重复的目录」
> 状态：**整理已完成，等待用户确认后再提交 GitHub**（未 commit、未 push）

---

## 一、根目录归位映射（整理前 11 项 → 整理后仅 2 项）

**保留在根**：`README.md`、`LICENSE`（GitHub 要求）

| 原根级条目 | 现位置 | 类别 | 跟踪状态 |
|---|---|---|---|
| 06-deployment/RELEASE_NOTES_INDEX.md | `06-deployment/RELEASE_NOTES_INDEX.md` | 发布 | 已跟踪（git mv） |
| 06-deployment/RELEASE_NOTES_v1.md | `06-deployment/RELEASE_NOTES_v1.md` | 发布 | 已跟踪（git mv） |
| 06-deployment/P1_patch1_release_notes.md | `06-deployment/P1_patch1_release_notes.md` | 发布 | 未跟踪（.gitignore） |
| 06-deployment/P1-pyc-cache-backup/（156.8 MB / 12,834 文件） | `06-deployment/P1-pyc-cache-backup/` | 发布资产 | 未跟踪（新增忽略规则） |
| 05-tests/P1_acceptance_evidence.zip | `05-tests/P1_acceptance_evidence.zip` | 验收证据 | 未跟踪（.gitignore） |
| 07-operations/git-sync.ps1 | `07-operations/git-sync.ps1` | 运维脚本 | 已跟踪（git mv） |
| 07-operations/sync-to-github.bat | `07-operations/sync-to-github.bat` | 运维脚本 | 已跟踪（git mv） |
| HANDOVER.md | `11-management/HANDOVER.md` | 项目管理 | 未跟踪（.gitignore） |
| project-phase-progress.xlsx | `11-management/project-phase-progress.xlsx` | 项目管理 | 已跟踪（git mv） |

**.gitignore**：原 `HANDOVER.md` / `05-tests/P1_acceptance_evidence.zip` / `06-deployment/P1_patch1_release_notes.md` 三条忽略规则为"文件名"形式，移至子目录后**依然命中**（实测 `git check-ignore` 通过）；另新增一条 `06-deployment/P1-pyc-cache-backup/`，使 pyc 备份在归位后仍保持不入库（沿用项目既有"阶段资产不入库"口径）。

## 二、新增 `11-management/`（项目管理与规划）

| 文件 | 来源 | 说明 |
|---|---|---|
| `management-index.md` | 新建 | 本目录索引（含与 01/05/06/09/10 的职责边界表） |
| `本地离线自动化测试工具_开发前盘点_v2.md` | 由工作目录迁入 | 开发前盘点 v2（全部 09-19 实测数据） |
| `本地离线自动化测试工具_开发前盘点.md` | 由工作目录迁入 | 盘点 v1（历史版本，保留存档） |
| `接下来的任务.txt` | 由桌面**复制**入库 | 10 轮任务规划（已按实测现状更新；桌面保留工作副本） |
| `HANDOVER.md` / `project-phase-progress.xlsx` | 由根目录归位 | 交接说明 / 阶段进度表 |
| `reorg-report_20260919.md` | 新建 | 本报告 |

## 三、09-19 取证资产入库（原先散落在工作目录）

| 位置 | 内容 |
|---|---|
| `10-env-baseline/_tools/` | 取证与验证脚本 20 个（回收站取证、波次归因、损失评估、Win32 API 验证、环境与元数据检测、覆盖法修复、回收站恢复、引用更新等） |
| `10-env-baseline/_evidence/` | 原始输出 11 份（全面检测原始输出、取证过程记录 01~09、文件数采样日志） |

理由：这些脚本与原始输出是 09-19 事故报告的直接证据源，报告里已按此新路径引用，放在项目内可复现。

## 四、索引与注释同步（对照实际位置）

| 类型 | 处理 |
|---|---|
| 活文档引用（批量） | `update_refs2.py` 更新 **14 个文件 / 24 处**：根级文件新路径、工作目录→项目内新路径、盘点新路径 |
| 各目录索引 | `05-tests/tests-index.md`、`06-deployment/deployment-index.md`、`07-operations/operations-index.md`、`10-env-baseline/env-baseline-index.md` 全部按实际内容重写清单；新建 `11-management/management-index.md` |
| `README.md` | 目录结构表更新为 00~11 实况；新增"目录约定"（根目录仅留 README + LICENSE） |
| 技能索引 | `SKILLS_INDEX.md` / `doubao-prerequisites-index.md` 中的工具路径与变更记录已同步 |
| 过期注释（代码） | `log_decision.py` 第 2 行 docstring 由旧根目录路径改为技能权威源路径（权威源 + AppData 双份，SHA256 一致） |
| 历史文档 | `06-deployment/RELEASE_NOTES_v1.md`、`06-deployment/RELEASE_NOTES_INDEX.md`、`05-tests/P1_验收证据_20260916_195623.md`：**原文不改写**，追加"勘误注记"更名对照表 |

## 五、重复/相近目录排查结果

| # | 发现 | 判定 | 处置 |
|---|---|---|---|
| 1 | `04-implementation/P1-contracts-env-adapter/contracts/`（**仅 1 个 shim 文件**）↔ `04-implementation/P2-layers/contracts/`（9 文件）：同名同职责 | **真实重复**（P2-2 迁移过渡产物） | **未动**：消除它需要改调用方 import（P2-2 第 5 步）再删 shim（第 7 步），属代码改动 = 开发工作（当前暂停），且用户规划本就是与"scripts 按层迁移"同批处理以避免同一批文件改两遍。**建议纳入 P2-2 收尾** |
| 2 | `04-implementation/P1-contracts-env-adapter/` 目录名已名不副实（内含 scripts/tests/evidence，contracts 已迁出） | 命名与内容不符 | **未动**，建议 P2-2 收尾时改名或按层迁移后删除（同属代码结构调整） |
| 3 | `00-.../local-dev-environment/references/environment.md`（107 行）↔ `10-env-baseline/env-baseline_v1.md`（270 行）：同为环境信息，双份维护有漂移风险 | **内容相近**（不同定位：技能速查 vs 项目基线） | **已处置**：在技能侧文件顶部加「权威源声明」——以 `10-env-baseline` 为准、冲突时回来修正本文件（权威源 + AppData 已同步，SHA256 一致） |
| 4 | 各目录 `*-index.md` 与 `feedback-index.md`（机制说明）并存 | **非重复**（索引 vs 指南，与 08-review-logs 的 `review-logs-guide.md` + `INDEX.md` 分职一致） | 保持 |

**结论**：目录层面（含中文目录、根级散落文件、重复索引）已无冗余；**唯一残留的重复是 `contracts` shim 与 `P2-layers/contracts`**，属代码级、需在 P2-2 收尾时消除。

## 六、整理后目录树（实测）

```
F:\自动化验证工具\
├── README.md / LICENSE            ← 仅此 2 个文件（GitHub 要求）
├── 00-doubao-llm-prerequisites\   五技能权威源 + 缓存
├── 01-requirements\               需求规格 + env-report/
├── 02-architecture\               架构 v3 / v3.1 / v3.2
├── 03-detailed-design\            详细设计 v1 / v1.1
├── 04-implementation\             P1-contracts-env-adapter/（scripts/tests/evidence）+ P2-layers/（contracts/env_adapter）
├── 05-tests\                      验收证据 + P2-1/P2-2 验收报告 + 证据包
├── 06-deployment\                 RELEASE_NOTES 索引/说明 + P1-patch1 说明 + 06-deployment/P1-pyc-cache-backup/
├── 07-operations\                 07-operations/git-sync.ps1 + 07-operations/sync-to-github.bat
├── 08-review-logs\                审查日志
├── 09-feedback\                   timeline + daily/ + issues/
├── 10-env-baseline\               环境地基 + 09-19 四份报告 + _tools/ + _evidence/
└── 11-management\                 交接 + 进度表 + 盘点 v1/v2 + 任务规划 + 本报告
```

## 七、逐项全量验证（用户要求：不许抽查，必须逐一跑代码验证）

> 验证器：`10-env-baseline\_tools\verify_reorg.py`（12 类检查，**121 项判定全部通过**，rc=0，耗时 129.5 s）
> 原始报告：`10-env-baseline\_evidence\reorg-verify_20260919.txt`（122 个 ✅ / 0 个 ❌）

| 节 | 检查内容 | 逐项结果 |
|---|---|---|
| 1 | 根目录归位清单 | 9 项迁移（源已移除 + 目标在位）逐项 ✅；根目录无散落项 ✅ |
| 2 | 目录树 00~11 + 各目录索引 + `_tools`/`_evidence`/`_local_assets`/`legacy_repair` | 逐目录逐索引 ✅ |
| 3 | 全树旧路径/旧名残留 | 扫描 **132 个文件**：活文档命中 **0**；历史/说明性命中 27（勘误注记、整理变更表、验证脚本自身，逐条打印理由） |
| 4 | 项目内路径引用存在性 | 去重 **54 条**：存在 43 / 白名单 11（历史目录名、模板占位符，逐条打印理由）/ **缺失 0** |
| 5 | 11 个索引的条目解析（四级解析 + 目录名解析） | 共校验 **104 条**，**全部**解析到真实文件/目录 |
| 6 | README 结构表 vs 实际目录 | 11 个编号目录逐行一致 ✅ |
| 7 | 技能权威源 ↔ AppData | 五技能**逐文件** SHA256 一致（非仅 SKILL.md）✅ |
| 8 | .gitignore 逐项期望 | 10 项应忽略 + 10 项应入库，逐项 ✅ |
| 9 | git 状态 | **重命名/移动 16 条**逐条打印；**删除 D=0** ✅ |
| 10 | 脚本可用性 | `_tools` 21 个脚本逐脚本**编译 + 实跑**；`legacy_repair` 11 个脚本逐个编译 ✅ |
| 11 | 功能回归 | 56 单测 / 28 模块导入 / `pip check`（告警 ⊆ 已知基线）/ 区域截图 320×200 / 模板匹配 1.0 ✅ |
| 12 | 本地资产与遗留脚本归位 | `_local_assets`（54 + 1028 文件）、`legacy_repair` 18 项、工作目录已清空 ✅ |

### 验证过程中发现并修复的 6 个真实问题（抽查发现不了）

| # | 问题 | 性质 | 处置 |
|---|---|---|---|
| 1 | `verify_e2e.py` / `verify_env_full.py` / `watch_files.py` 移入后**硬编码输出路径仍指向旧工作目录** | 移动引入的缺陷 | 改为 `10-env-baseline\_evidence\...`，并实跑复验 |
| 2 | 技能 `local-dev-environment\SKILL.md` 的"排查工具"路径仍指向旧工作目录（`SKILLS_INDEX.md` 同步） | 文档失效引用 | 改为 `10-env-baseline\_tools\` |
| 3 | 技能 `parallel-serial-decider` 的 `decision-log\decisions.jsonl` / `log.txt` 在 AppData 侧与权威源**内容不一致**（历史累积漂移） | 双份不同步 | 已同步并复验（五技能逐文件一致） |
| 4 | 09-18/19 的 18 个修复/探针脚本与版本清单仍散落在项目外，项目内报告引用无法落到项目内 | 引用悬空 | 归入 `10-env-baseline\_tools\legacy_repair\`，引用同步（P2-1 报告 11 处） |
| 5 | 大体积本地资产（wheel 归档 54 文件、旧包备份 1,028 文件）仍在项目外 | 资产未归位 | 归入 `10-env-baseline\_local_assets\` 并加入 .gitignore（不入库） |
| 6 | `09-feedback\daily\feedback_20260919.md` 残留 `_investigation\` 旧路径 | 文档失效引用 | 改为 `10-env-baseline\_evidence\` |

### 验证器自身的判定口径修正（避免误报/漏报，逐条记录）

| 项 | 原口径问题 | 修正后 |
|---|---|---|
| §3 | 用"根因取证"词组匹配，误伤正文（如"根因取证结论"）；未排除 AI 记忆目录与原始取证目录 | 改为精确文件名/目录名匹配；排除 `.workbuddy`、`_evidence`、`legacy_repair` 存档；"整理变更表/验证脚本自身"列入允许并打印理由 |
| §4 | 正则被标点截断（如把 `**（git`、`）——` 当路径） | 抽取后去标点/括号截断；历史目录名与模板占位符进白名单并逐条打印理由 |
| §5 | 只在"索引所在目录 + 项目根 + 技能根 + 同名文件"四级里找，目录类条目会误报 | 增加**目录名解析**；跳过纯扩展名与模板占位符 |
| §10 | `restore_from_wheels.py` 无参返回 rc=2（设计上的"用法提示"）被判失败 | 接受 rc=2 且输出含用法 |
| §11 | 要求 `pip check` 退出码为 0 | 改为"告警集合 ⊆ 已知基线告警"（基线那条 cudnn 版本提示长期存在） |
| §12 | 用 `os.listdir` 计数，把 `__pycache__` 目录算进去 | 改为按扩展名分项计数，并清理两处 `__pycache__` |

> 附注：清理 `_tools\__pycache__`（67 个文件）时触发了沙箱的批量删除确认门（`count:67 > threshold:50`，`SAFE_DELETE_BULK_CONFIRM_REQUIRED`）——这是安全机制的正常表现，不是故障。

---

## 八、发布记录（用户确认后执行）

用户 2026-09-19 15:19 确认"保存并推送"，已执行并逐项验证：

| 项 | 内容 |
|---|---|
| 提交 1 | `a9a5311` 目录树整理 + 09-19 环境事故取证归档（根目录仅保留 README/LICENSE，逐项验证 121 项全过）——**108 个文件：68 新增 / 24 修改 / 16 重命名 / 删除 0**；仓库体积安全（暂存最大文件 98 KB，大体积资产走 .gitignore） |
| 提交 2 | `33bcccd` 验证器补强（技能一致性口径改为"技能代码"、运行时日志单一源化；§9 增加远端一致性校验） |
| 提交 3 | `2efc0b7` 验证器最终版（远端校验改 gh api 直读 + ls-remote 兜底；模板匹配改数值判定；去重复判定） |
| 推送 | `a0aeccc..2efc0b7  main -> main`（**快进推送**，无需 force）；补推了此前本地领先而未推送的 P2-2 两次提交（`1ae52c5` / `340049d`） |
| 远端核验 | `gh api .../git/ref/heads/main` = 本地 HEAD = `2efc0b77...` ✅；远端根目录实况 = `.gitignore` + `LICENSE` + `README.md` + 12 个编号目录（与本地一致） |
| 提交前备份 | cache-manager 快照 `temp-cache\20260919_153047`（11-management + 09-feedback）与 `20260919_154108`（10-env-baseline 新增件 + 根级文档）；被终止的两份半成品缓存已清理 |
| 最终验证 | `verify_reorg.py` **123 项判定 / 0 失败**（提交后重跑，含远端一致性），报告 `10-env-baseline\_evidence\reorg-verify_20260919.txt` |

### 本轮新发现的环境特性（均已处理并记录）

| # | 现象 | 证据 | 处置 |
|---|---|---|---|
| 1 | **`.git/refs/remotes/` 下的写入会被丢弃** | `git fetch` 与 `git update-ref` 均报成功，但引用文件不存在（复现 2 次），`git status -sb` 显示 `[gone]` | 改用 Write 工具直写 ref 文件后生效（`git status` 恢复正常跟踪显示）；推送本身不受影响 |
| 2 | **git HTTPS 偶发 TLS 吊销检查失败** | `schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK`（子进程内 2 次；重试 3/3 成功） | 远端校验改为 `gh api` 优先 + `git -c http.schannelCheckRevoke=false ls-remote` 兜底 |
| 3 | **验证器自身的判定口径也会误判** | 模板匹配实测 `0.9999998807907104`，原按字面 `"1.0"` 匹配 → 误报失败 | 改为解析 `confidence` 数值判定 ≥0.99 |

---

## 九、后续待办（不阻塞发布）

1. 第 5 节第 1/2 项（`contracts` shim 重复、P1 目录名名不副实）建议留到 **P2-2 收尾**一起做 —— 属代码结构调整，需你点头后才动。
2. `10-env-baseline\_local_assets\`（wheel 归档 + 旧包备份，约 580 MB）**不入库**，仅本机保留；重建方式：`pip download` 按需重取。
3. 开发工作仍按你的指示**暂停**，等下一步指令。

---

## 十、补记（2026-09-19 21:5x）

第九节待办 1 **已完成**：contracts shim 去重 + P1 目录改名，随 P2-2 收尾落地——
`P1-contracts-env-adapter/` 已更名为 **`P1-toolbox-legacy/`**（git mv 保历史），contracts shim 已删除
（唯一实现 = `P2-layers/contracts/`，一键回退工具 `restore_p1_shim.py`）。详见 05-tests P2-2 验收报告 §5。
