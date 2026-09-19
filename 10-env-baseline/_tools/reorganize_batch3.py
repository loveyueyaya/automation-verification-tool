# -*- coding: utf-8 -*-
"""补齐归位：剩余修复/探针脚本入库 + 大体积本地资产归入项目内(不入库)。"""
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"
WORK = r"F:\wordbuddy\2026-09-18-21-23-01"
LEGACY = os.path.join(BASE, "10-env-baseline", "_tools", "legacy_repair")
ASSETS = os.path.join(BASE, "10-env-baseline", "_local_assets")

SCRIPTS = ["repair_env.py", "repair_env2.py", "repair_env3.py", "repair_env4_metadata.py",
           "repair_env5_autofix.py", "repair_env6", "restore_cuda_and_test",
           "restore_missing_dists", "probe_libs.py", "probe_ocr_tuning.py",
           "probe_uia_deep.py", "probe_uia_foreground.py", "_probe_step3.py", "p21",
           "reorganize_batch2.py", "_repair_reqs.txt", "_repair_small.txt", "_restore_reqs.txt"]
DIRS = ["_wheels", "_backup_opencv_stale"]


def main():
    os.makedirs(LEGACY, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    print("=== 1) 修复/探针脚本 → 10-env-baseline/_tools/legacy_repair/ ===")
    for f in SCRIPTS:
        s = os.path.join(WORK, f)
        if not os.path.exists(s):
            print("  ℹ 源不存在:", f); continue
        d = os.path.join(LEGACY, f)
        if os.path.exists(d):
            print("  ℹ 目标已存在:", f); continue
        shutil.move(s, d)
        print("  ✅", f)
    print("\n=== 2) 本地资产（不入库）→ 10-env-baseline/_local_assets/ ===")
    for d in DIRS:
        s = os.path.join(WORK, d)
        if not os.path.exists(s):
            print("  ℹ 源不存在:", d); continue
        t = os.path.join(ASSETS, d)
        if os.path.exists(t):
            print("  ℹ 目标已存在:", d); continue
        shutil.move(s, t)
        n = sum(len(f) for _, _, f in os.walk(t))
        print("  ✅ %s（%d 文件）" % (d, n))

    print("\n=== 复验 ===")
    print("  legacy_repair: %d 项" % len(os.listdir(LEGACY)))
    print("  _local_assets: %s" % sorted(os.listdir(ASSETS)))
    print("  工作目录剩余: %s" % sorted(os.listdir(WORK)))


if __name__ == "__main__":
    main()
