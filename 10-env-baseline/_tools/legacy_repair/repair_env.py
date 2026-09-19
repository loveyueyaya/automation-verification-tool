# -*- coding: utf-8 -*-
"""P2-1 环境修复：用「下载 wheel + 覆盖拷回」方式修复被部分损坏的包，全程不删除任何文件。
（pip install 的卸载阶段会触发沙箱批量删除保护，故改为覆盖式修复）"""
import csv
import os
import subprocess
import sys
import tempfile
import zipfile

PY = r"C:\Program Files\Python313\python.exe"
SP = r"C:\Program Files\Python313\Lib\site-packages"
BASE = r"F:\自动化验证工具\10-env-baseline\pip_before_20260918.txt"
OFFICIAL_PADDLE = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"

# 基线版本表
base = {}
for line in open(BASE, encoding="utf-8", errors="ignore"):
    line = line.strip()
    if "==" in line:
        n, v = line.split("==", 1)
        base[n.lower().replace("_", "-")] = v
base.setdefault("pywin32", "312")
base.setdefault("uiautomation", "2.0.29")


def missing_files(dist_name):
    """按 RECORD 列出该包缺失的文件路径。"""
    rec = os.path.join(SP, dist_name, "RECORD")
    if not os.path.isfile(rec):
        return None  # 无 RECORD：整体重装
    miss = []
    with open(rec, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            p = row[0].replace("/", os.sep)
            if p.endswith((".pyc", "RECORD", "INSTALLER", "WHEEL", "REQUESTED", "top_level.txt")):
                continue
            if not os.path.exists(os.path.join(SP, p)):
                miss.append(p)
    return miss


def download(pkg, ver, index=None):
    d = tempfile.mkdtemp(prefix="whl_")
    cmd = [PY, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "-d", d, f"{pkg}=={ver}"]
    if index:
        cmd += ["-i", index]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    whls = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".whl")]
    return whls[0] if whls else None, r.returncode, (r.stderr or "")[-300:]


def overlay(whl, only_files=None):
    """解压 wheel 并覆盖到 site-packages。only_files 为 None 时全部覆盖。"""
    tmp = tempfile.mkdtemp(prefix="unz_")
    with zipfile.ZipFile(whl) as z:
        z.extractall(tmp)
    copied = 0
    for root, _, files in os.walk(tmp):
        for fn in files:
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, tmp).replace("/", os.sep)
            if rel.endswith((".dist-info/RECORD",)) or os.sep + "RECORD" == rel[-7:]:
                continue
            if only_files is not None and rel not in only_files:
                continue
            dst = os.path.join(SP, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
            copied += 1
    return copied


# 需要修复的包（名称, dist-info 目录名前缀）
targets = [
    ("certifi", "certifi-2026.7.22"),
    ("dxcam", "dxcam-0.3.0"),
    ("aiohttp", "aiohttp-3.14.3"),
    ("cryptography", "cryptography-50.0.1"),
    ("protobuf", "protobuf-7.36.1"),
    ("pycryptodome", "pycryptodome-3.23.0"),
    ("python-dateutil", "python_dateutil-2.9.0.post0"),
    ("python-bidi", "python_bidi-0.6.11"),
    ("py-cpuinfo", "py_cpuinfo-9.0.0"),
    ("pefile", "pefile-2024.8.26"),
    ("tqdm", "tqdm-4.70.1"),
    ("pywin32", "pywin32-312"),
    ("uiautomation", "uiautomation-2.0.29"),
    ("imagesize", "imagesize-2.0.1"),
    ("networkx", "networkx-3.6.1"),
    ("httpx", "httpx-0.28.1"),
    ("anyio", "anyio-4.15.1"),
    ("click", "click-8.5.0"),
    ("fsspec", "fsspec-2026.7.0"),
    ("filelock", "filelock-3.32.6"),
    ("modelscope", "modelscope-1.40.1"),
    ("aistudio-sdk", "aistudio_sdk-0.3.9"),
]

print("=" * 70)
for pkg, dist in targets:
    ver = base.get(pkg)
    miss = missing_files(dist)
    if miss is not None and not miss:
        print(f"[跳过] {pkg:18s} 文件完整")
        continue
    whl, rc, err = download(pkg, ver)
    if not whl:
        print(f"[失败] {pkg:18s} 下载失败 rc={rc} {err[:120]}")
        continue
    n = overlay(whl, only_files=set(miss) if miss else None)
    tag = f"补 {len(miss)} 个文件" if miss else "整体覆盖"
    print(f"[修复] {pkg:18s} {ver:12s} {tag}: 写入 {n} 个文件  ({os.path.basename(whl)})")

# paddle 单独处理（1GB 级，只补缺失文件）
print("=" * 70)
pkg, ver = "paddlepaddle-gpu", base["paddlepaddle-gpu"]
miss = missing_files("paddlepaddle_gpu-3.3.1") or []
if miss:
    whl, rc, err = download(pkg, ver, index=OFFICIAL_PADDLE)
    if whl:
        n = overlay(whl, only_files=set(miss))
        print(f"[修复] {pkg} {ver}: 补 {len(miss)} 个文件，写入 {n} 个")
    else:
        print(f"[失败] {pkg} 下载失败 rc={rc} {err[:200]}")
else:
    print(f"[跳过] {pkg} 文件完整")
print("=" * 70)
print("修复结束")
