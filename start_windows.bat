@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
exit /b 0
:missing
echo 先にsetup_windows.batをダブルクリックしてください。
pause
exit /b 1
:failed
echo 起動に失敗しました。setup_windows.batを実行し直してください。
pause
exit /b 1
