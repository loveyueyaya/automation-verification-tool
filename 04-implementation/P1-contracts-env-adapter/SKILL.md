---
name: ui-toolbox
description: 本地 UI 自动化工具箱（Windows 真实操作）。当用户要求"真实模拟用户操作/接管鼠标键盘/验证工具使用/UI 自动化测试/自动化验证/点击输入注入"时使用。提供全屏截图（DXGI 物理像素）、PaddleOCR 中文识别（GPU）、坐标定位（OCR+句柄+模板三路合一）、SendInput 输入、审计时间线。强制流程：先看→决定→点→等→验证→截图，全部打时间戳落盘，产出可回放审计报告。禁止绕过本工具自行截图、换算坐标或注入输入。
---

# UI 自动化工具箱（ui-toolbox）

## 项目代码位置

项目代码权威源：F:\自动化验证工具\4代码实现\P1_契约与环境适配层\
禁止把项目代码写入 AppData 工作区。
AppData 只保留技能定义。

Windows 本地 UI 自动化：截图、识别、定位、注入、审计一体。所有动作走"先看 → 决定 → 点 → 等 → 验证 → 截图"六阶段，每步带毫秒时间戳自动落盘，形成可回放、可审计、可对比基线的测试报告。

## 核心契约（硬规则）

1. **坐标**：一律物理像素（本机 2560×1440 @125% DPI）。禁止用远程窗口/截图工具的分辨率换算坐标。
2. **流程**：任何自动化验证必须 `see → 决策 → 注入 → 等待 → verify → shot` 六阶段；`verify` 不通过不许宣布成功。
3. **时间**：每一步通过 `uitool.py` 执行（自动写 `timeline.jsonl` + 截图），禁止手动裸调底层函数绕开时间线。
4. **输入**：中文/长路径用剪贴板粘贴；控件焦点不可控时用句柄消息直投；双击一律用 `dblclick`（SendInput 双击序列）。
5. **定位**：句柄几何 > 模板匹配 > OCR，多路互为校验；OCR 只做"用户所见"与验证，不做精确坐标来源。
6. **截图**：默认 DXGI（dxcam，物理像素），透明窗口黑屏时降级 mss；每步证据图自动存档。

## 目录结构

```
scripts/
  env.py        环境层：DPI 感知、多屏几何、窗口/控件枚举、进程/端口
  shot.py       截图引擎：dxcam(DXGI) 主 + mss 兜底；--monitor --region
  ocr.py        PaddleOCR：GPU(显存上限 80%)、离线、--region 分块、--serve 常驻
  locate.py     定位三路合一：ocr/handle/template/verify(区域 diff)
  sendinput.py  输入层：SendInput + 剪贴板 + 句柄消息直投(post_key/post_char)
  timeline.py   审计：timeline.jsonl + report.md/html（延迟异常自动标注）
  cache.py      缓存：业务指令/元素规则/句柄位置移动判断/阈值配置
  uitool.py     统一入口（六阶段流程编排，推荐使用）
  perfmon.py    性能采样：进程 CPU%/内存（GetProcessTimes+WorkingSet）、GPU/显存（nvidia-smi）
  diagnose.py   点击失效七步排查：焦点→遮挡→坐标→权限→时序→注入→环境
  testbar.py    测试状态控制台：任务栏覆盖条+控制面板+全局热键+强制大写+冲突弹窗+实时性能图+一键诊断
```

## 快速开始

```powershell
# 1. 环境自检（DPI/多屏/分辨率）
python uitool.py env

# 2. 看：全屏截图 + 窗口状态 + OCR（决策依据）
python uitool.py see --session s01

# 3. 点（自动记录 + 截图）
python uitool.py click 1280 720 --session s01
python uitool.py dblclick 1280 720 --session s01
python uitool.py key 13 --session s01

# 4. 中文输入（剪贴板 + Ctrl+V）
python uitool.py paste 1280 720 "要输入的中文" --session s01

# 5. 验证（截图 → OCR 找期望文本）
python uitool.py verify-text "期望出现的文字" --session s01

# 6. 最终截图 + 审计报告
python uitool.py shot --session s01 --label final
python uitool.py report s01 --html <path>/report.html
```

## 定位细节

```powershell
# 句柄定位（精确控件，优先）
python locate.py handle --title "CookieSync" --class "ConsoleWindowClass"

# OCR 定位（用户所见文字）
python locate.py ocr --text "打开" --image D:/s.png

# 模板匹配（图标/图片）
python locate.py template --tpl D:/icon.png --image D:/s.png

# 区域 diff 验证（点前后界面是否变化）
python locate.py verify --image D:/before.png --tpl D:/after.png --region 100,100,300,200
```

## 缓存与阈值（减少云端/重复识别）

```powershell
# 业务指令缓存（流程复用）
python cache.py ops save flow1 '["click 100,200","key 13"]'
python cache.py ops get flow1

# 元素规则缓存（命中即复用坐标）
python cache.py rule add 确定按钮 '{"text":"确定","offset":[0,0]}'

# 句柄移动判断（缓存 rect，操作前比对；阈值可配）
python cache.py hwnd save 123456 100,200,300,400
python cache.py hwnd moved 123456            # same|moved|unknown

# 阈值配置
python cache.py config set move_px 8         # 句柄移动判定阈值（像素）
python cache.py config set sim_threshold 0.8 # 模板匹配相似度阈值
```

## OCR 服务模式（避免重复加载模型）

```powershell
# 常驻服务：stdin 逐行读 {"image": "...", "region": "x,y,w,h", "filter": "关键词"}
echo '{"image":"D:/s.png"}' | python ocr.py --serve
```
GPU 配置：显存上限 = 显卡显存 × 0.8（自动探测并设置 `FLAGS_gpu_memory_limit_mb`），分配策略 `auto_growth`；CUDA/cuDNN 动态链接库由 `paddlepaddle-gpu` wheel 内置，无需系统安装 CUDA。

## 时间线审计

每次 `uitool.py` 操作自动写入 `timeline/<session>/timeline.jsonl`：
`{ts, phase, step, action, target, method, result, latency_ms, evidence}`。
报告自动标注 >2s 的延迟异常（卡顿自暴露），可对比基线判断回归。

## 测试状态控制台（testbar）

真实 UI 自动化测试时的桌面覆盖层 + 控制面板 + 全局热键 + 性能监控 + 一键诊断：

```powershell
# 启动（Windows；立即显示覆盖条 + 控制面板）
& "C:/Program Files/Python313/python.exe" testbar.py
& "C:/Program Files/Python313/python.exe" testbar.py --no-panel   # 仅覆盖条
& "C:/Program Files/Python313/python.exe" testbar.py --keys 121,122,123  # 换键
```

- **覆盖条**：置顶覆盖任务栏时钟区，实时显示状态 + 快捷键提示
- **控制面板**：开始 / 暂停(继续) / 终止 / 关闭 按钮，可拖动
- **目标程序**：默认 cookie_sync.exe，带「浏览…」按钮自选任意 exe（未运行自动拉起）
- **实时性能图**：控制台与目标程序各自的 CPU / GPU / 显存 / 内存 曲线（1s 采样，90 点环形缓冲）
- **强制大写**：进入测试状态自动点亮 CapsLock，F12 终止后恢复原状态
- **热键冲突弹窗**：RegisterHotKey 注册失败即弹窗——「是=强制继续(禁用冲突键) / 否=暂停测试」；覆盖条 chip 与面板同步红字
- **一键诊断**：点击「🔍 一键诊断」按 焦点→遮挡→坐标→权限→时序→注入→环境 七步排查，面板内显示每步 ✓/⚠/✗ 与建议
- 状态机：IDLE → TESTING ⇄ PAUSED → TERMINATED（F10 切换暂停/继续，F11 设置面板，F12 终止并退出）

## 性能采样（perfmon）

```powershell
# 单测：目标进程 CPU/内存 + GPU 整卡利用率/显存
python perfmon.py --target cookie_sync
```

- 进程 CPU%：GetProcessTimes 差值 / 墙钟（PROCESS_QUERY_LIMITED_INFORMATION 权限）
- 内存：WorkingSetSize；GPU/显存：nvidia-smi 整卡 + compute-apps 按进程
- 接口：`PerfMonitor(interval, points)` → `set_target_by_name()` / `set_target(pid, name)` / `snapshot()`

## 七步排查（diagnose）

```powershell
python diagnose.py --target cookie_sync --click 1280,720
```

输出 JSON 数组，每步 `{step, name, status: ok|warn|fail|skip, detail, advice}`：

1. 焦点：目标窗口是否在前台（GetForegroundWindow 对比）
2. 遮挡：点击点顶层窗口是否为目标（WindowFromPoint）
3. 坐标：点击点是否在目标 rect 内
4. 权限：是否管理员 / 完整性级别（UIPI 前置条件）
5. 时序：本次检查耗时（>2s 标注卡顿）
6. 注入：当前完整性是否足够（SendInput 被 UIPI 静默拦截的判断依据）
7. 环境：会话是否锁定、屏幕物理分辨率（SetProcessDpiAwarenessContext 后）

> 注意：本模块依赖 Windows API（ctypes.windll / RegisterHotKey / SHAppBarMessage），只能在 Windows 桌面运行；测试期间建议关闭占用 F10-F12 的程序（如部分浏览器/录屏工具）。桌面部署副本在 `C:\Users\Administrator\Desktop\测试控制台\`（testbar.py + perfmon.py + diagnose.py + 启动测试控制台.bat）。

## 已知边界

- WGC（Windows Graphics Capture）：winrt 3.2.1 绑定缺静态工厂（CreateForMonitor），纯 Python 需手写 COM 互操作，暂以 DXGI（dxcam，文档同档"最接近用户所见"）为主引擎；如需 WGC 走 C# 桥接。
- 安全桌面（UAC 弹窗）任何常规 API 截不到。
- 全屏独占游戏可能拦截 DXGI 抓帧（此时用 mss 兜底）。
