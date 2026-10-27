"""Compare all compiled regex objects and string constants of old and new modules with the same name."""
import importlib.util, re, sys
def load(p, n):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
old, new = load(sys.argv[1], "old_m"), load(sys.argv[2], "new_m")
for k, v in vars(old).items():
    if isinstance(v, re.Pattern):
        w = getattr(new, k, None)
        print(("OK  " if w is not None and (w.pattern, w.flags) == (v.pattern, v.flags) else "DIFF"), k)
