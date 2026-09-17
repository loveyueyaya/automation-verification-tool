# 02-architecture - 架构设计

## 用途
存放架构设计文档与评审记录，定义七层 MVP 结构、三层自动闭环（感知层输出 target_hwnd / 动作层强制 locate / 审计层记录坐标来源+置信度+回退链）与契约化改造方向。

## 内容清单
- 本地离线自动化测试_修订版架构设计_v3.md — 架构设计 v3（7 层 MVP + 性能预算表 + 跨进程 trace 规格）
- 架构设计_v3.1.md — v3.1 增量（select_flow 5 流 / 元素 id 双用途 / state_hash target_hint / trace 偏移说明 / P1 越界标记 / 7 层实际落地路径）
- 架构设计_v3.2.md — v3.2 修正（state_hash 留 contracts / P1↔P2 git mv 规则 / 目录去+号 / LLM 流前提 / 越界迁移具体化）
- 用户评分.txt — 用户对 v3 设计的评审意见与 P1 落地要求

## 相关文档
- 03-detailed-design/（详细设计承接架构）
- 01-requirements/（需求来源）
