# -*- coding: utf-8 -*-
"""开发前盘点实测探针（只读、不修改项目）。"""
import subprocess, sys, time, statistics, json

PY = r"C:\Program Files\Python313\python.exe"
PROJ = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter"

def sec(title):
    print("\n" + "=" * 66)
    print(title)
    print("=" * 66)

# ---------- 1. 项目自带单测 ----------
sec("1. 项目自带单测（unittest discover）")
r = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-v"],
                   cwd=PROJ, capture_output=True, text=True, timeout=600)
tail = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
print("\n".join(tail[-6:]))
print("用例数(逐行 Ran)：", [l for l in tail if l.startswith("Ran ")])

# ---------- 2. 截图引擎实测 ----------
sec("2. 截图引擎实测（mss / dxcam）")
code = r'''
import time, statistics
def bench(fn, n=15):
    ts=[]; img=None
    for _ in range(n):
        t0=time.perf_counter(); img=fn(); ts.append((time.perf_counter()-t0)*1000)
    return img, statistics.median(ts), min(ts), max(ts)
try:
    import mss
    with mss.mss() as sct:
        mon=sct.monitors[0]
        img,med,mn,mx = bench(lambda: sct.grab(mon))
        print("mss      shape=%s median=%.1fms min=%.1f max=%.1f" % (getattr(img,'size',None), med,mn,mx))
except Exception as e:
    print("mss  FAIL:", type(e).__name__, e)
try:
    import dxcam
    cam=dxcam.create(output_idx=0, output_color="RGB")
    cam.grab()  # warmup
    img,med,mn,mx = bench(lambda: cam.grab())
    try: h,w = img.shape[:2]
    except Exception: h=w=-1
    print("dxcam    shape=(%s,%s) median=%.1fms min=%.1f max=%.1f" % (h,w,med,mn,mx))
    cam.stop()
except Exception as e:
    print("dxcam FAIL:", type(e).__name__, e)
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=300)
print(r.stdout.strip() or r.stderr.strip())

# ---------- 3. UIA 控件树实测 ----------
sec("3. UIA 控件树实测（uiautomation 已装未用）")
code = r'''
import time, sys
try:
    import uiautomation as auto
    print("uiautomation import OK")
except Exception as e:
    print("uiautomation import FAIL:", type(e).__name__, e); sys.exit(0)
try:
    t0=time.perf_counter()
    root=auto.GetRootControl()
    wins=root.GetChildren()
    t1=time.perf_counter()
    print("顶层窗口枚举: %d 个, 耗时 %.1f ms" % (len(wins), (t1-t0)*1000))
    shown=0
    for w in wins:
        try: n=(w.Name or "").strip()
        except Exception: continue
        if n and len(n)<40:
            print("   -", n[:40], "|", w.ControlTypeName)
            shown+=1
        if shown>=6: break
    # 深度遍历性能
    t0=time.perf_counter()
    target=None
    for w in wins:
        try:
            if (w.Name or "").strip(): target=w; break
        except Exception: pass
    if target:
        cnt=0
        def walk(c, d, maxd=3):
            global cnt
            if d>maxd: return
            for ch in c.GetChildren():
                cnt+=1
                walk(ch, d+1, maxd)
        walk(target, 0)
        t1=time.perf_counter()
        print("控件树遍历(depth<=3): %d 个控件, 耗时 %.1f ms" % (cnt, (t1-t0)*1000))
        # control_path 可行性
        def path(c, maxd=4):
            parts=[]
            cur=c
            for _ in range(maxd):
                parts.append("%s#%s" % (cur.ControlTypeName, (cur.Name or "")[:12]))
                p=cur.GetParentControl()
                if not p: break
                cur=p
            return "/".join(reversed(parts))
        try:
            first=target.GetChildren()[0]
            print("control_path 样例:", path(first))
        except Exception as e:
            print("control_path 构造 FAIL:", e)
except Exception as e:
    print("UIA 运行 FAIL:", type(e).__name__, e)
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=300)
print(r.stdout.strip() or r.stderr.strip()[:800])

# ---------- 4. 模板匹配 / 进程端口实测 ----------
sec("4. cv2 模板匹配 & psutil 实测")
code = r'''
import time, statistics, numpy as np, cv2
img=np.random.randint(0,255,(1080,1920,3),dtype=np.uint8)
tpl=img[400:500, 800:900].copy()
ts=[]
for _ in range(10):
    t0=time.perf_counter(); cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED); ts.append((time.perf_counter()-t0)*1000)
print("matchTemplate 全屏1920x1080 vs 100x100模板: median=%.1fms min=%.1f" % (statistics.median(ts), min(ts)))
reg=img[300:600, 700:1100].copy()
ts=[]
for _ in range(20):
    t0=time.perf_counter(); cv2.matchTemplate(reg, tpl, cv2.TM_CCOEFF_NORMED); ts.append((time.perf_counter()-t0)*1000)
print("matchTemplate 限区400x300            : median=%.2fms min=%.2f" % (statistics.median(ts), min(ts)))
import psutil
t0=time.perf_counter(); n=len(list(psutil.process_iter(["name"]))); t1=time.perf_counter()
print("psutil.process_iter: %d 进程, %.1f ms" % (n,(t1-t0)*1000))
t0=time.perf_counter(); c=psutil.net_connections(kind="inet"); t1=time.perf_counter()
print("psutil.net_connections: %d 条, %.1f ms" % (len(c),(t1-t0)*1000))
t0=time.perf_counter()
import subprocess as sp
sp.run(["nvidia-smi","--query-gpu=memory.total","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=5)
t1=time.perf_counter()
print("nvidia-smi 单次调用: %.1f ms" % ((t1-t0)*1000))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=300)
print(r.stdout.strip() or r.stderr.strip()[:800])

# ---------- 5. winrt 可安装性 ----------
sec("5. dxcam[winrt] 可安装性（dry-run，不实际安装）")
for pkg in ["winrt-Windows.Graphics.Capture", "websocket-client"]:
    r = subprocess.run([PY, "-m", "pip", "install", "--dry-run", "--no-deps", pkg],
                       capture_output=True, text=True, timeout=300)
    ok = [l for l in r.stdout.splitlines() if "Would install" in l or "already satisfied" in l]
    print("%-32s -> %s" % (pkg, ok[0].strip() if ok else "FAILED: " + r.stdout.strip().splitlines()[-1][:120]))

print("\n探针执行完毕。")
