"""Automatic tests of the tools on small invented examples (no published data needed).

    python -m pip install pytest
    python -m pytest tests

The examples are made up for the tests; they do not come from any publication. The test of
names_to_smiles needs no internet: structures are given in the table, as a user may draw them.
"""
import csv, os, subprocess, sys
import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

import count_1H_descriptions as cnt
import check_descriptions as chk


# ---------------------------------------------------------------- detection of 1H descriptions
@pytest.mark.parametrize("text, found", [
    ("1H NMR (400 MHz, CDCl3) δ 7.26 (s, 1H)", True),
    ("1H NMR (300 MHz, CDCl3): 7.35-7.28 (m, 2H), 6.89 (d, J = 8.0 Hz, 2H)", True),   # no delta
    ("1H NMR (CDCl3, 400 MHz) 8.94 (d, J = 8.8 Hz, 1H)", True),                       # no delta, no colon
    ("1H NMR (400 MHz, CDCl3) of 3a (Figure S5)", False),                              # caption
    ("1H NMR (400 MHz, CDCl3) spectrum was recorded at 298 K (see Figure 2)", False),  # prose
])
def test_description_detection(text, found):
    assert bool(cnt.DESC_BODY.search(text)) is found


# ---------------------------------------------------------------- multiplicity parser
@pytest.mark.parametrize("mult, code, n_j", [
    ("dd", "dd", 2), ("td", "td", 2), ("ddt", "ddt", 3), ("hept", "sept", 1),
    ("heptd", "septd", 2), ("pentd", "pd", 2), ("app t", "t", 1),
])
def test_parse_mult(mult, code, n_j):
    p = chk.parse_mult(mult)
    assert p is not None and p[0] == code
    assert chk.expected_j(p[0]) == n_j


# ---------------------------------------------------------------- text-only checks
def test_item4a_triplet_with_two_constants():
    r = chk.check("1H NMR (400 MHz, CDCl3) δ 7.84 (t, J = 5.4, 3.2 Hz, 2H), 7.71 (dd, J = 5.4, 3.1 Hz, 2H).")
    assert r["item4a"] == "inconsistent"

def test_item3_partners_found():
    r = chk.check("1H NMR (400 MHz, CDCl3) δ 7.80 (d, J = 8.2 Hz, 1H), 6.10 (d, J = 8.2 Hz, 1H).")
    assert r["item3"] == "consistent"

def test_item3_constant_without_partner():
    r = chk.check("1H NMR (400 MHz, CDCl3) δ 7.80 (d, J = 8.2 Hz, 1H), 6.10 (d, J = 6.5 Hz, 1H).")
    assert r["item3"].startswith("inconsistent")


# ---------------------------------------------------------------- full check with structures
def _table(path, rows):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(["id", "description", "hetero", "smiles"])
    for r in rows:
        ws.append(r)
    wb.save(path)

def test_check_descriptions_with_structures(tmp_path):
    good = "1H NMR (400 MHz, CDCl3) δ 4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (t, J = 7.1 Hz, 3H)."
    bad = "1H NMR (400 MHz, CDCl3) δ 4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (t, J = 7.1 Hz, 4H)."
    inp, out = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    _table(inp, [["good", good, "", "CCOC(C)=O"], ["bad", bad, "", "CCOC(C)=O"]])
    p = subprocess.run([PY, os.path.join(ROOT, "check_descriptions", "check_descriptions.py"), str(inp),
                        "-o", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    ws = openpyxl.load_workbook(out)["checked"]
    head = [str(c.value).split("\n")[0] for c in ws[1]]
    rows = {r[0]: dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)}
    assert rows["good"]["item 1"] == "consistent"
    assert rows["bad"]["item 1"].startswith("inconsistent")


# ---------------------------------------------------------------- extraction from a PDF
DEMO = """General procedure. All reactions were carried out under argon.
Ethyl acetate (1a)
Colorless liquid. 1H NMR (400 MHz, CDCl3) δ 4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (t, J = 7.1 Hz, 3H).
13C NMR (101 MHz, CDCl3) δ 171.1, 60.4, 21.0, 14.2. HRMS (ESI) m/z: [M + H]+ calcd for C4H9O2 89.0597; found 89.0598.
Methyl benzoate (1b)
Colorless oil. 1H NMR (400 MHz, CDCl3): 8.04 (d, J = 7.6 Hz, 2H), 7.55 (t, J = 7.4 Hz, 1H), 7.43 (t, J = 7.6 Hz, 2H), 3.91 (s, 3H).
13C NMR (101 MHz, CDCl3) δ 167.1, 132.9, 130.2, 129.6, 128.4, 52.1. HRMS (ESI) m/z: [M + H]+ calcd for C8H9O2 137.0597; found 137.0596.
"""

def _demo_pdf(path):
    import pymupdf
    doc = pymupdf.open(); page = doc.new_page()
    html = "".join(f"<p>{line}</p>" for line in DEMO.strip().split("\n"))
    page.insert_htmlbox(pymupdf.Rect(50, 60, 550, 800), html, css="* {font-size: 9px;}")   # keeps δ
    doc.save(path)

def test_extract_names_and_count_on_pdf(tmp_path):
    pdf = tmp_path / "demo_SI.pdf"
    _demo_pdf(str(pdf))
    rows, n13, nhr = cnt.analyse(str(pdf))
    assert [r["label"] for r in rows] == ["1a", "1b"]          # the second one has no delta
    assert rows[0]["file"] == "demo_SI.pdf"
    out = tmp_path / "compounds.xlsx"
    p = subprocess.run([PY, os.path.join(ROOT, "extract_names", "extract_names.py"), str(pdf), "-o", str(out)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    ws = openpyxl.load_workbook(out).active
    head = [c.value for c in ws[1]]
    got = [dict(zip(head, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    assert [g["name"] for g in got] == ["Ethyl acetate", "Methyl benzoate"]
    assert [g["formula"] for g in got] == ["C4H8O2", "C8H8O2"]


# ---------------------------------------------------------------- command-line interface
@pytest.mark.parametrize("script", ["extract_names/extract_names.py", "names_to_smiles/names_to_smiles.py",
                                    "check_descriptions/check_descriptions.py",
                                    "count_1H_descriptions/count_1H_descriptions.py"])
def test_help(script):
    p = subprocess.run([PY, os.path.join(ROOT, script), "--help"], capture_output=True, text=True)
    assert p.returncode == 0 and "usage" in p.stdout.lower()


# ---------------------------------------------------------------- rename_SI
def test_rename_si(tmp_path):
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    for name, size in [("ol6c00980_si_001.pdf", 100), ("Pages from ol6c00980_si_001.pdf", 30),
                       ("ol6c01297_si_001.pdf", 50), ("ol6c01297_si_002.pdf", 60), ("ol6c00980.pdf", 500)]:
        (src / name).write_bytes(b"x" * size)
    sample = tmp_path / "sample.csv"
    with open(sample, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["order", "doi", "file_key"])
        w.writerow([1, "10.1021/acs.orglett.6c00980", r"ol6c00980_si_\d{3}"])
        w.writerow([3, "10.1021/acs.orglett.6c01297", r"ol6c01297_si_\d{3}"])
    p = subprocess.run([PY, os.path.join(ROOT, "rename_SI", "rename_SI.py"), str(src), str(dst), "--sample", str(sample)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert sorted(os.listdir(dst)) == ["SI001.pdf", "SI003_1.pdf", "SI003_2.pdf"]
    assert (dst / "SI001.pdf").stat().st_size == 100            # the full file, not the "Pages from" copy


# ---------------------------------------------------------------- Google Colab cell
def test_count_runs_in_a_notebook_cell(tmp_path, monkeypatch):
    """In a Jupyter/Colab cell sys.argv holds the kernel's arguments ("-f kernel.json");
    the script must ignore them (pasting the script into a Colab cell is a documented way to run it)."""
    import runpy, types
    monkeypatch.setitem(sys.modules, "ipykernel", types.ModuleType("ipykernel"))
    google = types.ModuleType("google"); colab = types.ModuleType("google.colab")
    files = types.ModuleType("google.colab.files")
    pdf = tmp_path / "demo_SI.pdf"
    _demo_pdf(str(pdf))
    files.upload = lambda: {str(pdf): b""}
    colab.files = files; google.colab = colab
    for name, mod in (("google", google), ("google.colab", colab), ("google.colab.files", files)):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(sys, "argv", ["colab_kernel_launcher.py", "-f", "/root/kernel-1.json"])
    monkeypatch.chdir(tmp_path)
    runpy.run_path(os.path.join(ROOT, "count_1H_descriptions", "count_1H_descriptions.py"), run_name="__main__")
    assert (tmp_path / "1H_descriptions.xlsx").exists()


def test_run_all_labels_with_prime_on_windows_code_page(tmp_path, monkeypatch):
    """On Windows a script printing into a pipe uses the local code page (cp1251), which cannot
    encode a label such as 3k′; run_all must make the scripts write UTF-8 (found 18.10.2026)."""
    import importlib.util
    monkeypatch.setenv("PYTHONIOENCODING", "cp1251")      # what a Russian Windows gives a pipe
    script = tmp_path / "prints_prime.py"
    script.write_text('print("  42/69  OK  ol5c04456_3k\\u2032")\n', encoding="utf-8")
    bare = subprocess.run([sys.executable, str(script)], capture_output=True)
    assert bare.returncode != 0                           # the failure seen in the 200-SI run
    spec = importlib.util.spec_from_file_location("run_all", os.path.join(ROOT, "run_all.py"))
    ra = importlib.util.module_from_spec(spec); spec.loader.exec_module(ra)
    log = tmp_path / "log.txt"
    with open(log, "w", encoding="utf-8") as fh:
        assert ra.step(str(script), [], fh)
    assert "3k′" in log.read_text(encoding="utf-8")
