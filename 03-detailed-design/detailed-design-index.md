# 03-detailed-design - 详细设计

## 用途
存放详细设计文档（按架构 v3.1 的 P2 阶段产出），定义 7 层目录结构、首个模块清单、config yaml、跨进程 trace 协议与幂等性分级。

## 内容清单（逐文件）

| 文件 | 作用 | 状态 |
|---|---|---|
| `detailed-design-index.md` | 本目录索引 | — |
| `详细设计_v1.md` | 详细设计 v1：7 层目录结构目标形态（contracts/core/cli/config/tests/utils 规划）、每层首个实现模块清单、budget/fallback/paths 三份 yaml、trace 协议落地版、幂等性分级 L0-L3 | 历史版本，保留 |
| `详细设计_v1.1.md` | **当前有效版**：7 处修正——state_hash 留 contracts、迁移一律 git mv、目录名去 `+` 号、paths 不写死、trace 字段 P2 标注 | ✅ 现行 |

> 注：v1 规划的目录名（P2-seven-layer-architecture）在 P2-2 实际执行时改为 `P2-layers/`（只迁有代码的 contracts + env_adapter，先建空壳会误导）——偏差记录见 `05-tests\P2-2_分层迁移_验收报告.md` 与 `11-management\接下来的任务.txt` 第二节。
> 版本规则：v1 / v1.1 并存不覆盖；冲突时以 v1.1 为准。

## 相关文档
- `02-architecture\`（架构设计 v3.2）
- `04-implementation\P2-layers\`（按本设计落地的代码）
- `05-tests\P2-2_分层迁移_验收报告.md`（落地实测）
