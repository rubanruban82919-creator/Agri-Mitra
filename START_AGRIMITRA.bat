@echo off
setlocal
cd /d "%~dp0"
title AgriMitra - Starting
echo ============================================
echo             AGRIMITRA WEBSITE
echo ============================================
echo.
where py >nul 2>nul
if not errorlevel 1 (
  set PY=py -3
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python is not installed.
    echo Install Python 3.10 or newer from https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set PY=python
)
echo Installing required packages...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation failed. Check internet and Python installation.
  pause
  exit /b 1
)
echo.
echo Starting AgriMitra...
echo Keep this window open while using the website.
start "" http://127.0.0.1:8000
%PY% -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
echo.
echo Server stopped.
pause
