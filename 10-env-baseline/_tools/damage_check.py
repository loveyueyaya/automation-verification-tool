# -*- coding: utf-8 -*-
"""判定回收站中的删除条目是否造成"当前缺失"：
  - 当前仍存在  → 属于覆盖式替换的旧版本（良性）
  - 当前不存在  → 真实丢失（事故受害文件），可从 $R 负载恢复

用法：python damage_check.py [--list]
"""
import os
import sys
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
    name = os.path.basename(path)
    rname = "$R" + name[2:]
    payload = os.path.join(os.path.dirname(path), rname)
    return {"ts": ts, "orig": parts[-1] if parts else "", "i": path, "r": payload,
            "has_payload": os.path.exists(payload),
            "psize": os.path.getsize(payload) if os.path.exists(payload) else 0}


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
    sp = [r for r in items if r["orig"].startswith(SP)]
    missing = [r for r in sp if not os.path.exists(r["orig"])]
    present = [r for r in sp if os.path.exists(r["orig"])]
    print("site-packages 回收条目: {}（当前仍存在 {} / 当前缺失 {}）".format(len(sp), len(present), len(missing)))
    print("缺失条目中带可恢复负载 ($R) 的: {}".format(sum(1 for r in missing if r["has_payload"])))
    print("可恢复负载总字节: {:.1f} MB".format(sum(r["psize"] for r in missing) / 2 ** 20))
    top = collections.Counter(r["orig"][len(SP) + 1:].split("\\")[0] for r in missing)
    print("\n缺失文件的顶层包分布（Top 25）:")
    for k, v in top.most_common(25):
        print("  {:32} {}".format(k, v))
    t = collections.Counter(r["ts"].strftime("%m-%d %H:%M") for r in missing)
    print("\n缺失文件的删除时刻分布（Top 15）:")
    for k, v in sorted(t.items(), key=lambda kv: -kv[1])[:15]:
        print("  {}  {} 条".format(k, v))
    if "--list" in sys.argv:
        print("\n=== 全部缺失条目 ===")
        for r in sorted(missing, key=lambda x: x["ts"]):
            print("  {} | {:>9} | {} | 负载={}".format(
                r["ts"], r["psize"], r["orig"][len(SP):], "有" if r["has_payload"] else "无"))


if __name__ == "__main__":
    main()
