# -*- coding: utf-8 -*-
"""目录树整理：批量更新引用（活文档），历史文档另行加勘误注记。"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"
EXTS = {".md", ".py", ".ps1", ".bat", ".txt", ".json", ".cfg", ".toml"}
SKIP_DIRS = {".git", "temp-cache", "P1-pyc-cache-backup", "__pycache__", ".workbuddy"}
# 历史文档（不改写内容，另加注记）
HISTORICAL = {
    os.path.join(BASE, "RELEASE_NOTES_v1.md"),
    os.path.join(BASE, "05-tests", "P1_验收证据_20260916_195623.md"),
    os.path.join(BASE, "RELEASE_NOTES_INDEX.md"),
}

REPL = [
    ("env-report/", "env-report/"),
    ("01-requirements/env-report/", "01-requirements/env-report/"),
    ("P1-contracts-env-adapter/evidence/", "P1-contracts-env-adapter/evidence/"),
    ("P1-contracts-env-adapter\\证据\\", "P1-contracts-env-adapter\\evidence\\"),
    ("evidence/compare_", "evidence/compare_"),
    ("evidence/diff_", "evidence/diff_"),
    ("evidence/full_dis_out.txt", "evidence/full_dis_out.txt"),
    ("evidence/字符串搜索输出", "evidence/字符串搜索输出"),
    ("`evidence/", "`evidence/"),
    ("env-incident_20260919_root-cause.md", "env-incident_20260919_root-cause.md"),
    ("env-incident_20260919_root-cause", "env-incident_20260919_root-cause"),
    ("sync-to-github.bat", "sync-to-github.bat"),
    ("project-phase-progress.xlsx", "project-phase-progress.xlsx"),
]


def main():
    changed = []
    for root, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(root, f)
            if os.path.splitext(f)[1].lower() not in EXTS:
                continue
            if p in HISTORICAL:
                continue
            try:
                t0 = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            t1 = t0
            hits = 0
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


if __name__ == "__main__":
    main()
