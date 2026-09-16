# automation-verification-tool

面向 **Windows 桌面 UI 自动化验证**的工具链。目标是让"感知 → 定位 → 注入 → 审计"四层闭环从"LLM 手动编排"升级为"确定性自动化"：感知层输出 `target_hwnd`（不靠 LLM 猜窗口）、动作层强制走定位（拒绝裸坐标）、审计层记录"坐标来源 + 置信度 + 回退链"（失败可归因）。

## 当前状态

| 阶段 | 状态 |
| --- | --- |
| P1 契约 + 环境适配层 | ✅ **已完成并封板**（tag `ui-toolbox-P1-20260916`） |
| P2 按 7 层拆目录 | 规划中 |
| P3 smoke 门禁 + tag 基线回归 | 规划中 |

P1 验收：**56 个单元测试全绿**（contracts 27 + 重建自洽 29）、pyc 字节码备份 12834 个、字符串字面量扫描 0 真违规。
权威源：本机 `F:\自动化验证工具`；AppData 仅保留技能定义，禁止向 AppData 写项目代码。

## 目录结构

```
automation-verification-tool/
├── 00-doubao-llm-prerequisites/   # 豆包 LLM 前置技能（local-dev-environment）
├── 01-requirements/               # 需求分析：运行环境报告、需求规格说明书 v0.1
├── 02-architecture/               # 架构设计：修订版架构设计 v3、用户评分
├── 03-detailed-design/            # 详细设计
├── 04-implementation/
│   └── P1-contracts-env-adapter/  # P1 代码实现（权威源）
│       ├── contracts/             # 契约包：enums / models / errors / stable_id / state_hash / validators / flow / version
│       ├── env_adapter/           # 环境适配：env_probe / env_cache / input_router / capture_router / focus_manager / fallback_policy
│       ├── scripts/               # 运行脚本：uitool / locate / timeline / shot / cache / ocr / sendinput / env
│       ├── tests/                 # 单元测试（56 用例）
│       ├── 证据/                  # P1 验收证据：审计日志、字节码对比工具、full_dis_out
│       └── MIGRATION.md           # 权威源迁移与 pyc 反汇编重建记录
├── 05-tests/                      # 验收证据
├── 6deployment/                   # 部署上线（规划）
├── 7operations/                   # 运维迭代（规划）
├── 项目阶段进度表.xlsx             # 全流程进度台账
├── git-sync.ps1                   # 自动同步脚本
└── README.md
```

## 技术栈

- Python 3.13（本机绝对路径 `C:\Program Files\Python313\python.exe`）
- DXGI 截图 + 本地 PaddleOCR（离线识别，GPU 可加速，不依赖云端）
- UIA / 坐标 / 语义三路定位 + SendInput 注入
- PyInstaller 打包 EXE（依赖库做 DLL）
- Git 2.54

## Releases

每个阶段收尾时打 tag 并发布 GitHub Release（硬规则，见 `00-doubao-llm-prerequisites/local-dev-environment/SKILL.md`「阶段封板流程」）。

| Release | 内容 | 资产 |
| --- | --- | --- |
| [ui-toolbox-P1-20260916](https://github.com/loveyueyaya/automation-verification-tool/releases/tag/ui-toolbox-P1-20260916) | P1: contracts + env_adapter（56/56 测试通过） | `P1_acceptance_evidence.zip`（验收证据）、`P1_pyc_backup.zip`（pyc 备份 12834 个） |

Release 是"最后保险"：任何代码丢失都可从 Release 资产 + tag 指向的 commit 恢复。

## 快速开始

```powershell
cd 04-implementation/P1-contracts-env-adapter
& "C:\Program Files\Python313\python.exe" -m unittest discover -s tests -v
```

## 关键文档

- `04-implementation/P1-contracts-env-adapter/MIGRATION.md` — 权威源迁移、pyc 重建、已知偏差
- `02-architecture/本地离线自动化测试_修订版架构设计_v3.md` — 架构设计 v3（7 层 + 横切 + 4 个关键机制）
- `01-requirements/需求规格说明书_v0.1.md` — 功能边界与兼容性矩阵
- `项目阶段进度表.xlsx` — 阶段进度与验收/遗留
