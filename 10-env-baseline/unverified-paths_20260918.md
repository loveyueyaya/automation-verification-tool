# 未验证路径清单

> 记录日期：2026-09-18
> 记录依据：`env-baseline_v1.md` 第八节末尾发现的降级事实（用户审阅时指出其更深层含义）
> 状态：P1 阶段全部测试均在**降级路径**下完成

---

## 背景

本机 `env_adapter/env_probe.py::probe_env()` 实测 `security=wujie`（探测到无界远程控制类软件正在运行），
因此判定 `focus_reliable=False`，env_adapter 自动降级：

- 输入：`InputMethod.SEND_INPUT` → **`InputMethod.HANDLE_POST`**（句柄直投）
- 截图：`CaptureMethod.DXCAM` → **`CaptureMethod.MSS`**

结论：**P1 阶段所有测试跑的是 HANDLE_POST + MSS 降级路径**，主路径从未真机验证。

实测证据（`probe_env()` 本机输出）：

| 字段 | 实测值 |
|---|---|
| dpi_scale | 1.25 |
| integrity_level | medium |
| security | wujie |
| focus_reliable | **False** |
| input_method | InputMethod.HANDLE_POST |
| capture_method | CaptureMethod.MSS |

---

## 未验证的主路径

| 路径 | 状态 | 验证条件 |
|---|---|---|
| SendInput 注入 | ❌ 从未真机验证 | 关闭远程软件后测试 |
| dxcam（DXGI）截图 | ❌ 从未真机验证 | 关闭远程软件后测试 |

## 未验证的间接路径

| 路径 | 状态 | 说明 |
|---|---|---|
| comtypes COM 初始化 | ❌ 未真机验证（主路径） | import dxcam 时连带加载 22 子模块；远程软件环境下的初始化路径不代表真实环境 |

> 间接路径提示：若关闭远程软件后 dxcam 初始化行为与现在不同，**问题可能出在 comtypes 那一层**，而非 dxcam 自身。
> 排查顺序建议：dxcam 报错 → 先看 comtypes COM 初始化 → 再看 DXGI 调用。

---

## 影响

- P2/P3 首次切换主路径（SendInput / dxcam）时可能出问题，且故障点可能不在表层
- comtypes 初始化差异属于"隐藏层"，症状容易被误判为 dxcam 本身不兼容

---

## 行动项

- P3 smoke 测试必须包含"关闭远程软件，验证主路径"用例
- 或 P2-4 trace 落地后专门安排一次真实环境验证
- 验证时若 dxcam 初始化异常，按上述排查顺序先看 comtypes 层

---

*本清单所有实测值来自 `probe_env()` 真实调用输出。*
