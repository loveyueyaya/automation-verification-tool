# -*- coding: utf-8 -*-
"""P2-1 收尾：修复包的 *.dist-info 元数据（此前"覆盖式修复"只补了包文件，未补 RECORD）。
同时与基线快照做精确差分，输出"新增 / 缺失 / 版本变化"三类清单。"""
import csv
import glob
import os
import subprocess
import tempfile
import zipfile
from importlib.metadata import version

PY = r"C:\Program Files\Python313\python.exe"
SP = r"C:\Program Files\Python313\Lib\site-packages"
BASE = r"F:\自动化验证工具\10-env-baseline\pip_before_20260918.txt"


def norm(n):
    return n.lower().replace("_", "-")


# ---------- 1. 与基线差分 ----------
base = {}
for line in open(BASE, encoding="utf-8", errors="ignore"):
    line = line.strip()
    if "==" in line:
        n, v = line.split("==", 1)
        base[norm(n)] = v

now = {}
for di in glob.glob(os.path.join(SP, "*.dist-info")):
    name = os.path.basename(di)[: -len(".dist-info")]
    if "-" not in name:
        continue
    n, v = name.rsplit("-", 1)
    now[norm(n)] = v

added = sorted(set(now) - set(base))
removed = sorted(set(base) - set(now))
changed = sorted((n, base[n], now[n]) for n in set(base) & set(now) if base[n] != now[n])

print("=== 相对基线：新增包 ===")
for n in added:
    print(f"  + {n}=={now[n]}")
print("=== 相对基线：缺失包 ===")
for n in removed:
    print(f"  - {n}=={base[n]}")
print("=== 相对基线：版本变化 ===")
for n, a, b in changed:
    print(f"  * {n}: {a} -> {b}")

# ---------- 2. 补齐 dist-info ----------
print()
print("=== 补齐 dist-info（RECORD 等）===")
targets = []
for di in glob.glob(os.path.join(SP, "*.dist-info")):
    if not os.path.isfile(os.path.join(di, "RECORD")):
        name = os.path.basename(di)[: -len(".dist-info")]
        if "-" not in name:
            continue
        pkg, ver = name.rsplit("-", 1)
        targets.append((pkg.replace("_", "-"), ver, di))

for pkg, ver, di in sorted(targets):
    tmp = tempfile.mkdtemp(prefix="di_")
    idx = ["-i", "https://www.paddlepaddle.org.cn/packages/stable/cu126/"] if "paddle" in pkg else []
    r = subprocess.run([PY, "-m", "pip", "download", "--no-deps", "--no-cache-dir",
                        "-d", tmp, f"{pkg}=={ver}"] + idx,
                       capture_output=True, text=True, timeout=3000)
    whls = [os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".whl")]
    if not whls:
        print(f"  [失败] {pkg} {ver} 下载失败: {(r.stderr or '')[-120:]}")
        continue
    unz = tempfile.mkdtemp(prefix="diz_")
    with zipfile.ZipFile(whls[0]) as z:
        z.extractall(unz)
    src_di = None
    for d in os.listdir(unz):
        if d.endswith(".dist-info"):
            src_di = os.path.join(unz, d)
            break
    if not src_di:
        print(f"  [失败] {pkg} wheel 内无 dist-info")
        continue
    n = 0
    for fn in os.listdir(src_di):
        s = os.path.join(src_di, fn)
        if not os.path.isfile(s):
            continue  # 跳过 licenses 等子目录
        # 只补元数据文件，不动包文件本身
        with open(s, "rb") as a:
            data = a.read()
        with open(os.path.join(di, fn), "wb") as b:
            b.write(data)
        n += 1
    print(f"  [补齐] {pkg:22s} {ver:12s} 写入 {n} 个元数据文件")
print("收尾结束")
