# 技能索引（.user_skills）

权威源：`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\`
加载方式：AppData junction（`C:\...\workspace\.user_skills` → 指向本目录，每轮对话自动注入）

## 四技能职责矩阵

| 技能名 | 用途 | 职责边界 | 依赖 | 加载方式 |
|---|---|---|---|---|
| local-dev-environment | 本机工具链 + 封板流程 | 只提供环境信息和标准命令 | 无 | AppData junction |
| parallel-serial-decider | 并行/串行判定 | 只判定和写日志，不做缓存 | → cache-manager | AppData junction |
| cache-manager | 缓存/回滚 | 只做快照和恢复 | 无（被调用） | AppData junction |
| feedback-logger | 事件流记录 | 只记录，不判定 | 无 | AppData junction |

## 调用链

```
判定（parallel-serial-decider）→ 建缓存/回滚（cache-manager）→ 写日志（parallel-serial-decider 决策日志 + feedback-logger 事件流）
```
