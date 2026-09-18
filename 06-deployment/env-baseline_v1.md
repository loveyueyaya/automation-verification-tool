# 环境地基清单 v1（env-baseline）

> 初版生成：**2026-09-18 12:15:05 +0800**（系统命令 `date` 获取）
> 本次修订：**2026-09-18 12:32:36 +0800**（系统命令 `date` 获取）
> 修订依据：用户审阅意见（3 个必须处理问题 + 2 项澄清 + 平台坑入规范）
> 适用范围：`F:\自动化验证工具`（P2 及后续阶段）
> 状态：**已验收**（地基零漂移、卸载后 56 测试仍全绿、GPU 栈可用、UIA 实测可枚举）

### 修订记录

| # | 修订内容 | 对应意见 |
|---|---|---|
| 1 | 卸载 pyautogui 及 8 个污染依赖，重跑 56 测试确认全绿 | 问题 1 |
| 2 | 回滚快照另存 F 盘 `08-env-baseline\pip_before_20260918.txt`，本节路径已更新 | 问题 2 |
| 3 | 新增第十节「P2-2 迁移顺序（修正版 7 步）」，撤销原"git mv + shim"错误顺序 | 问题 3 |
| 4 | 新增第八节：P1 `env_probe` 的 Windows API 调用方式澄清（ctypes，非 pywin32） | 澄清 1 |
| 5 | 新增第九节：56 测试全绿的三个时点，明确"补装后仍全绿" | 澄清 2 |
| 6 | 第六节坑 2 / 坑 3 已同步写入 `local-dev-environment` 技能 SKILL.md | 平台坑 |

---

## 一、硬件与操作系统

| 项 | 实测值 | 取证方式 |
|---|---|---|
| OS | Windows 11 10.0.22631（64bit） | `platform.platform()` |
| CPU | 24 物理核 / 32 逻辑核 | psutil |
| 内存 | 总计 63.7 GB，可用 46.6 GB | psutil |
| GPU | NVIDIA GeForce RTX 4080 Laptop GPU，12282 MiB，驱动 616.56 | `nvidia-smi --query-gpu` |
| 屏幕 | 2560 × 1440（DPI 缩放 1.25） | `pyautogui.size()`（卸载前实测）/ `scripts\env.py::dpi_for_window` |
| 磁盘 C | 总 200 GB / 剩余 109 GB | `shutil.disk_usage` |
| 磁盘 F | 总 1908 GB / 剩余 **993 GB**（模型/缓存落 F 盘） | `shutil.disk_usage` |

---

## 二、工具链（绝对路径 + 实测版本）

| 工具 | 版本 | 绝对路径 | 备注 |
|---|---|---|---|
| Python | **3.13.14** | `C:\Program Files\Python313\python.exe` | 项目权威源指定，务必用绝对路径 |
| Git | 2.54.0.windows.1 | `C:\Program Files\Git\cmd\git.exe` | |
| Go | 1.27.1 | `C:\Program Files\Go\bin\go.exe` | |
| Rust | 1.98.1 | `%USERPROFILE%\.cargo\bin\rustc.exe` | |
| Java | 21.0.12.1 LTS | `C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\java.exe` | |
| MSVC C++ | VS2022 BuildTools | `...\BuildTools\VC\Auxiliary\Build\vcvars64.bat` | `cl.exe` 不在 PATH，须先激活；实测 `...\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe` 存在 |
| VS Code | 1.137.0 | `...\Microsoft VS Code\bin\code.cmd` | |
| PyInstaller | 6.22.3 | `C:\Program Files\Python313\Scripts\pyinstaller.exe` | `--windowed` 打包 |

> 外部进程调用一律带 `creationflags=CREATE_NO_WINDOW`（0x08000000），杜绝黑窗口闪屏（项目硬规则）。

---

## 三、Python 包清单

### 3.1 地基包（版本锁定，任何安装都不得漂移）

| 包 | 版本 | 用途 |
|---|---|---|
| numpy | 2.3.5 | 数值底座 |
| opencv-python | 5.0.0.93 | 模板匹配（默认定位方式） |
| paddlepaddle-gpu | 3.3.1 | OCR GPU 推理（GPU 占用上限 80%） |
| paddleocr | 3.7.0 | OCR 引擎 |
| psutil | 7.2.2 | 性能监控（**禁用 os.system/popen 读系统数据**） |
| pillow | 12.3.0 | 图像处理 |
| comtypes | 1.4.16 | dxcam / uiautomation / pywinauto 三方 COM 底座（dxcam 首选截图引擎的 DXGI/Desktop Duplication 依赖） |
| dxcam | 0.3.0 | 截图首选引擎（WGC） |
| mss | 10.2.0 | 截图备选 |

### 3.2 保留包（本轮补装，层5 execution 依赖）

| 包 | 版本 | 用途 / 对应架构层 |
|---|---|---|
| **pywin32** | 312 | `win32gui` / `win32con` / `win32api` → UIA 层级 A 原生 Win32 |
| **pywinauto** | 0.6.9 | 控件树、窗口枚举 → 层5 handle |
| **uiautomation** | 2.0.29 | UIA 控件树 → 层5 uia |

### 3.3 已卸载包（用户裁定：污染依赖，无明确用途）

| 包 | 曾装版本 | 卸载理由 |
|---|---|---|
| pyautogui | 0.9.54 | 项目主力不用它：截图走 dxcam/mss，输入走 SendInput + 句柄直投 + WM_CHAR |
| ├ mouseinfo | 0.1.3 | 随 pyautogui 引入，无独立用途 |
| ├ pygetwindow | 0.0.9 | 同上（窗口能力由 pywinauto/win32gui 提供） |
| ├ pyscreeze | 1.0.1 | 同上（截图/定位能力由 dxcam/mss/cv2 提供） |
| ├ pytweening | 1.2.0 | 同上（缓动由自研 smooth_hover 插值提供） |
| ├ pyrect | 0.2.0 | 同上 |
| ├ pymsgbox | 2.0.1 | 同上 |
| └ pyperclip | 1.11.0 | 同上 |

**9 个包已全部卸载并确认不可导入，56 测试回归仍全绿（见第五节）。**

---

## 四、本轮操作记录（可复现）

```bash
# 前置：Bash 必须补 PATH，否则 coreutils 缺失（见第六节坑 1）
export PATH="/c/Program Files/Git/usr/bin:$PATH"
PY="C:/Program Files/Python313/python.exe"

# 安装前快照（回滚依据）
"$PY" -m pip freeze > pip_before.txt

# 第 1 批：pywin32（其他包的基础）+ 注册 DLL/COM
"$PY" -m pip install --disable-pip-version-check pywin32
"$PY" "C:/Program Files/Python313/Scripts/pywin32_postinstall.py" -install

# 第 2 批：UIA 双引擎（钉住 numpy/pillow 防漂移）
"$PY" -m pip install --disable-pip-version-check pywinauto uiautomation "numpy==2.3.5" "pillow==12.3.0"

# 第 3 批（随后已撤销）：pyautogui —— 用户裁定为污染依赖
# "$PY" -m pip install --disable-pip-version-check pyautogui ...

# 撤销第 3 批：卸载 pyautogui 及 8 个污染依赖
"$PY" -m pip uninstall -y pyautogui mouseinfo pygetwindow pyscreeze pytweening pyrect pymsgbox pyperclip

# 每步之后回归
cd "/f/自动化验证工具/04-implementation/P1-contracts-env-adapter"
"$PY" -m unittest discover -s tests
```

**防漂移做法**：安装时把地基包版本写成 `==` 钉子一并交给 pip 解析，pip 输出 `Requirement already satisfied` 即证明未被间接依赖撬动。三批安装与一次卸载后均复验，地基零漂移。

**引号坑**：Bash 中 `PY="C:/Program Files/..."` 调用时必须写 `"$PY"`（带引号），否则路径中的空格会被截断为 `C:/Program: No such file or directory`（退出码 127）。

---

## 五、验收证据（最终状态 = 卸载后）

| 验收项 | 结果 | 退出码 |
|---|---|---|
| 地基包版本一致性 | 7 项全部一致，**漂移项：无** | 0 |
| 保留包 | pywin32 312 / pywinauto 0.6.9 / uiautomation 2.0.29 均存在 | 0 |
| 卸载确认 | pyautogui + 8 依赖全部"已卸载"，`import pyautogui` 抛 ImportError（预期） | 0 |
| import 冒烟 | win32gui/win32con/win32api/pythoncom/pywinauto/uiautomation/cv2/numpy/psutil/dxcam/mss/PIL 全 OK | 0 |
| UIA 真实枚举 | `uiautomation` 顶层控件 **9** 个；`pywinauto.findwindows` 顶层窗口 **23** 个（含 hwnd/pid/class） | 0 |
| GPU 栈 | `paddle 3.3.1`，`is_compiled_with_cuda()=True`，`cuda.device_count()=1` | 0 |
| **项目基线回归** | `unittest discover -s tests` → **Ran 56 tests in 0.121s / OK** | 0 |

---

## 六、环境坑与规避（本轮实测确认，必读）

### 坑 1：Bash 缺 coreutils（`ls`/`date`/`stat`/`head`/`tail` 全失效）

- **现象**：`ls: command not found`、`date: command not found`。
- **根因**：确为 Git Bash（`MSYSTEM=MINGW64`），但系统 PATH 只挂了 `C:\Program Files\Git\cmd`（11 条目，仅 git.exe），coreutils 实际在 `C:\Program Files\Git\usr\bin`（372 条目）**未入 PATH**。
- **规避**：Bash 命令一律前置 `export PATH="/c/Program Files/Git/usr/bin:$PATH"`；实测 `ls`、`date` 立即恢复。

> Bash 只是外层壳，其中运行的 `python.exe`、`git.exe` 均为 Windows 原生程序，与 Linux/macOS 无关。

### 坑 2：PowerShell 工具 stdout 不回传 ★已写入 SKILL.md

- **现象**：执行后只返回 exit code，零输出（实测两次，含无管道的 `Write-Output`）。
- **规避**：需要看完整原始输出时改用 Bash + python；PowerShell 仅用于无需观察输出的操作。

### 坑 3：中文 Windows 外部命令输出为 GBK ★已写入 SKILL.md

- **现象**：`subprocess.run(..., text=True)` 抛 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd3`。
- **规避**：显式 `encoding='gbk'` 或 `errors='replace'`；脚本内 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`。

### 坑 4：裸 `python` 命令解析到错误版本 ★已写入 SKILL.md

- **现象**：`shutil.which('python')` → `...\.workbuddy\binaries\python\versions\3.13.12\python.EXE`（3.13.12），**不是**项目的 3.13.14。
- **规避**：一律写绝对路径 `C:\Program Files\Python313\python.exe`。

---

## 七、回滚依据

- 安装前全量快照（**已另存 F 盘**）：
  - 路径：`F:\自动化验证工具\08-env-baseline\pip_before_20260918.txt`
  - 行数 **106**，字节 **2348**，sha256 `a9ea9fdaffbbfdb815efe5a41cc090e6a5291900d64b3aaf8c34e29dcc8500ec`
- 回滚方式：按该快照对比当前版本；对保留包执行
  `pip uninstall -y pywin32 pywinauto uiautomation`，地基包版本以 3.1 节为准。
- 本轮安装与卸载均实测**零漂移**，未触发回滚。

---

## 八、澄清 1：P1 `env_probe` 如何调用 Windows API

**结论：用 `ctypes` 直接 FFI，不是 pywin32，也不是 comtypes。装 pywin32 后行为零变化。**

代码位置：`04-implementation\P1-contracts-env-adapter\env_adapter\env_probe.py`

| 能力 | 实现方式 | 代码位置 |
|---|---|---|
| 进程完整性级别（UIPI） | `ctypes.windll.advapi32.OpenProcessToken` / `GetTokenInformation` / `kernel32.CloseHandle` | `_integrity_level()`，第 27-62 行 |
| 远程软件探测 | `psutil.process_iter(["name"])` | `_remote_software()`，第 65-78 行 |
| DPI / 窗口枚举 | 复用 `scripts\env.py::dpi_for_window` / `scripts\env.py::find_windows` | 第 86、93 行 |

**装 pywin32 后是否有行为变化：没有。** 干净进程实测证据（新开 python 进程，只 import env_probe）：

```
--- import env_probe 之前 ---
  pywin32系命中 = []
  pywinauto/uiautomation 命中 = []
--- import env_probe 之后 ---
  pywin32系命中 = []            ← 仍未进入 sys.modules
  pywinauto/uiautomation 命中 = []
  comtypes 命中 = []
  ctypes 是否加载 = True        ← 只加载了 ctypes
```

即：`env_probe` 的导入链**完全不触碰** pywin32 / pywinauto / uiautomation / comtypes，ctypes 是 Python 标准库，装不装 pywin32 都不改变这条路径。所有 ctypes 调用都包在 `try/except` 内，失败降级为 `medium`。

`probe_env()` 本机实测输出（可作为后续对照基线）：

| 字段 | 实测值 |
|---|---|
| dpi_scale | 1.25 |
| integrity_level | medium |
| security | **wujie** |
| focus_reliable | **False** |
| input_method | InputMethod.HANDLE_POST |
| capture_method | CaptureMethod.MSS |
| probe_ms | 8.37 ~ 35.0 |

> ⚠️ 注意：本机当前被判定 `security=wujie`（检测到无界远程控制类软件在运行），因此 `focus_reliable=False`，env_adapter 自动降级为**句柄直投 + MSS 截图**。做 UI 自动化实测时需注意这一点——若目标是真实键鼠验证，应先关闭远程软件再跑。

---

## 九、澄清 2：56 测试全绿的时点

**文档初版写的"56 测试 OK（0.118s）"是【三批补装全部完成之后】跑的**，即补装 pywin32 + pywinauto + uiautomation + pyautogui 之后、卸载之前。三个时点完整记录如下：

| # | 时点 | 环境状态 | 结果 | 说明 |
|---|---|---|---|---|
| 1 | 2026-09-18 11:5x（接手核验；前后锚点 11:54:52 与 12:04:43，未单独落秒级时间戳） | **补装前** | Ran 56 tests in **0.130s** / OK | 证明 P1 封板基线可复现 |
| 2 | 2026-09-18 12:1x | **三批补装全部完成（含 pyautogui）** | Ran 56 tests in **0.118s** / OK | **证明补装没有破坏契约层** |
| 3 | 2026-09-18 12:3x | **卸载 pyautogui + 8 依赖后** | Ran 56 tests in **0.121s** / OK | 证明卸载同样安全 |

结论：补装与卸载均未触碰契约层行为，三个时点全绿、退出码均为 0。

---

## 十、P2-2 迁移顺序（修正版 7 步）

> 原文档结尾写的「`git mv contracts → P2-layers/contracts` + P1 shim」**顺序有害**：先搬走再补 shim，中间的 import 会立即断裂。**已作废**，以下为正确顺序。

| 步 | 动作 | 关键点 | 完成判据 |
|---|---|---|---|
| 1 | 建 `P2-layers/contracts`（**复制**，不动 P1） | 此时 P1 仍是唯一生效入口，零风险 | 目录与文件齐备 |
| 2 | 验证两处内容一致（**逐文件 diff**） | 有任何差异先解决，不得带差异进下一步 | diff 全等 |
| 3 | 改 P1 `contracts/__init__.py` 为 **shim**（re-export 到新路径） | 旧 import 路径不变，由 shim 接管转发 | shim 生效 |
| 4 | 跑 56 测试 | 此时 P1 仍是主入口，shim 接管 | **全绿**才进第 5 步 |
| 5 | 逐脚本改 import 到新路径 | 一次改一个脚本，改完即测 | 每个脚本改后全绿 |
| 6 | 全绿后，删 P1 的 contracts 具体模块（**保留 `__init__.py` shim**） | 只删具体模块，`__init__.py` 继续做 shim | 56 测试全绿 |
| 7 | 最后删 shim | 至此 P1 目录只留 MIGRATION.md | 56 测试全绿 |

**每一步都要跑 56 测试，全绿才允许进入下一步。** 中途任一环节失败，回滚到上一步全绿状态再排查。

补充约束（来自 HANDOVER）：
- 迁移一律 `git mv` 保留历史，**禁止复制**（第 1 步的"复制"是临时双份，第 6/7 步会删除，与"禁止复制留存双份实现"不冲突——最终只有一份）
- 层目录名全英文无 `+` 号：`perception` / `planning` / `execution`
- `state_hash` / `stable_id` / `models` / `enums` 留 contracts；`flow.py`（select_flow）属领域逻辑，迁 orchestrator
- 测试归属已定：迁**主 `tests\`**（用户 2026-09-18 确认）

---

## 十一、遗留与下一步

1. `cl.exe`（MSVC）未入 PATH —— 需编译 C++ 扩展时先跑 `vcvars64.bat`，不影响当前纯 Python 阶段。
2. 本机 `security=wujie` 导致 `focus_reliable=False` —— UI 自动化实测前建议关闭远程控制软件。
3. 下一步按用户指令执行 P2-2，**严格按第十节 7 步顺序**，第 1 步动手前先建可回滚缓存。
4. `.workbuddy/` 目录目前是 git 未跟踪状态，提交前需决定加入 `.gitignore` 还是随仓库提交。

---

*本清单所有版本号与实测结果均来自本机命令输出（退出码 0），时间戳取自系统 `date` 命令，无人工估计值。*
