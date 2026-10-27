"""Run the whole check on every PDF in the folder data (any file names):
extract_names -> names_to_smiles -> check_descriptions -> Word report. The three tables of each PDF
and the Word report (checked_<file name>.docx: one compound per page, easier to read than the table)
go into results/<file name>/ . Files already done are skipped, so an interrupted run can simply be
started again (use --redo to recompute everything).

    python run_all.py                     all PDF files in data
    python run_all.py --redo              recompute files that are already done
    python run_all.py --selftest          check the tools themselves (unit tests + stress tests, a few minutes)
    python run_all.py --sample SAMPLE_TABLE.csv --from FOLDER_WITH_DOWNLOADED_SI
                                          reproduce a study sample: first copy its SI files into data
                                          under the study names (SI001.pdf ...) with rename_SI, then
                                          run the check on these files only

Only PDF files are checked: a Word file (.docx) must first be saved as PDF and put into data.
names_to_smiles uses the OPSIN web service (internet connection needed).

Before the check, run_all looks for Python 3.10 or newer and the packages pymupdf, openpyxl,
rdkit and python-docx. If a package is missing it offers to install it (versions from requirements.txt). Where the
system does not allow installing packages into its own Python (many Linux distributions), the
packages go into a folder .venv next to this file, and later runs use it automatically.
"""
import importlib.util
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")
VENV = os.path.join(ROOT, ".venv")
MIN_PYTHON = (3, 10)             # the tested package versions have no builds for older Python
# import name -> package name for pip
PACKAGES = {"fitz": "pymupdf", "openpyxl": "openpyxl", "rdkit": "rdkit", "docx": "python-docx"}   # v2.1.1: python-docx
OPSIN_TEST = "https://www.ebi.ac.uk/opsin/ws/benzene.json"
REEXEC = "NMR_TOOLS_RESTARTED"   # set when run_all restarts itself, so that it never loops
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")
# v2.1: Windows refuses paths longer than 260 characters unless they start with "\\?\"; a result table is
# results\<SI name>\compounds_<SI name>.xlsx, so a long folder name of the tools can exceed the limit
if os.name == "nt" and len(RESULTS) > 100 and not RESULTS.startswith("\\\\?\\"):
    RESULTS = ("\\\\?\\UNC\\" + RESULTS[2:]) if RESULTS.startswith("\\\\") else "\\\\?\\" + RESULTS
EXTRACT = os.path.join(ROOT, "extract_names", "extract_names.py")
SMILES = os.path.join(ROOT, "names_to_smiles", "names_to_smiles.py")
CHECK = os.path.join(ROOT, "check_descriptions", "check_descriptions.py")
RENAME = os.path.join(ROOT, "rename_SI", "rename_SI.py")
# v2.1.1: the Word report (Review to Word); it only reads the result table and changes no verdict
EXPORT = os.path.join(ROOT, "review_to_word", "export_docx.py")
# the scripts print compound labels such as 3k′; on Windows a script whose output goes to a pipe
# writes in the local code page (e.g. cp1251), which cannot encode them: make it write UTF-8
CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


# ===== Python and packages =====

def venv_python():
    """Python of the local .venv, if it exists."""
    for p in (os.path.join(VENV, "Scripts", "python.exe"), os.path.join(VENV, "bin", "python")):
        if os.path.exists(p):
            return p
    return None

def in_venv():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)

def restart(python):
    """Run run_all.py again with another Python (or after an installation) and stop this one."""
    env = dict(os.environ, **{REEXEC: "1"})
    sys.exit(subprocess.call([python, os.path.abspath(__file__)] + sys.argv[1:], env=env))

def missing():
    return [pkg for mod, pkg in PACKAGES.items() if importlib.util.find_spec(mod) is None]

def ask(question):
    """y/n question; without a console (e.g. output to a file) the answer is 'no'."""
    if not sys.stdin or not sys.stdin.isatty():
        return False
    try:
        return input(question + " [y/n] ").strip().lower() in ("y", "yes", "д", "да")
    except EOFError:
        return False

def pip(python, args):
    """Run pip; return (worked, output)."""
    p = subprocess.run([python, "-m", "pip", "install", "--disable-pip-version-check"] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode == 0, p.stdout + p.stderr

def install(python, user):
    """Install the tested versions; if they have no build for this Python, the latest ones."""
    extra = ["--user"] if user else []
    ok, out = pip(python, extra + ["-r", REQUIREMENTS])
    if ok:
        return True, out
    if "No module named pip" in out or "externally-managed-environment" in out:
        return False, out
    print("The tested versions could not be installed; trying the latest versions instead\n"
          "(results should be the same, but they were not tested with these versions) ...")
    return pip(python, extra + list(PACKAGES.values()))

def check_python_and_packages():
    """Make sure the scripts can run; offer to install what is missing."""
    if sys.version_info < MIN_PYTHON:
        sys.exit(f"Python {sys.version.split()[0]} is too old: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer "
                 "is needed.\nInstall it from https://www.python.org/downloads/ and start again.")
    venv = venv_python()
    if venv and not in_venv() and not os.environ.get(REEXEC):
        restart(venv)                    # packages were installed into .venv on an earlier run
    need = missing()
    if not need:
        return
    print("\nMissing packages: " + ", ".join(need))
    if os.environ.get(REEXEC):
        sys.exit("They are still missing after the installation. Install them by hand:\n"
                 f"    {sys.executable} -m pip install -r requirements.txt")
    if not ask("Install them now (versions from requirements.txt, a few minutes, internet needed)?"):
        sys.exit("Nothing was installed. To install them by hand:\n"
                 f"    {sys.executable} -m pip install -r requirements.txt")
    print("Installing ...")
    ok, out = install(sys.executable, user=not in_venv())
    if ok:
        restart(sys.executable)          # a fresh start sees the newly installed packages
    if "No module named pip" in out:
        sys.exit("pip (the package installer) is missing in this Python.\n"
                 "Linux (Debian/Ubuntu): sudo apt install python3-pip python3-venv\n"
                 "Other systems: python -m ensurepip --upgrade   - then start again.")
    if "externally-managed-environment" in out:
        # many Linux systems protect their own Python: use a separate environment next to the scripts
        print(f"This system does not allow packages in its own Python; creating a separate environment in\n{VENV} ...")
        p = subprocess.run([sys.executable, "-m", "venv", VENV], capture_output=True, text=True)
        venv = venv_python()
        if p.returncode != 0 or not venv:
            sys.exit("The environment could not be created. Linux (Debian/Ubuntu): sudo apt install python3-venv\n"
                     "then start again.\n" + p.stderr[-500:])
        ok, out = install(venv, user=False)
        if ok:
            restart(venv)
    sys.exit("The packages could not be installed. Check the internet connection and try again, "
             "or install them by hand:\n"
             f"    {sys.executable} -m pip install -r requirements.txt\n\nLast lines of the pip output:\n"
             + "\n".join(out.strip().splitlines()[-8:]))

def opsin_reachable():
    from urllib.request import urlopen
    try:
        with urlopen(OPSIN_TEST, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


# ===== self-test (v2.1) =====

STRESS = os.path.join(ROOT, "tests", "stress")
SEED = "20261023"                # fixed: the same descriptions and the same figures on every computer


def run_capture(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=CHILD_ENV)
    return p.returncode, p.stdout + p.stderr


def selftest(n):
    """Unit tests + four stress tests; prints one summary with PASS/FAIL. Returns the exit code."""
    import re
    out_dir = os.path.join(RESULTS, "selftest")
    os.makedirs(out_dir, exist_ok=True)
    rows, ok_all = [], True

    def row(name, value, passed, rule):
        nonlocal ok_all
        ok_all &= passed
        rows.append((name, value, "PASS" if passed else "FAIL", rule))

    print("Self-test: unit tests ...")
    if importlib.util.find_spec("pytest") is None:
        if ask("The unit tests need the package pytest. Install it now?"):
            pip(sys.executable, (["--user"] if not in_venv() else []) + ["pytest"])
            restart(sys.executable)
    if importlib.util.find_spec("pytest") is None:
        row("unit tests", "pytest not installed", False, "all pass")
    else:
        code, txt = run_capture([sys.executable, "-m", "pytest", "-q", "tests"], ROOT)
        last = [l for l in txt.strip().splitlines() if "passed" in l or "failed" in l or "error" in l][-1:] or ["?"]
        row("unit tests", last[0].strip(" ="), code == 0, "all pass")

    print(f"Self-test: format stress test, {n} synthetic descriptions ...")
    code, txt = run_capture([sys.executable, os.path.join(STRESS, "fuzz_parser.py"), str(n), SEED], out_dir)
    m = re.search(r"SUMMARY misread without unsupported forms .*?: (\d+) of (\d+) \(([\d.]+) %\); clean form misread: (\d+)", txt)
    if m:
        row("reading: clean descriptions misread", m.group(4), int(m.group(4)) == 0, "0")
        row("reading: noisy descriptions misread", f"{m.group(1)} of {m.group(2)} ({m.group(3)} %)",
            float(m.group(3)) <= 0.5, "<= 0.5 % (decimal comma not counted)")
    else:
        row("reading (format stress test)", "did not run", False, "see results/selftest/log.txt")

    print(f"Self-test: checks with known errors, {n} synthetic spin systems ...")
    code, txt2 = run_capture([sys.executable, os.path.join(STRESS, "semantic_test.py"), str(n), SEED], out_dir)
    txt += "\n" + txt2
    m = re.search(r"clean .*?any false finding: (\d+) \(([\d.]+) %\)", txt2)
    row("items 3, 4(a), 6(b): false findings on correct descriptions", m.group(2) + " %" if m else "?",
        bool(m) and int(m.group(1)) == 0, "0")
    for kind, item, need in (("j_mismatch", "3", 100.0), ("j_missing", "4(a)", 100.0), ("j_extra", "4(a)", 100.0),
                             ("strong", "6(b)", 90.0)):
        m = re.search(kind + r" .*?caught under item\S+: \d+ \(([\d.]+) %\)", txt2)
        row(f"item {item}: known errors found ({kind})", (m.group(1) + " %") if m else "?",
            bool(m) and float(m.group(1)) >= need, f">= {need:g} %" + (" (isolated AB pairs are exempt)" if kind == "strong" else ""))

    print(f"Self-test: structure checks with known errors, {n} descriptions from structures ...")
    code, txt3 = run_capture([sys.executable, os.path.join(STRESS, "structure_test.py"), str(n), SEED], out_dir)
    txt += "\n" + txt3
    m = re.search(r"clean .*?item 1 flagged (\d+) \(([\d.]+) %\), item 4\(b\) flagged (\d+)", txt3)
    if m:
        row("item 1: false findings on correct descriptions", m.group(2) + " %", float(m.group(2)) <= 0.5, "<= 0.5 %")
        row("item 4(b): false findings on correct descriptions", m.group(3), int(m.group(3)) == 0, "0")
    m = re.search(r"h_wrong .*?item 1 flagged \d+ \(([\d.]+) %\)", txt3)
    row("item 1: wrong integral found", (m.group(1) + " %") if m else "?", bool(m) and float(m.group(1)) >= 85,
        ">= 85 % (one H fewer with an NH/OH: subcategory)")
    m = re.search(r"mult_more .*?item 4\(b\) flagged \d+ \(([\d.]+) %\)", txt3)
    if m:
        rows.append(("item 4(b): too many partners found", m.group(1) + " %", "info", "upper bound only"))

    print(f"Self-test: realistic reading test, {n} descriptions in styles of published ones ...")   # v2.1
    code, txt4 = run_capture([sys.executable, os.path.join(STRESS, "realistic_test.py"), str(n), SEED], out_dir)
    txt += "\n" + txt4
    m = re.search(r"SUMMARY realistic descriptions misread: (\d+) of (\d+) \(([\d.]+) %\)", txt4)
    row("reading: realistic descriptions misread", f"{m.group(1)} of {m.group(2)} ({m.group(3)} %)" if m else "did not run",
        bool(m) and float(m.group(3)) <= 0.5, "<= 0.5 % (forms and frequencies of the development data)")

    with open(os.path.join(out_dir, "log.txt"), "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("\n" + "=" * 100)
    print(f"Self-test of {open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').readline().strip()}, "
          f"{n} synthetic descriptions per test, seed {SEED}")
    print("=" * 100)
    for name, value, res, rule in rows:
        print(f"  {res:5s} {name:62s} {value:>24s}   expected {rule}")
    print("=" * 100)
    print("ALL PASSED" if ok_all else "SOME CHECKS FAILED - see results/selftest/log.txt")
    print("The synthetic descriptions test the program, not its accuracy on published descriptions.")
    return 0 if ok_all else 1


# ===== the check =====

def step(script, args, log):
    """Run one script; return True if it worked. The output goes into the log file."""
    p = subprocess.run([sys.executable, script] + args, cwd=os.path.dirname(script),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=CHILD_ENV)
    log.write(f"\n$ {os.path.basename(script)} {' '.join(args)}\n{p.stdout}{p.stderr}")
    return p.returncode == 0

def word_report(chk, out, log):
    """v2.1.1: Word report from the result table (review_to_word/export_docx.py); True if it was made.
    It only reads checked_<name>.xlsx: the verdicts are those of the table."""
    if not os.path.exists(EXPORT):
        return False
    return step(EXPORT, [chk + ".xlsx", "-o", out, "--lang", "en"], log) and os.path.exists(chk + ".docx")

def smiles_with_retry(comp, smi, log, tries=3, pause=30):
    """names_to_smiles needs the OPSIN web service; a network error is retried after a pause."""
    for k in range(1, tries + 1):
        if step(SMILES, [comp + ".xlsx", "-o", smi], log) and os.path.exists(smi + ".xlsx"):
            return True
        if k < tries:
            print(f"      names_to_smiles: no answer from OPSIN, new try in {pause} s ({k + 1}/{tries}) ...")
            time.sleep(pause)
    return False

def cross_check(pdf, n1h):
    """v2.1: numbers of 13C descriptions and HRMS values in the same PDF; a warning when clearly fewer
    1H descriptions were found than 13C/HRMS ones (descriptions in an unknown form are not read silently)."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "count_1H_descriptions"))
        import count_1H_descriptions as cnt
        _, n13, nhr = cnt.analyse(pdf)
    except Exception:
        return None, None, ""
    ref = max(n13, nhr / 2)        # v2.1: one compound may have two or three HRMS values (several ions)
    warn = (f"CHECK: {n1h or 0} 1H descriptions read, but {n13} 13C and {nhr} HRMS - some 1H descriptions "
            f"may be written in a form the tool does not read") if ref >= 3 and (n1h or 0) < 0.5 * ref else ""
    # v2.1: problems of the PDF text itself (no text layer, symbol-font or unreadable characters)
    try:
        sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))
        import pymupdf
        from read_quality import file_quality
        doc = pymupdf.open(pdf)
        # the text as the tools read it (symbol-font characters already mapped): what is left is really lost
        notes = file_quality(cnt.pdf_text(pdf), len(doc), n1h or 0)
        if notes:
            warn = "; ".join(x for x in (warn, "PDF TEXT: " + "; ".join(notes)) if x)
    except Exception:
        pass
    return n13, nhr, warn


def rows(xlsx):
    try:
        import openpyxl
        ws = openpyxl.load_workbook(xlsx, read_only=True).worksheets[0]
        return max(ws.max_row - 1, 0)
    except Exception:
        return None

def structures(xlsx):
    try:
        import openpyxl
        ws = openpyxl.load_workbook(xlsx, read_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        head = list(next(it))
        k = head.index("smiles")
        return sum(1 for r in it if r[k])
    except Exception:
        return None

# v2.1: Excel cannot open a file whose full path is longer than 259 characters; a result table is
# results\<SI name>\checked_<SI name>.xlsx, about 110 characters after the folder of the tools
EXCEL_MAX_PATH = 259
RESULT_PATH_EXTRA = 115


def warn_long_path():
    root = ROOT[4:] if ROOT.startswith("\\\\?\\") else ROOT
    if os.name == "nt" and len(root) + RESULT_PATH_EXTRA > EXCEL_MAX_PATH:
        print(f"NOTE: the folder of the tools has a long path ({len(root)} characters). Excel cannot open files\n"
              f"whose path is longer than {EXCEL_MAX_PATH} characters, so some result tables may not open.\n"
              f"Move the folder to a short path, e.g. C:\\nmr\\, and run again.\n")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--redo", action="store_true", help="recompute files that are already done")
    ap.add_argument("--sample", help="sample table (CSV/XLSX) of a study, used with --from")
    ap.add_argument("--from", dest="src", help="folder with the downloaded SI files of the sample")
    ap.add_argument("--selftest", action="store_true",
                    help="check the tools themselves: unit tests and stress tests with synthetic descriptions")
    ap.add_argument("-n", type=int, default=10000, help="number of synthetic descriptions per stress test (default 10000)")
    args = ap.parse_args()
    check_python_and_packages()
    warn_long_path()
    if args.selftest:
        sys.exit(selftest(args.n))
    for s in (EXTRACT, SMILES, CHECK):
        if not os.path.exists(s):
            sys.exit(f"Not found: {s}\nKeep run_all.py in the main folder, next to the folders of the scripts.")
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(RESULTS, exist_ok=True)
    sample, src = args.sample, args.src
    only = None
    if sample or src:
        if not (sample and src):
            ap.error("--sample and --from are used together")
        print(f"Copying the SI files of the sample into {DATA} ...")
        p = subprocess.run([sys.executable, RENAME, src, DATA, "--sample", sample], text=True,
                           capture_output=True, encoding="utf-8", errors="replace", env=CHILD_ENV)
        print(p.stdout.strip().split("\n\n")[-1] if p.stdout else p.stderr)
        if p.returncode != 0:
            sys.exit("rename_SI failed:\n" + p.stderr)
        only = lambda name: name.upper().startswith("SI") and name[2:5].isdigit()

    files = sorted(f for f in os.listdir(DATA) if not f.startswith("."))
    pdfs = [f for f in files if f.lower().endswith(".pdf") and (only is None or only(f))]
    other = [f for f in files if not f.lower().endswith(".pdf") and f.lower() not in ("readme.txt", "readme.md")
             and os.path.isfile(os.path.join(DATA, f))]
    for f in other:
        print(f"skipped, not a PDF (save it as PDF and put it into data): {f}")
    if not pdfs:
        sys.exit(f"No PDF files in {DATA}. Put the SI PDF files there and start again.")
    online = opsin_reachable()
    if not online:
        print("\nThe OPSIN web service does not answer (no internet connection, or the service is down).\n"
              "Without it no structures are made from the names: only the checks from the text are made\n"
              "(items 3, 4(a), 6(b), and item 1 from the HRMS formula); items 4(b) and 6(a) need a structure.")
        if sys.stdin and sys.stdin.isatty() and not ask("Continue with the checks from the text only?"):
            sys.exit("Stopped. Connect to the internet and start again.")

    redo = args.redo
    t0 = time.time()
    summary = []
    with open(os.path.join(RESULTS, "run_log.txt"), "a", encoding="utf-8") as log:
        log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')}  {len(pdfs)} PDF files =====\n")
        for i, f in enumerate(pdfs, 1):
            n = os.path.splitext(f)[0]
            out = os.path.join(RESULTS, n)
            comp, smi, chk = (os.path.join(out, x + n) for x in ("compounds_", "smiles_", "checked_"))
            # a file checked without structures (no internet) is done again when OPSIN is available
            if not redo and os.path.exists(chk + ".xlsx") and (os.path.exists(smi + ".xlsx") or not online):
                if not os.path.exists(chk + ".docx"):                # v2.1.1: Word report of an earlier run
                    word_report(chk, out, log)
                print(f"[{i}/{len(pdfs)}] {n}: already done (--redo to recompute)")
                summary.append((n, rows(comp + ".xlsx"), structures(smi + ".xlsx"), "done earlier", 0.0, None, None, ""))
                continue
            os.makedirs(out, exist_ok=True)
            t = time.time()
            log.write(f"\n--- {n}\n")
            status = "ok"
            if not step(EXTRACT, [os.path.join(DATA, f), "-o", comp], log) or not os.path.exists(comp + ".xlsx"):
                status = "extract_names failed (no 1H descriptions found?)"
            else:
                table = smi
                if not online or not smiles_with_retry(comp, smi, log):
                    table = comp             # no structures: check the descriptions from the text only
                    status = "ok, text checks only (no structures: OPSIN web service not available)"
                if not step(CHECK, [table + ".xlsx", "-o", chk], log) or not os.path.exists(chk + ".xlsx"):
                    status = "check_descriptions failed"
                elif not word_report(chk, out, log):
                    status += "; Word report not made (see run_log.txt)"
            dt = time.time() - t
            d, s = rows(comp + ".xlsx"), structures(smi + ".xlsx")
            n13, nhr, warn = cross_check(os.path.join(DATA, f), d)
            print(f"[{i}/{len(pdfs)}] {n}: {status}; descriptions {d if d is not None else '-'}, "
                  f"structures {s if s is not None else '-'}; {dt:.0f} s" + (f"\n      {warn}" if warn else ""))
            summary.append((n, d, s, status, dt, n13, nhr, warn))
    with open(os.path.join(RESULTS, "run_summary.csv"), "w", encoding="utf-8") as fh:
        fh.write("file,descriptions,structures,status,seconds,13C_descriptions,HRMS_values,warning\n")
        for n, d, s, st, dt, n13, nhr, warn in summary:
            fh.write(f"{n},{'' if d is None else d},{'' if s is None else s},\"{st}\",{dt:.0f},"
                     f"{'' if n13 is None else n13},{'' if nhr is None else nhr},\"{warn}\"\n")
    bad = [x for x in summary if not (x[3].startswith("ok") or x[3] == "done earlier")]
    print(f"\nDone: {len(summary)} files, {sum(x[1] or 0 for x in summary)} descriptions, "
          f"{sum(x[2] or 0 for x in summary)} structures, {time.time() - t0:.0f} s.")
    print(f"Results: {os.path.join(RESULTS, '<file name>')} - Word report checked_<file name>.docx (one compound per page)\n"
          f"and the table checked_<file name>.xlsx (all columns); summary: run_summary.csv ; details of every step: run_log.txt")
    if any(x[3].startswith("ok, text") for x in summary):
        print("Some files were checked from the text only (no structures): names_to_smiles needs an internet\n"
              "connection (OPSIN web service). Start run_all again when online: these files are done again.")
    warned = [x[0] for x in summary if x[7]]
    if warned:
        print(f"CHECK by hand ({len(warned)} files): fewer 1H descriptions read than 13C/HRMS ones - "
              "see the column 'warning' in run_summary.csv: " + ", ".join(warned[:10]) + (" ..." if len(warned) > 10 else ""))
    if bad:
        print("Problems in: " + ", ".join(x[0] for x in bad) + " (see run_log.txt)")
        print("Start run_all again: the files already done are skipped and only these are tried again.")

if __name__ == "__main__":
    main()
