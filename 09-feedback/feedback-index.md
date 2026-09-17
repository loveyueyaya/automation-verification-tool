# 反馈日志机制

## 目的
记录豆包每次工作遇到的问题、解决方式、遗留项、不清晰点。

## 触发时机
- 每次对话结束前
- 每次遇到阻碍性问题后

## 命名规范
- 按日：daily\feedback_YYYYMMDD.md
- 遗留问题：issues\issue_NNN_<topic>.md
- 事件流：timeline.jsonl（append-only，只追加不修改）

## 目录树规划（09-feedback）

```
09-feedback\
├── feedback-index.md       ← 本机制说明（含时间戳规则 v3）
├── INDEX.md                ← 索引（日期/任务/问题数/解决数/遗留数/事件流完整度）
├── timeline.jsonl          ← 事件流（append-only，每行一条 JSON）
├── daily\                  ← 日报（按日：feedback_YYYYMMDD.md）
└── issues\                 ← 遗留问题（issue_NNN_<topic>.md）
```

## 技能位置（feedback-logger）

- 权威源：`F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\feedback-logger\`
- 镜像：`C:\...\workspace\.skills\feedback-logger\`（复制副本，不用 junction，防系统清理连带删除）
- 自动加载：经 AppData `.user_skills` junction（→F 盘权威源）与 `.skills` 镜像双路径可见，每轮对话注入

## 时间戳规则 v3（三层锚点）

### 规则 1：时间戳必须当场取
- 所有时间戳必须来自系统命令输出（Get-Date / Get-Item / git log）
- 禁止 AI 自己写时间
- 每条时间戳标注来源：`system`（Get-Date）/ `fs`（Get-Item 文件时间）/ `git`（git log/tag）

### 规则 2：三层锚点
- 第一层 会话锚点：会话开始时间（秒级）、会话结束时间（秒级）
- 第二层 事件锚点：事件时间（秒级）、事件类型（incident/action/decision/fix/result）
- 第三层 证据锚点：文件（创建时间/修改时间/访问时间/SHA256）、代码（git commit hash/tag）、对话（原始片段，不加工）

### 规则 3：事件流文件 timeline.jsonl
- append-only，只追加不修改
- 每行一条独立 JSON
- 事件发生时立刻写入，不攒到晚上
- 格式：
  `{"ts":"...","ts_source":"system|fs|git","type":"incident|action|decision|fix|result","subject":"...","evidence":{"path":"...","created":"...","modified":"...","accessed":"...","sha256":"..."},"action":"...","result":"...","git_commit":"..."}`

### 规则 4：时间戳取值口径（v3 新增）
- **后续记录**：取**当前系统时间**（`datetime.now().astimezone()`，秒级 ISO8601 带时区）
- **过往记录**：取**对应文件的系统时间**（`os.stat`），并**同时记录创建时间 / 修改时间 / 访问时间**
- 代码事件取 git log / git tag 时间；无锚点禁止编造

### 规则 5：日报模板（v2）
1. 会话窗口（开始/结束/会话ID）
2. 事件流（引用 timeline.jsonl 中该时间段的记录）
3. 关键事件（含时间戳来源+证据）
4. 不清晰记录（明确标注哪里不清晰）
5. 后续建议

### 规则 6：不清晰必须明确标注
- 找不到时间戳 → 标注"对话记录缺失，不清晰"
- 不确定来源 → 标注"来源不明，不清晰"
- 不许编造时间戳

### 规则 7：立即生效
新事件发生时：
1. 立即执行 Get-Date 取时间戳（当前事件）
2. 涉及文件立即执行 Get-FileHash + 记录创建/修改/访问时间
3. 涉及代码立即记录 git commit hash
4. append 一行到 timeline.jsonl（可用 feedback-logger 技能 scripts/log_event.py）
