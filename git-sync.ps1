# git-sync.ps1 — 项目自动同步到 GitHub（无变更不提交，无领先不推送；CI 无阻塞）
# 用法：powershell -ExecutionPolicy Bypass -File .\git-sync.ps1   （或双击 .bat 包装）
# 规范：不依赖 git stderr 判断成败；成败只看 $LASTEXITCODE；全程无交互阻塞
$ErrorActionPreference = "Continue"
$p = Split-Path -Parent $MyInvocation.MyCommand.Path
$git = "C:\Program Files\Git\cmd\git.exe"
Set-Location $p

# 1. 有变更才提交（工作区 + 暂存区）
$changed = (& $git status --porcelain | Measure-Object -Line).Lines
if ($changed -gt 0) {
    & $git add -A
    if ($LASTEXITCODE -ne 0) { Write-Host "[sync] git add 失败"; exit 1 }
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $summary = (& $git status --porcelain | Select-Object -First 3) -join "; "
    & $git -c user.name="自动化验证工具" -c user.email="auto-verify@local" commit -m "auto-sync: $ts [$($changed) 个变更] $summary"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[sync] 已提交 $changed 个变更 @ $ts"
    } else {
        Write-Host "[sync] 提交失败（可能无内容可提交）"
        exit 1
    }
} else {
    Write-Host "[sync] 无变更，跳过提交"
}

# 2. 有领先提交才推送（先确认 remote 与上游分支）
$remote = (& $git remote).Trim()
if (-not $remote) {
    Write-Host "[sync] 未配置 remote，跳过推送。请先执行 git remote add origin [仓库URL]"
    exit 0
}
$upstream = (& $git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null).Trim()
if (-not $upstream) {
    Write-Host "[sync] 当前分支无上游分支，跳过推送。请先 git push -u origin [分支名]"
    exit 0
}
$ahead = 0
try { $ahead = [int]((& $git rev-list --count '@{u}..HEAD').Trim()) } catch { $ahead = 0 }
if ($ahead -le 0) {
    Write-Host "[sync] 无领先提交（本地与远端一致），跳过推送"
    exit 0
}

Write-Host "[sync] 领先 $ahead 个提交，推送中..."
& $git push origin HEAD
if ($LASTEXITCODE -eq 0) {
    Write-Host "[sync] 推送成功 ✓"
    exit 0
} else {
    Write-Host "[sync] 推送失败（检查认证/网络）✗"
    exit 1
}
