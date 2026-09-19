# 00-doubao-llm-prerequisites - AI 协作技能权威源

## 用途
存放与本项目配套的**全部 AI 技能**（SKILL.md + 配套脚本）的权威源。模型每轮对话自动加载技能，加载目录为 `C:\Users\Administrator\.workbuddy\skills\`（**实体目录副本，非 junction** —— 2026-09-19 实测）。**改本目录后必须同步到 AppData 才在下一轮生效**：用 `10-env-baseline\_tools\sync_skills.py` 同步并 SHA256 逐文件校验。

## 内容清单（逐文件）

### 根
| 文件 | 作用 |
|---|---|
| `doubao-prerequisites-index.md` | 本目录索引（含缓存位置说明与变更记录） |

### .user_skills\（六技能）
| 文件 | 作用 |
|---|---|
| `SKILLS_INDEX.md` | 六技能职责矩阵（用途 / 职责边界 / 依赖 / 加载方式 / SHA256 校验口径） |
| `cache-manager\SKILL.md` | 临时缓存/快照技能：可回滚安全操作（git 写操作前、目录移动前、改配置前必建快照；大删除须先建快照且超时放大） |
| `cache-manager\scripts\make_cache.py` | 快照工具：`--task --paths` 建快照、`--list` 列出、`--clean --days N` 清理；`CACHE_ROOT` 硬编码为 `.user_skills\cache-manager\temp-cache\`（唯一权威缓存根，别处不存在第二份） |
| `cache-manager\temp-cache\` | 快照存放处（自身 `.gitignore` 忽略，不入库；当前 13 份，每份含 snapshot/ + git_state.txt + manifest.json + restore.ps1） |
| `computer-use-automation\SKILL.md` | Windows 桌面 GUI 自动化技能（计算器/设置/文件选择器等本机应用操作，平面=cu） |
| `feedback-logger\SKILL.md` | 反馈日志技能：三层锚点时间戳 v3 + timeline.jsonl 事件流 + 日报模板 |
| `feedback-logger\scripts\log_event.py` | 事件流写入工具（追加一条 JSON 到 timeline.jsonl） |
| `github-remote\SKILL.md` | GitHub 远程操作技能（api / 仓库 / Release） |
| `github-remote\.credentials\github_token` | PAT 凭证（已被根 .gitignore 忽略，不入库，AppData 侧无副本；当前 classic PAT 可用，**建议后续收敛为仓库级 fine-grained 最小权限**——现含 delete_repo 偏大） |
| `local-dev-environment\SKILL.md` | 本机开发环境技能：工具链绝对路径 + 标准工作流 + 阶段封板流程（tag+Release）+ 索引维护硬规则 + **平台实测坑 A-E**（PowerShell stdout 不回传 / 中文 GBK / Bash coreutils 缺失 / 裸 python=3.13.12 / pip 钉子防漂移） |
| `local-dev-environment\references\environment.md` | 环境完整参考（各工具版本/路径/常用命令） |
| `local-dev-environment\scripts\env_check.py` | 工具链版本检测脚本（可直接执行） |
| `parallel-serial-decider\SKILL.md` | 并行/串行判定技能（R1-R23 规则表；所有多任务调度统一归口，其他技能不再内嵌） |
| `parallel-serial-decider\decision-log\decisions.jsonl` | 决策日志（机器读，append-only；09-19 起为**单一权威源**，根目录旧副本已并入） |
| `parallel-serial-decider\log.txt` | 决策日志**可读镜像**（与 jsonl 双写，改脚本必须保持同步） |
| `parallel-serial-decider\scripts\log_decision.py` | 决策日志写入工具（一次调用双写 jsonl + log.txt） |

## 缓存位置说明
- 临时缓存根（**唯一**）：`.user_skills\cache-manager\temp-cache\`（硬编码于 make_cache.py；2026-09-19 已合并 AppData 侧遗留副本）
- 2026-09-19 18:48 已清理其他对话遗留快照 `20260919_181801`（46 文件/0.3MB，源内容全在 git）

## 相关文档 / 硬规则（必读）
- **绝对规则（用户 2026-09-19 裁定，已写入 SOUL.md 与 local-dev-environment/SKILL.md）**：一切判断基于本地代码真实执行结果；先取证再动手；破坏性操作必须可回滚（修环境用覆盖法，**禁用 pip --force-reinstall / 大包 pip uninstall**——本机实测会超时被强杀导致包半删）；用户的话也是待验证输入；版本问题查官方手册、不涉及被调用 API 不升级
- **`.skills` 系统技能目录（108 官方技能）会清理非官方内容，禁止放自定义技能镜像**（2026-09-17 实测；junction 更危险，被清时递归删权威源）
- 环境地基清单：`10-env-baseline\env-baseline_v1.md`；pip 安装前快照：`10-env-baseline\pip_before_20260918.txt`

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-19 | 六技能复验同步（SKILL.md SHA256 两边一致）；junction 更正为实体目录副本；缓存根归并唯一；绝对规则落盘；新增本机删除高危禁令 |
| 2026-09-19 | 决策日志单一权威源（根目录 `决策日志/` 并入后移除）；log_decision.py docstring 修正 |
| 2026-09-19 18:5x | 本 index 重写为逐文件粒度（新模型可读性工程）；补 github-remote 技能与凭证说明、temp-cache 清理记录 |
