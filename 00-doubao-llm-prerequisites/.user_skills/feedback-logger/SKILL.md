---
name: feedback-logger
description: "反馈日志机制技能（三层锚点 + timeline 事件流）。当需要记录工作问题/事件/决策/结果、写反馈日报（daily\\feedback_YYYYMMDD.md）、追加事件流（timeline.jsonl）、创建遗留问题（issues\\issue_NNN_<topic>.md）、或在对话结束前做反馈收尾时使用。触发场景：每次对话结束前、每次遇到阻碍性问题后、任何 incident/action/decision/fix/result 事件发生时、需要回填历史事件时间戳时。"
---

# feedback-logger（反馈日志机制）

## 数据位置（权威源 F 盘）

- 事件流：`F:\自动化验证工具\09-feedback\timeline.jsonl`（append-only，只追加不修改）
- 日报：`F:\自动化验证工具\09-feedback\daily\feedback_YYYYMMDD.md`
- 遗留问题：`F:\自动化验证工具\09-feedback\issues\issue_NNN_<topic>.md`
- 索引：`F:\自动化验证工具\09-feedback\INDEX.md`
- 机制说明：`F:\自动化验证工具\09-feedback\feedback-index.md`

## 镜像说明（重要）

- 权威源：`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\feedback-logger\`
- 镜像：`C:\...\workspace\.skills\feedback-logger\`（复制副本，**不要用 junction**——.skills 系统技能目录会被豆包系统管理，junction 被清理时会连带删除权威源内容，已实测发生）
- 更新技能时：先改权威源，再复制同步到镜像（保持两份一致）

## 时间戳规则 v3（硬规则）

1. **当前事件**：时间戳取系统当前时间（`Get-Date` / `datetime.now().astimezone()`），标注 `ts_source=system`
2. **过往事件**：时间戳取对应文件的系统时间（`os.stat`），**同时记录创建时间 / 修改时间 / 访问时间**，标注 `ts_source=fs`
3. **代码事件**：时间戳取 `git log` / `git tag` 时间，标注 `ts_source=git`
4. **禁止 AI 自己写时间**；无锚点 → 标注"对话记录缺失，不清晰"；来源不明 → 标注"来源不明，不清晰"

## 事件类型

`incident`（事故/问题）/ `action`（动作）/ `decision`（决策）/ `fix`（修复）/ `result`（结果）

## timeline.jsonl 格式（每行一条独立 JSON）

```json
{"ts":"2026-09-16T20:11:03+08:00","ts_source":"system|fs|git","type":"incident|action|decision|fix|result","subject":"...","evidence":{"path":"...","created":"...","modified":"...","accessed":"...","sha256":"..."},"action":"...","result":"...","git_commit":"..."}
```

- append-only：事件发生时立刻写入，不攒到晚上；只追加，不修改历史行

## 日报模板（v2）

1. 会话窗口（开始/结束/会话ID，秒级）
2. 事件流（引用 timeline.jsonl 中该时间段的记录）
3. 关键事件（含时间戳来源 + 证据：文件三时间/SHA256 或 git hash/tag）
4. 不清晰记录（明确标注哪里不清晰）
5. 后续建议

## 不清晰规则

- 找不到时间戳 → 标注"对话记录缺失，不清晰"
- 不确定来源 → 标注"来源不明，不清晰"
- 不许编造时间戳

## 工作流

1. **事件发生时**（立即执行，不攒）：
   - 当前事件：`python scripts/log_event.py --type <t> --subject "<s>" [--evidence-path <p>] [--git-commit <hash>] [--action "<a>"] [--result "<r>"]`
   - 过往事件回填：加 `--use-file-time`（ts 取文件修改时间，evidence 记录三时间 + SHA256）
2. **对话结束前**：写/更新 `daily\feedback_YYYYMMDD.md` + `INDEX.md`
3. **遗留问题**：`issues\issue_NNN_<topic>.md`（发现时间/现象/影响/处置/状态）

## 资源

- `scripts/log_event.py` — 追加一行到 timeline.jsonl（自动取系统时间或文件时间；用法见脚本头部）
