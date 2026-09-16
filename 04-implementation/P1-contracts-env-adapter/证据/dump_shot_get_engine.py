# -*- coding: utf-8 -*-
"""dump shot.pyc 的 get_engine / _ENGINE 完整定义，用于重建依赖。"""
import dis
import marshal
import types

PYC = (r"C:\Users\Administrator\AppData\Local\Doubao\User Data\sandbox_runtime"
       r"\.cache\python\pyc-cache\Users\Administrator\AppData\Local\Doubao"
       r"\User Data\Default\.doubao\agent_mode\workspace\.user_skills"
       r"\ui-toolbox\scripts\shot.cpython-313.pyc")

with open(PYC, "rb") as f:
    f.read(16)
    co = marshal.loads(f.read())

print("模块级常量表(非code):")
for c in co.co_consts:
    if not isinstance(c, types.CodeType):
        print("  ", repr(c)[:120])
print("模块级名称: %s" % list(co.co_names))

def walk(c, path=""):
    for k in c.co_consts:
        if isinstance(k, types.CodeType):
            p = (path + "." + k.co_name) if path else k.co_name
            if k.co_name == "get_engine" or k.co_name == "ShotEngine":
                print("=" * 70)
                print("### %s" % p)
                print("常量表: %s" % [repr(x)[:80]
                      for x in k.co_consts if not isinstance(x, types.CodeType)])
                print("局部变量: %s" % list(k.co_varnames))
                print("名称: %s" % list(k.co_names))
                dis.dis(k)
            walk(k, p)

walk(co)
