# 00-doubao-llm-prerequisites - 豆包技能前置文件

## 用途
存放豆包 AI 与本项目配套的技能定义与调度规则。本目录是 local-dev-environment（本地开发环境）、parallel-serial-decider（并行/串行判定）、feedback-logger（反馈日志）、cache-manager（临时缓存管理）四个技能的权威源。

## 内容清单
- .user_skills/local-dev-environment/ — 本机开发环境技能（工具链绝对路径 + 标准工作流 + 阶段封板流程 + 索引维护规则 + **平台实测坑 A-E**（2026-09-18 新增：PowerShell stdout 不回传 / 中文输出 GBK 解码失败 / Bash coreutils 缺失 / 裸 python 指向 3.13.12 / pip 钉子防漂移））
- .user_skills/parallel-serial-decider/ — 并行/串行判定技能（R1-R23 规则表 + 决策日志 + log.txt 可读镜像 + 回滚协议，缓存已移交 cache-manager）
- .user_skills/feedback-logger/ — 反馈日志技能（三层锚点时间戳 v3 + timeline.jsonl 事件流 + 日报模板）
- .user_skills/cache-manager/ — 临时缓存管理技能（make_cache.py 创建/列出/清理 + restore.ps1 回滚）
- .user_skills/SKILLS_INDEX.md — 四技能职责矩阵（用途 / 职责边界 / 依赖 / 加载方式）

## 缓存位置说明
- 临时缓存根（**唯一**）：`.user_skills\cache-manager\temp-cache\`（路径硬编码在 `make_cache.py` 的 `CACHE_ROOT`；2026-09-19 已把 AppData 侧遗留副本 `20260919_030131` 合并回此处）
- 缓存目录内有自身 `.gitignore`（`*`），git 不会跟踪

## 相关文档
- 技能加载目录：`C:\Users\Administrator\.workbuddy\skills\`（五技能每轮对话自动注入）
- **加载机制（2026-09-19 复验）**：AppData 侧与权威源**均为实体目录**（非 junction、非符号链接）。改权威源后**必须同步复制到 AppData**，并用 SHA256 逐文件校验一致才生效（校验命令见 `.user_skills\SKILLS_INDEX.md`）
- **绝对规则（用户 2026-09-19 裁定）**：一切判断必须建立在本地代码的真实执行结果上；文件/包是否存在只用执行验证（不得用 RECORD/README/索引描述替代）；先取证再动手；破坏性操作必须可回滚（修环境用覆盖法，禁用 `pip --force-reinstall`）。规则已写入 `SOUL.md` 与 `local-dev-environment/SKILL.md`
- **`.skills` 系统技能目录（108 个官方技能）会被系统清理非官方内容，不可用于自定义技能镜像**（2026-09-17 实测：复制镜像数分钟内被清；junction 更危险，被清时递归删除权威源）
- local-dev-environment/SKILL.md 含"阶段封板流程"与"索引维护"硬规则；并行/串行判定统一见 parallel-serial-decider（v2.0 不再内嵌）
- 环境地基清单：`F:\自动化验证工具\10-env-baseline\env-baseline_v1.md`（硬件/工具链/包版本/可复现安装命令/验收证据/P2-2 迁移顺序修正版 7 步）；安装前 pip 快照：`F:\自动化验证工具\10-env-baseline\pip_before_20260918.txt`

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-09-19 | 五技能全部复验同步（SKILL.md SHA256 两边一致）；更正 junction → 实体目录副本；缓存根归并为唯一路径；新增绝对规则 4 条 |
| 2026-09-19 | 新增规则：**用户的话也是待验证输入**；**版本问题查官方手册、不涉及被调用 API 则不做升级**；新增「本机删除高危特性与禁令」章节（大包 pip uninstall/--force-reinstall 会超时被强杀 → 包半删） |
| 2026-09-19 | **决策日志单一权威源**：根目录 `决策日志/` 已并入 `parallel-serial-decider/decision-log/decisions.jsonl` 与 `log.txt`（各 +1 行）后移除；修正 `log_decision.py` 第 2 行过期 docstring（原指向根目录旧路径），权威源与 AppData 副本 SHA256 校验一致 |

