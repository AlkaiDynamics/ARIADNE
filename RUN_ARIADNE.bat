@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Run SETUP_ARIADNE.bat first.
  pause
  exit /b 1
)
python ariadne.py run
if errorlevel 1 (
  echo.
  echo ARIADNE hit an error. Copy the error above into ChatGPT.
  pause
  exit /b 1
)
