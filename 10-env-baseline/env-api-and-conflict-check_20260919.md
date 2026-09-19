# 环境 API 逐一验证 + 冲突/缺失/功能异常全面检测报告

- 检测时间：**2026-09-19 04:47 ~ 04:55 +0800**（系统时间实测）
- 解释器：`C:\Program Files\Python313\python.exe`（3.13.14）
- 检测口径：**项目实际调用面逐项实跑**（不采信文档描述）；源码调用点由 grep 抽取
- 原始输出：`F:\自动化验证工具\10-env-baseline\_evidence\10_env_full_check.txt`
- 可复现脚本：`verify_win32_api.py` / `probe_symbols.py` / `verify_env_full.py` / `check_metadata.py` / `verify_e2e.py`（均在 `F:\自动化验证工具\10-env-baseline\_tools\`）
- 关联：`env-incident_20260919_root-cause.md`、`env-damage-assessment_20260919.md`

---

## 一、Win32 API 逐一验证（源码抽取 46 项）

调用点来源：`scripts\env.py` / `sendinput.py` / `shot.py` / `env_adapter\env_probe.py`（grep `windll.*` / `WinDLL`）

| DLL | API 数 | 结果 |
|---|---|---|
| user32 | 33 | ✅ 实跑通过（含 EnumWindows 枚举到 **504** 个顶层窗口、EnumDisplayMonitors、GetMonitorInfoW、SendMessageTimeoutW(WM_NULL)、PostMessageW(WM_NULL)、SendInput(0 事件)、AttachThreadInput 配对进出、SetWindowPos 全 no-op 标志） |
| kernel32 | 8 | ✅ 实跑通过（含 `GlobalAlloc/GlobalLock/GlobalSize/GlobalUnlock` —— **注意：在 kernel32 而非 user32**，与项目实际绑定一致） |
| advapi32 | 4 | ✅ 实跑通过（OpenProcessToken(TokenIntegrityLevel) → GetTokenInformation → GetSidSubAuthorityCount → GetSidSubAuthority，UIPI 判定链完整） |
| shcore | 1 | ✅ 实跑通过（SetProcessDpiAwareness 返回 S_OK） |
| gdi32 | 2 | 🟡 仅确认可解析（盘点标注"当前未使用"） |
| user32 剪贴板写入 | 2 | 🟡 `EmptyClipboard` / `SetClipboardData` **主动不实跑**（会改写用户剪贴板）——需真实粘贴场景时再验 |

**合计 46 项：实跑通过 42 / 仅解析 4 / 失败 0。**

> 说明：首轮检测曾报 5 项"失败"，经 `probe_symbols.py` 用 GetProcAddress 原始句柄复核，全部是**我方首版脚本绑错 DLL**（把 `GlobalAlloc` 挂到 user32、把 `GetDC` 挂到 gdi32）。按项目真实绑定修正后 **0 失败**。已把"绑错 DLL 会假报缺失"记入经验。

---

## 二、Python 库功能实跑（23 项）

### 2.1 项目源码直接 import（10 项，全部 ✅）

| 库 | 版本 | 实跑动作与结果 | 耗时 |
|---|---|---|---|
| PIL | — | 建图 `(32,16) RGB` | 43 ms |
| cv2 | 4.10.0 | matchTemplate=1.000、imencode=True、ximgproc 可用 | 60 ms |
| dxcam | 0.3.0 | 抓帧 `(1440,2560,3) uint8` | 514 ms |
| mss | 10.2.0 | 抓屏 `2560×1440` | 71 ms |
| numpy | 2.3.5 | sum/dot 运算正常 | 0.1 ms |
| psutil | 7.2.2 | 230 进程、32 核、63.7 GB | 35 ms |
| pynvml | 模块在位 | 走 `ocr.py` 预加载路径读显存 **12282 MiB** | 21 ms |
| paddle | 3.3.1 | `cuda=True`、matmul 结果正确 | 4.1 s（首次加载） |
| paddleocr | 3.7.0 | 版本可读 | 3.1 s |
| paddlex | 3.7.2 | 版本可读 | 0 ms |

### 2.2 已装未直接调用（13 项，全部 ✅）

comtypes(含 `comtypes.client.GetModule`)、uiautomation（前台控件可读）、pywinauto(Desktop)、pywin32(win32gui.EnumWindows=503)、PyYAML、requests、openpyxl、python-dateutil、pycryptodome(AES)、protobuf(序列化)、colorlog、colorama(init/deinit)、huggingface_hub。

---

## 三、外部命令 / 进程（subprocess 调用面）

| 调用 | 实测 |
|---|---|
| `nvidia-smi --query-gpu=name,memory.total,driver_version` | ✅ rc=0，`NVIDIA GeForce RTX 4080 Laptop GPU, 12282 MiB, 616.56`，**147 ms/次** |
| `taskkill /?` | ✅ rc=0（项目用于杀进程，帮助输出正常） |
| `pynvml` 读显存（`ocr.py` 用它替代 nvidia-smi） | ✅ 20.8 ms（比 nvidia-smi 快约 7 倍） |
| `WgcCapture.exe` | ⚠ **不存在** → 截图第一档 WGC 不可用，实际走 dxcam/mss（**盘点已记录，非新增缺陷**） |
| `uitool.py` 子进程解释器 | ℹ 用 `sys.executable` → **启动 uitool 的解释器必须与项目解释器一致**，否则子脚本会用错 Python |

---

## 四、冲突检测

### 4.1 实发现（2 项，均为低风险但会干扰后续 pip）

| # | 问题 | 证据 | 影响 | 建议 |
|---|---|---|---|---|
| **C1** | **僵尸 dist-info：`opencv_python-5.0.0.93` 与 `opencv_python-4.10.0.84` 并存** | `importlib.metadata.distributions()` 列出 opencv-python **两条**（4.10.0.84 / 5.0.0.93）；5.0.0.93 那份**无 RECORD**；`pip list` 只显示 4.10.0.84 → 两套视图不一致 | 任何读 metadata 的依赖判断（`pip check`、`paddlex.is_extra_available`、`pip install` 解析）可能读到 **5.0.0.93 的版本号**，导致版本判断错误或误触发重装 | 清理该僵尸目录（删除即进回收站，可回滚）——**待你确认** |
| **C2** | **`pynvml` / `nvidia_smi` 模块在、但 pip 看不见** | 模块文件在（`pynvml.py` 56 KB），`importlib.metadata` 无 `nvidia-ml-py` 记录（其 dist-info 已被删） | 依赖审计/`pip check` 漏检；若将来条件触发 pip 解析，可能重复安装或版本冲突 | 可选：用 wheel 覆盖法补回 `nvidia-ml-py` 的 dist-info（只补元数据，不动模块） |

### 4.2 排除项（逐项实测，均正常）

| 检查 | 结果 |
|---|---|
| `pip check` | 仅 1 条：`paddlepaddle-gpu 3.3.1 requires nvidia-cudnn-cu12==9.5.1.17, but you have 9.9.0.52`（**盘点基线原有，非本轮引入**） |
| 同名多版本共存 | 仅 C1（opencv-python） |
| `~` 前缀僵尸元数据 | **无** |
| 元数据孤儿（有 dist-info、模块全不可导入） | **无** |
| 共享命名空间风险 | `opencv-python` + `opencv-contrib-python` 同时存在且**版本一致 4.10.0.84**（paddlex 要求 contrib==4.10.0.84，合规）；`paddlepaddle`(CPU) 已卸载，仅留 GPU 版 ✅ |
| nvidia CUDA 六件套 | cudnn 9.9.0.52 / cublas 12.6.4.1 / cuda-runtime 12.6.77 / cufft 11.3.0.4 / curand 10.3.7.77 / cusparse 12.5.4.2 —— 元数据齐全 |
| 解释器冲突 | 裸 `python` → `.workbuddy\binaries\python\3.13.12`；项目用 `C:\Program Files\Python313`（3.13.14）→ **已知坑，一律绝对路径** |
| 副作用文件 | `comtypes\gen`（COM 缓存正常生成）、`six.py`、`pynvml.py`、`cv2\py.typed` 均正常在位 |
| 已注册杀软 | `(空，未注册)`；Defender cmdlet 不存在 → **不是杀软拦截**（与根因取证一致） |

---

## 五、功能异常扫描

| 检查 | 结果 |
|---|---|
| 导入期 warnings（13 个关键库） | ✅ **无告警**（此前 `mss.mss` 的 DeprecationWarning 只在本方脚本调用 `mss.mss()` 时出现；项目 `shot.py` 亦用 `mss.mss()` → **建议后续改用 `mss.MSS`**，属代码级小项） |
| `ocr.py` 是否残留 subprocess 调 nvidia-smi | ✅ 无（仅注释提及，实测代码走 pynvml） |
| `shot.py` 区域截图修复（BUG-1） | ✅ `_region_box` 在位；实跑 `--region 200,200,320,200` 返回 `[320,200]` |
| `ocr.py` OCR 单例（BUG-3） | ✅ `def get_ocr` 在位；常驻模式 infer 901→106 ms |
| BUG-4 `framework` 被安全软件污染 | ⚠ **仍存在**（实测 `framework='wujie'`、`security='wujie'`）→ 待 P2 恢复后修 |
| BUG-2 `env_adapter` 零引用 | ⚠ **仍存在**（可显式导入，但 8 个脚本无一引用）→ 待接线 |
| 磁盘余量 | C: 200 GB 总 / **72 GB 剩**（64%）；F: 1908 GB 总 / **991 GB 剩**（48%） |

---

## 六、端到端功能验证（快照 04:51:31）

| 项 | 实测 |
|---|---|
| 56 单测 | `Ran 56 tests in 0.339s — OK`（rc=0） |
| 区域截图 | `{"engine":"dxcam","mode":"region 200,200 320x200","size":[320,200]}` ✅ |
| 模板匹配 | `confidence 1.0`，坐标 `(0,0,320,200)` ✅ |
| 差分比对 | `diff_pct 0.0, changed false` ✅ |
| OCR 常驻 | `{"ready":true,"gpu":12282,"limit_mb":9825}`；冷启动 8888 ms；**22 条**，901 → 106 ms ✅ |
| 环境探测 | `remote=wujie browser=None framework=wujie security=wujie focus=False`；`input=handle_post`；`capture=mss` ✅（与盘点一致） |
| UIA | 前台 `WorkBuddy` / PaneControl / 直接子控件 2 ✅ |

---

## 七、结论

1. **API 层零失败**：46 项 Win32 API 实跑通过 42、仅因"会改动用户剪贴板/盘点标注未使用"而保留 4 项仅解析，**失败 0**；23 个 Python 库功能实跑全部通过；3 个外部命令全部正常。
2. **无阻塞性冲突/缺失**：`pip check` 仅剩基线原有 1 条；无元数据孤儿、无 `~` 僵尸元数据。
3. **两项低风险隐患待你拍板**：C1 僵尸 `opencv_python-5.0.0.93.dist-info`（建议清理）、C2 `pynvml` 元数据缺失（建议补元数据）。
4. **两项已知代码级缺陷**（非环境问题，待 P2 恢复后处理）：BUG-4 framework 污染、BUG-2 env_adapter 未接线。
5. 所有开发工作**保持暂停**，等待你的指示。

---

## 附：API 调用点抽取命令（可复现）

```bash
cd F:\自动化验证工具\04-implementation
grep -rh -o -E "(windll|WinDLL)\.[a-z0-9]+\.[A-Za-z_]+" --include=*.py .
grep -rn -E "subprocess\.(run|Popen)" --include=*.py .
grep -rh -E "^\s*(import|from)\s+[a-zA-Z_]" --include=*.py . | awk '{print $2}' | cut -d. -f1 | sort -u
```
