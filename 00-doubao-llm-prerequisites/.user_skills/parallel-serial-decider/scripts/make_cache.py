# -*- coding: utf-8 -*-
"""创建临时缓存：F:\\自动化验证工具\\临时缓存\\<时间戳>\\

包含：
- snapshot\\    ← 完整复制指定路径（--paths，逗号分隔；缺省为空）
- git_state.txt ← git branch / git log -1 / git status
- manifest.json ← 快照元数据
- restore.ps1   ← 一键恢复脚本

用法：
  python make_cache.py --task "改分支名" --strategy serial --paths "F:\\x\\04-implementation,F:\\x\\config"
"""
import argparse, datetime, json, os, shutil, subprocess

ROOT = r"F:\自动化验证工具"
CACHE_ROOT = os.path.join(ROOT, r"00-doubao-llm-prerequisites\.user_skills\parallel-serial-decider\temp-cache")
GIT = r"C:\Program Files\Git\cmd\git.exe"


def run_git(args, cwd):
    try:
        r = subprocess.run([GIT] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.stdout.strip() + ("\n[stderr] " + r.stderr.strip() if r.stderr.strip() else "")
    except Exception as e:
        return "ERROR: %s" % e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="")
    ap.add_argument("--strategy", default="serial")
    ap.add_argument("--paths", default="", help="逗号分隔的绝对路径，将被复制进 snapshot")
    args = ap.parse_args()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_dir = os.path.join(CACHE_ROOT, ts)
    snap_dir = os.path.join(cache_dir, "snapshot")
    os.makedirs(snap_dir, exist_ok=True)

    # 1. snapshot 复制
    snapshot_of = []
    for p in [x.strip() for x in args.paths.split(",") if x.strip()]:
        if os.path.exists(p):
            dst = os.path.join(snap_dir, os.path.basename(p.rstrip("\\/")))
            if os.path.isdir(p):
                shutil.copytree(p, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(p, dst)
            snapshot_of.append(p)
            print("snapshot: %s -> %s" % (p, dst))

    # 2. git_state.txt
    git_state = "\n".join([
        "=== branch ===", run_git(["branch", "--show-current"], ROOT),
        "=== log -1 ===", run_git(["log", "-1", "--oneline"], ROOT),
        "=== status ===", run_git(["status", "--short"], ROOT),
    ])
    with open(os.path.join(cache_dir, "git_state.txt"), "w", encoding="utf-8") as f:
        f.write(git_state)

    # 3. manifest.json
    manifest = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "task": args.task,
        "strategy": args.strategy,
        "snapshot_of": snapshot_of,
        "git_branch": run_git(["branch", "--show-current"], ROOT),
        "git_commit": run_git(["log", "-1", "--format=%h"], ROOT),
        "restore_cmd": "powershell -File restore.ps1",
    }
    with open(os.path.join(cache_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 4. restore.ps1
    restore_lines = [
        "# 一键恢复脚本（由 make_cache.py 生成）",
        "$Cache = Split-Path -Parent $MyInvocation.MyCommand.Path",
        "$Snap = Join-Path $Cache 'snapshot'",
        "if (-not (Test-Path $Snap)) { Write-Host 'snapshot 不存在，无法恢复'; exit 1 }",
        "Get-ChildItem $Snap | ForEach-Object {",
        "    $Target = $_.FullName.Replace($Snap, '')",
        "    $Dst = 'F:\\自动化验证工具' + $Target",
        "    if ($_.PSIsContainer) {",
        "        if (Test-Path $Dst) { Remove-Item $Dst -Recurse -Force }",
        "        Copy-Item $_.FullName $Dst -Recurse -Force",
        "    } else {",
        "        Copy-Item $_.FullName $Dst -Force",
        "    }",
        "    Write-Host ('restored: ' + $Dst)",
        "}",
        "Write-Host '恢复完成，请人工核对 git 状态。'",
    ]
    with open(os.path.join(cache_dir, "restore.ps1"), "w", encoding="utf-8-sig") as f:
        f.write("\n".join(restore_lines) + "\n")

    print("缓存已创建: %s" % cache_dir)
    print("manifest: %s" % os.path.join(cache_dir, "manifest.json"))


if __name__ == "__main__":
    main()
