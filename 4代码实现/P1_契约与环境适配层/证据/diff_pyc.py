# -*- coding: utf-8 -*-
"""逐指令 diff：原始 pyc vs 重建 pyc，输出每个不一致函数的第一处指令差异与上下文。"""
import dis
import marshal
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


def instrs(co):
    return [(i.opname, i.argval, i.argrepr) for i in dis.get_instructions(co)]


targets = ["locate.py", "timeline.py", "uitool.py", "env.py"]
for fn in targets:
    name = fn[:-3]
    src_path = os.path.join(SRC, fn)
    pyc_path = os.path.join(PYC, name + ".cpython-313.pyc")
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    new_co = compile(src, fn, "exec")
    old_co = load_pyc(pyc_path)
    old_f = dict(flatten(old_co))
    new_f = dict(flatten(new_co))
    for k in old_f:
        if k in new_f:
            o, n = old_f[k], new_f[k]
            if o.co_code != n.co_code:
                oi, ni = instrs(o), instrs(n)
                print("### %s  [原始 %d 指令 / 重建 %d 指令]"
                      % (k, len(oi), len(ni)))
                print("  原始 consts: %s" % [repr(c)[:40]
                      for c in o.co_consts if not isinstance(c, types.CodeType)])
                print("  重建 consts: %s" % [repr(c)[:40]
                      for c in n.co_consts if not isinstance(c, types.CodeType)])
                print("  原始 varnames: %s" % list(o.co_varnames))
                print("  重建 varnames: %s" % list(n.co_varnames))
                # 第一处差异
                for idx in range(max(len(oi), len(ni))):
                    a = oi[idx] if idx < len(oi) else ("<END>", None, "")
                    b = ni[idx] if idx < len(ni) else ("<END>", None, "")
                    if a != b:
                        lo = max(0, idx - 3)
                        hi = min(len(oi), idx + 4)
                        print("  第一差异 @指令 %d:" % idx)
                        for j in range(lo, hi):
                            mark = ">>" if j == idx else "  "
                            ov = oi[j] if j < len(oi) else ("<END>", None, "")
                            print("    %s 原始[%d] %-32s %s" % (mark, j, ov[0], ov[1]))
                        lo2 = max(0, idx - 3)
                        hi2 = min(len(ni), idx + 4)
                        for j in range(lo2, hi2):
                            mark = ">>" if j == idx else "  "
                            nv = ni[j] if j < len(ni) else ("<END>", None, "")
                            print("    %s 重建[%d] %-32s %s" % (mark, j, nv[0], nv[1]))
                        break
                print()
