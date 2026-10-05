@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 setup_titan.py
) else (
  python setup_titan.py
)
pause
