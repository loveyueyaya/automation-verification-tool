# -*- coding: utf-8 -*-
"""临时缓存管理：F:\\自动化验证工具\\00-doubao-llm-prerequisites\\.user_skills\\cache-manager\\temp-cache\\

子命令：
  create  创建缓存（默认）：snapshot + git_state.txt + manifest.json + restore.ps1
  --list  列出全部缓存（含 task/strategy/commit）
  --clean 清理缓存（--days 保留天数，默认：保留 7 天，清理更早的缓存）

创建用法：
  python make_cache.py --task "改分支名" --strategy serial --paths "F:\\x\\04-implementation,F:\\x\\config"
"""
import argparse, datetime, json, os, shutil, subprocess

ROOT = r"F:\自动化验证工具"
CACHE_ROOT = os.path.join(
    ROOT, r"00-doubao-llm-prerequisites\.user_skills\cache-manager\temp-cache")
GIT = r"C:\Program Files\Git\cmd\git.exe"


def run_git(args, cwd):
    try:
        r = subprocess.run([GIT] + args, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip() + ("\n[stderr] " + r.stderr.strip() if r.stderr.strip() else "")
    except Exception as e:
        return "ERROR: %s" % e


def list_caches():
    if not os.path.isdir(CACHE_ROOT):
        print("缓存目录不存在: %s" % CACHE_ROOT)
        return
    for d in sorted(os.listdir(CACHE_ROOT)):
        p = os.path.join(CACHE_ROOT, d)
        if not os.path.isdir(p):
            continue
        mf = os.path.join(p, "manifest.json")
        if os.path.exists(mf):
            with open(mf, encoding="utf-8") as f:
                j = json.load(f)
            print("%s | %s | %s | %s" % (d, j.get("strategy", "?"), j.get("task", "?"), j.get("git_commit", "?")))
        else:
            print("%s | (无 manifest)" % d)


def clean_caches(days):
    if not os.path.isdir(CACHE_ROOT):
        print("缓存目录不存在")
        return
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    removed = 0
    for d in os.listdir(CACHE_ROOT):
        p = os.path.join(CACHE_ROOT, d)
        if not os.path.isdir(p):
            continue
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(p))
            if mtime < cutoff:
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
                print("cleaned: %s (mtime %s)" % (d, mtime.isoformat(timespec="seconds")))
        except Exception as e:
            print("skip %s: %s" % (d, e))
    print("共清理 %d 个缓存（保留最近 %d 天）" % (removed, days))


def create_cache(args):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cache_dir = os.path.join(CACHE_ROOT, ts)
    snap_dir = os.path.join(cache_dir, "snapshot")
    os.makedirs(snap_dir, exist_ok=True)

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

    git_state = "\n".join([
        "=== branch ===", run_git(["branch", "--show-current"], ROOT),
        "=== log -1 ===", run_git(["log", "-1", "--oneline"], ROOT),
        "=== status ===", run_git(["status", "--short"], ROOT),
    ])
    with open(os.path.join(cache_dir, "git_state.txt"), "w", encoding="utf-8") as f:
        f.write(git_state)

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="")
    ap.add_argument("--strategy", default="serial")
    ap.add_argument("--paths", default="", help="逗号分隔的绝对路径，将被复制进 snapshot")
    ap.add_argument("--list", action="store_true", help="列出全部缓存")
    ap.add_argument("--clean", action="store_true", help="清理过期缓存")
    ap.add_argument("--days", type=int, default=7, help="--clean 时保留天数")
    args = ap.parse_args()

    if args.list:
        list_caches()
    elif args.clean:
        clean_caches(args.days)
    else:
        create_cache(args)


if __name__ == "__main__":
    main()
