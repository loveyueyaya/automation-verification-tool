# MIGRATION.md — P1 落地记录与迁移说明（初始版）

> 日期：2026-09-16
> 阶段：P1（contracts + env_adapter 落地；现有脚本 import 契约，不改目录结构）
> 架构依据：《本地离线自动化测试_修订版架构设计_v3.md》

## 0. 封板信息（P1）

- **P1 验收：已通过**（56 测试全绿：27 基线 + 29 重建自洽测试，2026-09-16 实测 `Ran 56 tests in 0.146s / OK`；用户本机实测 1.083s（含首次模块加载），属正常范围）
- **重建日期：2026-09-16**（4 个契约化脚本由 pyc 缓存反汇编重建落盘 F 盘）
- **pyc 备份：`F:\自动化验证工具\P1_pyc缓存备份_20260916`**（12834 个，源/备份数量一致，抽样 hash 验证通过，用户亲测）
- **tag：`ui-toolbox-P1-20260916`（待打）**——等本 MIGRATION.md 封板表述定稿后，由用户在 git 恢复时执行
- **已知偏差：见第 6.3 节（残余项）与第 7.8 节（诚实表述汇总）**

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

## 6. 审计补充（2026-09-16）：重建记录与 P1 越界实现标记

### 6.1 重建与原始 pyc：非逐字节等价；"行为等价"仅为逻辑论证，非运行对拍

**诚实表述（见 7.8）：本文档所称"行为等价/等价性证明"均指"重建版行为自洽 + 差异逐项归因"，不是与原始版的运行对拍等价**——因为原始版存在 LRESULT bug（7.2），无法运行，无法做双版本对拍。

- 4 个契约化脚本（locate/timeline/uitool/env）模块级与函数级 `co_code` sha256 与原始 pyc **全部不一致**（编译器形态差异 + code object 元数据差异），但**函数集合 0 增 0 删、常量表一致（除 env.process_count docstring 缺失）**。
- 逐指令 diff 定位：全部差异归因于 ① 编译器对等价表达式的不同生成（三元表达式、`+=`、闭包行号）、② 元数据（行号/文件名/局部变量名）、③ 两处实现差异（见下）。
- **两处实现差异的行为论证**（`tests/test_rebuild_equiv.py` 覆盖，2026-09-16 全绿；性质为"重建版行为自洽"而非"与原始对拍等价"）：
  1. `uitool.verify_text`：重建引入中间变量 `cmd`（原始内联列表）+ `items.get("items", []) if items else []` 空值保护（原始无条件 get）。正常路径命令列表逐项一致（`ocr.py --image <shot> [--filter <text>] [--region <region>]`），返回与时间线审计字段（src=SourceEnum.OCR / conf / chain / result）一致；空值路径重建更健壮（items=None 不抛 AttributeError）。
  2. `env.find_windows`：原始模块级 `_find_windows_cache` 为 dict 直接下标访问；重建为 `None` + 显式判空。首次调用/ttl 内命中/ttl 过期重枚举/cache_ttl<=0 不读不写 四种路径行为一致（测试用 mock EnumWindows + mock time 覆盖）。
- **测试中发现并修复的运行缺陷**：F 盘 `scripts/shot.py` 复制自桌面旧版（06:53），**缺模块级单例 `get_engine`**，而重建版 `uitool.py`（原始 pyc 同款）调用 `shot_mod.get_engine()` → AttributeError。已按原始 pyc（15:56:30）反汇编语义补回 `_ENGINE = None` + `get_engine(monitor=0, output_color="RGB")`。修复后全量 36 用例（27 基线 + 9 新增）通过。

### 6.2 P1 越界实现（明确标记，非重建新增）

`scripts/env.py` 中的以下函数**在原始契约化 pyc（2026-09-16 15:53:45）里本来就有**（证据：pyc 模块级 co_names 含 NOISE_TITLES/NOISE_CLASSES/_find_windows_cache/pick_target；pick_target co_code 原始 962B；函数集合对比 0 增 0 删；桌面旧版 env.py 227 行无 pick_target），因 AppData 源码被清，按 pyc 忠实还原保留：

| 函数 | v3 架构归属 | 处理 |
|------|------------|------|
| `pick_target` / `pick_target.noise` | 感知层（P2 迁 perception/） | **越界实现**，P2 拆层时迁出 |
| `wait_window_ready` | 感知层（P2） | 同上 |
| `process_count` | 硬件层（P2） | 同上 |
| `port_listen` | 硬件层（P2） | 同上 |
| `find_windows(pid=..., cache_ttl=...)` 的 pid/ttl 扩展 | 感知层（P2） | 同上 |

**结论：原始 pyc 本来就有 → 标记"P1 越界实现"保留，不删除**（删了 uitool.see 等既有调用会崩）；P2 拆层时整体迁出至 perception/ 与 hardware/，届时 env.py 瘦身为纯环境适配。

### 6.3 已知偏差（如实记录，未证等价的残余项）

1. `env.process_count`：原始有 docstring，重建缺——纯文档差异，不影响执行（不涉及逻辑）。
2. `scripts/shot.py`：与原始 pyc 仍存在非 get_engine 部分的差异（pyc 版模块级另有 `grab_shot` 函数与 WGC 优先的 `grab()` 异常链；F 盘为桌面旧版 06:53 形态）。本次仅按 pyc 补回测试所需 `get_engine`；**完整对齐 shot.py 到 pyc 版（含 grab_shot、WGC 降级链）列为 P2 前置任务**，当前功能路径（get_engine→grab）已验证可用。
3. 字节码层面非逐字节等价本身即"偏差"：全部可归因为编译形态/元数据，语义由 test_rebuild_equiv.py 覆盖，风险已闭环。

## 7. 审计补充（2026-09-16 第二轮）：全函数覆盖 + 依赖比对 + 证据归档

### 7.1 重建自洽测试扩展到全部 9 个差异函数（29 用例）

**诚实表述：这 29 个测试验证的是"重建版行为自洽"，不是"与原始版等价"**。真正的等价性证明需要原始版可运行，但原始版存在 LRESULT bug（7.2），无法运行；等价性只通过"差异逐项归因"作逻辑论证。

`tests/test_rebuild_equiv.py` 从 9 用例扩至 **29 用例**，覆盖字节码 diff 的全部差异函数：

| 函数 | 新增用例 | 覆盖行为 |
|------|---------|---------|
| locate.loc_by_template | 3 | 阈值命中/低于阈值/图读取失败 → 返回结构 |
| timeline.Timeline.shot | 1 | 截图落盘 + 相对路径（Windows 分隔符） |
| timeline.report | 2 | 分阶段统计（mean/P50/P95/max 精确值）+ >2s 异常标注 + HTML + 空时间线 |
| uitool.auto_click | 3 | 无 expect 成功 / 定位失败记录 locate_fail / expect 命中 |
| uitool.main | 1 | env 分支 DPI/多屏 JSON 输出 |
| env.pick_target | 3 | 无规则无 target / 规则命中打分 / 全噪声 |
| env.process_count | 2 | 大小写不敏感计数 / 异常兜底 0 |
| env.port_listen | 3 | psutil 命中 / socket 兜底 / 双失败 |
| env.wait_window_ready | 2 | 响应即 True / 超时轮询 3 次返回 False |

**全量结果：`Ran 56 tests in 0.146s / OK`**（27 基线 + 29 新增，无回归）。

### 7.2 LRESULT 修复：**重建版本 = 原始 + 修复，不是等价重建**

`env.wait_window_ready` 原始（及重建）均使用 `ctypes.wintypes.LRESULT()` —— **Python 3.13.14 实测 `ctypes.wintypes` 无 LRESULT 属性，函数一旦调用即 AttributeError**。原始 pyc 亦如此写法，**从未运行过该函数故未暴露**；本轮测试首次调用即触发。

- **根因：原始代码本身有 bug，不是重建引入。**
- **修复：`ctypes.wintypes.LRESULT()` → `ctypes.c_long()`**（LRESULT 等价 c_long），已加注释"修复自审计"。
- **因此 F 盘 env.py 的 wait_window_ready 严格说是"原始 + 修复"的派生版本，不能表述为"与原始等价重建"。** 这是唯一一处"有意偏离原始"的位置；其余函数按 pyc 忠实还原。

### 7.3 字符串字面量搜索（重建后重跑）：36 处命中，真违规 0

完整输出见 `证据/字符串搜索输出`（命令：`Get-ChildItem -Recurse -Include *.py | Select-String -Pattern '"ocr"|"uia"|"handle"|"template"'`）。逐条分类：

| 分类 | 数量 | 位置 |
|------|------|------|
| 枚举定义 | 4 | contracts/enums.py L12-16（HANDLE/UIA/OCR/TEMPLATE 值） |
| 注释 | 2 | enums.py L4 硬规则说明、timeline.py L53 docstring |
| 字典键 | 8 | stable_id.py L67/75/76/92/93、validators.py L21 |
| CLI 参数名 | 7 | locate.py L108/144/155/158/161 |
| 测试断言（验证枚举值序列化） | 15 | tests/test_rebuild_equiv.py、tests/test_stable_id.py |
| **真违规** | **0** | — |

### 7.4 运行依赖与 pyc 一致性比对（cache/ocr/sendinput）

对 F 盘 3 个复制依赖做模块级 co_names + 函数集合 + 函数 co_code 与原始 pyc 比对（脚本 `证据/compare_deps_pyc.py`、`diff_deps_pyc.py`）：

| 脚本 | co_names | 函数集合 | 函数 co_code | 结论 |
|------|----------|----------|--------------|------|
| cache.py | 一致 | 一致 | **全部一致** | **完全合规**（F盘==pyc==桌面，hash 一致） |
| ocr.py | 一致 | 一致 | 4 函数不一致 | **pyc 编译自 AppData 分叉代码，与桌面版不是同一代码线**：pyc（11:17:38）无 nvapi 探测/tmp 识别，F盘==桌面当前版（hash 一致 666ACE4B…），功能为 superset。非复制错误。 |
| sendinput.py | 一致 | 一致 | 4 函数不一致 | 同上：pyc（11:17:38）为分叉版（type_ascii 38 指令无大小写、to_clipboard 226 指令含 last_err），F盘==桌面当前版（hash 一致 AEDC02E1…）。非复制错误。 |

**处置**：cache.py 无需动作；ocr.py/sendinput.py 以 F 盘（==桌面当前版）为权威，pyc 标记为"编译自 AppData 分叉代码的旧功能缓存"，P2 契约化时统一对齐。shot.py 差异即 6.1 已记录的 get_engine 修复。

### 7.5 证据归档目录

`F:\自动化验证工具\4代码实现\P1_契约与环境适配层\证据\` 已建，全部证据类文件移入（今后证据不再放 Temp）：
- `full_dis_out.txt`（39873 B，verify_text/find_windows 完整指令序列）
- `compare_pyc.py` / `diff_pyc.py` / `dump_full_dis.py` / `dump_shot_get_engine.py` / `compare_deps_pyc.py` / `diff_deps_pyc.py`（全部可重跑）

### 7.6 ocr.py / sendinput.py 的"F 盘权威"决策时间线（用户质询答复）

**问题一：F 盘那版（含 nvapi 探测、tmp 识别、剪贴板重试、大小写键入）是哪次会话里产生的？时间戳？**

客观时间戳证据（2026-09-16 实测）：

| 对象 | 时间 | 证据 |
|------|------|------|
| 桌面 ui-toolbox 全套脚本（ocr/sendinput/cache/shot/env/uitool 6 文件） | **06:53:56**（统一写入） | `Get-Item LastWriteTime`，6 文件一致 |
| F 盘 scripts 副本（ocr/sendinput/cache） | 06:53:56 | 复制自桌面版，时间戳保留 |
| pyc 缓存（ocr/sendinput） | **11:17:38** | 编译自 **AppData 版**源码（另一份分叉代码，无 nvapi/tmp/重试/大小写） |
| pyc 缓存（cache） | 07:13:54 | 与桌面版一致 |
| F 盘 shot.py | 21:39:38 | 本轮 get_engine 修复 |

**结论：nvapi 探测 / tmp 识别 / 剪贴板重试 / 大小写键入等功能升级产生于 2026-09-16 上午 06:53 之前的会话迭代期（桌面版迭代阶段），06:53:56 完成桌面版统一部署。** 它们不是 P1 重建期间（当晚 20:34–20:42）补加的；P1 期间只是把桌面版整体复制进 F 盘权威源。pyc 的"旧版"来源于 AppData 分叉代码（11:17 编译），与桌面版/F 盘版不是同一条代码线。

**问题二：有没有经过测试？**

- **无独立单元测试**（不在 P1 tests/ 范围内）。
- **有真实运行验证**：这些功能在 cookie_sync 真实验证流程中实际执行过——OCR GPU 识别（PaddleOCR，显存上限 80%）实际出文字框；剪贴板中文粘贴（to_clipboard 重试路径）实际输入中文成功；点击注入（SendInput）实际生效。属于"真机冒烟通过，无自动化回归保障"。**（由豆包报告，用户未独立验证。）**

**问题三：和 P1 的契约化改造有没有冲突？**

- **无冲突**：ocr.py / sendinput.py 不在 P1 契约化清单（P1 契约化了 uitool/env/timeline/locate 4 个脚本，见第 1.3 节"未改造脚本"）。它们是随权威源迁移"补齐运行依赖"复制进 F 盘的，供契约化脚本子进程调用。
- 但与"P1 只做契约+适配"的边界有**范围外事实**：F 盘权威源含 4 个未契约化运行依赖（shot/ocr/sendinput/cache），P2 需统一契约化并消除字符串字面量。

**问题四：是否标记"P1 越界实现"？**

- **判定：不标记为"P1 越界实现"。** 越界定义（6.2 节）是"P1 期间产出 P2 功能"；而 ocr/sendinput 的功能升级发生在 **P1 之前**（06:53 桌面迭代期），P1 仅作随迁。
- **标记为："P1 范围外运行依赖（升级早于 P1，随权威源迁移带入），P2 契约化时统一对齐。"** 与之并列的已知事实：cache.py 完全合规；shot.py 的 get_engine 修复属 P1 期间为兼容重建脚本的必要修复（6.1）。

### 7.7 证据目录 6 个分析脚本说明

| 脚本 | 做什么 | 输入 | 输出 | 已知限制 |
|------|--------|------|------|----------|
| `compare_pyc.py` | 对比 4 个契约化脚本：模块级/函数级 co_code 的 sha256、函数集合增减、常量表差异 | F 盘 scripts\*.py + pyc 缓存 4 个 .pyc | 逐脚本一致性结论（"0 增 0 删"等） | 只报 hash 与集合差异，不定位到指令；常量表比较忽略嵌套 code 对象 |
| `diff_pyc.py` | 对不一致函数逐指令 diff，输出第一处指令差异与局部变量名差异 | 同 compare_pyc.py | 每函数"原始 N 指令/F盘 M 指令 + 第一处差异指令对" | 只显示第一处差异（非全量指令序列）；全量序列见 dump_full_dis.py |
| `dump_full_dis.py` | 输出 verify_text / find_windows 的完整 dis 指令序列（原始+重建） | F 盘 scripts\uitool.py、env.py + 对应 pyc | full_dis_out.txt（39873 B） | 仅覆盖 2 个函数（其余函数差异由 diff_pyc.py 定位） |
| `dump_shot_get_engine.py` | 反汇编 pyc 版 shot.py 的 get_engine / _ENGINE 模块级代码，佐证补回语义 | pyc 缓存 shot.cpython-313.pyc | 控制台打印 get_engine/_ENGINE 指令序列 | 只针对 shot.py 单例补回验证 |
| `compare_deps_pyc.py` | 对比运行依赖（cache/ocr/sendinput）模块级 co_names + 函数集合 + 函数 co_code | F 盘 scripts\cache.py/ocr.py/sendinput.py + pyc 缓存对应 .pyc | 逐脚本一致性结论（含不一致函数名单） | 不定位差异指令（定位用 diff_deps_pyc.py） |
| `diff_deps_pyc.py` | 对不一致依赖函数逐指令 diff + 局部变量名 + 常量表 | 同 compare_deps_pyc.py | 每函数差异定位与"第一处差异指令对" | 同 diff_pyc.py：只显示第一处差异 |

### 7.8 诚实表述汇总（封板前必须明确的 3 点）

1. **LRESULT 修复 ≠ 等价重建**：`env.wait_window_ready` 重建版 = 原始 + 修复（LRESULT→c_long）。原因是原始代码本身有 bug，从未运行过。不表述为"等价重建"（详见 7.2）。
2. **test_rebuild_equiv.py 验证的是"重建版行为自洽"，不是"与原始版等价"**：真正的等价性证明需要原始版可运行，但原始版存在 LRESULT bug，无法运行。等价性仅以"差异逐项归因"作逻辑论证（详见 7.1 / 6.1）。
3. **ocr.py / sendinput.py 的"F 盘权威"是时间线事实**：功能升级早于 P1（06:53 桌面迭代期），P1 仅随迁；无单测、有真机冒烟；与 P1 契约化无冲突；不标"P1 越界实现"，标"P1 范围外运行依赖，P2 统一对齐"（详见 7.6）。

## 8. 历史修复记录（2026-09-18 补记）

> 记录"为什么这么写"的关键上下文，避免后人重写时踩坑。

| 修复项 | 位置 | 说明 |
|---|---|---|
| ctypes 指针截断 | `scripts/sendinput.py::to_clipboard` | `SetClipboardData` 等 API 显式设置 `restype=c_void_p`（windll 默认截断为 32 位，句柄会出错） |

补充说明（2026-09-18 核实）：

- `to_clipboard` 完整调用链：`OpenClipboard → EmptyClipboard → GlobalAlloc(0x0042) → GlobalLock → memmove → GlobalUnlock → SetClipboardData(CF_UNICODETEXT=13) → CloseClipboard`；数据 UTF-16LE 编码，剪贴板被占用时重试 3 次。
- 指针截断修复覆盖：`kernel32.GlobalAlloc / GlobalLock / GlobalSize` 的 `restype`，以及 `user32.SetClipboardData` 的 `argtypes` / `restype`。
- 该实现**不依赖 pyperclip，也不依赖 pywin32 的 win32clipboard**，纯 ctypes + user32/kernel32（实测：干净进程 import sendinput，`pyperclip` 不在 `sys.modules`）。

## 9. P2-2 迁移记录（2026-09-19）

> 依据：《架构设计 v3.2》方案 B + `10-env-baseline/env-baseline_v1.md` 第十节「P2-2 迁移顺序（修正版 7 步）」。
> commit：`1ae52c5`

### 9.1 本次完成的动作

| 步 | 动作 | 实测结果 |
|---|---|---|
| 1 | 复制 contracts 到 `04-implementation/P2-layers/contracts`（P1 不动） | 9 个文件落盘 |
| 2 | 逐文件 diff 校验 | 9/9 IDENTICAL |
| 3 | P1 `contracts/__init__.py` 改为 shim | `contracts.__file__` → `P2-layers/contracts/__init__.py` |
| 4 | 跑 56 测试 | `Ran 56 tests in 0.411s / OK` |
| 6 | 用 `git mv -f` 把 8 个具体模块迁入 P2-layers，P1 只留 shim | 双份消除，56 测试仍 OK |
| 附 | `git mv` env_adapter 整目录 → `P2-layers/env_adapter` | 零引用，无需 shim |

`state_hash.py` / `stable_id.py` / `models.py` / `enums.py` 按架构 v3.2 必修 1 **留在 contracts 横切区**，未下放到 planning/execution 层。

### 9.2 shim 实现方式（为什么不是 `from ... import *`）

目录名 `P2-layers` 含连字符，不能作为包名 import，因此 shim 采用
`importlib.util.spec_from_file_location(name, new_init, submodule_search_locations=[new_dir])`
构造新包并**整体替换 `sys.modules['contracts']`**。好处：子模块（`contracts.enums`、
`contracts.state_hash`）也一并从新目录解析，`from contracts.state_hash import state_hash`
这类"父包属性被子模块同名函数遮蔽"的写法照旧可用。CPython 的 `importlib._bootstrap._InstalledSafely`
注释明确支持这种 sys.modules 替换写法。

### 9.3 环境事故（必读）

- 现象：执行 `git rm` 批量删除 8 个契约模块后，**`04-implementation/P1-contracts-env-adapter/`
  整个目录被外部删除**（两次复现，含 scripts / tests / 证据 / MIGRATION.md），
  随后未入库的 `P2-layers/` 与已入库的 `implementation-index.md` 也一度消失。
- 处置：全部用 `git reset` + `git checkout -- <path>` 恢复（HEAD `a0aeccc` 完整）；
  P2-1 未提交的 shot.py / ocr.py 修复由回滚缓存
  `C:\Users\Administrator\.workbuddy\skills\cache-manager\temp-cache\20260919_030131` 补回。
- 结论：**本环境下 `git rm` 会触发目录级丢失，改用 `git mv` 未复现**。
  后续删除类操作一律先 `git add` 入对象库再动手，并优先用 `git mv`。
- 与 2026-09-19 早些时候"nvidia CUDA DLL / modelscope_hub / colorama 反复丢失"
  疑为同一环境侧问题，根因仍未定位（无 hooks 配置、非磁盘空间）。

### 9.4 遗留（不在本次范围）

- 第 5 步（逐脚本改 import 到新路径）与第 7 步（删 shim）：
  需先给 3 个脚本 + 4 个测试文件加 `P2-layers` 的 `sys.path` 引导，
  与"scripts 按层迁入 perception / execution / observability"同批做，避免重复改动。
- BUG-2（env_adapter 零引用）与 BUG-4（framework 误判）仍未处理。

