# -*- coding: utf-8 -*-
"""分析回收站删除波次的组成：每波删了哪些目录、多少文件。

用法：python analyze_waves.py
"""
import os
import re
import glob
import struct
import datetime
import collections

SP = r"C:\Program Files\Python313\Lib\site-packages"


def parse_i(path):
    with open(path, "rb") as f:
        b = f.read()
    if len(b) < 24:
        return None
    ft = struct.unpack_from("<Q", b, 16)[0]
    ts = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft / 10) + datetime.timedelta(hours=8)
    txt = b[24:].decode("utf-16-le", errors="ignore")
    parts = [x for x in txt.split("\x00") if x.strip()]
    return ts, (parts[-1] if parts else "")


def collect():
    items = []
    for drv in ("C", "F"):
        for sub in glob.glob("{}:\\$RECYCLE.BIN\\*".format(drv)):
            if not os.path.isdir(sub):
                continue
            for f in glob.glob(os.path.join(sub, "$I*")):
                r = parse_i(f)
                if r:
                    items.append(r)
    return items


def wave_of(ts):
    h = ts.strftime("%m-%d %H:%M")
    if ts.strftime("%m-%d") == "09-19":
        if "00:0" in h or "00:1" in h:
            return "波次A 00:08-00:17"
        if "01:4" in h or "01:5" in h:
            return "波次B 01:49-01:55"
        if "03:3" in h or "03:4" in h:
            return "波次C 03:33-03:41"
    return "其他"


def main():
    items = collect()
    sp = [(t, p) for t, p in items if p.startswith(SP)]
    waves = collections.defaultdict(list)
    for t, p in sp:
        waves[wave_of(t)].append((t, p))
    for name in sorted(waves.keys()):
        rows = waves[name]
        print("=" * 70)
        print("{}  共 {} 条".format(name, len(rows)))
        if not rows:
            continue
        rows.sort()
        print("  时间跨度: {} ~ {}".format(rows[0][0], rows[-1][0]))
        top = collections.Counter()
        for _, p in rows:
            rel = p[len(SP) + 1:]
            top[rel.split("\\")[0]] += 1
        print("  顶层目录分布（Top 15）:")
        for k, v in top.most_common(15):
            print("    {:38} {}".format(k, v))
        exts = collections.Counter(os.path.splitext(p)[1].lower() for _, p in rows)
        print("  扩展名分布:", dict(exts.most_common(8)))
        print("  前 3 条样例:")
        for t, p in rows[:3]:
            print("    {} | {}".format(t, p[len(SP) + 1:]))


if __name__ == "__main__":
    main()
