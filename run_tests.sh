#!/usr/bin/env bash
# ============================================================
#  Linux and macOS: check the tools themselves (bash run_tests.sh):
#  unit tests and stress tests with synthetic descriptions (about 2 minutes).
#  It does not need any SI file and does not change anything.
# ============================================================
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
    echo " Python was not found on this computer. Install Python 3.10 or newer and start again."
    exit 1
fi
"$PY" run_all.py --selftest "$@"
