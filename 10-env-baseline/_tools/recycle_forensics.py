# -*- coding: utf-8 -*-
"""回收站取证：解析 $I 元数据，还原被删除文件的原路径 + 删除时间。

用法：python recycle_forensics.py [关键字子串] [--since "YYYY-MM-DD HH:MM"]
"""
import os
import sys
import glob
import struct
import datetime
import collections

SP_PREFIX = r"C:\Program Files\Python313"


def parse_i(path):
    with open(path, "rb") as f:
        b = f.read()
    if len(b) < 24:
        return None
    ft = struct.unpack_from("<Q", b, 16)[0]
    try:
        ts = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft / 10) + datetime.timedelta(hours=8)
    except Exception:
        ts = None
    txt = b[24:].decode("utf-16-le", errors="ignore")
    parts = [x for x in txt.split("\x00") if x.strip()]
    return ts, (parts[-1] if parts else "")


def collect():
    items = []
    bins = []
    for drv in ("C", "F"):
        for sub in glob.glob("{}:\\$RECYCLE.BIN\\*".format(drv)):
            if os.path.isdir(sub):
                bins.append(sub)
    for b in bins:
        for f in glob.glob(os.path.join(b, "$I*")):
            r = parse_i(f)
            if r:
                items.append(r)
    return bins, items


def main():
    argv = sys.argv[1:]
    kws = []
    since = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--since":
            since = datetime.datetime.strptime(argv[i + 1], "%Y-%m-%d %H:%M")
            i += 2
            continue
        kws.append(a)
        i += 1
    bins, items = collect()
    print("回收站目录数:", len(bins))
    print("条目总数:", len(items))
    sp = [(t, p) for t, p in items if p.startswith(SP_PREFIX)]
    print("Python313 相关条目:", len(sp))
    if since:
        sp = [(t, p) for t, p in sp if t and t >= since]
        print("  其中 >= {}: {}".format(since, len(sp)))
    if kws:
        sp = [(t, p) for t, p in sp if any(k.lower() in p.lower() for k in kws)]
        print("  匹配关键字 {}: {}".format(kws, len(sp)))
    sp.sort(key=lambda x: x[0] or datetime.datetime.min)
    c = collections.Counter(t.strftime("%m-%d %H:%M") for t, _ in sp)
    print("\n按时分聚合（Top 20）:")
    for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:20]:
        print("  {}  {} 条".format(k, v))
    print("\n明细（最多 40 条）:")
    for t, p in sp[:40]:
        print("  {} | {}".format(t, p[:130]))


if __name__ == "__main__":
    main()
