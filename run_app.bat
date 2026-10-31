@echo off
title Audiobook Studio - Edge TTS
chcp 65001 >nul
echo ========================================================
echo        DANG KHOI DONG AUDIOBOOK STUDIO...
echo ========================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay moi truong ao .venv!
    echo Vui long chay: python -m venv .venv truoc.
    pause
    exit /b 1
)

:: Tu dong tim va cau hinh Tcl/Tk thu vien tren Windows
if exist "%LOCALAPPDATA%\Programs\Python\Python313\tcl\tcl8.6" (
    set "TCL_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tcl8.6"
    set "TK_LIBRARY=%LOCALAPPDATA%\Programs\Python\Python313\tcl\tk8.6"
)

start "" ".venv\Scripts\pythonw.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo [THONG BAO] Chay che do debug console:
    ".venv\Scripts\python.exe" main.py
)
