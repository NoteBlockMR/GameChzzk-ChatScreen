@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist soop-addon.jar (
 echo Build first: powershell -File build.ps1
 pause
 exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
