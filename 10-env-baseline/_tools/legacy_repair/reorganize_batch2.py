# -*- coding: utf-8 -*-
"""第二批归位：
1) 盘点 v2（工作目录）→ 11-management/；接下来的任务.txt（桌面）→ 11-management/（副本，桌面保留）
2) 09-19 取证/验证工具 → 10-env-baseline/_tools/
3) 09-19 原始输出/证据   → 10-env-baseline/_evidence/
"""
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"
WORK = r"F:\wordbuddy\2026-09-18-21-23-01"
DESK = r"C:\Users\Administrator\Desktop"

TOOLS = [
    "restore_from_wheels.py", "restore_from_recycle.py", "watch_files.py",
    "recycle_forensics.py", "damage_check.py", "analyze_waves.py", "attribute_waves.py",
    "final_assessment.py", "assess_damage.py", "list_core_damage.py", "verify_packages.py",
    "sample_noext.py", "verify_win32_api.py", "probe_symbols.py", "verify_env_full.py",
    "check_metadata.py", "verify_e2e.py", "update_refs.py", "reorganize_root.py",
]


def mv(src, dst_dir, move=True):
    if not os.path.exists(src):
        return "源不存在"
    os.makedirs(dst_dir, exist_ok=True)
    d = os.path.join(dst_dir, os.path.basename(src))
    if os.path.exists(d):
        return "目标已存在，跳过"
    if move:
        shutil.move(src, d)
        return "✅ 已移动"
    shutil.copy2(src, d)
    return "✅ 已复制"


def main():
    mg = os.path.join(BASE, "11-management")
    tools = os.path.join(BASE, "10-env-baseline", "_tools")
    evid = os.path.join(BASE, "10-env-baseline", "_evidence")

    print("=== 1) 管理类文档 → 11-management/ ===")
    print("  盘点 v2:", mv(os.path.join(WORK, "本地离线自动化测试工具_开发前盘点_v2.md"), mg))
    print("  任务清单:", mv(os.path.join(DESK, "接下来的任务.txt"), mg, move=False), "（桌面原件保留）")
    # 盘点 v1 一并入库留档（它是 v2 的前身，属历史版本）
    print("  盘点 v1:", mv(os.path.join(WORK, "本地离线自动化测试工具_开发前盘点.md"), mg))

    print("\n=== 2) 09-19 取证/验证工具 → 10-env-baseline/_tools/ ===")
    for t in TOOLS:
        st = mv(os.path.join(WORK, t), tools)
        if "跳过" not in st and "不存在" not in st:
            print("  ✅ %s" % t)

    print("\n=== 3) 原始输出/证据 → 10-env-baseline/_evidence/ ===")
    inv = os.path.join(WORK, "_investigation")
    if os.path.isdir(inv):
        os.makedirs(evid, exist_ok=True)
        for f in sorted(os.listdir(inv)):
            print("  %s: %s" % (f, mv(os.path.join(inv, f), evid)))
        try:
            os.rmdir(inv)
            print("  _investigation/ 已清空并移除")
        except OSError as e:
            print("  _investigation/ 未空: %s" % e)

    print("\n=== 复验 ===")
    for d in (mg, tools, evid):
        p = d
        print("  %s: %d 项" % (os.path.relpath(d, BASE), len(os.listdir(d)) if os.path.isdir(d) else -1))
    print("\n  工作目录剩余:", sorted(os.listdir(WORK)))


if __name__ == "__main__":
    main()
