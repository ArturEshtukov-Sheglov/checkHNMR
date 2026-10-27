"""Run every tool of one version (tool root) on the 201 SI of the Org. Lett. sample.
usage: python run_tools.py TOOL_ROOT OUT_DIR
Outputs: OUT_DIR/{count,extract,smiles,check,checkpdf}/<key>.* plus stdout files."""
import csv, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

# folders of the machine on which the check was run: SI files (S/SI), results of the frozen run (H),
# frozen version (FREEZE); set them to your own copies
S = "/tmp/claude-0/-home-claude/4bd0c572-87ac-5560-85de-632aa64682ce/scratchpad"
H = S + "/art_res/results"
ROOT, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
FREEZE = "/home/claude/en_dev/v17c/release/nmr-1h-description-tools"
rows = list(csv.DictReader(open(FREEZE + "/samples/OrgLett_2026H1.csv")))
his = sorted(d for d in os.listdir(H) if os.path.isdir(H + "/" + d))
HERE = os.path.dirname(os.path.abspath(__file__))


def si(h):
    o = int([r for r in rows if re.fullmatch(r["file_key"], h)][0]["order"])
    return S + "/SI/" + ("SI146_%d" % int(h[-3:]) if o == 146 else "SI%03d" % o) + ".pdf"


env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
for d in ("count", "extract", "smiles", "check", "checkpdf"):
    os.makedirs(OUT + "/" + d, exist_ok=True)


def run(args, out_txt, cwd):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, env=env, cwd=cwd)
    # paths of the two versions differ: remove them from the printed output
    txt = (p.stdout + "\n--stderr--\n" + p.stderr + f"\n--rc {p.returncode}\n").replace(ROOT, "<ROOT>").replace(OUT, "<OUT>")
    open(out_txt, "w", encoding="utf-8").write(txt)


def one(h):
    pdf = si(h)
    run([ROOT + "/count_1H_descriptions/count_1H_descriptions.py", pdf, "-o", f"{OUT}/count/{h}"],
        f"{OUT}/count/{h}.txt", OUT)
    run([ROOT + "/extract_names/extract_names.py", pdf, "-o", f"{OUT}/extract/{h}"],
        f"{OUT}/extract/{h}.txt", OUT)
    run([HERE + "/fake_opsin_run.py", ROOT, f"{H}/{h}/compounds_{h}.xlsx", f"{OUT}/smiles/{h}.xlsx",
         f"{H}/{h}/smiles_{h}.xlsx"], f"{OUT}/smiles/{h}.txt", OUT)
    run([ROOT + "/check_descriptions/check_descriptions.py", f"{H}/{h}/smiles_{h}.xlsx", "-o", f"{OUT}/check/{h}"],
        f"{OUT}/check/{h}.txt", OUT)


def pdfmode(h):
    run([ROOT + "/check_descriptions/check_descriptions.py", si(h), "-o", f"{OUT}/checkpdf/{h}"],
        f"{OUT}/checkpdf/{h}.txt", OUT)


with ThreadPoolExecutor(3) as ex:
    list(ex.map(one, his))
    list(ex.map(pdfmode, his[::10]))
print("done", len(his))
