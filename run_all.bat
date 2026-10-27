@echo off
rem ============================================================
rem  Double-click this file to check every PDF in the folder data.
rem  The result tables appear in the folder results.
rem ============================================================
cd /d "%~dp0"

echo.
echo  ==========================================================================
echo   checkHNMR (local version): consistency check of 1H NMR descriptions
echo.
echo   Author: Artur V. Eshtukov-Shcheglov
echo   The code was written with the assistance of Claude Opus 5.5 (Anthropic)
echo   and was reviewed and tested by the author.  License: MIT.
echo   Questions and bug reports: nemtcev.94.nmr@gmail.com
echo.
echo   "The first principle is that you must not fool yourself -
echo    and you are the easiest person to fool."   Richard P. Feynman, 1974
echo  ==========================================================================

rem --- 1. Python
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

rem --- 2. Python version and packages: run_all.py checks them and offers to install what is missing

rem --- 3. Input files
if not exist "data\*.pdf" (
    echo.
    echo  There are no PDF files in the folder data.
    echo  Put the PDF files there ^(as PDF; a Word file must first be saved as PDF^) and start again.
    echo.
    pause
    exit /b 1
)

rem --- 4. Run
echo.
echo  Checking the PDF files in data. Structures are made with the OPSIN web service,
echo  so the computer must be online. This can take about a minute per file.
echo.
%PY% run_all.py %*
echo.
echo  The Word reports and the tables are in the folder results ^(one folder per PDF file^).
echo.
pause
