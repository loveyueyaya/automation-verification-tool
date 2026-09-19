# -*- coding: utf-8 -*-
"""开发环境全面检测（冲突 / 缺失 / 功能异常）——项目实际调用面逐项实跑。

输出：stdout + F:\自动化验证工具\10-env-baseline\_evidence\10_env_full_check.txt
用法：python verify_env_full.py
"""
import io
import os
import re
import subprocess
import sys
import time
import warnings
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PY = r"C:\Program Files\Python313\python.exe"
SP = r"C:\Program Files\Python313\Lib\site-packages"
OUT = r"F:\自动化验证工具\10-env-baseline\_evidence\10_env_full_check.txt"

buf = io.StringIO()


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    buf.write(s + "\n")


def section(t):
    P("")
    P("=" * 78)
    P(t)
    P("=" * 78)


# ---------------------------------------------------------------- 1. Python 库
def check_lib(name, fn, note=""):
    t = time.perf_counter()
    try:
        r = fn()
        P("  ✅ {:24} {:>8.1f} ms  {}".format(name, (time.perf_counter() - t) * 1000, str(r)[:90]))
        return True
    except Exception as e:
        P("  ❌ {:24} {:>8.1f} ms  {}: {} {}".format(name, (time.perf_counter() - t) * 1000,
                                                     type(e).__name__, str(e)[:120], note))
        return False


def part1_libs():
    section("1. Python 库（项目实际调用面）")
    P("--- 1.1 项目源码直接 import 的库（实跑功能调用）---")
    import numpy as np

    def _pil():
        from PIL import Image
        im = Image.new("RGB", (32, 16), (1, 2, 3))
        return "size=%s mode=%s" % (im.size, im.mode)

    def _cv2():
        import cv2
        img = np.zeros((40, 60, 3), np.uint8)
        r = cv2.matchTemplate(img, np.zeros((10, 10, 3), np.uint8), cv2.TM_CCOEFF_NORMED)
        ok, b = cv2.imencode(".png", img)
        return "ver=%s match=%.3f imencode=%s ximgproc=%s" % (
            cv2.__version__, float(r.max()), ok, hasattr(cv2, "ximgproc"))

    def _dxcam():
        import dxcam
        c = dxcam.create()
        f = c.grab()
        shape = None if f is None else f.shape

        class _D:
            pass
        return "frame=%s dtype=%s" % (shape, None if f is None else f.dtype)

    def _mss():
        import mss
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            return "size=%s" % (shot.size,)

    def _np():
        a = np.arange(12, dtype=np.float32).reshape(3, 4)
        return "ver=%s sum=%.1f dot=%s" % (np.__version__, float(a.sum()), np.dot(a, a.T).shape)

    def _psutil():
        import psutil
        return "ver=%s procs=%d cpu=%d mem=%.1fGB" % (
            psutil.__version__, len(list(psutil.process_iter())), psutil.cpu_count(),
            psutil.virtual_memory().total / 2 ** 30)

    def _pynvml():
        import ctypes as ct
        import pynvml
        # 复刻 ocr.py 的 Windows 兼容路径（nvml.dll 仅存在于 System32）
        if getattr(pynvml, "nvmlLib", None) is None:
            for cand in [os.path.join(os.getenv("ProgramFiles", "C:/Program Files"),
                                      "NVIDIA Corporation", "NVSMI", "nvml.dll"), "nvml.dll"]:
                try:
                    pynvml.nvmlLib = ct.CDLL(cand)
                    break
                except OSError:
                    continue
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(h)
        pynvml.nvmlShutdown()
        return "total=%.0f MiB (走 ocr.py 的预加载路径)" % (info.total / 2 ** 20)

    def _paddle():
        import paddle
        x = paddle.to_tensor([[1.0, 2.0], [3.0, 4.0]])
        y = paddle.matmul(x, x)
        return "ver=%s cuda=%s matmul=%s" % (paddle.__version__, paddle.is_compiled_with_cuda(), y.numpy().tolist())

    def _paddleocr():
        import paddleocr
        return "ver=%s" % paddleocr.__version__

    def _paddlex():
        import paddlex
        return "ver=%s" % paddlex.__version__

    for nm, fn in [("PIL", _pil), ("cv2", _cv2), ("dxcam", _dxcam), ("mss", _mss), ("numpy", _np),
                   ("psutil", _psutil), ("pynvml", _pynvml), ("paddle", _paddle),
                   ("paddleocr", _paddleocr), ("paddlex", _paddlex)]:
        check_lib(nm, fn)

    P("")
    P("--- 1.2 已装但项目未直接调用（层5/UIA/配置相关，实跑导入+最小调用）---")

    def _comtypes():
        import comtypes
        import comtypes.client
        comtypes.client.GetModule
        return "ver=%s client=OK GetModule=OK" % comtypes.__version__

    def _uia():
        import ctypes as ct
        import uiautomation as auto
        hwnd = ct.windll.user32.GetForegroundWindow()
        c = auto.ControlFromHandle(hwnd)
        kids = c.GetChildren() or []
        return "前台=%r 类型=%s 直接子控件=%d" % (c.Name, c.ControlTypeName, len(kids))

    def _pywinauto():
        import pywinauto
        from pywinauto import Desktop
        return "ver=%s Desktop=OK" % pywinauto.__version__

    def _win32():
        import win32api
        import win32con
        import win32gui
        hwnds = []
        win32gui.EnumWindows(lambda h, l: hwnds.append(h) or True, None)
        return "win32gui.EnumWindows=%d win32api=%s" % (len(hwnds), bool(win32api))

    def _yaml():
        import yaml
        return "ver=%s load=%s" % (yaml.__version__, yaml.safe_load("a: 1"))

    def _requests():
        import requests
        return "ver=%s Session=OK" % requests.__version__

    def _openpyxl():
        import openpyxl
        wb = openpyxl.Workbook()
        wb.active["A1"] = 1
        return "ver=%s cell=%s" % (openpyxl.__version__, wb.active["A1"].value)

    def _dateutil():
        from dateutil import parser
        return "parse=%s" % parser.parse("2026-09-19T04:00:00")

    def _crypto():
        from Crypto.Cipher import AES
        return "AES 模块可用"

    def _protobuf():
        from google.protobuf import descriptor_pb2
        d = descriptor_pb2.FileDescriptorProto()
        d.name = "x"
        return "序列化 %d 字节" % len(d.SerializeToString())

    def _colorlog():
        import colorlog
        return "ColoredFormatter=%s" % bool(colorlog.ColoredFormatter)

    def _colorama():
        import colorama
        colorama.init(strip=True)
        colorama.deinit()
        return "init/deinit OK"

    def _hf():
        import huggingface_hub
        return "ver=%s" % huggingface_hub.__version__

    for nm, fn in [("comtypes(+client)", _comtypes), ("uiautomation", _uia), ("pywinauto", _pywinauto),
                   ("pywin32(win32gui/api)", _win32), ("PyYAML", _yaml), ("requests", _requests),
                   ("openpyxl", _openpyxl), ("python-dateutil", _dateutil),
                   ("pycryptodome", _crypto), ("protobuf", _protobuf),
                   ("colorlog", _colorlog), ("colorama", _colorama), ("huggingface_hub", _hf)]:
        check_lib(nm, fn)


# ------------------------------------------------------- 2. 外部命令 / 进程
def part2_cli():
    section("2. 外部命令与进程（subprocess 调用面）")

    def run(cmd, timeout=60, **kw):
        t = time.perf_counter()
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="gbk",
                           errors="replace", timeout=timeout, **kw)
        return r, (time.perf_counter() - t) * 1000

    try:
        r, ms = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                     "--format=csv,noheader"])
        P("  ✅ nvidia-smi        {:>7.0f} ms  rc={}  {}".format(ms, r.returncode, r.stdout.strip()[:80]))
    except Exception as e:
        P("  ❌ nvidia-smi 失败: {}".format(e))

    try:
        r, ms = run(["taskkill", "/?"])
        P("  ✅ taskkill /?       {:>7.0f} ms  rc={}  (帮助输出 {} 字节)".format(ms, r.returncode, len(r.stdout)))
    except Exception as e:
        P("  ❌ taskkill 失败: {}".format(e))

    pynvml_ms = None
    try:
        import pynvml
        t = time.perf_counter()
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        pynvml.nvmlDeviceGetMemoryInfo(h)
        pynvml.nvmlShutdown()
        pynvml_ms = (time.perf_counter() - t) * 1000
        P("  ✅ pynvml 取显存     {:>7.1f} ms（替代 nvidia-smi 的路径）".format(pynvml_ms))
    except Exception as e:
        P("  ❌ pynvml 失败:", e)

    wgc = os.path.join(r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter\scripts\wgc", "WgcCapture.exe")
    P("  {} WgcCapture.exe    {}".format("✅" if os.path.isfile(wgc) else "⚠", "存在" if os.path.isfile(wgc) else "不存在（截图第一档 WGC 不可用 → 走 dxcam/mss，属已知状态）"))

    P("  ℹ 项目用 sys.executable 作为子进程解释器（uitool.py PY = sys.executable）→ 用哪个解释器启动就必须全程一致")


# ------------------------------------------------------------- 3. 冲突检测
def part3_conflicts():
    section("3. 冲突检测")

    r = subprocess.run([PY, "-m", "pip", "check"], capture_output=True, text=True,
                       encoding="gbk", errors="replace")
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    P("--- 3.1 pip check ---")
    if not lines:
        P("  ✅ 无任何依赖冲突")
    else:
        for l in lines:
            P("  ⚠ " + l)

    P("")
    P("--- 3.2 同名包/多版本/僵尸元数据 ---")
    import glob
    names = {}
    for di in glob.glob(os.path.join(SP, "*.dist-info")):
        b = os.path.basename(di)[:-len(".dist-info")]
        if "-" not in b:
            continue
        n, v = b.rsplit("-", 1)
        names.setdefault(re.sub(r"[-_.]+", "-", n).lower(), []).append(v)
    dup = {k: v for k, v in names.items() if len(v) > 1}
    P("  多版本共存: " + (str(dup) if dup else "无"))
    tilde = [os.path.basename(p) for p in glob.glob(os.path.join(SP, "~*"))]
    P("  ~ 前缀僵尸元数据: " + (str(tilde) if tilde else "无"))

    P("")
    P("--- 3.3 共享命名空间/依赖互斥风险 ---")
    risky = {
        "opencv-python + opencv-contrib-python": ["opencv-python", "opencv-contrib-python"],
        "paddlepaddle(CPU) + paddlepaddle-gpu": ["paddlepaddle", "paddlepaddle-gpu"],
    }
    for label, pkgs in risky.items():
        have = [p for p in pkgs if re.sub(r"[-_.]+", "-", p).lower() in names]
        vers = {p: names[re.sub(r"[-_.]+", "-", p).lower()][0] for p in have}
        if len(have) > 1:
            same = len(set(vers.values())) == 1
            P("  {} {} → 同时存在，版本{}".format("⚠" if not same else "ℹ", label,
                                                 "一致" if same else "不一致：%s" % vers))
        else:
            P("  ✅ {} → 仅 {}".format(label, have or "均未安装"))

    P("")
    P("--- 3.4 nvidia CUDA 依赖 vs paddlepaddle-gpu 要求 ---")
    req = {"nvidia-cudnn-cu12": "9.5.1.17", "nvidia-cublas-cu12": None,
           "nvidia-cuda-runtime-cu12": None, "nvidia-cufft-cu12": None,
           "nvidia-curand-cu12": None, "nvidia-cusparse-cu12": None}
    for k in req:
        v = names.get(k)
        P("  {:28} 实装={}".format(k, v[0] if v else "元数据缺失"))

    P("")
    P("--- 3.5 解释器/路径冲突 ---")
    import shutil
    P("  项目解释器      : {} ({})".format(PY, os.path.exists(PY)))
    P("  PATH 裸 python  : {}".format(shutil.which("python")))
    P("  PATH 裸 python3 : {}".format(shutil.which("python3")))
    P("  当前 sys.executable: {}".format(sys.executable))
    P("  → 裸 python 与项目解释器不同即为已知坑（一律用绝对路径）")

    P("")
    P("--- 3.6 site-packages 中的冲突副作用文件 ---")
    for f in ["comtypes/gen", "comtypes/gen/__init__.py", "six.py", "pynvml.py", "nvidia_smi.py",
              "cv2/py.typed", "distutils-precedence.pth", "_distutils_hack"]:
        p = os.path.join(SP, f.replace("/", os.sep))
        P("  {:34} {}".format(f, "存在" if os.path.exists(p) else "不存在"))

    P("")
    P("--- 3.7 已注册杀软 / Defender / 冲突软件 ---")
    try:
        ps = ("Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | "
              "Select-Object -ExpandProperty displayName")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                           text=True, encoding="gbk", errors="replace", timeout=60)
        P("  注册杀软: " + ((r.stdout or "").strip() or "(空，未注册)"))
    except Exception as e:
        P("  杀软查询失败: {}".format(e))


# ------------------------------------------------------- 4. 功能异常扫描
def part4_anomaly():
    section("4. 功能异常扫描")

    P("--- 4.1 导入期告警（warnings）---")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import importlib
        for m in ["cv2", "numpy", "PIL.Image", "dxcam", "mss", "psutil", "paddle", "paddlex",
                  "paddleocr", "comtypes", "uiautomation", "pywinauto", "pynvml"]:
            try:
                importlib.import_module(m)
            except Exception as e:
                P("  ❌ {} 导入失败: {}".format(m, e))
        seen = {}
        for x in w:
            key = "{}: {}".format(x.category.__name__, str(x.message)[:110])
            seen.setdefault(key, 0)
            seen[key] += 1
        if seen:
            for k, v in seen.items():
                P("  ⚠ [x{}] {}".format(v, k))
        else:
            P("  ✅ 无导入期告警")

    P("")
    P("--- 4.2 项目源码已知问题点复检 ---")
    src = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter\scripts"
    checks = [
        ("ocr.py 是否残留 subprocess 调 nvidia-smi",
         lambda t: ("nvidia-smi" in t and "subprocess" in t and "pynvml" not in t)),
        ("shot.py 区域截图修复标记 _region_box",
         lambda t: "_region_box" in t),
        ("ocr.py OCR 单例 get_ocr",
         lambda t: "def get_ocr" in t),
        ("uitool.py 子进程用 sys.executable",
         lambda t: "PY = sys.executable" in t),
    ]
    for name, pred in checks:
        f = os.path.join(src, name.split()[0])
        t = open(f, encoding="utf-8", errors="replace").read() if os.path.exists(f) else ""
        P("  {} {}".format("⚠" if pred(t) else "ℹ", name))

    P("")
    P("--- 4.3 环境侧已知缺陷（对照盘点/日报，逐项复验）---")
    sys.path.insert(0, r"F:\自动化验证工具\04-implementation\P2-layers")
    sys.path.insert(0, src)
    try:
        from env_adapter.env_probe import probe_env, _remote_software
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        p = probe_env(hwnd)
        P("  BUG-4 framework 污染: framework={!r} security={!r} → {}".format(
            p.framework, p.security,
            "仍存在（framework 被安全软件名污染）" if p.framework == p.security else "已修复"))
    except Exception as e:
        P("  probe_env 调用异常: {}: {}".format(type(e).__name__, e))
    try:
        import subprocess as sp2
        r = sp2.run([PY, "-c", "import sys;sys.path.insert(0,r'F:\\自动化验证工具\\04-implementation\\P2-layers');"
                               "import importlib;p=importlib.import_module('env_adapter');print('env_adapter ok')"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
        P("  BUG-2 env_adapter 可被显式导入: {}".format("是" if "ok" in (r.stdout or "") else "否"))
    except Exception as e:
        P("  BUG-2 复检异常: {}".format(e))

    P("")
    P("--- 4.4 磁盘/内存余量 ---")
    import shutil as sh
    for d in ["C:/", "F:/"]:
        u = sh.disk_usage(d)
        P("  {} 总 {:.0f} GB / 剩余 {:.0f} GB ({:.0f}% 已用)".format(
            d, u.total / 2 ** 30, u.free / 2 ** 30, u.used / u.total * 100))


def main():
    P("环境全面检测报告  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    P("解释器: {}".format(PY))
    part1_libs()
    part2_cli()
    part3_conflicts()
    part4_anomaly()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    P("")
    P("报告已写入: {}".format(OUT))


if __name__ == "__main__":
    main()
