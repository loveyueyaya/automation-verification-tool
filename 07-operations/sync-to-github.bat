@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0git-sync.ps1"
exit /b %ERRORLEVEL%
