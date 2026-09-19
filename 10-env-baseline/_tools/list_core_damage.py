# -*- coding: utf-8 -*-
"""列出"真实缺失"的文件明细，区分核心/外围；并显式报告回收站扫描口径。"""
import os
import glob
import struct
import datetime
import collections

SP = r"C:\Program Files\Python313\Lib\site-packages"
PERI = ("test", "tests", "testing", "example", "examples", "doc", "docs",
        "benchmark", "benchmarks", "demos", "demo", "__pycache__", "licenses")
PERI_EXT = (".pyi", ".pxd", ".h", ".hpp", ".f90", ".f", ".c", ".cpp", ".pyx", ".tpl",
            ".txt", ".md", ".rst", ".json", ".cfg", ".toml", ".in", ".pyc")


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


def is_core(rel):
    parts = rel.split("\\")
    nm = parts[-1].lower()
    if any(p.lower() in PERI for p in parts[:-1]):
        return False
    if nm.endswith(PERI_EXT):
        return False
    return nm.endswith((".py", ".pyd", ".dll", ".so"))


def main():
    pats = ["{}:\\$RECYCLE.BIN\\*".format(d) for d in ("C", "F")]
    print("扫描模式:", pats)
    bins, items = [], []
    for pat in pats:
        for sub in glob.glob(pat):
            if os.path.isdir(sub):
                bins.append(sub)
                for f in glob.glob(os.path.join(sub, "$I*")):
                    r = parse_i(f)
                    if r:
                        items.append(r)
    print("回收站子目录:", len(bins), "| 条目总数:", len(items))
    sp_items = [(t, p) for t, p in items if p.startswith(SP)]
    missing = [(t, p) for t, p in sp_items if not os.path.exists(p)]
    print("site-packages 条目:", len(sp_items), "| 当前缺失:", len(missing))
    real = [(t, p) for t, p in missing
            if "\\~" not in p and not os.path.basename(p).startswith("~") and "_delbench" not in p and "_wbaudit" not in p]
    junk = len(missing) - len(real)
    core = [(t, p) for t, p in real if is_core(p[len(SP) + 1:])]
    peri = [(t, p) for t, p in real if not is_core(p[len(SP) + 1:])]
    print("\n排除 ~ 残留/测试残留后：真实缺失 {}（其中 ~ 等残留 {}）".format(len(real), junk))
    print("  核心文件缺失: {}".format(len(core)))
    print("  外围文件缺失: {}".format(len(peri)))
    print("\n=== 核心文件缺失明细 ===")
    for t, p in sorted(core):
        print("  {} | {}".format(t, p[len(SP) + 1:]))
    print("\n=== 外围缺失按目录聚合 Top 20 ===")
    c = collections.Counter()
    for t, p in peri:
        parts = p[len(SP) + 1:].split("\\")
        c["\\".join(parts[:2]) if len(parts) > 1 else parts[0]] += 1
    for k, v in c.most_common(20):
        print("  {:52} {}".format(k, v))
    print("\n=== 外围缺失按包聚合 Top 20 ===")
    c2 = collections.Counter(p[len(SP) + 1:].split("\\")[0] for t, p in peri)
    for k, v in c2.most_common(20):
        print("  {:32} {}".format(k, v))


if __name__ == "__main__":
    main()
