# -*- coding: utf-8 -*-
"""完整指令序列对比：verify_text(uitool) / find_windows(env)，原始 pyc vs 重建源码编译。"""
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


def find_fn(co, qname):
    parts = qname.split(".")
    def walk(c, depth=0, path=""):
        if depth > 6:
            return None
        for k in c.co_consts:
            if isinstance(k, types.CodeType):
                p = (path + "." + k.co_name) if path else k.co_name
                if p == qname:
                    return k
                r = walk(k, depth + 1, p)
                if r is not None:
                    return r
        return None
    return walk(co)


targets = [("uitool.py", "verify_text"),
           ("env.py", "find_windows")]
for fn, qname in targets:
    name = fn[:-3]
    src_path = os.path.join(SRC, fn)
    pyc_path = os.path.join(PYC, name + ".cpython-313.pyc")
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    new_co = compile(src, fn, "exec")
    old_co = load_pyc(pyc_path)
    o = find_fn(old_co, qname)
    n = find_fn(new_co, qname)
    print("=" * 78)
    print("### %s.%s  原始(%d 指令) vs 重建(%d 指令)"
          % (name, qname, len(list(dis.get_instructions(o))),
             len(list(dis.get_instructions(n)))))
    print("原始常量表: %s" % [repr(c)[:60]
          for c in o.co_consts if not isinstance(c, types.CodeType)])
    print("重建常量表: %s" % [repr(c)[:60]
          for c in n.co_consts if not isinstance(c, types.CodeType)])
    print("原始局部变量: %s" % list(o.co_varnames))
    print("重建局部变量: %s" % list(n.co_varnames))
    print("-" * 78)
    print("原始 dis:")
    dis.dis(o)
    print("-" * 78)
    print("重建 dis:")
    dis.dis(n)
    print()
