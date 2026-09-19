# -*- coding: utf-8 -*-
"""P2-1 环境修复第三轮：补齐 nvidia-* CUDA 系列包缺失的 DLL（覆盖式，不删除文件）。"""
import csv
import os
import subprocess
import tempfile
import zipfile

PY = r"C:\Program Files\Python313\python.exe"
SP = r"C:\Program Files\Python313\Lib\site-packages"


def record_missing(dist_dir):
    rec = os.path.join(SP, dist_dir, "RECORD")
    if not os.path.isfile(rec):
        return None
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


def name_ver(dist_dir):
    # 例：nvidia_cudnn_cu12-9.9.0.52.dist-info -> nvidia-cudnn-cu12, 9.9.0.52
    base = dist_dir[: -len(".dist-info")] if dist_dir.endswith(".dist-info") else dist_dir
    if "-" in base:
        n, v = base.rsplit("-", 1)
        return n.replace("_", "-"), v
    return base, None


def main():
    dists = [d for d in os.listdir(SP) if d.startswith("nvidia") and d.endswith(".dist-info")]
    print("检测到 nvidia 相关 dist:", len(dists))
    for d in sorted(dists):
        pkg, ver = name_ver(d)
        miss = record_missing(d)
        if miss is None:
            print(f"  [跳过] {pkg} 无 RECORD")
            continue
        if not miss:
            print(f"  [完好] {pkg} {ver}")
            continue
        print(f"  [缺失] {pkg} {ver}: {len(miss)} 个文件，开始下载 wheel ...", flush=True)
        tmpdir = tempfile.mkdtemp(prefix="nvwhl_")
        r = subprocess.run([PY, "-m", "pip", "download", "--no-deps", "--no-cache-dir",
                            "-d", tmpdir, f"{pkg}=={ver}"],
                           capture_output=True, text=True, timeout=3000)
        whls = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".whl")]
        if not whls:
            print(f"     !! 下载失败 rc={r.returncode}: {(r.stderr or '')[-160:]}")
            continue
        whl = whls[0]
        print(f"     -> {os.path.basename(whl)} ({os.path.getsize(whl)//1024//1024} MB)", flush=True)
        tmp = tempfile.mkdtemp(prefix="nvunz_")
        with zipfile.ZipFile(whl) as z:
            z.extractall(tmp)
        copied = 0
        for rel in miss:
            src = os.path.join(tmp, rel.replace(os.sep, "/"))
            if not os.path.isfile(src):
                continue
            dst = os.path.join(SP, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
            copied += 1
        print(f"     写入 {copied}/{len(miss)} 个文件", flush=True)


if __name__ == "__main__":
    main()
    print("第三轮修复结束")
