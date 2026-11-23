@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "URL=http://127.0.0.1:8766/"

echo.
echo  PSSM Self Knowledge
echo  -------------------
echo  Welcome: %URL%
echo.
echo  Keep this window open. Page edits reload themselves.
echo  Python edits restart the server without closing this window.
echo  Ctrl+C stops the server.
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo  ERROR: Python not found on PATH.
  echo.
  echo  Install Python 3.10+ from:
  echo    https://www.python.org/downloads/
  echo  Check "Add python.exe to PATH", then re-open this window.
  echo.
  pause
  exit /b 1
)

python "%~dp0scripts\check_python_env.py"
if errorlevel 1 (
  echo.
  echo  ERROR: Python 3.10 or newer is required.
  echo  Download: https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

start "PSSM Self Knowledge browser" /min cmd /c "ping -n 3 127.0.0.1 >nul & start %URL%"

python serve.py --no-browser --host 127.0.0.1 --port 8766
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
  echo.
  echo Server exited with code %ERR%.
  pause
)

endlocal
exit /b %ERR%
