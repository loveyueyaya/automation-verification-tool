# P2-1 验收报告：依赖清理 + 阻塞 BUG 修复

> 执行时间：2026-09-18 23:00 ~ 2026-09-19 00:50
> 项目根：`F:\自动化验证工具` ｜ 解释器：`C:\Program Files\Python313\python.exe`
> 硬性规则遵守情况：① 全部结论本机实跑；② 每改一次跑一遍 56 单测；③ 未碰目录结构、未新增业务功能（仅改 2 个已有文件）

---

## 0. 结论速览

| 任务 | 验收标准 | 结果 | 实测要点 |
|---|---|---|---|
| 1. OpenCV 冗余清理 | 三包 → 一包 | ⚠ **部分达成（3→2）** | headless 已卸载 ✅；contrib **不能卸**（PaddleOCR 硬依赖，见 §4.1） |
| 2. 显存监控换 pynvml | 读数准确、无缓存需求 | ✅ 达成 | pynvml 读 12282 MiB，与 nvidia-smi 完全一致；单次 **0.0017 ms** vs nvidia-smi **136.18 ms** |
| 3. 修 BUG-1 区域截图 | 不同位置/DPI 下正确 | ✅ 达成 | 5 组区域与全屏裁剪 **像素完全等价（5/5）**；CLI 输出 640×360（修复前为 2560×1440） |
| 4. 修 BUG-3 OCR 重复初始化 | 首次/后续耗时对比 | ✅ 达成 | 单例首次 5255 ms → 复用 **0.0007 ms**；常驻模式请求 417→80 ms |
| 5. BUG-2 / BUG-4 本轮不修 | 保持原状 | ✅ 遵守 | 未改动 env_adapter 任何文件 |
| 单测 | 56 个全绿 | ✅ 全绿 | `Ran 56 tests in 0.126s — OK`（每步改动后均已复跑） |

---

## 1. 变更文件清单

| 绝对路径 | 改动 | 说明 |
|---|---|---|
| `F:\自动化验证工具\04-implementation\P1-contracts-env-adapter\scripts\shot.py` | +32 / −6 | BUG-1：新增 `_region_box()`，`_try_dxcam/_try_mss` 支持 region，`grab()` 透传 region；dxcam 返回 None 时降级 mss |
| `F:\自动化验证工具\04-implementation\P1-contracts-env-adapter\scripts\ocr.py` | +59 / −17 | 任务2：删除 `nvidia-smi` subprocess 与 `nvapi` 死代码，改 pynvml；任务4：新增 `get_ocr()` 模块级单例，`main()` 两处调用改为单例 |

**未新增 / 未删除任何项目文件**，`git diff --stat` 仅上述 2 个文件。

---

## 2. 各项实跑数据

### 2.1 任务 1：OpenCV 清理

```bash
# 清理前
pip list | grep -i opencv
# opencv-contrib-python  4.10.0.84
# opencv-python          5.0.0.93
# opencv-python-headless 5.0.0.93

# 清理后
pip list | grep -i opencv
# opencv-contrib-python  4.10.0.84   ← 因 paddlex 硬依赖保留（见 §4.1）
# opencv-python          5.0.0.93    ← cv2 二进制由它提供
python -c "import cv2; print(cv2.__version__)"   # 5.0.0
```

图像功能回归（清理后）：

| 检查项 | 结果 |
|---|---|
| `cv2.__version__` | 5.0.0 |
| `cv2.__file__` | `C:\Program Files\Python313\Lib\site-packages\cv2\__init__.py` |
| `matchTemplate(TM_CCOEFF_NORMED)` | 1.0 |
| `absdiff` 自差分 | 0 |
| `IMREAD_GRAYSCALE / IMREAD_COLOR` | 0 / 1 |
| `locate.py template` 实跑（640×360） | `confidence: 1.0` |
| `locate.py verify` 实跑 | `diff_pct: 0.0, changed: false` |
| 56 单测 | OK |

### 2.2 任务 2：pynvml 替换 nvidia-smi

```python
# 可复现验证代码
import os, ctypes, time, subprocess, pynvml
if pynvml.nvmlLib is None:                       # Windows 路径兼容（见 §4.2）
    for c in [os.path.join(os.getenv("ProgramFiles","C:/Program Files"),
                           "NVIDIA Corporation","NVSMI","nvml.dll"), "nvml.dll"]:
        try: pynvml.nvmlLib = ctypes.CDLL(c); break
        except OSError: continue
pynvml.nvmlInit()
h = pynvml.nvmlDeviceGetHandleByIndex(0)
i = pynvml.nvmlDeviceGetMemoryInfo(h)
print(i.total//1024//1024, i.used//1024//1024)
```

| 指标 | pynvml | nvidia-smi（旧方案） |
|---|---|---|
| 显存总量读数 | **12282 MiB** | 12282 MiB（一致 ✅） |
| 已用 | 2318 MiB | — |
| 单次调用耗时 | **0.0017 ms** | **136.18 ms**（慢约 8 万倍） |
| 是否需要缓存 | 不需要 ✅ | 需要（旧代码每次 load_ocr 都付 151.79 ms） |

`ocr.py --serve` 的 ready 行实测输出：`{"ready": true, "gpu": 12282, "limit_mb": 9825}` —— 由 pynvml 提供，非 nvidia-smi。

### 2.3 任务 3：BUG-1 区域截图

```python
# 可复现验证代码（像素级等价判定）
import sys, numpy as np
sys.path.insert(0, r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter\scripts")
import shot
eng = shot.ShotEngine(); full = eng.grab()
for reg in ["0,0,320,200","200,200,320,200","1000,600,400,300","1500,900,640,360","2400,1300,160,140"]:
    x,y,w,h = [int(v) for v in reg.split(",")]
    got = eng.grab(region=reg); exp = full[y:y+h, x:x+w]
    print(reg, got.shape, np.array_equal(got, exp))
```

| region | 修复前实得 | 修复后实得 | 与全屏裁剪像素等价 |
|---|---|---|---|
| `0,0,320,200` | 2560×1440 ❌ | 320×200 | ✅ |
| `200,200,320,200` | 2560×1440 ❌ | 320×200 | ✅ |
| `1000,600,400,300` | 2560×1440 ❌ | 400×300 | ✅ |
| `1500,900,640,360` | 2560×1440 ❌ | 640×360 | ✅ |
| `2400,1300,160,140` | 2560×1440 ❌ | 160×140 | ✅ |

CLI 端到端：`shot.py --out ... --region 500,300,640,360` → `{"size": [640, 360], "ms": 562.8}`（修复前 `size` 恒为 `[2560, 1440]`）。
区域抓取耗时 0.6–70 ms（命中 dxcam 新帧时 <2 ms，未命中时回退 mss 取帧）。

> DPI 说明：本机缩放为 100%（`GetDpiForSystem()=96`），**无法在本机复现 125%/150% 场景**；
> 代码已保证 `env.set_dpi_awareness()`（PER_MONITOR_V2，上下文 −4）在截图前调用，坐标统一为物理像素，
> 高 DPI 目标机需另行回归（不谎报已验证）。

### 2.4 任务 4：BUG-3 OCR 单例化

```python
import sys, os, time
sys.path.insert(0, r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter\scripts")
import ocr
t=time.perf_counter(); o1=ocr.get_ocr(); t1=(time.perf_counter()-t)*1000
t=time.perf_counter(); o2=ocr.get_ocr(); t2=(time.perf_counter()-t)*1000
```

| 指标 | 实测 |
|---|---|
| 首次 `get_ocr()`（含模型加载） | 5255 ms（另一轮实测 9108 ms，含 CUDA 初始化） |
| 第二次 `get_ocr()` | **0.0007 ms** |
| `o1 is o2` | True ✅ |
| `recognize()` 第 1 次（预热） | 430.3 ms |
| `recognize()` 第 2/3 次 | **64.3 / 64.0 ms** |
| 进程级单发（`ocr.py --image`，640×360） | 6.9 s（修复前同场景 10.97 s） |
| `--serve` 常驻：ready | 4603 ms（一次性） |
| `--serve` 常驻：请求耗时 | 417.8 → **80.3 → 79.7 ms** |

---

## 3. 单测结果（每步改动后复跑）

```
cd /d F:\自动化验证工具\04-implementation\P1-contracts-env-adapter
C:\Program Files\Python313\python.exe -m unittest discover -s tests
```

| 时点 | 结果 |
|---|---|
| 改动前基线 | Ran 56 tests in 0.129s — OK |
| 卸载 OpenCV 两包后 | Ran 56 tests in 0.129s — OK |
| 恢复 contrib + cv2 5.0 后 | Ran 56 tests in 0.127s — OK |
| 改 shot.py（BUG-1）后 | Ran 56 tests in 0.132s — OK |
| 改 ocr.py（pynvml + 单例）后 | **Ran 56 tests in 0.126s — OK** ✅ |

---

## 4. 遇到的依赖冲突与解决方案

### 4.1 OpenCV 与 PaddleOCR（paddlex）的硬冲突 —— 本轮最重要的发现

**现象**：卸载 `opencv-contrib-python` 后，PaddleOCR 直接不可用：
```
paddlex.utils.deps.DependencyError: `OCR` requires additional dependencies ...
RuntimeError: A dependency error occurred during pipeline creation.
```

**根因（实测定位）**：
1. `paddlex 3.7.2` 把 `opencv-contrib-python==4.10.0.84` 声明为 `ocr` / `ocr-core` extra 依赖；
2. `paddleocr` 初始化时调用 `pipeline_requires_extra("ocr", alt="ocr-core")`，
   而 `is_extra_available()` 走 `get_dep_version(dep)` —— **检查的是 dist 元数据是否存在，不是 cv2 能否 import**；
3. 实测逐项可用性：`ocr-core` 6 项依赖中，仅 `opencv-contrib-python` 一项因卸载而 False → 整条 extra 判定 False → 拒绝创建流水线。

**实测验证的因果链**：
```
安装 opencv-contrib-python==4.10.0.84 → cv2 立刻变成 4.10.0   （证明两包共用 cv2/ 命名空间）
再覆盖 opencv-python==5.0.0.93        → cv2 回到 5.0.0        （二进制由后者提供）
此时：contrib dist 仍在（paddlex 通过）+ cv2 = 5.0（项目期望）→ OCR 与图像功能均正常
```

**最终采用**：`opencv-python 5.0.0.93`（提供 cv2 5.0）+ `opencv-contrib-python 4.10.0.84`（仅作为 paddlex 的元数据依赖），`opencv-python-headless` 已卸载。

**"三包变一包"未能达成的原因与可选方案（需你决策）**：

| 方案 | 做法 | 代价 / 风险 |
|---|---|---|
| A（当前采用） | 保留 2 包，contrib 仅作元数据 | 与基线状态一致（原为 3 包），最稳；包数 3→2 |
| B | 只保留 `opencv-contrib-python`，卸载 `opencv-python` | 名义上 1 包，但 **cv2 降到 4.10**（较 5.0 退版），且 contrib 体积更大 |
| C | 升级 paddleocr/paddlex 到不再依赖 contrib 的版本 | 治本，但属版本升级，超出"本轮只做前置准备"范围，且 paddle GPU 包需从官方源装 |
| D | 为 paddlex 伪造 `opencv-contrib-python` 的 dist-info | 欺骗第三方库依赖检查，脆弱、不推荐 |

### 4.2 pynvml 在 Windows 上找不到 nvml.dll

`pynvml` 只在 `%ProgramFiles%/NVIDIA Corporation/NVSMI/nvml.dll` 找库；本机该路径不存在，`nvml.dll` 位于 `C:\Windows\System32\nvml.dll`，直接 `nvmlInit()` 报 `NVML_ERROR_LIBRARY_NOT_FOUND`。
**解决**：`_gpu_total_mb()` 中先按候选路径（NVSMI → `nvml.dll`）用 `ctypes.CDLL` 预加载并赋值给 `pynvml.nvmlLib`，再 `nvmlInit()`。已实测通过（读数 12282 MiB）。

### 4.3 pip 中断操作导致的环境损伤（严重，已修复）

**起因**：`pip uninstall` / `pip install --force-reinstall` 在共享命名空间包（cv2）上执行时抛 `OSError [WinError 3]`，随后 `pip install --force-reinstall opencv-python` 又把 numpy 当成待升级依赖卸载到一半 → **numpy 被破坏**；此后多次 pip 操作（含被 SIGTERM 打断的批量卸载）进一步把 29 个包的 dist-info/文件删成半成品。

**损伤清单（比基线快照 `10-env-baseline\pip_before_20260918.txt` 少 29 个包；RECORD 体检另有 31 个包文件缺失）**：
`numpy`（仅剩 7 个文件）、`paddle`（缺 `__init__.py` 等 134 个文件，退化为命名空间包）、`cudnn64_9.dll`、`certifi`、`dxcam`、`aiohttp`、`cryptography`、`protobuf`、`pycryptodome`、`mss`、`comtypes`、`nvidia-cublas/cuda-runtime/curand/cusolver/cusparse` 等。

**修复方法（关键经验）**：沙箱会拦截 pip 的**批量删除**（`SAFE_DELETE_BULK_GUARD_ERROR`），因此改为**覆盖式修复**——
`pip download` 取 wheel → 解压 → 按"本地缺失才写入"覆盖回 site-packages，**全程不删除任何文件**：

```bash
C:\Program Files\Python313\python.exe F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env.py    # 22 个小/中包
C:\Program Files\Python313\python.exe F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env2.py   # protobuf/multidict/frozenlist/h11/colorama + paddlepaddle-gpu(官方源)
C:\Program Files\Python313\python.exe F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env3.py   # nvidia CUDA 系列
```
- paddlepaddle-gpu 3.3.1 **不在 PyPI**，需 `-i https://www.paddlepaddle.org.cn/packages/stable/cu126/`；
- 合计补回：paddle 118 个文件、cudnn 22 个、cufft 13 个、pywin32 610 个、networkx 600 个等。

**修复后体检**：14/14 关键库可导入（numpy / PIL / cv2 / mss / dxcam / psutil / comtypes / yaml / requests / uiautomation / **pynvml** / paddle / paddleocr / paddlex），`import paddle; is_compiled_with_cuda()` = **True**。

### 4.4 遗留的已知依赖告警（与基线一致，未恶化）

```
pip check → paddlepaddle-gpu 3.3.1 requires nvidia-cudnn-cu12==9.5.1.17,
            but you have nvidia-cudnn-cu12 9.9.0.52
```
基线快照中已是 9.9.0.52 且 OCR 正常工作，**本轮刻意不升级**（升级会引发更大范围版本漂移）。

---

## 5. 遗留与下一轮建议

1. **OpenCV 单包方案待决策**（§4.1 的 B / C 方案）—— 需要你确认是否接受 cv2 退到 4.10，或同意升级 paddleocr/paddlex。
2. **BUG-2（env_adapter 零引用）与 BUG-4（framework 误判）** 按计划留到 P2-2 骨架搭建时一并处理。
3. **高 DPI / 多屏回归**：本机 100% 缩放无法复现，建议在 125%/150% 目标机补测（截图坐标 + OCR 区域裁剪）。
4. **环境基线应重新冻结**：本轮依赖有变动（新增 `nvidia-ml-py3 7.352.0`；opencv 3→2 包），建议 P4-2 前重跑一次 `pip freeze` 覆盖 `10-env-baseline\pip_before_20260918.txt`。
5. **教训**：共享命名空间包（cv2 类）绝不要用 `pip install --force-reinstall`（会连带卸载 numpy 等依赖）；
   本机修复应一律用"下载 wheel + 覆盖写入"，不要用批量 uninstall。

---

## 5.5 补记（2026-09-19 01:35 复核，环境状态已变更）

> 因上一轮对话记录丢失，应要求对当前环境做了逐项复核。**结论：环境已不是本报告 §2.1 描述的 5.0 状态，
> 而是两个 OpenCV 包统一到 4.10.0.84。**以下为机器实测结果，以此为准。

**与基线的精确差分**（`pip_before_20260918.txt` vs 当前）：

| 类别 | 内容 |
|---|---|
| 新增 | `nvidia-ml-py3 7.352.0`、`pywin32 312`、`pywinauto 0.6.9`、`uiautomation 2.0.29`、`ruamel-yaml 0.19.1`、**`winrt-windows-* 11 个（3.2.1）`** |
| 缺失 | `opencv-python-headless 5.0.0.93`（有意卸载）、`ruamel.yaml`/`winrt-windows.*`（仅打包名规范化差异，非真缺失） |
| 版本变化 | **`opencv-python` 5.0.0.93 → 4.10.0.84** |
| 包总数 | 109（基线 106；+winrt 11、+pywin32、+uiautomation、+pywinauto、+nvidia-ml-py3、+ruamel-yaml、+pip；−headless、−opencv-python 5.0 …） |

**当前实测状态**：

| 检查项 | 结果 |
|---|---|
| OpenCV 包 | `opencv-contrib-python 4.10.0.84` + `opencv-python 4.10.0.84`（headless 已卸） |
| `cv2.__version__` | **4.10.0**（`C:\Program Files\Python313\Lib\site-packages\cv2\__init__.py`） |
| contrib 扩展 | `cv2.ximgproc` ✅ / `cv2.aruco` ✅ / `cv2.xfeatures2d` ✅（`cv2.tracking` 不存在，4.10 无此顶层名） |
| cv2 目录完整性 | **107 MB / 135 个文件**，含 `cv2.pyd`、`opencv_videoio_ffmpeg4100_64.dll` —— 完整安装（此前"只剩 439K"的残缺状态已不复存在） |
| 孤儿 dist-info | `site-packages\~*` **无残留** ✅ |
| 项目 6 个 cv2 API | `imread` / `IMREAD_GRAYSCALE,IMREAD_COLOR` / `matchTemplate`(1.0) / `minMaxLoc` / `absdiff`(0) 全部正常 |
| 56 单测 | `Ran 56 tests in 0.147s — OK` ✅ |
| paddle | `3.3.1`，`is_compiled_with_cuda()` = **True** ✅ |
| OCR 端到端 | 可初始化并识别 ✅ |
| `shot.py --region 400,400,320,200` | 输出 **320×200**（BUG-1 修复仍生效）✅ |
| `pip check` | 仅 `paddlepaddle-gpu 需 nvidia-cudnn-cu12==9.5.1.17，实装 9.9.0.52`（基线既有） |
| winrt / WGC 能力 | `winrt.windows.graphics.capture` **可导入** ✅（P3-2 的 dxcam[winrt] 前置已具备） |

**另外补齐的一处元数据缺口**：此前用"覆盖式修复"补回的 16 个包（aiohttp / certifi / cryptography / dxcam / networkx / nvidia-cudnn / nvidia-cufft 等）
只有包文件、缺 `RECORD` 等 dist-info，导致 pip 元数据不完整。现已用
`F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env4_metadata.py` 从 wheel 内补齐元数据（各 3~5 个文件），`pip check` / `pip list` 恢复可信。

**📌 对截图所述内容的核对结论（详见对话回复）**：截图称 `paddlex → 3.7.7`、`paddleocr → 3.7.7`，
**实测为 `paddlex 3.7.2`、`paddleocr 3.7.0`**，与截图不符（其余各项均与实测一致）。

**⚠ 待你决策（两件）**：
1. `opencv-python` 已从 5.0.0.93 降到 **4.10.0.84**，是否接受？若要不要，恢复方式是用 wheel 覆盖（**不要**再用 `pip --force-reinstall`，见 §4.3）。
2. `paddlepaddle 3.3.1`(CPU) 与 `paddlepaddle-gpu 3.3.1`(GPU) 两个 dist 共存于同一 site-packages。
   实测 `is_compiled_with_cuda()=True`，说明**文件层面 GPU 版生效**、功能正常；
   但两者共享 `paddle/` 目录，**任何一次 pip 安装/卸载其中任一个都可能互相破坏**（这正是 §4.3 事故的成因之一）。
   **建议：本轮不动**，在 P4-2 基线冻结时用"覆盖式重装 GPU 版 + 删除 CPU dist-info"的保守方式处理。

---

## 6. 本轮产出文件

| 文件 | 绝对路径 |
|---|---|
| 验收报告（本文档） | `F:\自动化验证工具\05-tests\P2-1_依赖清理与BUG修复_验收报告.md` |
| 环境修复脚本①（小/中包） | `F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env.py` |
| 环境修复脚本②（paddle 等） | `F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env2.py` |
| 环境修复脚本③（nvidia CUDA） | `F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env3.py` |
| 环境修复脚本④（dist-info 元数据补齐 + 基线差分） | `F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\repair_env4_metadata.py` |
| 恢复/修复版本清单 | `F:\自动化验证工具\10-env-baseline\_tools\legacy_repair\_restore_reqs.txt`、`_repair_reqs.txt`、`_repair_small.txt` |
| pip 残留备份（未删除，可回溯） | `F:\自动化验证工具\10-env-baseline\_local_assets\_backup_opencv_stale\` |
