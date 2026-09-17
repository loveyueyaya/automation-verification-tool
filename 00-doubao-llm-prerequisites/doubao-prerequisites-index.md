# 00-doubao-llm-prerequisites - 豆包技能前置文件

## 用途
存放豆包 AI 与本项目配套的技能定义与调度规则。本目录是 local-dev-environment（本地开发环境）与 parallel-serial-decider（并行/串行判定）两个技能的权威源。

## 内容清单
- .user_skills/local-dev-environment/ — 本机开发环境技能（工具链绝对路径 + 标准工作流 + 阶段封板流程）
- .user_skills/parallel-serial-decider/ — 并行/串行判定技能（R1-R23 规则表 + 决策日志 + 临时缓存 + 回滚协议）

## 相关文档
- AppData 侧 `.user_skills` 是本目录的 junction 符号链接（同一份文件，C 盘跳转 F 盘）
- local-dev-environment/SKILL.md 含"阶段封板流程"与"任务并行/串行规则"硬规则
