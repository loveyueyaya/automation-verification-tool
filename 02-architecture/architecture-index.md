# 02-architecture - 架构设计

## 用途
存放架构设计文档与评审记录，定义七层 MVP 结构、三层自动闭环（感知层输出 target_hwnd / 动作层强制 locate 拒绝裸坐标 / 审计层记录坐标来源+置信度+回退链）与契约化改造方向。

## 内容清单（逐文件）

| 文件 | 作用 | 状态 |
|---|---|---|
| `architecture-index.md` | 本目录索引 | — |
| `本地离线自动化测试_修订版架构设计_v3.md` | 架构 v3 基础版：7 层 MVP 结构（orchestrator→env_adapter→感知/缓存/执行→校验/观测 + contracts 横切）、性能预算表、跨进程 trace 规格 | 历史版本，保留 |
| `架构设计_v3.1.md` | v3.1 增量：select_flow 5 流（CACHE/NORMAL/LLM/EXCEPTION/HUMAN 短路规则）、元素 id 双用途（定位 L1>L2>L3 / 缓存 L3>L2>L1）、state_hash target_hint、trace 偏移归一、P1 越界标记、7 层实际落地路径 | 历史版本，保留 |
| `架构设计_v3.2.md` | **当前有效版**：7 处修正——state_hash 留 contracts、P1↔P2 一律 git mv 保留历史、目录名去 `+` 号、LLM 流前提、越界迁移具体化 | ✅ 现行 |
| `用户评分.txt` | **用户对 v3 设计的评审意见**——select_flow 5 流规则的原始出处、P1 落地验收口径的来源；读架构时配合 v3.1 对照 | 评审存档 |

> 版本规则：v3 / v3.1 / v3.2 **并存不覆盖**；冲突时以 v3.2 为准。
> ⚠ 已知问题：根 `README.md` 的架构链接仍指向 v3 文件名（更新需用户确认，见 11-management 遗留）。

## 相关文档
- `03-detailed-design\`（详细设计承接架构）
- `01-requirements\`（需求来源）
- `04-implementation\P2-layers\`（7 层骨架的实际落地）
