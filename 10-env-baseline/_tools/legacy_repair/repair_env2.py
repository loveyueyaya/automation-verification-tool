# -*- coding: utf-8 -*-
"""P2-1 环境修复第二轮：强制按 wheel 内容补齐缺失文件（不删除任何文件）。
覆盖：paddlepaddle-gpu（1GB 级，仅补缺失）、protobuf、multidict、frozenlist、h11、colorama、
      aiosignal、nvidia-cudnn-cu12、nvidia-cufft-cu12（若缺失）
"""
import os
import subprocess
import sys
import tempfile
import zipfile

PY = r"C:\Program Files\Python313\python.exe"
SP = r"C:\Program Files\Python313\Lib\site-packages"
OFFICIAL = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"

TARGETS = [
    ("protobuf", "7.36.1", None),
    ("multidict", "6.8.0", None),
    ("frozenlist", "1.8.0", None),
    ("aiosignal", "1.4.0", None),
    ("h11", "0.16.0", None),
    ("colorama", "0.4.6", None),
    ("paddlepaddle-gpu", "3.3.1", OFFICIAL),
]


def dl(pkg, ver, index=None):
    d = tempfile.mkdtemp(prefix="whl2_")
    cmd = [PY, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "-d", d, f"{pkg}=={ver}"]
    if index:
        cmd += ["-i", index]
    print(f"  下载 {pkg}=={ver} ...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3000)
    whls = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".whl")]
    if not whls:
        print(f"   !! 下载失败 rc={r.returncode}: {(r.stderr or '')[-200:]}", flush=True)
        return None
    print(f"   -> {os.path.basename(whls[0])} ({os.path.getsize(whls[0])//1024//1024} MB)", flush=True)
    return whls[0]


def overlay_missing(whl, force_all=False):
    """缺失才拷；force_all=True 时整包覆盖。"""
    tmp = tempfile.mkdtemp(prefix="unz2_")
    with zipfile.ZipFile(whl) as z:
        z.extractall(tmp)
    copied = skipped = 0
    for root, _, files in os.walk(tmp):
        for fn in files:
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, tmp).replace("/", os.sep)
            dst = os.path.join(SP, rel)
            if os.path.exists(dst) and not force_all:
                skipped += 1
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
            copied += 1
    return copied, skipped


for pkg, ver, idx in TARGETS:
    print(f"=== {pkg} ===", flush=True)
    whl = dl(pkg, ver, idx)
    if not whl:
        continue
    c, s = overlay_missing(whl, force_all=(pkg == "protobuf"))
    print(f"   写入 {c} 个文件，已存在跳过 {s} 个", flush=True)

print("=" * 60)
print("第二轮修复结束")
