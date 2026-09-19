# -*- coding: utf-8 -*-
"""第三步补充实测：env_probe 耗时 + UIA 控件树深度遍历（给 stable_id 的 L2 control_path 铺路）"""
import os
import sys
import time
from collections import deque

P1 = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter"
sys.path.insert(0, P1)
sys.path.insert(0, os.path.join(P1, "scripts"))

print("=== A. env_probe 实测 ===")
try:
    from env_adapter.env_probe import probe_env
    from env_adapter.env_cache import env_cache_key, get_cached, put_cached
except ImportError as e:
    print(f"  env_cache API 与实际不符: {e}")
    from env_adapter.env_probe import probe_env

t0 = time.perf_counter()
p = probe_env(None)
print(f"  probe_env(None) 首次: {(time.perf_counter()-t0)*1000:.2f} ms")
print(f"  -> dpi={p.dpi_scale} integrity={p.integrity_level} browser={p.browser} "
      f"framework={p.framework} security={p.security} focus_reliable={p.focus_reliable}")
print(f"  -> input={p.input_method.value} capture={p.capture_method.value} probe_ms={p.probe_ms}")

# 针对一个真实窗口探测（取最前面的浏览器窗口）
try:
    import env as env_util
    wins = env_util.find_windows(visible_only=True, cache_ttl=0)
    cand = [w for w in wins if w.get("title") and ("360" in w["title"] or "Chrome" in w["title"] or "Edge" in w["title"])]
    if cand:
        hwnd = cand[0]["hwnd"]
        t0 = time.perf_counter()
        p2 = probe_env(hwnd)
        print(f"  probe_env(hwnd={hwnd}) : {(time.perf_counter()-t0)*1000:.2f} ms -> browser={p2.browser} framework={p2.framework}")
        from env_adapter.input_router import route_input, route_reason
        from env_adapter.capture_router import route_capture, capture_reason
        print(f"  input_router -> {route_input(p2).value}  ({route_reason(p2)})")
        print(f"  capture_router -> {route_capture(p2).value}  ({capture_reason(p2)})")
    else:
        print("  未找到浏览器窗口供定向探测")
except Exception as e:
    print(f"  定向探测失败: {type(e).__name__}: {e}")

print()
print("=== B. UIA 控件树深度遍历实测 ===")
import uiautomation as auto

root_children = auto.GetRootControl().GetChildren()
target = None
for c in root_children:
    if c.Name and ("浏览器" in c.Name or "Chrome" in c.Name or "Edge" in c.Name or "Translate" in c.Name):
        target = c
        break
if target is None:
    target = next((c for c in root_children if c.Name), None)

print(f"  目标窗口: {target.Name!r} ({target.ControlTypeName})")


def bfs(root, max_depth=3, limit_nodes=2000):
    """手写 BFS，统计节点数、可提取 (Name, ControlType, 深度) 的比例、矩形可用性。"""
    t0 = time.perf_counter()
    nodes = 0
    with_rect = 0
    with_name = 0
    paths = []
    q = deque([(root, 0, ())])
    while q and nodes < limit_nodes:
        ctrl, depth, prefix = q.popleft()
        nodes += 1
        try:
            name = ctrl.Name or ""
            ctype = ctrl.ControlTypeName.replace("Control", "")
            r = ctrl.BoundingRectangle
            if r and (r.right - r.left) > 0 and (r.bottom - r.top) > 0:
                with_rect += 1
            if name.strip():
                with_name += 1
            path = prefix + (f"{ctype}[{name}]" if name.strip() else ctype,)
            if len(paths) < 8:
                paths.append("/".join(path))
        except Exception:
            path = prefix
        if depth < max_depth:
            try:
                kids = ctrl.GetChildren()
            except Exception:
                kids = []
            for k in kids:
                q.append((k, depth + 1, path))
    return nodes, with_rect, with_name, paths, (time.perf_counter() - t0) * 1000


for depth in (2, 3):
    n, wr, wn, paths, ms = bfs(target, max_depth=depth)
    print(f"  BFS(maxDepth={depth}): {n} 节点 / {ms:.1f} ms | 有矩形 {wr} ({wr/max(n,1)*100:.0f}%) | 有Name {wn} ({wn/max(n,1)*100:.0f}%)")
print("  样例 control_path（可直接喂给 stable_id 的 L2）:")
for p in paths:
    print(f"    {p}")

print()
print("=== C. UIA 能否稳定评估 --force-renderer-accessibility 层级B ===")
try:
    import env as env_util
    for w in env_util.find_windows(visible_only=True, cache_ttl=0):
        t = (w.get("title") or "")
        if "360" in t or "Chrome" in t or "Edge" in t:
            pass
    # 用 UIA 侧再取一次该窗口的子控件数量，作为"辅助树是否开启"的间接指标
    n2, wr2, wn2, _, ms2 = bfs(target, max_depth=1)
    print(f"  目标窗口 depth<=1: {n2} 节点, 有Name {wn2} -> 若近似 0 说明 Chromium 辅助树未开，需要 --force-renderer-accessibility")
except Exception as e:
    print(f"  层级B 评估失败: {type(e).__name__}: {e}")

print()
print("=== D. Win32 SendInput 与 UIA 坐标一致性（同一控件两条路取坐标） ===")
try:
    import env as env_util
    rect = None
    for w in env_util.find_windows(visible_only=True, cache_ttl=0):
        if w.get("title") and target.Name[:8] in (w.get("title") or ""):
            rect = (w["hwnd"], w.get("rect"))
            break
    print(f"  env.find_windows 取到的窗口: hwnd={rect[0] if rect else None} rect={rect[1] if rect else None}")
    print(f"  UIA BoundingRectangle (窗口级): {target.BoundingRectangle}")
except Exception as e:
    print(f"  对比失败: {type(e).__name__}: {e}")
