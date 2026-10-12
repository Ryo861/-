@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 初回準備を開始します。インターネット接続が必要です。
py -3.11 -c "import sys; assert sys.maxsize > 2**32; import tkinter"
if errorlevel 1 goto missing
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m tools.diagnose
if errorlevel 1 goto failed
echo 準備完了です。start_windows.batをダブルクリックしてください。
pause
exit /b 0
:missing
echo Python 3.11の64bit版をPython公式サイトからインストールしてください。
echo インストール時に「Python Launcher」と「tcl/tk and IDLE」を有効にしてください。
goto failed
:failed
echo 準備に失敗しました。この画面のエラーを確認してください。
pause
exit /b 1
