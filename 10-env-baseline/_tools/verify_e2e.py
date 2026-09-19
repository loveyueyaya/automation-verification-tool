# -*- coding: utf-8 -*-
"""项目端到端功能验证快照：单测 / 截图 / 定位 / OCR / 环境探测 / UIA。结果追加到检测报告。"""
import io
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PY = r"C:\Program Files\Python313\python.exe"
P1 = r"F:\自动化验证工具\04-implementation\P1-contracts-env-adapter"
P2 = r"F:\自动化验证工具\04-implementation\P2-layers"
OUT = r"F:\自动化验证工具\10-env-baseline\_evidence\10_env_full_check.txt"

buf = io.StringIO()

TEMPLATE_OCR = """
import subprocess, json, time
P = subprocess.Popen([r"__PY__", r"__OCR__", "--serve"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
t0 = time.perf_counter()
first = P.stdout.readline()
print("ready:", first.strip()[:70])
print("cold_ms=%.0f" % ((time.perf_counter() - t0) * 1000))
for i in range(2):
    t = time.perf_counter()
    P.stdin.write(json.dumps({"image": r"F:\\tmp\\e2e.png"}) + "\\n")
    P.stdin.flush()
    line = P.stdout.readline()
    try:
        n = len(json.loads(line).get("items", []))
    except Exception:
        n = "?"
    print("infer%d items=%s ms=%.0f" % (i + 1, n, (time.perf_counter() - t) * 1000))
P.kill()
"""

TEMPLATE_PROBE = """
import sys, ctypes
sys.path.insert(0, r"__P2__")
sys.path.insert(0, r"__SCRIPTS__")
from env_adapter.env_probe import probe_env, _remote_software
from env_adapter.input_router import route_input, route_reason
from env_adapter.capture_router import route_capture
h = ctypes.windll.user32.GetForegroundWindow()
p = probe_env(h)
print("remote=%s browser=%s framework=%s security=%s focus=%s" % (_remote_software(), p.browser, p.framework, p.security, p.focus_reliable))
print("input=%s | %s" % (route_input(p).value, route_reason(p)))
print("capture=%s" % route_capture(p).value)
"""


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    buf.write(s + "\n")


def run(cmd, cwd=None, timeout=900, enc="utf-8"):
    t = time.perf_counter()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding=enc, errors="replace", timeout=timeout)
    return r, (time.perf_counter() - t) * 1000


def main():
    P("")
    P("=" * 78)
    P("5. 项目端到端功能验证（快照 " + time.strftime("%Y-%m-%d %H:%M:%S") + "）")
    P("=" * 78)

    r, ms = run([PY, "-m", "unittest", "discover", "-s", "tests"], cwd=P1)
    tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
    P("  单测: rc={} {:.0f} ms  {}".format(r.returncode, ms, " | ".join(tail)))

    r, ms = run([PY, os.path.join(P1, "scripts", "shot.py"), "--out", r"F:\tmp\e2e.png",
                 "--region", "200,200,320,200"])
    P("  区域截图: {:.0f} ms  {}".format(ms, r.stdout.strip()[-140:]))

    r, ms = run([PY, os.path.join(P1, "scripts", "locate.py"), "template",
                 "--image", r"F:\tmp\e2e.png", "--tpl", r"F:\tmp\e2e.png"])
    P("  模板匹配: {:.0f} ms  {}".format(ms, r.stdout.strip()[-140:]))

    r, ms = run([PY, os.path.join(P1, "scripts", "locate.py"), "verify",
                 "--image", r"F:\tmp\e2e.png", "--tpl", r"F:\tmp\e2e.png"])
    P("  差分比对: {:.0f} ms  {}".format(ms, r.stdout.strip()[-140:]))

    # OCR：常驻模式（冷启动 + 2 次推理）
    code = TEMPLATE_OCR.replace("__PY__", PY).replace("__OCR__", os.path.join(P1, "scripts", "ocr.py"))
    r, ms = run([PY, "-c", code], timeout=900)
    for l in (r.stdout or "").strip().splitlines():
        P("  OCR常驻: " + l)

    code = TEMPLATE_PROBE.replace("__P2__", P2).replace("__SCRIPTS__", os.path.join(P1, "scripts"))
    r, ms = run([PY, "-c", code])
    for l in (r.stdout or "").strip().splitlines():
        P("  环境探测: " + l)

    code = (
        "import ctypes,uiautomation as auto\n"
        "h=ctypes.windll.user32.GetForegroundWindow(); c=auto.ControlFromHandle(h)\n"
        "print('fg=%r type=%s childs=%d'%(c.Name,c.ControlTypeName,len(c.GetChildren() or [])))\n"
    )
    r, ms = run([PY, "-c", code])
    P("  UIA: {:.0f} ms  {}".format(ms, (r.stdout or "").strip()))

    with open(OUT, "a", encoding="utf-8") as f:
        f.write(buf.getvalue())
    P("")
    P("（已追加到 {}）".format(OUT))


if __name__ == "__main__":
    main()
