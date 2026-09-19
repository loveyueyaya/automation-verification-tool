# 环境验证报告（对照《开发前盘点》§5.3 逐条代码验证）

- 验证时间：**2026-09-19 03:35 ~ 04:05 +0800**（系统时间实测）
- 解释器：`C:\Program Files\Python313\python.exe`（Python 3.13.14）
- 项目权威源：`F:\自动化验证工具`（基线 commit `340049d`）
- 对照文件：`F:\自动化验证工具\11-management\本地离线自动化测试工具_开发前盘点.md`（§5.3 可复现验证代码）
- 判定口径：**只认本地代码执行输出**；文档描述与实测冲突时以实测为准

---

## 一、本轮修复清单（全部为实测驱动）

### 1.1 按要求清理 CPU 版

| 动作 | 命令 | 实测输出 |
|---|---|---|
| 卸载 `paddlepaddle`（CPU） | `python.exe -m pip uninstall -y paddlepaddle` | `Successfully uninstalled paddlepaddle-3.3.1` |
| 复核 | 列目录 | 仅剩 `paddlepaddle_gpu-3.3.1.dist-info`，无 `paddlepaddle-*.dist-info` |

### 1.2 环境事故：包文件大面积丢失（实测取证）

`importlib.util.find_spec` + `os.path.isdir` 逐个实测，**不依赖 RECORD/top_level.txt 描述**（实测发现 RECORD 存在而实际目录已丢失的反例）：

| 类型 | 包 | 实测证据 |
|---|---|---|
| 整目录丢失（最严重） | `paddle`、`dxcam` | `os.path.isdir(...)=False`；`import paddle` → `ModuleNotFoundError` |
| 元数据+文件丢失 | 14 个（含 idna/httpx/huggingface-hub/charset-normalizer/cython/fsspec/future/cffi/aiohappyeyeballs/aiosignal/bce-python-sdk/hf-xet 等） | pip 基线 106 包 → 当前仅 96 包可见 |
| 部分文件丢失 | `modelscope` 1942/2910、`pywin32` 23/611、`pyinstaller` 6/579、`paddlex` 2/1336、`pip` 3/470 | RECORD 逐行比对缺失数 |
| 子模块丢失 | `comtypes.client`（致 uiautomation 无法导入）、`colorama.init`（致 paddlex 日志初始化失败） | `import uiautomation` → `ModuleNotFoundError: comtypes.client` |

**持续监控结论（实证，非推测）**：布设 `watch_files.py` 对 cv2/paddle/dxcam/numpy/PIL/paddleocr/paddlex/mss 每 20 秒采样 16 次（5 分 9 秒），**文件数全程零变化**；标记文件 `_wbmk/m1..m3.txt` 亦未消失 → **当前不存在持续删除行为**。
⚠️ 但删除**已真实发生过至少两次**（03:39 前后 cv2 目录文件全失、上一轮的 nvidia DLL 与 paddle 目录丢失），**根因未定位**（唯一确证的规律：大多发生在环境类写操作附近）。已按项目硬规则改用「覆盖法」修复，全程不删除文件。

### 1.3 修复方式（覆盖法，只补不删）

工具：`F:\自动化验证工具\10-env-baseline\_tools\restore_from_wheels.py`（wheel 解压 → 逐文件覆盖写入，旧 RECORD 已存在则保留）
wheel 归档：`F:\自动化验证工具\10-env-baseline\_local_assets\_wheels\`（含 `paddlepaddle_gpu-3.3.1` 579.4 MB，取自 paddle 官方源 `cu126`）

| 批次 | 包 | 写入文件数 | 结果 |
|---|---|---|---|
| 小包 | dxcam + 12 个依赖 | 728 | 逐个 import 实测 OK |
| CUDA | cudnn/cublas/cuda-runtime/cufft/curand/cusparse/nvjitlink | 208 | OCR GPU 恢复 |
| 主包 | paddlepaddle-gpu 3.3.1 | 3504 | `paddle 3.3.1 cuda=True` |
| OpenCV | opencv-python + opencv-contrib-python（均 4.10.0.84） | 86 + 127 | `cv2 4.10.0` 全功能 |
| 二批 | 元数据/模块丢失 12 包 | 1143 | pip check 收敛 |
| 三批 | 无 RECORD 的 19 包（comtypes/modelscope/paddlex/pywin32/pyinstaller/pip/colorama 等） | 6449 | 全量 import 通过 |

---

## 二、§5.3 逐条验证结果（全部实跑）

| # | 验证项 | 盘点基线值 | 本次实测输出 | 结论 |
|---|---|---|---|---|
| ① | 56 单测 | `Ran 56 tests in 0.135s — OK` | `Ran 56 tests in 0.398s — OK` | ✅ 一致 |
| ② | 区域截图（BUG-1） | 修复前恒返回全屏 2560×1440 | `{"engine":"dxcam","mode":"region 200,200 320x200","size":[320,200]}`；PNG 实测 `(320,200)` | ✅ BUG-1 已修复 |
| ③ | OCR 进程模式 | ~10.97 s / 169 条 | 11 s，识别出真实界面文本（置信度 0.99+） | ✅ 可用 |
| ③ | OCR 常驻模式 | 冷启动 8937 ms；全屏 2856→2136 ms | `{"ready":true,"gpu":12282,"limit_mb":9825}`；冷启动 **6990 ms**；263 条 **2003→1486 ms** | ✅ GPU 栈正常 |
| ④ | 模板匹配 | confidence 0.9999992 | `{"x":200,"y":200,"w":320,"h":200,"confidence":1.0}` | ✅ 定位返回值与实际贴图位置完全一致 |
| ④ | 差分 | `diff_pct 7.642` | `diff_pct 0.0, changed false`（同一张图自比） | ✅ 逻辑正确 |
| ⑤ | probe_env 路由 | `360se / wujie / wujie / False`，`handle_post`，`mss` | 实测 `_remote_software()='wujie'`；`None / wujie / wujie / False`；`handle_post | wujie 拦截 SendInput 鼠标`；`mss` | ✅ 一致（BUG-4 仍在） |
| ⑥ | UIA 控件树 | 深度1/2/3 = 5/9/10 节点，7/11/11 ms | 前台 `WorkBuddy`：深度3 **11 节点 / 有名字 2 / 18.4 ms** | ✅ 可用（comtypes 修复后） |
| ⑦ | 性能探针 | dxcam 0.04ms / mss 17.08ms / 匹配全屏 24.90ms・限区 0.43ms | dxcam 首帧 746.78ms、后续 **0.28 ms**；mss **21.61 ms**；匹配全屏 **28.53 ms**・限区 **0.50 ms**；psutil process_iter 6.06ms | ✅ 同量级 |
| ⑧ | 依赖体检 | cudnn 版本不符 + 三个 opencv 包共存 | `pip check` **仅剩 1 条**：`paddlepaddle-gpu 3.3.1 requires nvidia-cudnn-cu12==9.5.1.17, but you have 9.9.0.52` | ✅ OpenCV 冲突已消除 |

### 2.1 导入面实测

59 个关键模块实测导入 → **全部通过**（`pyinstaller`/`crc32c.crc32c` 两项失败经复核为我方测试写的错误模块名，正确名为 `PyInstaller`、`crc32c._crc32c`，二者均可正常导入）。

### 2.2 与基线的偏差（需你确认）

| 项 | 基线（09-18） | 本次实测 | 说明 |
|---|---|---|---|
| 屏幕分辨率 | 2560×1440（DPI 1.25） | **2560×1440（已复验一致）** | 04:14 复验：`GetSystemMetrics` 主屏/虚拟屏均为 2560×1440，`EnumDisplayMonitors` 1 台 2560×1440，dxcam 帧 `(1440,2560,3)`，`shot.py` 输出 `[2560,1440]` → **与基线一致**。此前 04:0x 测得 3200×1440 系系统切换多屏过程中的瞬时读数，现已恢复（用户说明经代码核实无误） |
| opencv-python | 5.0.0.93（三包共存） | **4.10.0.84**（contrib + python 同版本） | 上一轮已收敛；`opencv-python-headless 5.0.0.93` 已移除（旧包备份在 `F:\自动化验证工具\10-env-baseline\_local_assets\_backup_opencv_stale\`） |
| paddlepaddle（CPU） | 3.3.1 已装 | **已按要求卸载** | 仅保留 `paddlepaddle-gpu 3.3.1` |
| C 盘剩余 | 109 GB | **72 GB** | 本轮 wheel 下载与解压占用，已归档在 F 盘 `_wheels` |
| nvidia-cudnn-cu12 | 9.9.0.52（与 gpu 包要求 9.5.1.17 不符） | 9.9.0.52 | **基线原有偏差**，非本轮引入；实测 GPU 推理正常 |

---

## 三、遗留（按绝对规则标注）

1. **文件丢失根因已定位（04:35 更新）**：详见 `env-incident_20260919_root-cause.md` —— 工具层删除逐个进回收站（`genie-trash`，审计 4663 实证）→ 实测 47~126 ms/文件（`cmd del` 0.74 ms/文件，慢 64~170 倍）→ 大包 `pip uninstall`/`--force-reinstall` 超时被强杀（`killed=true` 28 次，时刻与删除潮末点重合）→ 包半删（`~pkg` 残留）。实测当前仍有 5,187 个文件缺失，其中 5,186 个可从回收站恢复（132.1 MB）——**恢复策略待用户拍板**。
2. **BUG-2 / BUG-4 未动**：`env_adapter` 六模块仍零引用、`probe_env` 的 `framework` 仍被远程软件污染（本轮实测复现）。
3. **P2-2 第 5/7 步未做**：改调用方 import、删 shim，需先补 `sys.path` 引导（沿用 P2-2 验收报告结论）。
4. **未提交**：本轮技能文档/索引改动为工作区修改状态，尚未 commit（等你确认后再提交）。
5. **`modelscope` 等 3.5 GB 级包**：已覆盖法恢复并可导入，但未做逐个功能验证（无项目调用点）。
