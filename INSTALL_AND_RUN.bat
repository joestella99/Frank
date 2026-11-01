@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed installing Pillow. Make sure Python 3.10+ is installed.
  pause
  exit /b 1
)
py -3 desktop.py
pause
