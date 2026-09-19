# 遗留问题 003：环境元数据残留与不一致（待处理）

- 发现时间：2026-09-19 04:52（全面检测）
- 检测报告：`10-env-baseline\env-api-and-conflict-check_20260919.md`
- 状态：**已处置（2026-09-19 05:2x，用户批准）**

## 处置记录（2026-09-19）

| 项 | 处置动作 | 复验结果 |
|---|---|---|
| C1 | 删除 `C:\Program Files\Python313\Lib\site-packages\opencv_python-5.0.0.93.dist-info`（进回收站，可回滚） | `opencv*` dist-info 仅剩 contrib/python 4.10.0.84 两份；`pip list` 与 `importlib.metadata` 视图**一致**；`cv2 4.10.0`（imread/ximgproc 可用） |
| C2 | 从回收站**原样恢复** `nvidia_ml_py3-7.352.0.dist-info`（6 文件：METADATA/RECORD/WHEEL/INSTALLER/REQUESTED/top_level.txt）——未下载 wheel，保证版本与模块一致 | `pip list` 出现 `nvidia-ml-py3 7.352.0`；`pip check` 无新增告警 |
| 回归 | 56 单测 + 13 个关键模块导入 | `Ran 56 tests — OK`；不可导入模块：无 |

工具：`F:\自动化验证工具\10-env-baseline\_tools\restore_from_recycle.py`（新增，可按原路径/关键字从回收站恢复，只补不删）

## C1：僵尸 dist-info `opencv_python-5.0.0.93`

- 现象：`site-packages` 下 `opencv_python-5.0.0.93.dist-info` 与 `opencv_python-4.10.0.84.dist-info` **同时存在**
- 证据：
  - `importlib.metadata.distributions()` → opencv-python **两条**（4.10.0.84、5.0.0.93）
  - `pip list` → 只显示 `opencv-python 4.10.0.84`（两套视图不一致）
  - 5.0.0.93 那份目录内**没有 RECORD**（残缺元数据）
- 影响：读 metadata 的依赖判断（`pip check` / `paddlex.is_extra_available` / `pip install` 解析）可能取到 5.0.0.93 版本号 → 版本判断错误、误触发重装；这正是"后续开发报错变难"的典型来源
- 处置建议：删除该僵尸目录（删除会进回收站，可回滚），并在删除后复验 `import cv2` 与 `pip list`
- 风险：低（不含任何模块文件，仅元数据）

## C2：`pynvml` / `nvidia_smi` 模块在但 pip 看不见

- 现象：`site-packages\pynvml.py`（56 KB，mtime 09-19 00:41）存在且可用；但 `importlib.metadata` 中**无 `nvidia-ml-py` 记录**（dist-info 已丢失）
- 证据：`check_metadata.py` 第 4 节输出 `['pynvml', 'nvidia_smi']`
- 影响：依赖审计与 `pip check` 漏检该包；若将来 pip 触发依赖解析，可能重复安装或版本冲突
- 功能侧：**当前正常**（`ocr.py` 内置 nvml.dll 预加载路径，实测读显存 12282 MiB / 21 ms）
- 处置建议：用覆盖法补回 `nvidia-ml-py` 的 dist-info（只补元数据，不动模块文件）
- 风险：低

## 已知代码级缺陷（非环境问题，随 P2 处理）

- BUG-4：`probe_env` 的 `framework` 被安全软件名污染（实测 `framework='wujie'`）
- BUG-2：`env_adapter` 六模块零引用（可导入但无人调用）
