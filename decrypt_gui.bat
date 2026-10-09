@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 decrypt_gui.py
  goto :end
)

where python >nul 2>&1
if %errorlevel%==0 (
  python decrypt_gui.py
  goto :end
)

echo Python 3 is not installed. Install it from https://www.python.org/downloads/
echo Make sure "Add python.exe to PATH" is checked.
pause
exit /b 1

:end
if errorlevel 1 (
  echo.
  echo If you saw a pycryptodome error, run:
  echo     pip install pycryptodome
  echo.
  pause
)
