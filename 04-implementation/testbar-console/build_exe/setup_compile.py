# -*- coding: utf-8 -*-
"""setup_compile.py — 用 Cython 把 perfmon.py / diagnose.py 编译为 .pyd（Windows DLL 扩展库）。

用法（在 build_exe 目录执行）：
  & "C:/Program Files/Python313/python.exe" setup_compile.py build_ext --inplace

产物：build_exe/perfmon.cp313-win_amd64.pyd、build_exe/diagnose.cp313-win_amd64.pyd
"""
import os
from setuptools import setup, Extension
from Cython.Build import cythonize

SRC = r"C:\Users\Administrator\Desktop\测试控制台"

exts = [
    Extension("perfmon", [os.path.join(SRC, "perfmon.py")]),
    Extension("diagnose", [os.path.join(SRC, "diagnose.py")]),
]

setup(
    name="testbar_libs",
    ext_modules=cythonize(
        exts,
        language_level=3,
        compiler_directives={"language_level": 3, "boundscheck": False},
    ),
)
