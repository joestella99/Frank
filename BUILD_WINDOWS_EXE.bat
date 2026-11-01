@echo off
cd /d "%~dp0"
echo Building Frank.exe for Windows...
py -3 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo Please install Python 3.10+ and try again.
  pause
  exit /b 1
)
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name Frank --add-data "assets;assets" desktop.py
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo Frank is ready in dist\Frank.exe
pause
