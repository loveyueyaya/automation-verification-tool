# 环境损失评估报告（对照《开发前盘点》）

- 评估时间：**2026-09-19 04:37 ~ 04:55 +0800**（系统时间实测）
- 评估口径：**一切结论以本地代码执行结果为准**；对照文件 `F:\自动化验证工具\11-management\本地离线自动化测试工具_开发前盘点.md`
- 关联：`env-incident_20260919_root-cause.md`（根因）、`env-verify_20260919.md`（环境验证）、`09-feedback\issues\issue_002_site-packages-file-loss.md`
- 用户裁定：**保留本次开启的系统审计**（此后同类事件可直接拿到肇事进程名与时间）

---

## 一、项目源码树（F:\自动化验证工具）—— **零损伤**

对照《开发前盘点》§5.0 记录的行数逐文件核对（新位置在 P2-2 迁移后的 `P2-layers`）：

| 目录 | 核对文件数 | 结果 |
|---|---|---|
| `04-implementation\P2-layers\contracts\` | 9 | **9/9 行数与基线完全一致** |
| `04-implementation\P2-layers\env_adapter\` | 7 | **7/7 行数与基线完全一致** |
| `04-implementation\P1-contracts-env-adapter\scripts\` | 8 | env.py 372 / uitool.py 403 / sendinput.py 258 / timeline.py 237 / cache.py 176 / locate.py 174 一致；**shot.py 190→216、ocr.py 146→188 为 P2-1 已记录的 BUG-1/BUG-3 修复**（实跑佐证：`_region_box` 命中 3 处、`def get_ocr` 命中 1 处、`pynvml` 命中 9 处） |
| `04-implementation\P1-contracts-env-adapter\tests\` | 4 | **4/4 行数一致**（534 / 135 / 81 / 78） |
| `MIGRATION.md` | 1 | 250→297（P2-2 迁移记录，已在 commit `340049d`） |
| `P1-contracts-env-adapter\contracts\` | 1 | `__init__.py` 51→39 = P2-2 的 shim（预期） |
| P1 侧 contracts 8 个模块 / env_adapter 7 个模块 | — | 已 `git mv` 至 P2-layers（盘点上记录的"缺失"属预期迁移） |

**结论：项目目录树下的所有子文件夹，核心代码文件 100% 在位、行数与基线一致。**

---

## 二、环境包（C:\Program Files\Python313\Lib\site-packages）—— 逐层评估

### 2.1 总量

| 项 | 数值 |
|---|---|
| 回收站条目总数 | 35,851 |
| site-packages 相关条目 | 29,695 |
| 其中当前仍缺失 | 5,290 |
| ├ 卸载残留（`~umpy`/`~yautogui`/`~pencv_*`/`~addlepaddle-*`）+ 测试残留 | 1,486（**属垃圾，非功能文件**） |
| └ **真实缺失** | **3,804** |
| &nbsp;&nbsp;├ **核心文件** | **1** |
| &nbsp;&nbsp;└ 外围文件 | 3,803 |

### 2.2 真实缺失的类型构成（判定功能影响的依据）

| 类型 | 数量 | 是否影响功能 | 说明 |
|---|---|---|---|
| `.pyc` | 3,220 | **否** | Python 字节码缓存，下次 import 自动重建 |
| 无扩展名（目录条目） | 571 | **否** | 抽样实证：`cv2\data\__pycache__`、`cv2\instr`、`*.dist-info` 目录、`accesstest_deleteme_*`（沙箱权限自检残留） |
| `.pyi` | 6 | **否** | 类型存根（IDE 提示用），明细：`cv2\instr\__init__.pyi`、`cv2\utils\logging\__init__.pyi` ×3 轮删除 |
| `.txt` | 4 | **否** | `nvidia_ml_py3-*.dist-info\top_level.txt`、`opencv_python_headless-5.0.0.93.dist-info\LICENSE*.txt`（均为已移除包的元数据） |
| `.dist-info`（目录） | 2 | **否** | 同上，已移除包的元数据目录 |
| `.dll` | **1** | **否** | `cv2\opencv_videoio_ffmpeg500_64.dll` = **opencv 5.0 版遗留**；当前 cv2 是 4.10.0，其配套 `opencv_videoio_ffmpeg4100_64.dll`（26.4 MB）**在位**，`cv2.pyd`（89.8 MB）**在位** |

### 2.3 逐包实测（44 个涉及包）

```
涉及包 44 个：可导入 44 / 不可导入 0
```

每个包的 `__init__.py` 与顶层核心 `.py` 均**在位**（`google` 为命名空间包无 `__init__.py`，属正常；`google.protobuf` 实测可导入）。
缺失明细按包：paddle 875、numpy 787、openpyxl 365、baidubce 233、huggingface_hub 196、Cython 159、comtypes 157、future 146、modelscope_hub 69、cv2 52、chardet 48、cryptography 41、opt_einsum 40、packaging 38、libfuturize 31、google 31、modelscope 31、httpcore 29、dxcam 29、nvidia 26 … —— **全部为上述外围类型**。

### 2.4 功能回归（实跑，非推断）

| 验证项 | 实测结果 |
|---|---|
| 关键模块导入（59 个） | 全部通过 |
| `cv2` | 4.10.0；`imread`/`matchTemplate`/`absdiff` 全在；contrib `ximgproc`/`aruco`/`xfeatures2d` 可用；实跑 `matchTemplate` 得 1.0 |
| `paddle` / `paddleocr` / `paddlex` | 3.3.1 / 3.7.0 / 3.7.2；`is_compiled_with_cuda()=True` |
| OCR 端到端 | 常驻模式 GPU 12282 MiB、冷启动 6.99 s、263 条、2003→1486 ms |
| 截图 | `shot.py` 区域 `320×200` 正确（BUG-1 已修）；dxcam/mss 正常 |
| 模板匹配定位 | confidence 1.0、坐标精确 |
| UIA 控件树 | 深度 3 = 11 节点 / 18.4 ms |
| 项目单测 | `Ran 56 tests — OK` |
| `pip check` | 仅剩 1 条基线原有偏差（cudnn 9.9.0.52 vs 包要求 9.5.1.17） |

---

## 三、评估结论与恢复建议

### 3.1 结论

**功能性损失 = 0。** 3,804 个"真实缺失"里，可影响运行的**核心文件只有 1 个**，且那 1 个是**已废弃版本（opencv 5.0 headless）的遗留 ffmpeg DLL**，与当前 4.10.0 无关；其余全是 `.pyc`（自动重建）、空目录条目、类型存根、已移除包的许可证/元数据文本。
项目源码树零损伤；44 个涉及包全部可导入；56 单测 + 7 项功能回归全部通过。

### 3.2 建议：**不恢复（Not restore）**

理由（均为实测依据）：
1. **无可恢复的功能缺口** —— 唯一的"核心"缺失项是废弃版本遗留文件。
2. **恢复反而有风险** —— 回收站里存的是**旧版本**内容；覆盖写入新版本目录会造成版本混杂（例如 `~umpy` 里的文件属已被替换的 numpy 版本）。
3. **成本高** —— 本环境写入/删除每个文件都要过拦截通道（实测 47~126 ms/文件），恢复 3,800 个文件的动作本身会产生新的回收站条目与耗时，收益近零。

### 3.3 若追求"账面干净"，可选的低成本动作（建议仅做第 1 项或都不做）

| 选项 | 内容 | 风险 | 收益 |
|---|---|---|---|
| A（可选） | 从 wheel 补 6 个 `.pyi`（cv2 类型存根） | 极低（只增文件） | IDE 类型提示恢复 |
| B（可选） | 回收站中 1,486 条垃圾残留（`~umpy`/`~yautogui*` 等）不清理 | 无 | 保留"可追溯/可取证"能力，占用空间约 132 MB |
| C（不建议） | 对 numpy/paddle 等做整包覆盖法重灌 | 中（版本混杂、大量写入） | 账面 100% 齐整，但无功能收益 |

**倾向：A 可不做，B 保留，C 不做。** 等下一阶段需要对基线与 `pip freeze` 对齐时（P4-2 基线冻结），再用官方 wheel 做一次"版本对齐 + 覆盖法补齐"，一次到位。

### 3.4 后续防复发（已入库为硬规则）

1. 不在本环境对大包执行 `pip uninstall` / `pip install --force-reinstall`（共享命名空间会连带删 `cv2/`、`paddle/`）。
2. 修环境一律用覆盖法（`pip download` → 解压 → 只补缺失 → 覆盖写入）。
3. 必须批量删除时先把命令超时放大到 ≥1800 s 并先建缓存快照。
4. 审计保留，可随时归因（回滚命令见根因报告 §2.3）。
