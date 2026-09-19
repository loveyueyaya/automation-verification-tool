# -*- coding: utf-8 -*-
"""环境损失评估（最终口径）：一次性输出分类汇总 + 无扩展名条目分布 + 逐包可导入实测。

用法：python final_assessment.py
"""
import os
import glob
import struct
import datetime
import collections
import importlib.util

SP = r"C:\Program Files\Python313\Lib\site-packages"
PERI_DIR = ("test", "tests", "testing", "example", "examples", "doc", "docs",
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
    if any(p.lower() in PERI_DIR for p in parts[:-1]):
        return False
    if nm.endswith(PERI_EXT):
        return False
    return nm.endswith((".py", ".pyd", ".dll", ".so"))


def collect_windows(pat):
    out = []
    for sub in glob.glob(pat):
        if os.path.isdir(sub):
            for f in glob.glob(os.path.join(sub, "$I*")):
                r = parse_i(f)
                if r:
                    out.append(r)
    return out


def main():
    patterns = ["C:\\$RECYCLE.BIN\\*", "F:\\$RECYCLE.BIN\\*"]
    items = []
    for p in patterns:
        items += collect_windows(p)
    sp_missing = [(t, x) for t, x in items if x.startswith(SP) and not os.path.exists(x)]
    tmp_junk = [(t, x) for t, x in sp_missing
                if "\\~" in x or os.path.basename(x).startswith("~")
                or "_delbench" in x or "_wbaudit" in x or "_wbmk" in x]
    real = [(t, x) for t, x in sp_missing if (t, x) not in tmp_junk]
    core = [(t, x) for t, x in real if is_core(x[len(SP) + 1:])]
    peri = [(t, x) for t, x in real if not is_core(x[len(SP) + 1:])]

    print("=== A. 总量 ===")
    print("回收站条目总数            :", len(items))
    print("site-packages 相关条目    :", len([1 for t, x in items if x.startswith(SP)]))
    print("其中当前仍缺失            :", len(sp_missing))
    print("  ├ 卸载残留/~ 前缀/测试残留:", len(tmp_junk), "（属垃圾，非功能文件）")
    print("  └ 真实缺失              :", len(real))
    print("      ├ 核心文件          :", len(core))
    print("      └ 外围文件          :", len(peri))

    print("\n=== B. 真实缺失的类型构成 ===")
    ext = collections.Counter(os.path.splitext(x)[1].lower() or "(无扩展名)" for _, x in real)
    for k, v in ext.most_common():
        print("  {:14} {}".format(k, v))

    print("\n=== C. 无扩展名条目的目录归属 ===")
    c = collections.Counter()
    for _, x in real:
        if os.path.splitext(x)[1]:
            continue
        top = x[len(SP) + 1:].split("\\")[0]
        c["(accesstest_* 沙箱权限自检残留)" if top.startswith("accesstest") else top] += 1
    for k, v in c.most_common(15):
        print("  {:44} {}".format(k, v))

    print("\n=== D. 核心文件缺失明细 ===")
    for t, x in sorted(core):
        print("  {} | {}".format(t, x[len(SP) + 1:]))

    print("\n=== E. 外围 .pyi 缺失明细（类型存根，不影响运行）===")
    for t, x in sorted([r for r in peri if r[1].lower().endswith(".pyi")]):
        print("  {} | {}".format(t, x[len(SP) + 1:]))

    print("\n=== F. 涉及包的可导入实测 ===")
    pkgs = sorted({x[len(SP) + 1:].split("\\")[0] for _, x in real
                   if not x[len(SP) + 1:].split("\\")[0].startswith("accesstest")})
    ok = fail = 0
    for pkg in pkgs:
        mod = pkg.replace("-", "_")
        if pkg.endswith(".dist-info") or not os.path.isdir(os.path.join(SP, pkg)):
            continue
        try:
            s = importlib.util.find_spec(mod)
            state = "OK" if s else "FAIL"
        except Exception as e:
            state = "FAIL(%s)" % type(e).__name__
        if state == "OK":
            ok += 1
        else:
            fail += 1
            print("  ⚠ {} → {}".format(pkg, state))
    print("  涉及包 {} 个：可导入 {} / 不可导入 {}".format(ok + fail, ok, fail))


if __name__ == "__main__":
    main()
