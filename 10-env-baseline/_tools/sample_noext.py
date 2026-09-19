# -*- coding: utf-8 -*-
"""抽样"无扩展名"缺失条目，确认是否含功能性文件。"""
import os
import glob
import struct
import datetime

SP = r"C:\Program Files\Python313\Lib\site-packages"
PERI_DIR = ("test", "tests", "testing", "example", "examples", "doc", "docs",
            "benchmark", "benchmarks", "demos", "demo", "__pycache__", "licenses")
PERI_EXT = (".pyi", ".pxd", ".h", ".hpp", ".f90", ".f", ".c", ".cpp", ".pyx", ".tpl",
            ".txt", ".md", ".rst", ".json", ".cfg", ".toml", ".in", ".pyc")


def parse_i(path):
    with open(path, "rb") as f:
        b = f.read()
    ft = struct.unpack_from("<Q", b, 16)[0]
    ts = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=ft / 10) + datetime.timedelta(hours=8)
    txt = b[24:].decode("utf-16-le", errors="ignore")
    parts = [x for x in txt.split("\x00") if x.strip()]
    return ts, (parts[-1] if parts else "")


def is_core(rel):
    parts = rel.split("\\")
    nm = parts[-1].lower()
    if any(p.lower() in PERI_DIR for p in parts[:-1]):
        return False
    if nm.endswith(PERI_EXT):
        return False
    return nm.endswith((".py", ".pyd", ".dll", ".so"))


def main():
    items = []
    for pat in ["C:\\$RECYCLE.BIN\\*", "F:\\$RECYCLE.BIN\\*"]:
        for sub in glob.glob(pat):
            if os.path.isdir(sub):
                for f in glob.glob(os.path.join(sub, "$I*")):
                    r = parse_i(f)
                    if r and r[1].startswith(SP) and not os.path.exists(r[1]):
                        items.append(r)
    real = [(t, x) for t, x in items
            if "\\~" not in x and not os.path.basename(x).startswith("~")
            and "_delbench" not in x and "_wbaudit" not in x and "_wbmk" not in x]
    ex = [(t, x) for t, x in real if not os.path.splitext(x)[1]]
    print("无扩展名真实缺失条目数:", len(ex))
    print("\n前 25 条全路径（供人工判定是否功能性文件）:")
    for t, x in sorted(ex)[:25]:
        print("  {} | {}".format(t, x[len(SP) + 1:]))
    # 统计这些路径的父目录
    import collections
    c = collections.Counter(os.path.dirname(x[len(SP) + 1:]) for _, x in ex)
    print("\n父目录 Top 15:")
    for k, v in c.most_common(15):
        print("  {:52} {}".format(k, v))


if __name__ == "__main__":
    main()
