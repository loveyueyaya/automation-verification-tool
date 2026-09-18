# -*- coding: utf-8 -*-
"""contracts — 契约层（横切 A）· P2-2 迁移 shim（方案 B）。

本文件不含任何契约实现：具体模块已 git mv 到
04-implementation/P2-layers/contracts/。本 shim 把 `contracts` 这个模块名
整体指向新位置的包，使 from contracts import ... / from contracts.state_hash
import ... 等旧写法零改动继续可用。

实现：按文件路径加载新包，并把 sys.modules['contracts'] 整体替换为新包对象
（__path__ 指向新目录，子模块也从新位置解析）。CPython 的 _InstalledSafely
明确支持 sys.modules 替换写法。

删除时机：7 步法第 7 步（所有调用方 import 改到新路径后）。
回滚：删 P2-layers/contracts，把本文件还原为原 __init__.py（git HEAD 有留存）。
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))   # .../P1-contracts-env-adapter/contracts
_IMPL = os.path.dirname(os.path.dirname(_HERE))      # .../04-implementation
_NEW_PKG = os.path.join(_IMPL, "P2-layers", "contracts")
_NEW_INIT = os.path.join(_NEW_PKG, "__init__.py")

if not os.path.isfile(_NEW_INIT):
    raise ImportError(
        "contracts shim：找不到迁移后的契约包 %s（P2-layers/contracts 缺失）" % _NEW_INIT
    )

_spec = importlib.util.spec_from_file_location(
    __name__, _NEW_INIT, submodule_search_locations=[_NEW_PKG]
)
if _spec is None or _spec.loader is None:
    raise ImportError("contracts shim：无法为新契约包构造 import spec %s" % _NEW_INIT)

_mod = importlib.util.module_from_spec(_spec)
sys.modules.pop(__name__, None)
sys.modules[__name__] = _mod
_spec.loader.exec_module(_mod)
