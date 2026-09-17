# 审查日志规范

## 目的
记录每次审查的发现、结论、修复、跟踪，避免重复思考，方便追溯。

## 命名规范
- 目录：08-review-logs（全英文）
- 索引：INDEX.md
- 单次审查：review_YYYYMMDD_<scope>.md
- AI 分歧：dispute_YYYYMMDD_<topic>.md

## 内容格式
见现有日志模板。

## 触发时机
- 每次云端审查（文心 / 扣子等）完成后
- 每次本地自查（豆包跑测试 / 搜索）完成后
- 每次补丁修复完成后
- 每次 AI 间分歧（误报 / 漏报）发生后

## 归档规则
- 超过 30 天的日志归档到 08-review-logs\archive\
- INDEX.md 保留全部记录
- dispute_*.md 永久保留（AI 可信度案例库）
