# -*- coding: utf-8 -*-
"""根目录归位：README.md / LICENSE 留根，其余条目按功能归入对应子目录。

跟踪文件用 git mv（保留历史），未跟踪文件用 os.replace（同盘移动，原子）。
执行前打印计划，执行后逐项复验存在性。
"""
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"

# (根级条目, 目标相对路径, 是否跟踪)
PLAN = [
    ("RELEASE_NOTES_INDEX.md",       r"06-deployment\RELEASE_NOTES_INDEX.md", True),
    ("RELEASE_NOTES_v1.md",          r"06-deployment\RELEASE_NOTES_v1.md", True),
    ("P1_patch1_release_notes.md",   r"06-deployment\P1_patch1_release_notes.md", False),
    ("P1-pyc-cache-backup",          r"06-deployment\P1-pyc-cache-backup", False),
    ("P1_acceptance_evidence.zip",   r"05-tests\P1_acceptance_evidence.zip", False),
    ("git-sync.ps1",                 r"07-operations\git-sync.ps1", True),
    ("sync-to-github.bat",           r"07-operations\sync-to-github.bat", True),
    ("HANDOVER.md",                  r"11-management\HANDOVER.md", False),
    ("project-phase-progress.xlsx",  r"11-management\project-phase-progress.xlsx", True),
]


def run(cmd, cwd=BASE):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def main():
    os.makedirs(os.path.join(BASE, "11-management"), exist_ok=True)
    print("=== 执行计划（%d 项）===" % len(PLAN))
    ok = fail = 0
    for src, dst_rel, tracked in PLAN:
        s = os.path.join(BASE, src)
        d = os.path.join(BASE, dst_rel)
        if not os.path.exists(s):
            print("  ⚠ 源不存在，跳过: %s" % src)
            fail += 1
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        try:
            if tracked:
                rc, out, err = run(["git", "mv", src, dst_rel])
                if rc != 0:
                    raise RuntimeError("git mv 失败: %s" % (err or out))
                how = "git mv"
            else:
                shutil.move(s, d)
                how = "move"
            print("  ✅ %-30s → %-40s [%s]" % (src, dst_rel, how))
            ok += 1
        except Exception as e:
            print("  ❌ %-30s → %-40s 失败: %s" % (src, dst_rel, e))
            fail += 1
    print("\n成功 %d / 失败 %d" % (ok, fail))

    print("\n=== 复验：根目录剩余条目 ===")
    for n in sorted(os.listdir(BASE)):
        if n in (".git",):
            continue
        p = os.path.join(BASE, n)
        print("  %-32s %s" % (n, "目录" if os.path.isdir(p) else "文件"))
    print("\n=== 复验：目标存在性 ===")
    for src, dst_rel, _ in PLAN:
        print("  %-40s %s" % (dst_rel, "存在" if os.path.exists(os.path.join(BASE, dst_rel)) else "缺失"))


if __name__ == "__main__":
    main()
