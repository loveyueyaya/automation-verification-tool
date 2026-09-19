# -*- coding: utf-8 -*-
"""按时间窗口 × 包名统计"当前缺失"的文件，用于把删除波次与具体操作做归因。

用法：python attribute_waves.py
"""
import os
import glob
import struct
import datetime
import collections

SP = r"C:\Program Files\Python313\Lib\site-packages"

WINDOWS = [
    ("W1 00:05-00:20 pip/依赖操作", datetime.datetime(2026, 9, 19, 0, 5), datetime.datetime(2026, 9, 19, 0, 20)),
    ("W2 01:45-02:00 opencv 卸载/覆盖", datetime.datetime(2026, 9, 19, 1, 45), datetime.datetime(2026, 9, 19, 2, 0)),
    ("W3 03:30-03:45 pip uninstall paddlepaddle", datetime.datetime(2026, 9, 19, 3, 30), datetime.datetime(2026, 9, 19, 3, 45)),
    ("W4 其他时刻", None, None),
]


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


def main():
    items = []
    for drv in ("C", "F"):
        for sub in glob.glob("{}:\\$RECYCLE.BIN\\*".format(drv)):
            if not os.path.isdir(sub):
                continue
            for f in glob.glob(os.path.join(sub, "$I*")):
                r = parse_i(f)
                if r:
                    items.append(r)
    missing = [(t, p) for t, p in items if p.startswith(SP) and not os.path.exists(p)]
    print("当前缺失文件总数:", len(missing))
    buckets = collections.defaultdict(list)
    for t, p in missing:
        name = "W4 其他时刻"
        for label, a, b in WINDOWS:
            if a and a <= t <= b:
                name = label
                break
        buckets[name].append((t, p))
    for label, _, _ in WINDOWS:
        rows = buckets.get(label, [])
        if not rows:
            continue
        print("\n" + "=" * 66)
        print("{}  共 {} 个缺失文件".format(label, len(rows)))
        rows.sort()
        print("  时间跨度: {} ~ {}".format(rows[0][0], rows[-1][0]))
        top = collections.Counter(p[len(SP) + 1:].split("\\")[0] for _, p in rows)
        print("  包分布（Top 12）:")
        for k, v in top.most_common(12):
            print("    {:30} {}".format(k, v))


if __name__ == "__main__":
    main()
