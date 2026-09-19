# -*- coding: utf-8 -*-
"""环境受损评估：按包统计缺失文件，区分"核心文件"与"外围文件"，并实测可导入性。

核心文件判定：包根 __init__.py、根级 *.py、任何 *.pyd/*.dll/*.so（原生扩展）、
              任何非 test/example/doc 路径下的 .py
外围文件判定：tests/、examples/、docs/、benchmarks/、*.pyi、*.pxd、*.h、*.f90、
              .dist-info 内文件、__pycache__、*.txt/*.md/*.rst 等

用法：python assess_damage.py
"""
import os
import glob
import struct
import datetime
import collections
import importlib.util

SP = r"C:\Program Files\Python313\Lib\site-packages"
PERIPHERAL_DIR = ("test", "tests", "testing", "example", "examples", "doc", "docs",
                  "benchmark", "benchmarks", "demos", "demo", "__pycache__", "licenses")


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
    return {"ts": ts, "orig": parts[-1] if parts else "", "payload": payload,
            "has_payload": os.path.exists(payload)}


def collect_missing():
    items = []
    for drv in ("C", "F"):
        for sub in glob.glob("{}:\\$RECYCLE.BIN\\*".format(drv)):
            if not os.path.isdir(sub):
                continue
            for f in glob.glob(os.path.join(sub, "$I*")):
                r = parse_i(f)
                if r and r["orig"].startswith(SP) and not os.path.exists(r["orig"]):
                    items.append(r)
    return items


def is_core(path):
    rel = path[len(SP) + 1:]
    parts = rel.split("\\")
    name = parts[-1].lower()
    if any(p.lower() in PERIPHERAL_DIR for p in parts[:-1]):
        return False
    if name.endswith((".pyi", ".pxd", ".h", ".hpp", ".f90", ".f", ".c", ".cpp", ".txt",
                      ".md", ".rst", ".json", ".cfg", ".toml", ".in", ".pyx", ".tpl")):
        return False
    if name.endswith((".py", ".pyd", ".dll", ".so")):
        return True
    # .pyc 之类算外围（可自动重建）
    return False


def main():
    missing = collect_missing()
    print("当前缺失文件总数: {}\n".format(len(missing)))
    by_pkg = collections.defaultdict(list)
    for r in missing:
        rel = r["orig"][len(SP) + 1:]
        top = rel.split("\\")[0]
        by_pkg[top if "\\" in rel else "(根级文件) " + rel].append(r)

    rows = []
    for pkg, rs in by_pkg.items():
        core = [r for r in rs if is_core(r["orig"])]
        recov = [r for r in rs if r["has_payload"]]
        # 实测可导入性
        modname = pkg.replace("~", "").replace("-", "_") if not pkg.startswith("(") else None
        importable = "—"
        if modname:
            try:
                importable = "是" if importlib.util.find_spec(modname) else "否"
            except Exception:
                importable = "否(异常)"
        rows.append((pkg, len(rs), len(core), len(recov), importable))

    rows.sort(key=lambda x: (-x[2], -x[1]))
    print("{:30} {:>6} {:>7} {:>6}  {:>6}".format("包/目录", "缺失数", "核心文件", "可恢复", "可导入"))
    print("-" * 68)
    tc = tm = 0
    for pkg, n, c, rc, imp in rows:
        tc += c
        tm += n
        print("{:30} {:>6} {:>7} {:>6}  {:>6}".format(pkg, n, c, rc, imp))
    print("-" * 68)
    print("{:30} {:>6} {:>7}".format("合计", tm, tc))


if __name__ == "__main__":
    main()
