# -*- coding: utf-8 -*-
"""第三步实测(3)：前台真实窗口的 UIA 遍历 + wujie 误判核查 + 最小化窗口风险核查"""
import os
import sys
import time
from collections import deque

P1 = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter"
sys.path.insert(0, P1)
sys.path.insert(0, os.path.join(P1, "scripts"))

import ctypes
import ctypes.wintypes as wt

print("=== A. 谁触发了 security=wujie ？ ===")
try:
    from env_adapter.env_probe import REMOTE_SOFTWARE, _remote_software
    print(f"  特征串: {REMOTE_SOFTWARE}")
    print(f"  _remote_software() -> {_remote_software()!r}")
    import psutil
    hits = []
    for p in psutil.process_iter(["name"]):
        n = (p.info.get("name") or "").lower()
        if n and any(r in n for r in REMOTE_SOFTWARE):
            hits.append(n)
    print(f"  命中的进程名: {sorted(set(hits))}")
except Exception as e:
    print(f"  核查失败: {type(e).__name__}: {e}")

print()
print("=== B. 前台真实窗口的 UIA 遍历（排除最小化） ===")
hwnd = ctypes.windll.user32.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
r = wt.RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
print(f"  前台窗口: hwnd={hwnd} title={buf.value!r} rect=({r.left},{r.top})-({r.right},{r.bottom})")

try:
    import psutil
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc = psutil.Process(pid.value)
    print(f"  进程: {proc.name()} (pid={pid.value})")
except Exception as e:
    print(f"  进程信息获取失败: {e}")

import uiautomation as auto


def bfs(ctrl, max_depth=3, limit=3000):
    t0 = time.perf_counter()
    nodes = with_rect = with_name = 0
    samples = []
    q = deque([(ctrl, 0, ())])
    while q and nodes < limit:
        cur, depth, prefix = q.popleft()
        nodes += 1
        try:
            name = (cur.Name or "").strip()
            ctype = cur.ControlTypeName.replace("Control", "")
            rect = cur.BoundingRectangle
            ok = rect and (rect.right - rect.left) > 0
            with_rect += 1 if ok else 0
            with_name += 1 if name else 0
            path = prefix + (f"{ctype}[{name[:24]}]" if name else ctype,)
            if name and len(samples) < 6:
                samples.append((path, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
        except Exception:
            path = prefix
        if depth < max_depth:
            try:
                kids = cur.GetChildren()
            except Exception:
                kids = []
            for k in kids:
                q.append((k, depth + 1, path))
    return nodes, with_rect, with_name, samples, (time.perf_counter() - t0) * 1000


try:
    ctrl = auto.ControlFromHandle(hwnd)
    print(f"  ControlFromHandle -> {ctrl.ControlTypeName} name={ctrl.Name!r}")
    for d in (1, 2, 3):
        n, wr, wn, samples, ms = bfs(ctrl, max_depth=d)
        print(f"  BFS(depth={d}): {n} 节点 / {ms:.1f} ms | 有矩形 {wr} ({wr/max(n,1)*100:.0f}%) | 有Name {wn} ({wn/max(n,1)*100:.0f}%)")
    print("  可坐标化样例（Name + 矩形）：")
    for path, x, y, w, h in samples:
        print(f"    {path[-2] if len(path)>1 else path} @ ({x},{y}) {w}x{h}")
except Exception as e:
    print(f"  UIA 遍历失败: {type(e).__name__}: {e}")

print()
print("=== C. 最小化窗口是否会误导目标选择（usp pick_target 风险） ===")
try:
    import env as env_util
    wins = env_util.find_windows(visible_only=True, cache_ttl=0)
    minimized = [w for w in wins if w["rect"][0] <= -32000]
    print(f"  find_windows(visible_only=True) 返回 {len(wins)} 个窗口")
    print(f"  其中处于最小化状态(rect.left<=-32000)的有 {len(minimized)} 个：")
    for w in minimized[:6]:
        print(f"    hwnd={w['hwnd']} title={w.get('title')!r} rect={w['rect']}")
    rules = env_util.config() if hasattr(env_util, "config") else {}
    t0 = time.perf_counter()
    picked = env_util.pick_target([], windows=wins)
    print(f"  pick_target(result=0 规则) 结果: {picked}  ({(time.perf_counter()-t0)*1000:.2f} ms)")
except Exception as e:
    print(f"  核查失败: {type(e).__name__}: {e}")

print()
print("=== D. 路由决策对本机的实际影响 ===")
try:
    from env_adapter.env_probe import probe_env
    from env_adapter.input_router import route_input
    from env_adapter.capture_router import route_capture
    p = probe_env(hwnd)
    print(f"  probe -> browser={p.browser} framework={p.framework} security={p.security} focus_reliable={p.focus_reliable}")
    print(f"  实际输入路由: {route_input(p).value}  |  实际截图路由: {route_capture(p).value}")
    print(f"  ⚠ 若 security 误判 -> 全局降级为 {route_capture(p).value}（慢 {17.08/0.04:.0f}x，按本次实测换算）")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")
