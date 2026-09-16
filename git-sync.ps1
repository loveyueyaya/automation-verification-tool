# git-sync.ps1 — 项目自动同步到 GitHub（有变更才提交推送，避免空提交）
# 用法：powershell -ExecutionPolicy Bypass -File .\git-sync.ps1   （或双击 .bat 包装）
$ErrorActionPreference = "Stop"
$p = Split-Path -Parent $MyInvocation.MyCommand.Path
$git = "C:\Program Files\Git\cmd\git.exe"
Set-Location $p

# 1. 检查是否有变更（工作区 + 暂存区）
$changed = (& $git status --porcelain 2>&1 | Measure-Object -Line).Lines
if ($changed -eq 0) {
    Write-Host "[sync] 无变更，跳过提交"
} else {
    & $git add -A
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $summary = (& $git status --porcelain | Select-Object -First 3) -join "; "
    & $git -c user.name="自动化验证工具" -c user.email="auto-verify@local" commit -m "auto-sync: $ts [$($changed) 个变更] $summary"
    Write-Host "[sync] 已提交 $changed 个变更 @ $ts"
}

# 2. 推送（无 remote 时提示）
$remote = (& $git remote 2>&1).Trim()
if (-not $remote) {
    Write-Host "[sync] 未配置 remote，跳过推送。请先执行 git remote add origin <仓库URL>"
    exit 0
}
Write-Host "[sync] 推送中..."
& $git push origin HEAD 2>&1
if ($LASTEXITCODE -eq 0) { Write-Host "[sync] 推送成功 ✓" } else { Write-Host "[sync] 推送失败（检查认证/网络）✗" }
