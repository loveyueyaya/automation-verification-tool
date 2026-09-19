# 05-tests - 测试与验收证据

## 用途
存放阶段验收证据与测试报告，与代码实现目录内的 tests/ 源码互补（单测源码在 `04-implementation\P1-contracts-env-adapter\tests\`，本目录放"验收结论与证据"）。

## 内容清单（逐文件）

| 文件 | 作用 |
|---|---|
| `tests-index.md` | 本目录索引 |
| `P1_验收证据_20260916_195623.md` | P1 阶段验收证据：完整文件树（33 跟踪文件）、27 用例全量 -v 输出、字符串搜索结果、MIGRATION 全文快照 |
| `P2-1_依赖清理与BUG修复_验收报告.md` | P2-1 验收：OpenCV 收敛（contrib 必留的实测依据）/ pynvml 替换 / BUG-1 区域截图 / BUG-3 OCR 常驻，含变更文件清单 |
| `P2-2_分层迁移_验收报告.md` | P2-2 验收：contracts+env_adapter 迁移至 P2-layers 全部实测（目录结构 find 输出、16 文件行数比对）、环境事故与 git mv 规避结论 |
| `P1_acceptance_evidence.zip` | P1 验收证据包（**本地副本，不入库**；同名资产已上传 GitHub Release `ui-toolbox-P1-20260916`） |

## 相关文档
- `04-implementation\P1-contracts-env-adapter\tests\`（56 单测源码）与 `evidence\`（重建审计证据）
- `06-deployment\`（Release 发布记录与资产）
- `10-env-baseline\env-verify_20260919.md`（环境侧功能回归，含端到端 7 项快照）
