# -*- coding: utf-8 -*-
"""定位 ocr.py / sendinput.py 同名函数 co_code 差异：指令/常量/局部名。"""
import dis
import marshal
import os
import types

SRC = r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层\scripts"
PYC = (r"C:\Users\Administrator\AppData\Local\Doubao\User Data\sandbox_runtime"
       r"\.cache\python\pyc-cache\Users\Administrator\AppData\Local\Doubao"
       r"\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
       r"\ui-toolbox\scripts")


def load_pyc(path):
    with open(path, "rb") as f:
        f.read(16)
        return marshal.loads(f.read())


def module_funcs(co):
    out = {}
    for k in co.co_consts:
        if isinstance(k, types.CodeType) and not k.co_name.startswith("<"):
            out[k.co_name] = k
    return out


def first_diff_insn(old, new):
    oi = list(dis.get_instructions(old))
    ni = list(dis.get_instructions(new))
    for a, b in zip(oi, ni):
        if (a.opname, a.argval, a.argrepr) != (b.opname, b.argval, b.argrepr):
            return (a, b)
    if len(oi) != len(ni):
        return ("len", len(oi), len(ni))
    return None


for fn in ("ocr.py", "sendinput.py"):
    name = fn[:-3]
    with open(os.path.join(SRC, fn), encoding="utf-8") as f:
        new_co = compile(f.read(), fn, "exec")
    old_co = load_pyc(os.path.join(PYC, name + ".cpython-313.pyc"))
    of = module_funcs(old_co)
    nf = module_funcs(new_co)
    print("=" * 72)
    print("### %s" % fn)
    for k in of:
        if k not in nf or of[k].co_code == nf[k].co_code:
            continue
        o, n = of[k], nf[k]
        d = first_diff_insn(o, n)
        const_ok = [repr(c) for c in o.co_consts
                    if not isinstance(c, types.CodeType)] == \
                   [repr(c) for c in n.co_consts
                    if not isinstance(c, types.CodeType)]
        print("- %s: 原始 %d 指令 / F盘 %d 指令 | 第一处差异: %s | 常量表一致: %s"
              % (k, len(list(dis.get_instructions(o))),
                 len(list(dis.get_instructions(n))), d, const_ok))
        print("    原始局部名: %s" % list(o.co_varnames))
        print("    F盘局部名: %s" % list(n.co_varnames))
        if d and isinstance(d, tuple) and len(d) == 2 and hasattr(d[0], "opname"):
            print("    原始指令: %s %s | F盘指令: %s %s"
                  % (d[0].opname, d[0].argrepr, d[1].opname, d[1].argrepr))
