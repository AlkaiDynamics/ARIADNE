@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo ARIADNE needs Python 3 installed.
  echo Install Python from https://www.python.org/downloads/ and check "Add Python to PATH".
  echo Then run this file again.
  echo.
  pause
  exit /b 1
)
python ariadne.py init
if errorlevel 1 (
  echo.
  echo ARIADNE setup failed. Copy the error above into ChatGPT.
  pause
  exit /b 1
)
echo.
echo ARIADNE is ready.
echo Put files in the inbox folder, then double-click RUN_ARIADNE.bat.
echo.
pause
