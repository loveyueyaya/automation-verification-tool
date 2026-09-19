# -*- coding: utf-8 -*-
"""外围缺失文件的类型分布 + 抽样，并逐包核对"包能否正常加载"的关键文件是否完好。"""
import os
import glob
import struct
import datetime
import collections
import importlib.util

SP = r"C:\Program Files\Python313\Lib\site-packages"
PERI = ("test", "tests", "testing", "example", "examples", "doc", "docs",
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
    if any(p.lower() in PERI for p in parts[:-1]):
        return False
    if nm.endswith(PERI_EXT):
        return False
    return nm.endswith((".py", ".pyd", ".dll", ".so"))


def main():
    items = []
    for d in ("C", "F"):
        for sub in glob.glob("{}:\\$RECYCLE.BIN\\*".format(d)):
            if os.path.isdir(sub):
                for f in glob.glob(os.path.join(sub, "$I*")):
                    r = parse_i(f)
                    if r and r[1].startswith(SP) and not os.path.exists(r[1]):
                        items.append(r)
    real = [(t, p) for t, p in items
            if "\\~" not in p and not os.path.basename(p).startswith("~")
            and "_delbench" not in p and "_wbaudit" not in p]
    peri = [(t, p) for t, p in real if not is_core(p[len(SP) + 1:])]

    ext = collections.Counter(os.path.splitext(p)[1].lower() or "(无扩展名)" for _, p in peri)
    print("=== 外围缺失文件 扩展名分布 ===")
    for k, v in ext.most_common():
        print("  {:14} {}".format(k, v))

    print("\n=== 抽样（每类前 3 条）===")
    shown = collections.defaultdict(int)
    for t, p in sorted(peri):
        e = os.path.splitext(p)[1].lower() or "(无扩展名)"
        if shown[e] < 3:
            shown[e] += 1
            print("  [{}] {}".format(e, p[len(SP) + 1:]))

    print("\n=== 逐包关键文件完整性（__init__.py / 顶层 .py / 扩展 pyd）===")
    pkgs = sorted({p[len(SP) + 1:].split("\\")[0] for _, p in real})
    pkgs = [k for k in pkgs if not k.endswith(".dist-info") and not k.startswith("accesstest_deleteme")]
    print("（已排除 *.dist-info 元数据目录与 accesstest_* 沙箱自检残留；共 {} 个实际包）".format(len(pkgs)))
    for pkg in pkgs:
        d = os.path.join(SP, pkg)
        if not os.path.isdir(d):
            print("  {:24} 目录不存在".format(pkg))
            continue
        init = os.path.join(d, "__init__.py")
        pys = [f for f in os.listdir(d) if f.endswith(".py")]
        pyds = [f for f in os.listdir(d) if f.endswith((".pyd", ".dll"))]
        miss_init = not os.path.exists(init)
        try:
            spec = importlib.util.find_spec(pkg)
            imp = "OK" if spec else "FAIL"
        except Exception as e:
            imp = "FAIL(%s)" % type(e).__name__
        flag = "⚠" if (miss_init or imp != "OK") else " "
        print("  {} {:24} import={:6} __init__.py={:8} 顶层.py={:3} pyd/dll={}".format(
            flag, pkg, imp, "缺失" if miss_init else "在位", len(pys), len(pyds)))


if __name__ == "__main__":
    main()
