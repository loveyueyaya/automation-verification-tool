# -*- coding: utf-8 -*-
"""按归位后的真实位置，批量更新活文档中的引用（历史文档跳过）。"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"
HISTORICAL = {
    os.path.join(BASE, "05-tests", "P1_验收证据_20260916_195623.md"),
    os.path.join(BASE, "06-deployment", "RELEASE_NOTES_v1.md"),
    os.path.join(BASE, "06-deployment", "RELEASE_NOTES_INDEX.md"),
    os.path.join(BASE, "11-management", "本地离线自动化测试工具_开发前盘点.md"),  # v1 历史版
}
TOOLS = ["restore_from_wheels.py", "restore_from_recycle.py", "watch_files.py", "recycle_forensics.py",
         "damage_check.py", "analyze_waves.py", "attribute_waves.py", "final_assessment.py",
         "assess_damage.py", "list_core_damage.py", "verify_packages.py", "sample_noext.py",
         "verify_win32_api.py", "probe_symbols.py", "verify_env_full.py", "check_metadata.py",
         "verify_e2e.py", "update_refs.py", "reorganize_root.py", "reorganize_batch2.py"]

WORK = r"F:\wordbuddy\2026-09-18-21-23-01"
TOOLDIR = r"F:\自动化验证工具\10-env-baseline\_tools"
EVIDDIR = r"F:\自动化验证工具\10-env-baseline\_evidence"
MG = r"F:\自动化验证工具\11-management"

REPL = [(WORK + "\\_investigation", EVIDDIR),
        (WORK + "/_investigation", EVIDDIR),
        (WORK + "\\本地离线自动化测试工具_开发前盘点_v2.md", MG + "\\本地离线自动化测试工具_开发前盘点_v2.md"),
        (WORK + "\\本地离线自动化测试工具_开发前盘点.md", MG + "\\本地离线自动化测试工具_开发前盘点.md")]
for t in TOOLS:
    REPL.append((WORK + "\\" + t, TOOLDIR + "\\" + t))

# 根级文件 → 子目录（相对名；按目录排除自身，避免自引用被改写）
REL = [("RELEASE_NOTES_INDEX.md", "06-deployment/RELEASE_NOTES_INDEX.md", "06-deployment"),
       ("RELEASE_NOTES_v1.md", "06-deployment/RELEASE_NOTES_v1.md", "06-deployment"),
       ("P1_patch1_release_notes.md", "06-deployment/P1_patch1_release_notes.md", "06-deployment"),
       ("P1_acceptance_evidence.zip", "05-tests/P1_acceptance_evidence.zip", "05-tests"),
       ("P1-pyc-cache-backup", "06-deployment/P1-pyc-cache-backup", "06-deployment"),
       ("HANDOVER.md", "11-management/HANDOVER.md", "11-management"),
       ("git-sync.ps1", "07-operations/git-sync.ps1", "07-operations"),
       ("sync-to-github.bat", "07-operations/sync-to-github.bat", "07-operations"),
       ("project-phase-progress.xlsx", "11-management/project-phase-progress.xlsx", "11-management")]
COLLAPSE = [("06-deployment/06-deployment/", "06-deployment/"), ("05-tests/05-tests/", "05-tests/"),
            ("11-management/11-management/", "11-management/"),
            ("07-operations/07-operations/", "07-operations/"),
            ("05-tests/06-deployment/", "06-deployment/"), ("06-deployment/05-tests/", "05-tests/")]


def main():
    changed = []
    for root, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in (".git", "temp-cache", "__pycache__", "P1-pyc-cache-backup")]
        for f in fn:
            if not f.lower().endswith((".md",)):
                continue
            p = os.path.join(root, f)
            if p in HISTORICAL:
                continue
            rel_dir = os.path.relpath(root, BASE).replace("\\", "/")
            t0 = open(p, encoding="utf-8").read()
            t1, hits = t0, []
            for a, b in REPL:
                if a in t1:
                    hits.append(a.split("\\")[-1])
                    t1 = t1.replace(a, b)
            for name, target, own_dir in REL:
                if rel_dir.startswith(own_dir):
                    continue
                if name in t1:
                    t1 = t1.replace(name, target)
                    hits.append(name)
            for a, b in COLLAPSE:
                while a in t1:
                    t1 = t1.replace(a, b)
            if t1 != t0:
                open(p, "w", encoding="utf-8").write(t1)
                changed.append((os.path.relpath(p, BASE), sorted(set(hits))))
    print("=== 已更新引用的活文档（%d 个）===" % len(changed))
    for r, hits in sorted(changed):
        print("  %s\n      修正: %s" % (r, ", ".join(hits)))


if __name__ == "__main__":
    main()
