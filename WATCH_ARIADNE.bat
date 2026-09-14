@echo off
setlocal
cd /d "%~dp0"
python warden.py watch
if errorlevel 1 pause
