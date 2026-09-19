# -*- coding: utf-8 -*-
"""整理结果全量逐项验证 v2（修正误报口径、补白名单、新增第 12 项）。

v1 → v2 的改动全部是"判定口径修正"，不是放宽标准：
  · §3 排除 AI 记忆目录 .workbuddy 与原始取证目录 _evidence（逐字证据不可改写）；
       旧名模式由"根因取证"改为精确文件名，避免误伤正文
  · §4 路径抽取去掉标点截断误差；历史目录名/占位符逐条列白名单并打印理由
  · §5 索引条目改四级解析（绝对 → 索引所在目录 → 技能根 → 全项目同名）
  · §10 接受脚本设计上的 rc=2（无参打印用法）
  · §11 pip check 判据改为"告警集合 ⊆ 已知基线告警"
  · 新增 §12 本地资产/遗留脚本归位专项
"""
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"F:\自动化验证工具"
TOOLS = os.path.join(BASE, "10-env-baseline", "_tools")
LEGACY = os.path.join(TOOLS, "legacy_repair")
EVID = os.path.join(BASE, "10-env-baseline", "_evidence")
ASSETS = os.path.join(BASE, "10-env-baseline", "_local_assets")
OUT = os.path.join(EVID, "reorg-verify_20260919.txt")
PY = r"C:\Program Files\Python313\python.exe"
SKILL_SRC = os.path.join(BASE, r"00-doubao-llm-prerequisites\.user_skills")
SKILL_APP = r"C:\Users\Administrator\.workbuddy\skills"
WORK = r"F:\wordbuddy\2026-09-18-21-23-01"

HIST_FILES = {
    os.path.normcase(os.path.join(BASE, r"05-tests\P1_验收证据_20260916_195623.md")),
    os.path.normcase(os.path.join(BASE, r"06-deployment\RELEASE_NOTES_v1.md")),
    os.path.normcase(os.path.join(BASE, r"06-deployment\RELEASE_NOTES_INDEX.md")),
    os.path.normcase(os.path.join(BASE, r"11-management\本地离线自动化测试工具_开发前盘点.md")),
    os.path.normcase(os.path.join(BASE, r"11-management\接下来的任务.txt")),
    os.path.normcase(os.path.join(BASE, r"11-management\reorg-report_20260919.md")),
    # 盘点 v2 内含"目录整理变更表"，逐行记录 旧名 → 新名，属必要记录
    os.path.normcase(os.path.join(BASE, r"11-management\本地离线自动化测试工具_开发前盘点_v2.md")),
}
# 说明性文件：整理/引用更新/验证脚本自身要引用旧名做比对，属必要
ALLOW_OLD_IN = ("update_refs", "reorganize_", "verify_reorg")

WHITELIST_REF = {
    r"F:\自动化验证工具\.cache": "详细设计中的示例缓存路径（从未创建）",
    r"F:\自动化验证工具\00-doubao-llm-prerequisites\.user_skills\cache-manager\temp-cache\20260916_223000":
        "技能 SKILL.md 里的缓存路径示例值（实际缓存见同目录其他时间戳）",
    r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层": "P1 时期历史目录名",
    r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层\MIGRATION.md": "历史目录下的历史文件",
    r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层\scripts\shot.py": "历史目录下的历史文件",
    r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层\tests\test_rebuild_equiv.py": "历史目录下的历史文件",
    r"F:\自动化验证工具\4代码实现\P1_契约与环境适配层\证据": "历史目录名（现 evidence/）",
    r"F:\自动化验证工具\P1_pyc缓存备份_20260916": "历史中文目录名（现 06-deployment/P1-pyc-cache-backup）",
    r"F:\自动化验证工具\08-env-baseline\pip_before_20260918.txt": "历史编号（现 10-env-baseline/）",
    r"F:\自动化验证工具\09-feedback\daily\feedback_YYYYMMDD.md": "技能文档中的命名模板占位符",
    r"F:\自动化验证工具\09-feedback\issues\issue_NNN_": "技能文档中的命名模板占位符",
}
PLACEHOLDER_TOKENS = ("**", "YYYY", "NNN", "（", "...", "<", "{")
EXTERNAL_BASENAMES = {"SOUL.md", "IDENTITY.md", "USER.md", "BOOTSTRAP.md", "MEMORY.md"}

COUNTS = {"pass": 0, "fail": 0}
FAILS = []
buf = io.StringIO()


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    buf.write(s + "\n")


def sec(t):
    P("")
    P("=" * 84)
    P(t)
    P("=" * 84)


def item(label, ok, detail=""):
    P("  {} {:<58} {}".format("✅" if ok else "❌", label, detail))
    COUNTS["pass" if ok else "fail"] += 1
    if not ok:
        FAILS.append(label)
    return ok


def run(cmd, timeout=600, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, cwd=cwd)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -999, "", "TIMEOUT"


def c1_layout():
    sec("1. 根目录归位清单逐项验证")
    root_now = sorted(os.listdir(BASE))
    plan = [("RELEASE_NOTES_INDEX.md", r"06-deployment\RELEASE_NOTES_INDEX.md"),
            ("RELEASE_NOTES_v1.md", r"06-deployment\RELEASE_NOTES_v1.md"),
            ("P1_patch1_release_notes.md", r"06-deployment\P1_patch1_release_notes.md"),
            ("P1-pyc-cache-backup", r"06-deployment\P1-pyc-cache-backup"),
            ("P1_acceptance_evidence.zip", r"05-tests\P1_acceptance_evidence.zip"),
            ("git-sync.ps1", r"07-operations\git-sync.ps1"),
            ("sync-to-github.bat", r"07-operations\sync-to-github.bat"),
            ("HANDOVER.md", r"11-management\HANDOVER.md"),
            ("project-phase-progress.xlsx", r"11-management\project-phase-progress.xlsx")]
    for src, dst in plan:
        gone = src not in root_now
        there = os.path.exists(os.path.join(BASE, dst))
        item("%s → %s" % (src, dst), gone and there, "源已移除=%s 目标在位=%s" % (gone, there))
    for old in ("决策日志", "同步到GitHub.bat", "项目阶段进度表.xlsx"):
        item("根级已无 %s" % old, old not in root_now)
    allow = {"README.md", "LICENSE", ".gitignore", ".git", ".workbuddy"}
    extra = [n for n in root_now if n not in allow and not re.match(r"^\d\d-", n)]
    item("根目录除白名单外无散落项", not extra, "多余=%s" % (extra or "无"))
    for n in ("README.md", "LICENSE"):
        item("保留项 %s 在位" % n, os.path.exists(os.path.join(BASE, n)))


def c2_tree():
    sec("2. 目录树 00~11 + 各目录索引 + 新增子目录")
    for i in range(12):
        d = [n for n in os.listdir(BASE) if n.startswith("%02d-" % i)]
        item("目录 %02d-* 唯一存在" % i, len(d) == 1 and os.path.isdir(os.path.join(BASE, d[0])),
             d[0] if d else "缺失")
    idx_map = {"00-doubao-llm-prerequisites": "doubao-prerequisites-index.md",
               "01-requirements": "requirements-index.md", "04-implementation": "implementation-index.md",
               "05-tests": "tests-index.md", "06-deployment": "deployment-index.md",
               "07-operations": "operations-index.md", "08-review-logs": "INDEX.md",
               "09-feedback": "INDEX.md", "10-env-baseline": "env-baseline-index.md",
               "11-management": "management-index.md"}
    for d, f in idx_map.items():
        item("%s/%s" % (d, f), os.path.exists(os.path.join(BASE, d, f)))
    for sub in ("_tools", "_evidence", "_local_assets"):
        item("10-env-baseline/%s" % sub, os.path.isdir(os.path.join(BASE, "10-env-baseline", sub)))
    item("_tools/legacy_repair 存在", os.path.isdir(LEGACY),
         "%d 项" % (len(os.listdir(LEGACY)) if os.path.isdir(LEGACY) else 0))


def c3_stale():
    sec("3. 全树旧路径/旧名残留扫描（活文档必须 0 命中）")
    PATS = [r"0运行环境报告", r"P1-contracts-env-adapter[\\/]证据",
            r"env-incident_20260919_根因取证", r"同步到GitHub\.bat", r"项目阶段进度表\.xlsx",
            r"wordbuddy[\\/]2026-09-18-21-23-01", r"_investigation"]
    SKIP_DIRS = {".git", "temp-cache", "__pycache__", "P1-pyc-cache-backup", ".workbuddy",
                 "_evidence", "_local_assets", "legacy_repair"}
    EXT = {".md", ".txt", ".py", ".ps1", ".bat", ".json", ".gitignore"}
    live, hist, scanned = [], [], 0
    for root, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if os.path.splitext(f)[1].lower() not in EXT and f != ".gitignore":
                continue
            p = os.path.join(root, f)
            scanned += 1
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            is_hist = os.path.normcase(p) in HIST_FILES
            is_allow = any(k in f for k in ALLOW_OLD_IN)
            for i, line in enumerate(lines, 1):
                for pat in PATS:
                    if re.search(pat, line):
                        (hist if (is_hist or is_allow) else live).append(
                            (os.path.relpath(p, BASE), i, pat, line.strip()[:100]))
    P("  扫描文件 %d；活文档命中 %d（要求 0）；历史/说明性命中 %d（允许）" % (scanned, len(live), len(hist)))
    for h in live[:20]:
        P("    ❌ %s:%d [%s] %s" % h)
    for h in hist[:8]:
        P("    ⚪ %s:%d [%s]" % (h[0], h[1], h[2]))
    item("活文档无旧路径/旧名残留", not live, "命中 %d" % len(live))


def c4_refs():
    sec("4. 全树「项目内路径引用」逐条存在性校验")
    pat = re.compile(r"F:[\\/]自动化验证工具[^\s`\"'<>|,;)\]}`]*")
    refs = {}
    SKIP_DIRS = {".git", "temp-cache", "__pycache__", "P1-pyc-cache-backup", ".workbuddy",
                 "_evidence", "_local_assets", "_tools"}
    for root, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if os.path.splitext(f)[1].lower() not in (".md", ".txt"):
                continue
            p = os.path.join(root, f)
            try:
                txt = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for m in pat.findall(txt):
                c = m.rstrip(".,;:）)】》」'\"\\*`、。，；：")
                c = c.split("（")[0].split("(")[0].strip()
                if len(c) < 14:
                    continue
                refs.setdefault(c.replace("/", "\\"), set()).add(os.path.relpath(p, BASE))
    missing, wl, ok_n = [], [], 0
    for r, srcs in sorted(refs.items()):
        if os.path.exists(r):
            ok_n += 1
            continue
        if any(t in r for t in PLACEHOLDER_TOKENS) or os.path.basename(r) in EXTERNAL_BASENAMES:
            wl.append((r, "占位符/外部文件"))
            continue
        hit = next((k for k in WHITELIST_REF if r == k or r.startswith(k)), None)
        if hit:
            wl.append((r, WHITELIST_REF[hit]))
            continue
        missing.append((r, sorted(srcs)))
    P("  去重后项目内引用 %d 条：存在 %d / 白名单 %d / 缺失 %d" % (len(refs), ok_n, len(wl), len(missing)))
    for r, why in wl:
        P("    ⚪ 白名单 %s ← %s" % (r, why))
    for r, srcs in missing:
        P("    ❌ 缺失 %s ← 引用自 %s" % (r, ", ".join(srcs[:3])))
    item("项目内路径引用全部存在（白名单除外）", not missing, "缺失 %d" % len(missing))


def c5_index():
    sec("5. 各目录索引条目逐条存在性校验（四级解析 + 目录名解析）")
    all_files, all_dirs = {}, set()
    for root, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in (".git", "temp-cache", "__pycache__", "P1-pyc-cache-backup")]
        for d in dn:
            all_dirs.add(d)
        for f in fn:
            all_files.setdefault(f, []).append(os.path.join(root, f))
    # 索引里的"变更记录"式引用（旧名 → 新名）不参与解析
    RENAME_RECORD = {"决策日志/", "决策日志"}
    IDX = ["00-doubao-llm-prerequisites/doubao-prerequisites-index.md",
           "01-requirements/requirements-index.md", "04-implementation/implementation-index.md",
           "05-tests/tests-index.md", "06-deployment/deployment-index.md",
           "07-operations/operations-index.md", "08-review-logs/INDEX.md", "09-feedback/INDEX.md",
           "10-env-baseline/env-baseline-index.md", "11-management/management-index.md", "README.md"]
    total = bad = 0
    for rel in IDX:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            item("索引存在 %s" % rel, False)
            bad += 1
            continue
        d = os.path.dirname(p)
        txt = open(p, encoding="utf-8").read()
        checked = 0
        for c in sorted(set(re.findall(r"`([^`\n]{3,140})`", txt))):
            c = c.strip()
            if c.startswith(".") or c in RENAME_RECORD or os.path.basename(c.rstrip("/")) in EXTERNAL_BASENAMES:
                continue
            if not re.search(r"(\.(md|py|txt|ps1|bat|zip|xlsx|jsonl|yaml|toml|json|pyi|dll|csv)$|/$|\\\\|/)", c):
                continue
            if c.startswith(("http", "C:", "F:", "pip ", "python ", "git ", "gh ", "auditpol",
                             "Get-", "Set-", "Remove-")):
                continue
            if re.search(r"[\s=<>|*?（）()]", c):
                continue
            checked += 1
            total += 1
            cp = c.replace("/", os.sep).rstrip(os.sep)
            ok = (os.path.exists(os.path.join(d, cp)) or os.path.exists(os.path.join(BASE, cp))
                  or os.path.exists(os.path.join(SKILL_SRC, cp))
                  or os.path.basename(cp) in all_files
                  or os.path.basename(cp) in all_dirs)
            if not ok:
                bad += 1
                P("    ❌ %s 中的 `%s` 未解析到真实文件/目录" % (rel, c))
        P("  %-54s 可校验 %d 条" % (rel, checked))
    item("索引条目全部解析到真实文件", bad == 0, "校验 %d / 失败 %d" % (total, bad))


def c6_readme():
    sec("6. README 目录结构表逐行 vs 实际目录")
    txt = open(os.path.join(BASE, "README.md"), encoding="utf-8").read()
    rows = re.findall(r"^\|\s*(\d\d-[a-z0-9\-]+)\s*\|", txt, re.M)
    real = sorted(n for n in os.listdir(BASE) if re.match(r"^\d\d-", n))
    item("README 目录行 = 实际目录", rows == real, "差集=%s" % (set(rows) ^ set(real) or "无"))
    P("   README: %s" % ", ".join(rows))


def c7_skills():
    sec("7. 技能权威源 ↔ AppData 逐文件 SHA256（技能代码；运行时日志只存权威源）")
    skills = ["cache-manager", "computer-use-automation", "feedback-logger",
              "local-dev-environment", "parallel-serial-decider"]
    # 运行时日志（decision-log/ 与 log.txt）由脚本写到权威源，AppData 侧不应存在副本
    RUNTIME = ("decision-log", "log.txt")

    def is_runtime(rel):
        rel = rel.replace("/", "\\")
        return rel.startswith("decision-log\\") or rel == "log.txt"

    allok = True
    for s in skills:
        def tree(r):
            out = {}
            for root, dn, fn in os.walk(r):
                dn[:] = [d for d in dn if d not in ("temp-cache", "__pycache__")]
                for f in fn:
                    if f == "_user_meta.json":
                        continue
                    pp = os.path.join(root, f)
                    rel = os.path.relpath(pp, r)
                    if is_runtime(rel):
                        continue
                    out[rel] = hashlib.sha256(open(pp, "rb").read()).hexdigest()
            return out
        a, b = tree(os.path.join(SKILL_SRC, s)), tree(os.path.join(SKILL_APP, s))
        only_s, only_a = sorted(set(a) - set(b)), sorted(set(b) - set(a))
        diff = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        ok = not only_s and not only_a and not diff
        allok &= ok
        item("技能 %s 代码逐文件一致" % s, ok,
             "%d 文件%s" % (len(a), "" if ok else " 仅源=%s 仅App=%s 不同=%s" % (only_s, only_a, diff)))
        # 运行时日志：AppData 侧不应存在副本（杜绝双份漂移）
        stale = [p for p in ("decision-log", "log.txt")
                 if os.path.exists(os.path.join(SKILL_APP, s, p))]
        if s == "parallel-serial-decider":
            item("parallel-serial-decider AppData 侧无运行时日志副本", not stale,
                 "残留=%s" % stale if stale else "已单一源化")
    item("五技能代码全部逐文件一致", allok)


def c8_gitignore():
    sec("8. .gitignore 逐项 check-ignore 期望")
    ign = ["HANDOVER.md", "11-management/HANDOVER.md", "P1_acceptance_evidence.zip",
           "05-tests/P1_acceptance_evidence.zip", "P1_patch1_release_notes.md",
           "06-deployment/P1_patch1_release_notes.md", "06-deployment/P1-pyc-cache-backup",
           ".workbuddy", "10-env-baseline/_local_assets", "10-env-baseline/_local_assets/_wheels"]
    trk = ["README.md", "LICENSE", ".gitignore", "06-deployment/RELEASE_NOTES_INDEX.md",
           "06-deployment/RELEASE_NOTES_v1.md", "07-operations/git-sync.ps1",
           "07-operations/sync-to-github.bat", "11-management/project-phase-progress.xlsx",
           "11-management/management-index.md", "10-env-baseline/_tools/verify_reorg.py"]
    allok = True
    for p in ign:
        ok = subprocess.run(["git", "check-ignore", "-q", p], cwd=BASE).returncode == 0
        allok &= ok
        item("忽略 %s" % p, ok, "" if ok else "未被忽略！")
    for p in trk:
        ok = subprocess.run(["git", "check-ignore", "-q", p], cwd=BASE).returncode != 0
        allok &= ok
        item("入库 %s" % p, ok, "" if ok else "被误忽略！")
    item(".gitignore 逐项期望成立", allok)


def c9_git():
    sec("9. git 状态核对：提交/推送一致性与删除计数")
    r = subprocess.run(["git", "status", "--porcelain"], cwd=BASE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    lines = [l for l in (r.stdout or "").splitlines() if l.strip()]
    ren = [l for l in lines if l[:1] == "R"]
    dele = [l for l in lines if l[:2].strip() == "D"]
    for l in ren:
        P("    R %s" % l[:130])
    item("无删除（D=0）", not dele, "D=%d" % len(dele))

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()
    # 远端一致性：优先用 gh api 直读远端 ref（独立通道），失败再退回 ls-remote（关闭吊销检查）
    remote_sha, channel, errs = "", "", []
    gh = subprocess.run(["gh", "api", "repos/loveyueyaya/automation-verification-tool/git/ref/heads/main",
                         "--jq", ".object.sha"], cwd=BASE, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=180)
    if (gh.stdout or "").strip():
        remote_sha, channel = gh.stdout.strip(), "gh api"
    else:
        errs.append("gh: %s" % ((gh.stderr or "").strip()[:100]))
        LR = ["git", "-c", "http.schannelCheckRevoke=false", "ls-remote", "origin", "refs/heads/main"]
        for _ in range(3):
            lr = subprocess.run(LR, cwd=BASE, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=180)
            if (lr.stdout or "").split():
                remote_sha, channel = (lr.stdout or "").split()[0], "ls-remote"
                break
            errs.append("ls-remote rc=%s %s" % (lr.returncode, (lr.stderr or "").strip()[:100]))
    if errs and not remote_sha:
        P("    ⚠ 远端读取诊断: %s" % " | ".join(errs[-2:]))
    item("本地 HEAD == 远端 main（直读远端）", bool(head) and head == remote_sha,
         "本地=%s 远端=%s%s" % (head[:7], remote_sha[:7] or "读取失败",
                                "（通道：%s）" % channel if channel else ""))
    if ren:
        item("重命名/移动已暂存待提交（≥8 条）", len(ren) >= 8, "%d 条（尚未提交）" % len(ren))
    else:
        # 验证器自身会产生产物（_evidence 下的报告/日志、_tools/verify_reorg.py 本体），
        # 这些属"验证动作的输出"，不作为未提交项计入
        SELF_OUT = ("10-env-baseline/_evidence/", "10-env-baseline/_tools/verify_reorg.py")
        dirty = [l for l in lines if not any(l[3:].startswith(p) for p in SELF_OUT)]
        self_out = len(lines) - len(dirty)
        item("工作区干净（整理变更已提交）", not dirty,
             "未提交 %d 条%s" % (len(dirty), "（另有 %d 条为验证器自身产物，已排除）" % self_out if self_out else ""))
        for l in dirty:
            P("    ? %s" % l[:120])
    P("   HEAD=%s / remote main=%s" % (head[:7], remote_sha[:7] or "?"))


def c10_tools():
    sec("10. _tools 与 legacy_repair 逐脚本：编译 + 实跑")
    RUNSPEC = {"recycle_forensics.py": ["--since", "2026-09-19 05:40"],
               "restore_from_wheels.py": None, "restore_from_recycle.py": None,
               "watch_files.py": ["1", "1"], "verify_reorg.py": None}
    for d in (TOOLS, LEGACY):
        if not os.path.isdir(d):
            continue
        P("  -- %s --" % os.path.relpath(d, BASE))
        for s in sorted(f for f in os.listdir(d) if f.endswith(".py")):
            p = os.path.join(d, s)
            rc_c, _, _ = run([PY, "-m", "py_compile", p], timeout=120)
            comp = rc_c == 0
            if d == LEGACY:
                item("%s 编译" % s, comp)
                continue
            args = RUNSPEC.get(s, [])
            if args is None:
                item("%s 编译" % s, comp, "（无实跑规格）")
                continue
            rc, out, err = run([PY, p] + args, timeout=420, cwd=d)
            usage = rc == 2 and ("usage" in (out + err).lower() or "用法" in (out + err))
            ran = rc == 0 or usage
            first = (out.strip().splitlines() or [""])[0][:50]
            item("%s 编译+实跑" % s, comp and ran,
                 "rc=%d%s %s" % (rc, "（无参→用法）" if usage else "", first))
    pc = os.path.join(TOOLS, "__pycache__")
    if os.path.isdir(pc):
        shutil.rmtree(pc, ignore_errors=True)
    plc = os.path.join(LEGACY, "__pycache__")
    if os.path.isdir(plc):
        shutil.rmtree(plc, ignore_errors=True)


def c11_func():
    sec("11. 功能回归（逐项实跑）")
    p1 = os.path.join(BASE, r"04-implementation\P1-contracts-env-adapter")
    rc, out, err = run([PY, "-m", "unittest", "discover", "-s", "tests"], timeout=600, cwd=p1)
    tail = [l for l in ((err or out) or "").splitlines() if l.strip()][-3:]
    item("56 单测", rc == 0 and "OK" in " ".join(tail), " | ".join(tail))
    code = ("import importlib.util as u;mods=['cv2','numpy','PIL','dxcam','mss','psutil','pynvml','paddle',"
            "'paddlex','paddleocr','comtypes.client','uiautomation','pywinauto','win32gui','openpyxl',"
            "'dateutil','Crypto','google.protobuf','colorama','colorlog','httpx','idna','certifi',"
            "'cryptography','cffi','yaml','requests','huggingface_hub'];"
            "bad=[m for m in mods if u.find_spec(m) is None];print('BAD:',bad)")
    rc, out, err = run([PY, "-c", code], timeout=600)
    item("关键模块导入（28）", rc == 0 and "BAD: []" in out, out.strip()[-30:])
    KNOWN = {"paddlepaddle-gpu 3.3.1 has requirement nvidia-cudnn-cu12==9.5.1.17, "
             "but you have nvidia-cudnn-cu12 9.9.0.52."}
    rc, out, err = run([PY, "-m", "pip", "check"], timeout=600)
    warns = {l.strip() for l in (out or "").splitlines() if l.strip()}
    item("pip check 告警 ⊆ 已知基线", warns <= KNOWN,
         "共 %d 条，非基线 %d 条" % (len(warns), len(warns - KNOWN)))
    rc, out, err = run([PY, os.path.join(p1, "scripts", "shot.py"), "--out", r"F:\tmp\v.png",
                        "--region", "200,200,320,200"], timeout=600)
    item("区域截图 320×200", '"size": [320, 200]' in (out or ""))
    rc, out, err = run([PY, os.path.join(p1, "scripts", "locate.py"), "template",
                        "--image", r"F:\tmp\v.png", "--tpl", r"F:\tmp\v.png"], timeout=600)
    confs = [float(x) for x in re.findall(r'"confidence":\s*([0-9.]+)', out or "")]
    item("模板匹配 confidence ≥ 0.99", bool(confs) and max(confs) >= 0.99,
         "实测 confidence=%s" % (confs[0] if confs else "无输出"))


def c12_assets():
    sec("12. 本地资产 / 遗留脚本归位专项")
    w = os.path.join(ASSETS, "_wheels")
    b = os.path.join(ASSETS, "_backup_opencv_stale")
    item("_local_assets/_wheels", os.path.isdir(w), "%d 文件" % sum(len(f) for _, _, f in os.walk(w)))
    item("_local_assets/_backup_opencv_stale", os.path.isdir(b),
         "%d 文件" % sum(len(f) for _, _, f in os.walk(b)))
    py_n = len([f for f in os.listdir(LEGACY) if f.endswith(".py")])
    other_n = len([f for f in os.listdir(LEGACY) if not f.endswith(".py")])
    item("legacy_repair 共 18 项（11 脚本 + 4 无扩展名脚本 + 3 清单）",
         py_n == 11 and other_n == 7, "py=%d 其他=%d 合计=%d" % (py_n, other_n, py_n + other_n))
    rem = sorted(os.listdir(WORK))
    item("工作目录已清空（仅 .workbuddy）", rem == [".workbuddy"], str(rem))
    idx = open(os.path.join(BASE, "10-env-baseline", "env-baseline-index.md"), encoding="utf-8").read()
    for k in ("_tools", "_evidence", "_local_assets", "legacy_repair"):
        item("10 索引登记 %s" % k, k in idx)


def main():
    t0 = time.time()
    P("目录整理全量逐项验证报告 v2  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    for fn in (c1_layout, c2_tree, c3_stale, c4_refs, c5_index, c6_readme, c7_skills,
               c8_gitignore, c9_git, c10_tools, c11_func, c12_assets):
        fn()
    sec("汇总")
    tot = COUNTS["pass"] + COUNTS["fail"]
    P("  判定项合计 %d：通过 %d / 失败 %d" % (tot, COUNTS["pass"], COUNTS["fail"]))
    if FAILS:
        for f in FAILS:
            P("    ❌ %s" % f)
    else:
        P("  ✅ 全部通过")
    P("  耗时 %.1f s" % (time.time() - t0))
    os.makedirs(EVID, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    P("  报告: %s" % OUT)


if __name__ == "__main__":
    main()
