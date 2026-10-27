@echo off
rem ============================================================
rem  Double-click this file to check the tools themselves:
rem  unit tests and stress tests with synthetic descriptions (about 2 minutes).
rem  It does not need any SI file and does not change anything.
rem ============================================================
cd /d "%~dp0"
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY py --version >nul 2>&1 && set "PY=py"
if not defined PY (
    echo.
    echo  Python was not found on this computer.
    echo  Install it from https://www.python.org/downloads/ and, in the first window
    echo  of the installer, tick the box "Add python.exe to PATH". Then start this file again.
    echo.
    pause
    exit /b 1
)
%PY% run_all.py --selftest %*
echo.
pause
