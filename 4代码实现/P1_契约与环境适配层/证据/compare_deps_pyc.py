# -*- coding: utf-8 -*-
"""步骤三：cache.py / ocr.py / sendinput.py 与原始 pyc 的模块级 co_names + 函数集合比对。"""
import marshal
import os
import sys
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


def collect_functions(co, prefix=""):
    """递归收集 {限定名: code}，排除类/函数内嵌嵌套（只到 2 层）。"""
    out = {}
    for k in co.co_consts:
        if isinstance(k, types.CodeType):
            name = k.co_name
            if k.co_flags & 0x20:  # generator
                # genexpr 是表达式，非顶层函数，跳过（记 genexpr 名）
                out[prefix + "<gen:%s>" % name] = k
                continue
            if name not in ("<lambda>",) and k.co_name:
                out[prefix + name] = k
    return out


def module_funcs(co):
    """模块级函数（第一层）"""
    out = {}
    for k in co.co_consts:
        if isinstance(k, types.CodeType) and not k.co_name.startswith("<"):
            out[k.co_name] = k
    return out


for fn in ("cache.py", "ocr.py", "sendinput.py"):
    name = fn[:-3]
    src_path = os.path.join(SRC, fn)
    pyc_path = os.path.join(PYC, name + ".cpython-313.pyc")
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    new_co = compile(src, fn, "exec")
    old_co = load_pyc(pyc_path)

    old_names = list(old_co.co_names)
    new_names = list(new_co.co_names)
    old_funcs = module_funcs(old_co)
    new_funcs = module_funcs(new_co)

    print("=" * 72)
    print("### %s" % fn)
    print("模块级 co_names 长度: 原始 %d / F盘 %d" % (len(old_names), len(new_names)))
    print("仅原始有: %s" % [n for n in old_names if n not in new_names])
    print("仅F盘有: %s" % [n for n in new_names if n not in old_names])
    print("函数集合 仅原始有: %s" % [k for k in old_funcs if k not in new_funcs])
    print("函数集合 仅F盘有: %s" % [k for k in new_funcs if k not in old_funcs])
    # 同名字段 co_code 一致性（非逐字节要求，看是否存在）
    diff = [k for k in old_funcs if k in new_funcs
            and old_funcs[k].co_code != new_funcs[k].co_code]
    print("同名函数 co_code 不一致: %s" % diff if diff else "同名函数 co_code 全部一致")
    print("模块级 co_code 一致: %s" % (old_co.co_code == new_co.co_code))
