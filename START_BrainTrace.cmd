@echo off
chcp 65001 >nul
powershell -NoProfile -File "%~dp0launch_site.ps1" -Port 8766
pause
