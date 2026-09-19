# -*- coding: utf-8 -*-
"""restore_p1_shim.py — 一键恢复 P1 contracts shim（feature flag "p1" 模式的依赖）。

背景：P2-2 收尾后契约层唯一实现在 04-implementation/P2-layers/contracts/，
P1 遗留目录（P1-toolbox-legacy）的 contracts shim 已删除（收尾 #2）。
feature flag：环境变量 UITOOL_CONTRACTS_SOURCE=p1 时，scripts/tests 的引导会走
P1 目录的 contracts shim —— 此时必须先运行本脚本恢复 shim 文件。

用法：
    python restore_p1_shim.py            # 恢复 shim（git 历史优先，内置内容兜底）
    python restore_p1_shim.py --remove   # 切回 p2 模式时移除 shim

恢复方式（双保险）：
    1) git 历史提取（在仓库根执行 git log/show，避免相对路径歧义）
    2) 兜底：脚本内置 shim 全文（与删除前版本一致）
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "contracts", "__init__.py")
HIST_PATHS = [
    "04-implementation/P1-contracts-env-adapter/contracts/__init__.py",
    "04-implementation/P1-toolbox-legacy/contracts/__init__.py",
]

SHIM_BUILTIN = '''# -*- coding: utf-8 -*-
"""contracts — 契约层（横切 A）· P2-2 迁移 shim（方案 B）。

本文件不含任何契约实现：具体模块已 git mv 到
04-implementation/P2-layers/contracts/。本 shim 把 `contracts` 这个模块名
整体指向新位置的包，使 from contracts import ... / from contracts.state_hash
import ... 等旧写法零改动继续可用。

实现：按文件路径加载新包，并把 sys.modules['contracts'] 整体替换为新包对象
（__path__ 指向新目录，子模块也从新位置解析）。

删除时机：7 步法第 7 步（所有调用方 import 改到新路径后）。
回滚：删 P2-layers/contracts，把本文件还原为原 __init__.py（git HEAD 有留存）。
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))   # .../P1-toolbox-legacy/contracts
_IMPL = os.path.dirname(_HERE)                       # .../04-implementation
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
'''


def git_root():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, cwd=HERE)
    return (r.stdout or "").strip()


def git(*args, cwd=None):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                          cwd=cwd or HERE)


def find_shim_commit():
    root = git_root()
    if not root:
        return None, None
    for p in HIST_PATHS:
        r = git("log", "--all", "--format=%H", "-n", "1", "--", p, cwd=root)
        c = (r.stdout or "").strip()
        if c:
            return c, p
    return None, None


def main():
    if "--remove" in sys.argv:
        if os.path.isfile(TARGET):
            os.remove(TARGET)
            print("已移除 shim:", TARGET)
        else:
            print("shim 本就不存在:", TARGET)
        return 0

    if os.path.isfile(TARGET):
        print("shim 已存在:", TARGET)
        return 0

    src = None
    commit, src = find_shim_commit()
    content = None
    if commit and src:
        root = git_root()
        r = git("show", "%s:%s" % (commit, src), cwd=root)
        if r.returncode == 0 and r.stdout:
            content = r.stdout
            print("恢复来源：git %s (%s)" % (commit[:10], src))
    if content is None:
        content = SHIM_BUILTIN
        print("恢复来源：脚本内置内容（git 历史未命中）")

    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print("shim 已写入:", TARGET)
    print("现在可设置环境变量 UITOOL_CONTRACTS_SOURCE=p1 切回 P1 路径。")
    print("切回 p2：python restore_p1_shim.py --remove")
    return 0


if __name__ == "__main__":
    sys.exit(main())
