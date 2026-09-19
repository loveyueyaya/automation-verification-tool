# -*- coding: utf-8 -*-
"""第三批引用更新：legacy_repair / _local_assets 新位置 + 技能文档失效工具路径。

只改"活文档"；原始取证记录（_evidence/*.txt）与历史文档（盘点v1、P1验收证据、
RELEASE_NOTES_v1、RELEASE_NOTES_INDEX）保持原文。
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"
WORK = r"F:\wordbuddy\2026-09-18-21-23-01"
LEG = r"F:\自动化验证工具\10-env-baseline\_tools\legacy_repair"
AST = r"F:\自动化验证工具\10-env-baseline\_local_assets"
TOOLS = r"F:\自动化验证工具\10-env-baseline\_tools"

LEGACY_FILES = ["repair_env.py", "repair_env2.py", "repair_env3.py", "repair_env4_metadata.py",
                "repair_env5_autofix.py", "repair_env6", "restore_cuda_and_test",
                "restore_missing_dists", "probe_libs.py", "probe_ocr_tuning.py",
                "probe_uia_deep.py", "probe_uia_foreground.py", "_probe_step3.py", "p21",
                "reorganize_batch2.py", "_repair_reqs.txt", "_repair_small.txt", "_restore_reqs.txt"]

REPL = []
for f in LEGACY_FILES:
    REPL.append((WORK + "\\" + f, LEG + "\\" + f))
REPL += [
    (WORK + "\\_wheels", AST + "\\_wheels"),
    (WORK + "\\_backup_opencv_stale", AST + "\\_backup_opencv_stale"),
    (WORK + "\\P2-1_依赖清理与BUG修复_验收报告.md", r"F:\自动化验证工具\05-tests\P2-1_依赖清理与BUG修复_验收报告.md"),
    (WORK + "\\P2-2_分层迁移_验收报告.md", r"F:\自动化验证工具\05-tests\P2-2_分层迁移_验收报告.md"),
    (WORK + "\\", TOOLS + "\\"),          # 兜底：其余仍指向工作目录的，归到 _tools
    (WORK + "/", TOOLS + "/"),
]

# 历史文档 / 原始证据（不改写）
SKIP_FILES = {
    os.path.normcase(os.path.join(BASE, r"05-tests\P1_验收证据_20260916_195623.md")),
    os.path.normcase(os.path.join(BASE, r"06-deployment\RELEASE_NOTES_v1.md")),
    os.path.normcase(os.path.join(BASE, r"06-deployment\RELEASE_NOTES_INDEX.md")),
    os.path.normcase(os.path.join(BASE, r"11-management\本地离线自动化测试工具_开发前盘点.md")),
    os.path.normcase(os.path.join(BASE, r"11-management\接下来的任务.txt")),
}
SKIP_DIRS = {".git", "temp-cache", "__pycache__", "P1-pyc-cache-backup", "_evidence"}
EXT = {".md", ".txt", ".py", ".ps1", ".bat", ".json"}


def main():
    changed = []
    for root, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(root, f)
            if os.path.splitext(f)[1].lower() not in EXT:
                continue
            if os.path.normcase(p) in SKIP_FILES:
                continue
            try:
                t0 = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            t1, hits = t0, 0
            for a, b in REPL:
                if a in t1:
                    hits += t1.count(a)
                    t1 = t1.replace(a, b)
            if t1 != t0:
                open(p, "w", encoding="utf-8").write(t1)
                changed.append((os.path.relpath(p, BASE), hits))
    print("=== 已更新引用的活文档（%d 个）===" % len(changed))
    for r, n in sorted(changed):
        print("  [%d 处] %s" % (n, r))

    # .gitignore 追加 _local_assets
    gi = os.path.join(BASE, ".gitignore")
    t = open(gi, encoding="utf-8").read()
    if "10-env-baseline/_local_assets/" not in t:
        t = t.rstrip() + "\n\n# 本地资产（wheel 归档 / 旧包备份，体积大，不入库；重建方式见同目录 README）\n10-env-baseline/_local_assets/\n"
        open(gi, "w", encoding="utf-8").write(t)
        print("\n✅ .gitignore 已追加 10-env-baseline/_local_assets/")


if __name__ == "__main__":
    main()
