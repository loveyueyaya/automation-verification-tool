---
name: cache-manager
description: "临时缓存/快照管理技能（可回滚安全操作）。当需要对可能改坏的操作建立可回滚的临时缓存、执行回滚、清理缓存、查看缓存列表时使用。触发场景：git 写操作（commit/push/mv/branch/reset/rebase）前、重命名/移动目录前、改 import/重构前、改配置前、用户说\"回滚\"/\"清理缓存\"/\"安全操作\"时。"
---

# cache-manager（临时缓存管理）

## 缓存根位置（权威源）

`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\cache-manager\temp-cache\<时间戳>\`

```
temp-cache/
└── <YYYYMMDD_HHMMSS>/
    ├── snapshot/       ← 完整复制指定路径（--paths）
    ├── git_state.txt   ← git branch / git log -1 / git status
    ├── manifest.json   ← 快照元数据
    └── restore.ps1     ← 一键恢复脚本（在缓存目录内执行）
```

## 何时创建缓存（触发条件）

以下任一命中，执行前必须建缓存：
- 策略是"谨慎"或"串行"（见 parallel-serial-decider 技能）
- 涉及 git 写操作（commit / push / mv / branch / reset / rebase）
- 涉及目录重命名、文件移动
- 涉及改 import / 重构
- 涉及配置修改
- 用户要求"安全操作"

## 工作流

### 1. 创建缓存（操作前）

```powershell
& "C:\Program Files\Python313\python.exe" "<技能目录>\scripts\make_cache.py" --task "<任务描述>" --strategy serial --paths "F:\x\dir1,F:\x\file.py"
```

### 2. 查看缓存列表（操作前可选）

```powershell
& "C:\Program Files\Python313\python.exe" "<技能目录>\scripts\make_cache.py" --list
```

### 3. 回滚（用户说"回滚"时）

1. 读取最近一次缓存的 manifest.json（或用户指定的时间戳目录）
2. 在缓存目录内执行 `restore.ps1`（`powershell -File restore.ps1`）
3. 验证恢复结果（对比 snapshot 与当前状态）
4. 写决策日志（parallel-serial-decider 的 log_decision.py），标记 failed + rollback
5. 报告：恢复了什么、从哪个时间点

### 4. 清理缓存（用户说"清理缓存"时）

1. 列出所有缓存目录（--list）
2. 让用户确认哪些可删
3. 删除后写决策日志

自动清理规则：成功后保留 7 天；失败后保留 30 天；手动清理由用户触发。

### 回滚必须满足

- 缓存存在且完整
- git 状态允许回滚（没有未提交的冲突）
- 用户明确确认

### 回滚失败时

- 不删缓存
- 报告失败原因
- 让用户手动处理

## manifest.json 格式

```json
{
  "ts": "2026-09-16T22:30:00",
  "task": "改分支名 + 目录重命名",
  "strategy": "serial",
  "snapshot_of": ["04-implementation", "config"],
  "git_branch": "main",
  "git_commit": "05ab9fc",
  "restore_cmd": "powershell -File restore.ps1"
}
```

## 加载与备份说明（实测结论 2026-09-17）

- **加载方式**：技能经 AppData `.user_skills` junction → F 盘权威源加载（每轮对话自动注入技能列表，无需手动点击）。权威源即加载源。
- **`.skills` 系统技能目录不可用于自定义技能镜像**：已实测（2026-09-17）复制镜像后数分钟内被豆包系统清理（108 个官方技能库，系统管理移除非官方内容）；junction 方案更危险（被清理时递归删除权威源内容，曾连带清空 feedback-logger 权威源）。请勿在 `.skills` 下放置自定义技能。
- **更新技能**：直接改权威源（`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\cache-manager\`），junction 自动同步到 AppData，下轮对话生效。

## 资源

- `scripts/make_cache.py` — 创建/列出/清理临时缓存（snapshot + git_state + manifest.json + restore.ps1；`--list` 查看，`--clean` 清理；用法见脚本头部）
