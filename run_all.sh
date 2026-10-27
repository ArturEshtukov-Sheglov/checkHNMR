#!/usr/bin/env bash
# ============================================================
#  Linux and macOS: check every PDF in the folder data.
#  Start it in a terminal from any folder:   bash run_all.sh
#  The result tables appear in the folder results.
# ============================================================
cd "$(dirname "$0")" || exit 1

echo
echo " =========================================================================="
echo "  checkHNMR (local version): consistency check of 1H NMR descriptions"
echo
echo "  Author: Artur V. Eshtukov-Shcheglov"
echo "  The code was written with the assistance of Claude Opus 5.5 (Anthropic)"
echo "  and was reviewed and tested by the author.  License: MIT."
echo "  Questions and bug reports: nemtcev.94.nmr@gmail.com"
echo
echo "  \"The first principle is that you must not fool yourself -"
echo "   and you are the easiest person to fool.\"   Richard P. Feynman, 1974"
echo " =========================================================================="

# --- 1. Python
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
    echo
    echo " Python was not found on this computer. Install Python 3.10 or newer:"
    echo "   Debian/Ubuntu:  sudo apt install python3 python3-pip python3-venv"
    echo "   Fedora:         sudo dnf install python3 python3-pip"
    echo "   macOS:          https://www.python.org/downloads/  (or: brew install python)"
    echo " Then start this file again."
    exit 1
fi

# --- 2. Python version and packages: run_all.py checks them and offers to install what is missing

# --- 3. Input files
shopt -s nullglob nocaseglob
PDFS=(data/*.pdf)
shopt -u nullglob nocaseglob
if [ ${#PDFS[@]} -eq 0 ]; then
    echo
    echo " There are no PDF files in the folder data."
    echo " Put the PDF files there (as PDF; a Word file must first be saved as PDF) and start again."
    exit 1
fi

# --- 4. Run
echo
echo " Checking the PDF files in data. Structures are made with the OPSIN web service,"
echo " so the computer must be online. This can take about a minute per file."
echo
"$PY" run_all.py "$@"
echo
echo " The Word reports and the tables are in the folder results (one folder per PDF file)."
