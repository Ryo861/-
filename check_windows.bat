@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto failed
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo 自動テスト完了。skippedがある場合は画面の検証は未完了です。
pause
exit /b 0
:failed
echo 検証に失敗しました。準備を確認し、表示されたエラーを保存してください。
pause
exit /b 1
