# -*- coding: utf-8 -*-
"""字节码等价性验证：F 盘重建 .py 编译后 vs pyc 缓存原始 .pyc 的 co_code sha256 对比。"""
import marshal
import hashlib
import types
import os

SRC = r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层\scripts"
PYC = (r"C:\Users\Administrator\AppData\Local\Doubao\User Data\sandbox_runtime"
       r"\.cache\python\pyc-cache\Users\Administrator\AppData\Local\Doubao"
       r"\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
       r"\ui-toolbox\scripts")


def load_pyc(path):
    with open(path, "rb") as f:
        f.read(16)
        return marshal.loads(f.read())


def flatten(co, prefix=""):
    out = []
    for k in co.co_consts:
        if isinstance(k, types.CodeType):
            p = (prefix + "." + k.co_name) if prefix else k.co_name
            out.append((p, k))
            out.extend(flatten(k, p))
    return out


def h(data):
    return hashlib.sha256(data).hexdigest()


targets = ["locate.py", "timeline.py", "uitool.py", "env.py"]
for fn in targets:
    name = fn[:-3]
    src_path = os.path.join(SRC, fn)
    pyc_path = os.path.join(PYC, name + ".cpython-313.pyc")
    if not os.path.exists(pyc_path):
        print("=== %s: pyc 不存在 %s" % (fn, pyc_path))
        continue
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    new_co = compile(src, fn, "exec")
    old_co = load_pyc(pyc_path)
    print("=== %s ===" % fn)
    print("模块级 co_code 长度: 原始 %d / 重建 %d"
          % (len(old_co.co_code), len(new_co.co_code)))
    print("模块级 co_code sha256 原始: %s" % h(old_co.co_code))
    print("模块级 co_code sha256 重建: %s" % h(new_co.co_code))
    print("模块级 co_code 一致: %s" % (old_co.co_code == new_co.co_code))
    old_f = dict(flatten(old_co))
    new_f = dict(flatten(new_co))
    only_old = [k for k in old_f if k not in new_f]
    only_new = [k for k in new_f if k not in old_f]
    print("函数集合仅原始有: %s" % only_old)
    print("函数集合仅重建有: %s" % only_new)
    mismatch = []
    for k in old_f:
        if k in new_f:
            o, n = old_f[k], new_f[k]
            if o.co_code != n.co_code:
                mismatch.append((k, len(o.co_code), len(n.co_code),
                                 h(o.co_code), h(n.co_code)))
    if mismatch:
        for m in mismatch:
            print("函数 co_code 不一致: %s 原始len=%d 重建len=%d"
                  % (m[0], m[1], m[2]))
            print("  原始 sha256: %s" % m[3])
            print("  重建 sha256: %s" % m[4])
    else:
        print("全部函数 co_code 一致: %d 个函数" % len(old_f))
    print()
