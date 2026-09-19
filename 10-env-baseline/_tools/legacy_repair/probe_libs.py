# -*- coding: utf-8 -*-
"""第三步：实测各依赖在本机的真实性能，用数据支撑"复用/薄封装/自研"决策。
只读操作，不修改项目任何文件。"""
import os
import sys
import time

P1 = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter"
sys.path.insert(0, P1)
sys.path.insert(0, os.path.join(P1, "scripts"))


def timing(label, fn, repeat=5):
    try:
        t0 = time.perf_counter()
        first = fn(repeat)
        if isinstance(first, tuple):
            first_out, rest = first
        else:
            first_out, rest = first, None
        dt = (time.perf_counter() - t0) * 1000
        print(f"{label:44s} {dt:9.2f} ms   <- 首帧/首次含初始化")
        return first_out
    except Exception as e:
        print(f"{label:44s} FAILED: {type(e).__name__}: {e}"[:200])
        return None


print("=== 1. 截图引擎 ===")
eng = None


def _dxcam_init(_=0):
    global eng
    import dxcam
    eng = dxcam.create(output_idx=0, output_color="RGB")
    return eng.grab()


frame = timing("dxcam 首次 create+grab（含 DXGI 初始化）", _dxcam_init)
if frame is not None:
    def _dxcam_loop(n):
        ts = []
        for _ in range(n):
            t = time.perf_counter()
            f = eng.grab()
            ts.append((time.perf_counter() - t) * 1000)
        return ts
    ts = _dxcam_loop(20)
    print(f"{'dxcam 后续 grab x20 平均':44s} {sum(ts)/len(ts):9.2f} ms   min={min(ts):.2f} max={max(ts):.2f}")
    print(f"{'  帧尺寸/类型':44s} {getattr(frame, 'shape', None)} {getattr(frame, 'dtype', None)}")


def _mss_loop(n):
    import mss
    import numpy as np
    sct = mss.mss()
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        img = np.asarray(sct.grab(sct.monitors[1]))[:, :, :3]
        ts.append((time.perf_counter() - t) * 1000)
    return ts


print()
mss_ts = None
try:
    t0 = time.perf_counter()
    mss_ts = _mss_loop(20)
    dt = (time.perf_counter() - t0) * 1000
    print(f"{'mss create+grab x20 平均':44s} {sum(mss_ts)/len(mss_ts):9.2f} ms   (总 {dt:.1f} ms)")
except Exception as e:
    print(f"mss FAILED: {e}")

print()
print("=== 2. cv2 模板匹配（本项目唯一用法） ===")
try:
    import cv2
    import numpy as np
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (1080, 1920, 3), dtype=np.uint8)
    tpl = img[300:360, 500:600].copy()
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    t = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    t0 = time.perf_counter()
    for _ in range(5):
        res = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
    full = (time.perf_counter() - t0) / 5 * 1000
    print(f"{'matchTemplate 全屏 1920x1080 模板100x60':44s} {full:9.2f} ms")
    # 区域匹配（推荐做法）
    sub = g[250:420, 450:700]
    t0 = time.perf_counter()
    for _ in range(5):
        res = cv2.matchTemplate(sub, t, cv2.TM_CCOEFF_NORMED)
    roi = (time.perf_counter() - t0) / 5 * 1000
    print(f"{'matchTemplate 限定区域 250x170':44s} {roi:9.2f} ms")
    _, mx, _, _ = cv2.minMaxLoc(res)
    print(f"{'  minMaxLoc 最大相关系数':44s} {mx:.4f}")
except Exception as e:
    print(f"cv2 FAILED: {type(e).__name__}: {e}")

print()
print("=== 3. psutil / 端口检测 ===")
try:
    import psutil
    t0 = time.perf_counter()
    for _ in range(3):
        psutil.net_connections(kind="tcp")
    print(f"{'psutil.net_connections(kind=tcp) 平均':44s} {(time.perf_counter()-t0)/3*1000:9.2f} ms")
    t0 = time.perf_counter()
    names = [p.info.get("name") for p in psutil.process_iter(["name"])]
    print(f"{'psutil.process_iter 全量枚举':44s} {(time.perf_counter()-t0)*1000:9.2f} ms  ({len(names)} 进程)")
except Exception as e:
    print(f"psutil FAILED: {e}")

print()
print("=== 4. 项目自身 env_adapter.probe_env ===")
try:
    from env_adapter.env_probe import probe_env
    from env_adapter.env_cache import get_profile, set_profile
    t0 = time.perf_counter()
    p = probe_env(None)
    print(f"{'probe_env(None) 首次':44s} {(time.perf_counter()-t0)*1000:9.2f} ms -> {p}")
except Exception as e:
    print(f"probe_env FAILED: {type(e).__name__}: {e}")

print()
print("=== 5. uiautomation 控件树（判断 UIA 缺口的实际可行性） ===")
try:
    import uiautomation as auto
    t0 = time.perf_counter()
    roots = auto.GetRootControl().GetChildren()
    names = [(c.Name, c.ControlTypeName) for c in roots]
    dt = (time.perf_counter() - t0) * 1000
    print(f"{'UIA 根级枚举':44s} {dt:9.2f} ms  ({len(names)} 个顶层窗口)")
    for n, t in names[:8]:
        print(f"    - {n!r:40s} {t}")
    # 找一个可深挖的窗口，实测 depth=2 遍历耗时
    target = None
    for c in roots:
        if c.Name:
            target = c
            break
    if target is not None:
        t0 = time.perf_counter()
        kids = target.GetChildren()
        dt2 = (time.perf_counter() - t0) * 1000
        print(f"{'  单个顶层窗口 GetChildren()':44s} {dt2:9.2f} ms  ({len(kids)} 个直接子控件)")
        t0 = time.perf_counter()
        cnt = [leaf for leaf in auto.WalkTree(target, maxDepth=3)]
        dt3 = (time.perf_counter() - t0) * 1000
        print(f"{'  WalkTree(maxDepth=3)':44s} {dt3:9.2f} ms  ({len(cnt)} 个节点)")
        # 实测控件是否带矩形 -> 能否拿到坐标（SourceEnum.UIA 的落地关键）
        sample = None
        for leaf in cnt:
            if getattr(leaf, "BoundingRectangle", None) and leaf.BoundingRectangle.width() > 0:
                sample = leaf
                break
        if sample is not None:
            r = sample.BoundingRectangle
            print(f"{'  样本控件':44s} Name={sample.Name!r} Type={sample.ControlTypeName}")
            print(f"{'    BoundingRectangle':44s} ({r.left},{r.top})-({r.right},{r.bottom})  可直出点击坐标 ✅")
        else:
            print("    未取到带矩形的控件（可能受权限/被测窗口限制，需实测确认）")
except Exception as e:
    print(f"uiautomation FAILED: {type(e).__name__}: {e}")

print()
print("=== 6. CDP 端口可达性（cookie_sync 的 9222） ===")
try:
    import json
    import urllib.request
    for port in (9222, 9223):
        try:
            t0 = time.perf_counter()
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1.5) as r:
                data = json.load(r)
            print(f"  端口 {port}: 可达  {(time.perf_counter()-t0)*1000:.2f} ms  Browser={data.get('Browser')} ws={data.get('webSocketDebuggerUrl')}")
        except Exception as e:
            print(f"  端口 {port}: 不可达（{type(e).__name__}）")
except Exception as e:
    print(f"CDP probe FAILED: {e}")

print()
print("=== 7. nvidia-smi 开销（ocr.py 每次 load_ocr 都调） ===")
import subprocess
t0 = time.perf_counter()
for _ in range(3):
    subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                   capture_output=True, text=True, timeout=5)
print(f"{'nvidia-smi 单次平均':44s} {(time.perf_counter()-t0)/3*1000:9.2f} ms")
