@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\pythonw.exe" (
 start "" ".venv\Scripts\pythonw.exe" "%~dp0bridge.py"
 exit /b
)
if exist "dist\1.1.7\ChzzkChatLounge-win32-x64\resources\python\pythonw.exe" (
 start "" "dist\1.1.7\ChzzkChatLounge-win32-x64\resources\python\pythonw.exe" "%~dp0bridge.py"
 exit /b
)
echo Python environment missing. Install requirements.txt in .venv first.
pause
