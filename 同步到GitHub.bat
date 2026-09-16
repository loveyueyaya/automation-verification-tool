@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File "%~dp0git-sync.ps1"
pause
