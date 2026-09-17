# 00-doubao-llm-prerequisites - 豆包技能前置文件

## 用途
存放豆包 AI 与本项目配套的技能定义与调度规则。本目录是 local-dev-environment（本地开发环境）、parallel-serial-decider（并行/串行判定）、feedback-logger（反馈日志）、cache-manager（临时缓存管理）四个技能的权威源。

## 内容清单
- .user_skills/local-dev-environment/ — 本机开发环境技能（工具链绝对路径 + 标准工作流 + 阶段封板流程 + 索引维护规则）
- .user_skills/parallel-serial-decider/ — 并行/串行判定技能（R1-R23 规则表 + 决策日志 + log.txt 可读镜像 + 回滚协议，缓存已移交 cache-manager）
- .user_skills/feedback-logger/ — 反馈日志技能（三层锚点时间戳 v3 + timeline.jsonl 事件流 + 日报模板）
- .user_skills/cache-manager/ — 临时缓存管理技能（make_cache.py 创建/列出/清理 + restore.ps1 回滚）
- .user_skills/SKILLS_INDEX.md — 四技能职责矩阵（用途 / 职责边界 / 依赖 / 加载方式）

## 缓存位置说明
- 临时缓存根：`.user_skills\cache-manager\temp-cache\`（2026-09-17 起统一归 cache-manager 管理，含从 parallel-serial-decider 迁移的 5 个历史缓存）
- 缓存目录内有自身 `.gitignore`（`*`），git 不会跟踪

## 相关文档
- AppData 侧 `.user_skills` 是本目录的 junction 符号链接（同一份文件，C 盘跳转 F 盘）——**这是豆包实际加载技能的目录，每轮对话自动注入**
- **`.skills` 系统技能目录（108 个官方技能）会被系统清理非官方内容，不可用于自定义技能镜像**（2026-09-17 实测：复制镜像数分钟内被清；junction 更危险，被清时递归删除权威源）
- local-dev-environment/SKILL.md 含"阶段封板流程"与"索引维护"硬规则；并行/串行判定统一见 parallel-serial-decider（v2.0 不再内嵌）
