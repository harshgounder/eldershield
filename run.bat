@echo off
REM ============================================================
REM  Kavach - one-click Windows launcher
REM  Installs dependencies (first run) and launches the demo UI
REM  Requires: Python 3.10+ installed and on PATH
REM  First run takes 5-15 min (downloads deps + ASR model).
REM  NOTE: runs on CPU on machines without NVIDIA GPU (slower).
REM ============================================================
setlocal
cd /d "%~dp0"
title Kavach - Voice-Scam Shield

echo.
echo  ============================================
echo    KAVACH - Digital-Arrest & Voice-Scam Shield
echo  ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Install Python 3.10+ from https://python.org and tick
    echo  "Add python.exe to PATH", then run this file again.
    pause
    exit /b 1
)

REM ---- create venv if missing ----
if not exist ".venv\Scripts\python.exe" (
    echo  [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create venv. Check Python install.
        pause
        exit /b 1
    )
)

REM ---- install deps if missing ----
if not exist ".venv\Lib\site-packages\gradio" (
    echo  [2/3] Installing dependencies (first run - this takes a while)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERROR] Dependency install failed. Check your internet.
        pause
        exit /b 1
    )
)

REM ---- launch ----
echo  [3/3] Launching Kavach demo UI...
echo  A browser window will open at http://127.0.0.1:7860
echo  Close this window to stop Kavach.
echo.
".venv\Scripts\python.exe" demo_ui.py
pause
