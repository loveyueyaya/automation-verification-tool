# -*- coding: utf-8 -*-
"""权威源 → AppData 技能同步 + 逐文件 SHA256 校验（可复用）。

背景（2026-09-19 实测）：两侧均为实体目录（非 junction），改权威源后必须同步到
AppData 才在下一轮对话生效；且权威源里的本地凭证目录（.credentials/）与运行时
日志（decision-log/、log.txt）不进 AppData。

用法：python sync_skills.py [--check-only]
"""
import hashlib
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills"
APP = r"C:\Users\Administrator\.workbuddy\skills"
SKIP_DIRS = {"temp-cache", "__pycache__", ".git", ".credentials"}
SKIP_FILES = {"_user_meta.json"}
# 运行时数据（只存权威源，不做镜像）
RUNTIME = ("decision-log", "log.txt")


def is_runtime(rel):
    rel = rel.replace("/", "\\")
    return rel.startswith("decision-log\\") or rel == "log.txt"


def tree(root, drop_runtime=False):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if f in SKIP_FILES:
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            if drop_runtime and is_runtime(rel):
                continue
            out[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def main():
    check_only = "--check-only" in sys.argv
    skills = sorted(d for d in os.listdir(SRC)
                    if os.path.isdir(os.path.join(SRC, d)) and not d.startswith("."))
    print("技能数：%d → %s" % (len(skills), ", ".join(skills)))
    copied = 0
    if not check_only:
        for s in skills:
            sdir, adir = os.path.join(SRC, s), os.path.join(APP, s)
            for rel, _ in tree(sdir, drop_runtime=True).items():
                sp, dp = os.path.join(sdir, rel), os.path.join(adir, rel)
                os.makedirs(os.path.dirname(dp), exist_ok=True)
                if os.path.exists(dp) and hashlib.sha256(open(sp, "rb").read()).hexdigest() == \
                        hashlib.sha256(open(dp, "rb").read()).hexdigest():
                    continue
                shutil.copy2(sp, dp)
                copied += 1
        print("同步复制/更新文件数：%d" % copied)
    print("\n%-30s %-6s %s" % ("技能", "文件", "结果"))
    allok = True
    for s in skills:
        a = tree(os.path.join(SRC, s), drop_runtime=True)
        b = tree(os.path.join(APP, s), drop_runtime=True) if os.path.isdir(os.path.join(APP, s)) else {}
        only_a = sorted(set(a) - set(b))
        only_b = sorted(set(b) - set(a))
        diff = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        ok = not only_a and not only_b and not diff
        allok &= ok
        print("%-30s %-6d %s" % (s, len(a), "✅ 一致" if ok else
                                 "❌ 仅权威源=%s 仅AppData=%s 内容不同=%s" % (only_a, only_b, diff)))
    print("\n五+一技能代码逐文件一致：%s" % ("✅ 是" if allok else "❌ 否"))
    # 本地凭证目录不应出现在 AppData
    cred = os.path.join(APP, "github-remote", ".credentials")
    print("AppData 侧无凭证目录：%s" % ("✅" if not os.path.exists(cred) else "❌ 存在！"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
