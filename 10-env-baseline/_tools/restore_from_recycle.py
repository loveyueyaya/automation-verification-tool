# -*- coding: utf-8 -*-
"""从回收站按原路径恢复文件/目录（只补不删，用于事故修复）。

原理：回收站里每对被删对象有两份：
  $I<id><ext>  → 元数据（原始路径、删除时间、大小）
  $R<id><ext>  → 实际内容（目录则含整棵子树）

用法：
  python restore_from_recycle.py --find "<关键字>"            # 只查不改
  python restore_from_recycle.py --path "<原始绝对路径>" --apply
  python restore_from_recycle.py --prefix "<目录前缀>" --apply
"""
import argparse
import datetime
import glob
import os
import shutil
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_i(path):
    with open(path, "rb") as f:
        b = f.read()
    if len(b) < 24:
        return None
    ft = struct.unpack_from("<Q", b, 16)[0]
    ts = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft / 10) + datetime.timedelta(hours=8)
    txt = b[24:].decode("utf-16-le", errors="ignore")
    parts = [x for x in txt.split("\x00") if x.strip()]
    return {"i": path, "r": os.path.join(os.path.dirname(path), "$R" + os.path.basename(path)[2:]),
            "orig": parts[-1] if parts else "", "ts": ts}


def collect():
    out = []
    for drv in ("C", "F"):
        for sub in glob.glob("{}:\\$RECYCLE.BIN\\*".format(drv)):
            if os.path.isdir(sub):
                for f in glob.glob(os.path.join(sub, "$I*")):
                    r = parse_i(f)
                    if r:
                        out.append(r)
    return out


def restore(item, apply_):
    orig, payload = item["orig"], item["r"]
    if not os.path.exists(payload):
        return "无负载，跳过"
    if os.path.isdir(payload):
        if os.path.exists(orig):
            return "目标已存在，跳过"
        if apply_:
            shutil.copytree(payload, orig)
            return "✅ 已恢复目录（%d 文件）" % sum(len(f) for _, _, f in os.walk(orig))
        return "将恢复目录（-apply 执行）"
    else:
        if os.path.exists(orig):
            return "目标已存在，跳过"
        if apply_:
            os.makedirs(os.path.dirname(orig), exist_ok=True)
            shutil.copy2(payload, orig)
            return "✅ 已恢复文件（%d 字节）" % os.path.getsize(orig)
        return "将恢复文件（-apply 执行）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--find")
    ap.add_argument("--path")
    ap.add_argument("--prefix")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    items = collect()
    if a.find:
        hits = [x for x in items if a.find.lower() in x["orig"].lower()]
        hits.sort(key=lambda x: x["ts"])
        print("匹配 %d 条：%s" % (len(hits), "(apply 模式)" if a.apply else "(dry-run)"))
        n_ok = 0
        for x in hits[:200]:
            st = restore(x, a.apply) if a.apply else ("负载=%s" % os.path.exists(x["r"]))
            print("  {} | {} | {}".format(x["ts"], x["orig"], st))
            if str(st).startswith("✅"):
                n_ok += 1
        if a.apply:
            print("完成：成功恢复 %d 项" % n_ok)
        return
    if not (a.path or a.prefix):
        ap.print_help()
        return
    print("收到 path=%r prefix=%r" % (a.path, a.prefix))
    hits = [x for x in items if (a.path and x["orig"] == a.path) or (a.prefix and x["orig"].startswith(a.prefix))]
    hits.sort(key=lambda x: len(x["orig"]))
    print("匹配 %d 条，模式=%s" % (len(hits), "apply" if a.apply else "dry-run"))
    n_ok = 0
    for x in hits:
        st = restore(x, a.apply)
        print("  {} | {}".format(x["orig"], st))
        if st.startswith("✅"):
            n_ok += 1
    print("完成：成功恢复 %d 项" % n_ok)


if __name__ == "__main__":
    main()
