# -*- coding: utf-8 -*-
"""P2-1 通用环境自愈：扫描所有 dist 的文件完整性 → 下载同名同版本 wheel → 覆盖补齐（全程不删除任何文件）。

背景（实测结论）：本沙箱中 pip 的 uninstall / install 会连带删除其它无关包的文件
（已复现两次：卸载 opencv-python 后 numpy、certifi、dxcam、paddle 等被部分删除）。
因此修复一律采用「pip download + 解压 + 覆盖写入」，绝不使用 pip uninstall / --force-reinstall。
"""
import csv
import glob
import os
import shutil
import subprocess
import tempfile
import zipfile

PY = r"C:\Program Files\Python313\python.exe"
SP = r"C:\Program Files\Python313\Lib\site-packages"
PADDLE_IDX = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"

SKIP = {"pip", "setuptools", "wheel"}


def split_name(dist_dir):
    base = dist_dir[: -len(".dist-info")] if dist_dir.endswith(".dist-info") else dist_dir
    if "-" not in base:
        return None, None
    n, v = base.rsplit("-", 1)
    return n.replace("_", "-"), v


def scan():
    """返回 [(pkg, ver, dist_dir, missing_list|None)]，None 表示无 RECORD（整体可疑）"""
    out = []
    for di in glob.glob(os.path.join(SP, "*.dist-info")):
        name = os.path.basename(di)
        pkg, ver = split_name(name)
        if not pkg or pkg.lower() in SKIP:
            continue
        rec = os.path.join(di, "RECORD")
        if not os.path.isfile(rec):
            out.append((pkg, ver, di, None))
            continue
        miss = []
        with open(rec, newline="", encoding="utf-8", errors="ignore") as f:
            for row in csv.reader(f):
                if not row or not row[0].strip():
                    continue
                p = row[0].replace("/", os.sep)
                if p.startswith(".." + os.sep):
                    continue
                if p.endswith((".pyc", "RECORD", "INSTALLER", "WHEEL", "REQUESTED", "top_level.txt")):
                    continue
                if not os.path.exists(os.path.join(SP, p)):
                    miss.append(p)
        if miss:
            out.append((pkg, ver, di, miss))
    return out


def fetch(pkg, ver):
    d = tempfile.mkdtemp(prefix="fx_")
    cmd = [PY, "-m", "pip", "download", "--no-deps", "--no-cache-dir", "-d", d, f"{pkg}=={ver}"]
    if pkg.startswith("paddlepaddle"):
        cmd += ["-i", PADDLE_IDX]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3000)
    whls = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".whl")]
    return whls[0] if whls else None


def apply_wheel(whl, missing, dist_dir):
    unz = tempfile.mkdtemp(prefix="fz_")
    with zipfile.ZipFile(whl) as z:
        z.extractall(unz)
    # 1) 补齐包文件
    n_file = 0
    if missing is None:
        for root, _, fs in os.walk(unz):
            for f in fs:
                s = os.path.join(root, f)
                rel = os.path.relpath(s, unz).replace("/", os.sep)
                if ".dist-info" + os.sep in rel:
                    continue
                dst = os.path.join(SP, rel)
                if os.path.exists(dst):
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(s, dst)
                n_file += 1
    else:
        for rel in missing:
            for cand in (os.path.join(unz, rel.replace(os.sep, "/")), os.path.join(unz, rel)):
                if os.path.isfile(cand):
                    dst = os.path.join(SP, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(cand, dst)
                    n_file += 1
                    break
    # 2) 补齐 dist-info 元数据
    n_meta = 0
    src_di = None
    for d in os.listdir(unz):
        if d.endswith(".dist-info"):
            src_di = os.path.join(unz, d)
            break
    if src_di:
        for fn in os.listdir(src_di):
            s = os.path.join(src_di, fn)
            if not os.path.isfile(s):
                continue
            if fn == "RECORD" and os.path.isfile(os.path.join(dist_dir, "RECORD")):
                continue  # 已有 RECORD 就不覆盖（避免与已装版本不一致）
            os.makedirs(dist_dir, exist_ok=True)
            shutil.copy2(s, os.path.join(dist_dir, fn))
            n_meta += 1
    return n_file, n_meta


def main():
    targets = scan()
    print(f"扫描完成：{len(targets)} 个包需要处理")
    for pkg, ver, dist_dir, missing in targets:
        tag = "无RECORD" if missing is None else f"{len(missing)} 文件缺失"
        print(f"  → {pkg} {ver} ({tag})", flush=True)
        whl = fetch(pkg, ver)
        if not whl:
            print(f"     !! 下载失败，跳过", flush=True)
            continue
        try:
            nf, nm = apply_wheel(whl, missing, dist_dir)
            print(f"     补齐 {nf} 个文件 / {nm} 个元数据", flush=True)
        except Exception as e:
            print(f"     !! 写入失败 {type(e).__name__}: {e}", flush=True)
    print("自愈结束")


if __name__ == "__main__":
    main()
