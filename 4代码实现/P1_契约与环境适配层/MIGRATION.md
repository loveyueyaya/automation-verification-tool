# MIGRATION.md — P1 落地记录与迁移说明（初始版）

> 日期：2026-09-16
> 阶段：P1（contracts + env_adapter 落地；现有脚本 import 契约，不改目录结构）
> 架构依据：《本地离线自动化测试_修订版架构设计_v3.md》

## 1. P1 已落地内容

### 1.1 contracts/ 包（契约层，横切 A）

```
contracts/
├── __init__.py      # 统一导出
├── enums.py         # SourceEnum / CoordType / ActionType / InputMethod
│                    # CaptureMethod / VerifyLevel / Flow(5) / ErrorCode
├── models.py        # 8 核心模型 + WindowInfo/OcrItem/Rule/ResourceSnapshot/StateDiff/FallbackAction
├── errors.py        # 契约异常层级 + to_error_code
├── version.py       # CONTRACT_VERSION="2026.09.16-P1" + check_contract_version
├── stable_id.py     # 元素指纹三层可分解 + resolve_for_action / resolve_for_cache（用途区分）
├── state_hash.py    # 状态哈希：参与/不参与字段、2% 网格、文本规范化
├── flow.py          # select_flow（5 流纯函数；P2 迁 orchestrator/flow.py）
└── validators.py    # validate_element_id / validate_snapshot / validate_resolved_action
```

### 1.2 env_adapter/ 包（第 2 层，新增核心）

```
env_adapter/
├── __init__.py
├── env_probe.py       # 探测：浏览器/框架/wujie/完整性级别/远程软件/DPI → EnvProfile
├── env_cache.py       # TTL + 版本 + 失效；过期不返回脏数据
├── input_router.py    # 注入路由（声明式规则表）：wujie/低完整性/焦点不可靠 → HANDLE_POST
├── capture_router.py  # 截图路由：wujie/远程 → MSS，默认 DXCAM
├── focus_manager.py   # 前台/置顶/焦点恢复（复用 scripts/env.activate_window）
└── fallback_policy.py # 声明式降级表：环境特征 × 错误码 → FallbackAction
```

### 1.3 现有脚本契约化改造（验收：至少 3 个实际使用枚举，非只 import）

| 脚本 | 改造点 |
|------|--------|
| `scripts/locate.py` | loc_by_ocr/handle/template 的 source 改为 `SourceEnum.OCR/HANDLE/TEMPLATE`；loc_all 排序用枚举键；json 序列化加 `default=_jdefault` |
| `scripts/timeline.py` | `record()` 的 src 接受 `SourceEnum`（序列化自动转 value）；report 兼容旧字符串记录 |
| `scripts/uitool.py` | `_locate_target` 四路定位 src 全部改枚举；chain 统一 `_v()` 转 value；see/click/paste/verify_text/auto_click 的 src 改枚举；main 所有 json.dumps 加 `default=_jdefault` |

**未改造脚本（P2 迁移时处理）**：shot.py / ocr.py / sendinput.py / cache.py / perfmon.py / diagnose.py / testbar.py / ocr_bench.py / wgc_probe.py / env.py（env.py 的 pick_target 属感知层，P2 迁 perception/）。

## 2. 硬规则（违规清单）

1. **字符串字面量违规**：代码中出现 `"ocr"` / `"uia"` / `"handle"` 等来源字符串字面量代替 `SourceEnum` → 视为违规。当前已改造的 3 个脚本合规。
2. **调用方判断环境违规**：任何脚本出现 `if wujie:` / `if 360se:` 等环境判断 → 必须收敛到 env_adapter，否则违规。
3. **拷贝违规**：同一逻辑只允许一份实现（single-source）；测试控制台 exe 内嵌的 perfmon/diagnose/shot 逻辑为已知违规，P2 合并。
4. **空段记号违规**：元素指纹空段一律 `none`，禁止自造空段记号（如双下划线）。

## 3. 跨进程 trace 落地锚点（P2 实施；P1 只列改造点）

现有 `uitool._sub()` 子进程调用点（共 5 处）——每处子进程当前不接收 trace_id，span 会断链：

| # | 位置（uitool.py） | 子进程 | 改造方案 |
|---|------------------|--------|---------|
| 1 | auto_click 内 `_sub(["sendinput.py","click",...])` | sendinput.py | 加 `--trace-id <tid>` |
| 2 | click() `_sub(["sendinput.py","dblclick"/"click",...])` | sendinput.py | 同上 |
| 3 | paste() `_sub(["sendinput.py","clip"/"click"/"hotkey",...])` 3 次 | sendinput.py | 同上（3 次调用传同一 tid） |
| 4 | verify_text() `_sub(["ocr.py","--image",...])` | ocr.py | 加 `--trace-id <tid>` |
| 5 | main key 分支 `_sub(["sendinput.py","key",...])` | sendinput.py | 同上 |

**统一改造协议**（P2 实施）：
- 子进程入口统一接收 `--trace-id`（或环境变量 `UI_TRACE_ID`，环境变量优先）
- 日志写同一 session 的 timeline.jsonl（不新建 session 目录），首行声明 `{pid, parent_trace_id, clock_offset}`
- 时间对齐：父进程 spawn 前记 `t_parent0`；子进程记 `t_child0=time.time()`；`offset = t_parent0 - t_child0`；子进程 span 的 ts = `time.time() + offset`
- 报告展示时加一行说明：**"子进程启动延迟 N ms 已计入偏移"**（offset 含子进程启动延迟是正常的，避免误判卡顿）
- 断链检测：报告生成时校验每个 span 的 trace_id 链完整；孤儿 span（无父）标黄 + 输出"跨进程断链"告警

## 4. 版本冻结基线

- 当前基线：`CONTRACT_VERSION = "2026.09.16-P1"`
- P1 验收通过后打 tag：`ui-toolbox-P1-20260916`
- P2 之前所有改动必须通过 tests/ 三件套 + 三工具 smoke（smoke 见 v3 第七节，P3 接入）

## 5. P2 预告（不在 P1 范围）

1. 按 v3 七层目录拆层（hardware+perception 合并、state_cache+planner 合并、locator+executor 合并）
2. 测试控制台改薄壳 import core（单源复用）
3. 跨进程 trace 传播落地（见第 3 节锚点）
4. 剩余 9 个脚本契约化（字符串字面量清零）
