# -*- coding: utf-8 -*-
"""元数据一致性专项：dist-info 与真实模块的版本/完整性核对，找出会导致后续 pip 报错的隐患。"""
import os
import glob
import csv
import importlib.metadata as md
import importlib.util
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SP = r"C:\Program Files\Python313\Lib\site-packages"
PY = r"C:\Program Files\Python313\python.exe"


def main():
    print("=== 1. dist-info 无 RECORD（pip uninstall / 依赖审计会失准）===")
    no_rec = []
    for di in sorted(glob.glob(os.path.join(SP, "*.dist-info"))):
        if not os.path.exists(os.path.join(di, "RECORD")):
            no_rec.append(os.path.basename(di)[:-len(".dist-info")])
    print("  数量:", len(no_rec))
    for n in no_rec:
        print("   -", n)

    print("\n=== 2. 同名多版本 dist-info（冲突源）===")
    names = {}
    for di in glob.glob(os.path.join(SP, "*.dist-info")):
        b = os.path.basename(di)[:-len(".dist-info")]
        if "-" not in b:
            continue
        n, v = b.rsplit("-", 1)
        names.setdefault(n.replace("_", "-").lower(), []).append((v, b))
    multi = {k: v for k, v in names.items() if len(v) > 1}
    if not multi:
        print("  无")
    for k, v in multi.items():
        print("  {} → {}".format(k, v))

    print("\n=== 3. 有 dist-info 但模块不可导入（元数据孤儿）===")
    orphan = []
    for di in sorted(glob.glob(os.path.join(SP, "*.dist-info"))):
        b = os.path.basename(di)[:-len(".dist-info")]
        tl = os.path.join(di, "top_level.txt")
        if not os.path.exists(tl):
            continue
        tops = [l.strip() for l in open(tl, encoding="utf-8", errors="replace") if l.strip()]
        if not tops:
            continue
        miss = [t for t in tops if "/" not in t and "\\" not in t
                and importlib.util.find_spec(t) is None]
        if miss and len(miss) == len(tops):
            orphan.append((b, miss))
    print("  数量:", len(orphan))
    for b, m in orphan:
        print("   - {} → 模块 {} 全不可导入".format(b, m))

    print("\n=== 4. 模块可导入但无 dist-info（pip 看不见）===")
    no_meta = []
    for cand in ["pynvml", "nvidia_smi", "six", "ujson", "dateutil", "Crypto", "cpuinfo",
                 "win32api", "win32gui", "pythoncom", "paddle", "cv2"]:
        try:
            spec = importlib.util.find_spec(cand)
        except Exception:
            spec = None
        if spec is None:
            continue
        if cand in ("win32api", "win32gui", "pythoncom"):
            has = any(os.path.isdir(os.path.join(SP, p)) for p in ("pywin32-312.dist-info",))
        else:
            has = False
            for d in md.distributions():
                tops = (d.read_text("top_level.txt") or "").split()
                if cand in tops or cand.split(".")[0] in tops:
                    has = True
                    break
        if not has:
            no_meta.append(cand)
    print("  数量:", len(no_meta), no_meta)

    print("\n=== 5. pip 自身的依赖/一致性校验（pip check 完整输出）===")
    r = subprocess.run([PY, "-m", "pip", "check"], capture_output=True, text=True,
                       encoding="gbk", errors="replace")
    out = (r.stdout or "").strip()
    print("  " + (out.replace("\n", "\n  ") if out else "（无输出）"))

    print("\n=== 6. pip list 与 importlib.metadata 是否一致（opencv 专项）===")
    r = subprocess.run([PY, "-m", "pip", "list"], capture_output=True, text=True,
                       encoding="gbk", errors="replace")
    pip_lines = [l for l in (r.stdout or "").splitlines() if "opencv" in l.lower()]
    print("  pip list  :", pip_lines)
    meta = sorted({(d.metadata["Name"], d.version) for d in md.distributions()
                   if "opencv" in (d.metadata["Name"] or "").lower()})
    print("  metadata  :", meta)
    print("  → 不一致 = 存在僵尸 dist-info，会干扰后续依赖解析")


if __name__ == "__main__":
    main()
