# 09-feedback - 反馈日志（问题/解决/遗留/事件流）

## 用途
记录每轮 AI 工作遇到的问题、解决方式、遗留项、不清晰点；`timeline.jsonl` 为全项目事件流（append-only）。本目录 = 过程记录；"当前状态"以 `11-management\接下来的任务.txt` 为准。

## 逐文件说明

| 文件 | 作用 |
|---|---|
| `INDEX.md` | 反馈日志索引（本文件：日报一览 + 遗留问题清单） |
| `feedback-index.md` | **反馈日志机制说明**：目的/触发时机/命名规范/时间戳规则 v3（三层锚点）/日报模板/技能位置——"怎么做事"看这个 |
| `timeline.jsonl` | 事件流，append-only，每行一条 JSON（ts/ts_source/type/subject/evidence/action/result/git_commit）；写入用 feedback-logger 技能的 `log_event.py` |
| `daily\feedback_20260916.md` | 09-16 日报：P1 开发+重建（问题 5 / 解决 4 / 遗留 1） |
| `daily\feedback_20260917.md` | 09-17 日报：P1 复核+补丁（问题 3 / 解决 3 / 遗留 0） |
| `daily\feedback_20260919.md` | 09-19 日报：P2-1 修复、P2-2 迁移+**收尾 5 项闭环**、清理 CPU 版 paddle、环境全检、**文件丢失根因取证**、目录整理、凭证落地、**晚间会话：index 逐文件化+目录消失事件+恢复+SACL 加固**（§6，system 锚点即时写入，最完整的一天） |
| `issues\issue_001_pyc_cache_dir.md` | 遗留 001：中文目录导致 GitHub URL 编码失败 —— **已解决**（目录全英文化） |
| `issues\issue_002_site-packages-file-loss.md` | 遗留 002：site-packages 包文件批量丢失 —— **根因已定位**（genie-trash 回收站删除 × pip 强杀 → 包半删）；损失评估结论=不恢复（详见 `10-env-baseline\env-damage-assessment_20260919.md`） |
| `issues\issue_003_env-metadata-residue.md` | 遗留 003：环境元数据残留（C1 僵尸 opencv dist-info / C2 pynvml 元数据缺失）—— **已处置**（C1 删除、C2 回收站原样恢复；复验一致） |

## 日报一览

| 日期 | 主要任务 | 问题/解决/遗留 | 日报文件 |
|---|---|---|---|
| 09-16 | P1 开发+重建 | 5 / 4 / 1 | daily\feedback_20260916.md |
| 09-17 | P1 复核+补丁 | 3 / 3 / 0 | daily\feedback_20260917.md |
| 09-18 | 环境地基+审查日志+反馈机制+技能体系 | — | **daily\feedback_20260918.md 缺失，待补** |
| 09-19 | 修复+迁移+取证+整理+凭证 | 5 / 4 / 1 | daily\feedback_20260919.md |

## 相关文档
- 机制与时间戳规则：`feedback-index.md`（时间戳三层锚点 v3 必读：当前事件取系统时间、过往事件取文件三时间、无锚点标"不清晰"禁编造）
- 技能权威源：`00-doubao-llm-prerequisites\.user_skills\feedback-logger\`
