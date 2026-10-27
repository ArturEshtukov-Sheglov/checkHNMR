"""Make the tool folders importable in the tests."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("count_1H_descriptions", "extract_names", "check_descriptions", "rename_SI"):
    sys.path.insert(0, os.path.join(ROOT, d))
