"""Checks of 1H NMR descriptions against the pass-3 protocol (v1.2), from the text of the
description and, where available, the structure (SMILES).

Items checked: 1 (proton count; needs a SMILES or a molecular formula), 3 (coupling partners),
4(a) (number of J), 6(a) (magnetic non-equivalence; needs a SMILES) and 6(b) (strong coupling).
A screening aid: every finding must be checked by a person. What each item means, test results,
output columns and limitations: README_check_descriptions.txt in this folder.

    python check_descriptions.py smiles.xlsx [-o checked.xlsx]
    python check_descriptions.py SI_1.pdf [SI_2.pdf ...] [-o checked.xlsx]   (text only)

The code is split into: description_parser.py (reading a description into signals),
text_checks.py (items 3, 4(a), 6(b)), structure_checks.py (items 1, 6(a); RDKit),
verdicts.py (verdict words, conclusion), excel_output.py (the output table).

Author: Artur V. Eshtukov-Shcheglov. Code written with the assistance of Claude Opus 5.5
(Anthropic); reviewed and tested by the author. Version 1.1 (October 2026).
"""

import os
import re
import sys
import warnings

warnings.filterwarnings("ignore", message=".*mkl-service.*")
try:
    import openpyxl
except ImportError:
    sys.exit("The package openpyxl is missing. Install the packages with:\n    python -m pip install -r requirements.txt\n(or: python -m pip install pymupdf openpyxl rdkit)")

# the parts of the script are in this folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from description_parser import parse_mult, expected_j  # noqa: E402
from text_checks import check, verdict_6b  # noqa: E402
from item4b import check_item4b                                     # v2
from read_quality import reading_quality  # noqa: E402
from structure_checks import (Chem, RDKIT_PROBLEM, check_item1, check_item1_formula, check_item6a,  # noqa: E402
                              aromatic_hx_possible, h_counts)
from verdicts import conclusion, combine_item6  # noqa: E402
from excel_output import write_table  # noqa: E402


# functions used by the tests and by other scripts
__all__ = ["parse_mult", "expected_j", "check", "run", "from_table", "from_pdfs"]


# ===== Constants =====

DEFAULT_OUT = "checked.xlsx"
LABEL_WINDOW = 700               # PDF input: characters before a header searched for the compound label
MAX_DESCRIPTION = 4000           # PDF input: longest description kept
DESC_END_SKIP = 8                # the header itself is not a data-block end
ID_COLUMNS = 4                   # table without an "id" column: the id is made of the first columns
FORMULA = r"(?:[A-Z][a-z]?\d*)+"  # a molecular formula: C12H5ClF3NO
STAT_ITEMS = ("item1", "item3", "item4a", "item4b", "item6", "item6a", "item6b")


# ===== Input =====

def from_pdfs(paths):
    """Descriptions read directly from SI PDF files (without structures)."""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (here, os.path.join(here, "..", "count_1H_descriptions")):
        if os.path.isfile(os.path.join(d, "count_1H_descriptions.py")):
            sys.path.insert(0, os.path.abspath(d))
            break
    else:
        sys.exit("For PDF input count_1H_descriptions.py is needed (same folder or ../count_1H_descriptions/).")
    from count_1H_descriptions import pdf_text, is_description_header, H1, LABEL, DESC_END

    rows = []
    for p in paths:
        S = pdf_text(p)
        heads = [m.start() for m in H1.finditer(S) if is_description_header(S, m.start())]
        for k, h in enumerate(heads):
            nxt = heads[k + 1] if k + 1 < len(heads) else len(S)
            e = DESC_END.search(S, h + DESC_END_SKIP)
            end = e.start() if e and e.start() < nxt else min(nxt, h + MAX_DESCRIPTION)
            labs = list(LABEL.finditer(S[max(0, h - LABEL_WINDOW): h]))
            label = (labs[-1].group(1) or labs[-1].group(2)) if labs else ""
            stem = re.sub(r"(_si_\d+)?\.pdf$", "", os.path.basename(p), flags=re.I)
            rows.append(dict(id=f"{stem}_{label or k + 1}", description=S[h:end].strip(), hetero=S[end:nxt]))
    return rows


def from_table(path):
    """Descriptions from the table of names_to_smiles.py or extract_names.py (or any table with a
    column whose header contains 'description'; optional columns id, hetero/19F, smiles, formula)."""
    ws = openpyxl.load_workbook(path, read_only=True).active
    data = list(ws.iter_rows(values_only=True))
    head = [str(h or "").strip() for h in data[0]]
    low = [h.lower() for h in head]

    dcol = next((i for i, h in enumerate(low) if "1h" in h and "desc" in h), None)
    if dcol is None:
        dcol = next((i for i, h in enumerate(low) if "description" in h), None)
    if dcol is None:
        sys.exit("No description column found (header must contain 'description').")
    icol = next((i for i, h in enumerate(low) if h == "id"), None)
    hcol = next((i for i, h in enumerate(low) if "hetero" in h or "19f" in h), None)
    scol = next((i for i, h in enumerate(low) if h == "smiles"), None)
    fcol = next((i for i, h in enumerate(low) if h == "formula"), None)
    ocol = next((i for i, h in enumerate(low) if h == "opsin_status"), None)      # v2.1

    rows = []
    for k, r in enumerate(data[1:], 1):
        if not r[dcol]:
            continue
        rid = r[icol] if icol is not None else "_".join(str(r[i]) for i in range(min(dcol, ID_COLUMNS)) if r[i] is not None) or k
        rows.append(dict(id=str(rid), description=str(r[dcol]), hetero=str(r[hcol] or "") if hcol is not None else "",
                         smiles=str(r[scol] or "").strip() if scol is not None else "",
                         formula=str(r[fcol] or "").strip() if fcol is not None else "",
                         opsin_status=str(r[ocol] or "").strip() if ocol is not None else ""))
    return rows


def output_name(name):
    """The output file name given with -o; '.xlsx' is added if missing."""
    return name if name.lower().endswith(".xlsx") else name + ".xlsx"


# ===== Checking one description =====

def text_result(r, arom_hx_possible=True, x_in_structure=None):
    """Text checks of row r, with the structure columns not yet filled."""
    res = check(r["description"], r.get("hetero", ""), arom_hx_possible=arom_hx_possible,
                x_in_structure=x_in_structure)
    res.update(id=r["id"], description=r["description"], smiles=r.get("smiles", ""),
               H_reported=None, H_structure=None, item1="no structure", item6a="no structure",
               findings1="", findings6a="", item4b="no structure", findings4b="")
    return res


def item3_in6(res, nfo, mol):
    """Whether the item-3 inconsistencies lie only in signals already not first-order under item 6."""
    bad6 = set(nfo) if mol is not None else set()
    for pr in res["_pairs"]:
        if pr["status"] == "INCONSISTENT":
            bad6 |= {pr["i"], pr["j"]}
    if not res["_inc3"]:
        return ""
    if res["_inc3"] <= bad6:
        return "yes (all in non-first-order signals)"
    return "partly" if res["_inc3"] & bad6 else "no"


# v2: heteronuclei that can give a large coupling to 1H (19F, 31P, and B, Si, Se, Sn, Te, Pt, Rh, Hg, ...)
SPIN_X = {"F", "P", "B", "Si", "Se", "Sn", "Te", "Pt", "Rh", "Hg", "Tl", "Cd", "Pb", "W", "Ag", "Y", "Li"}


def element_count(formula, el):
    m = re.search(el + r"(\d*)(?![a-z])", formula or "")
    return int(m.group(1) or 1) if m else 0


def name_structure_guard(mol, r):
    """v2.1: a structure made from the name by OPSIN whose formula differs from the HRMS formula
    (names_to_smiles marks it 'FORMULA MISMATCH'). Two cases are acted on, all others (salts, ions, typos in
    the HRMS) are kept: the name gives several structures, each with the C count of the formula (isomers named
    together: which one is described is unknown); the structure has fewer C than the HRMS formula (the name of another compound, e.g. a reagent
    taken from the procedure) -> the structure is not used and item 1 is checked against the formula.
    Structures typed by a person (status GIVEN) are never changed."""
    st = r.get("opsin_status", "")
    formula = r.get("formula", "")
    if mol is None or not st.startswith("OK") or "FORMULA MISMATCH" not in st or not re.fullmatch(FORMULA, formula):
        return mol, ""
    frags = Chem.GetMolFrags(mol, asMols=True)
    if len(frags) > 1 and all(sum(a.GetSymbol() == "C" for a in f.GetAtoms()) == element_count(formula, "C")
                              for f in frags):
        return None, ("the name gives %d structures, each with the C of the HRMS formula (isomers named together?): "
                      "structure not used, item 1 checked against the formula" % len(frags))
    if sum(a.GetSymbol() == "C" for a in mol.GetAtoms()) < element_count(formula, "C"):
        return None, ("structure from the name has fewer C than the HRMS formula (name of another compound?): "
                      "structure not used, item 1 checked against the formula")
    return mol, ""


TINY_FACTOR = 3        # reported H at least 3 times the H of the structure ...
TINY_EXCESS = 10       # ... and at least 10 H more: the structure cannot be of the described compound
TINY_ATOMS = 8         # only for a small structure (a class word or a fragment of the name); not for mixtures,
#                        whose integrals may be scaled to the minor component


def tiny_structure_guard(mol, r, res):
    """v2.1: a structure from the name far smaller than the description (the name is a class word such as
    "Carbamate" taken as the compound name: OPSIN gives the carbamate ion, CH2NO2-, for a 33 H description).
    The structure is not used; structures typed by a person (status GIVEN) are kept."""
    st = r.get("opsin_status", "")
    if mol is None or not st.startswith("OK") or res["_mixture"] or mol.GetNumHeavyAtoms() > TINY_ATOMS:
        return mol, ""
    ints = [x.get("nH") for x in res["_sigs"]]
    if not ints or any(x is None for x in ints):
        return mol, ""
    rep, struct_h = sum(ints), h_counts(Chem.AddHs(mol))[0]
    if rep >= TINY_FACTOR * struct_h and rep - struct_h >= TINY_EXCESS:
        return None, ("structure from the name has %d H for a description of %g H (a class word as the name?): "
                      "structure not used" % (struct_h, rep)) + (", item 1 checked against the formula"
                                                                 if r.get("formula") else "")
    return mol, ""


def check_row(r):
    """All checks of one table row."""
    res = text_result(r)
    mol = Chem.MolFromSmiles(r["smiles"]) if (Chem and r.get("smiles")) else None
    mol, guard = name_structure_guard(mol, r)                                   # v2.1
    if not guard:
        mol, guard = tiny_structure_guard(mol, r, res)                          # v2.1
    if guard:
        r = dict(r, smiles=Chem.MolToSmiles(mol) if mol is not None else "")
    if mol is not None:
        # v2: whether a J above 25 Hz can be explained: F, P or another spin-active heteronucleus in the
        # structure OR in the HRMS formula (the structure from the name may be another compound)
        formula_els = set(re.findall(r"[A-Z][a-z]?", r.get("formula") or ""))
        has_x = any(a.GetSymbol() in SPIN_X for a in mol.GetAtoms()) or bool(formula_els & SPIN_X)
        # no aromatic proton within four bonds of F/P: aromatic constants are not H-X
        res = text_result(r, arom_hx_possible=aromatic_hx_possible(mol), x_in_structure=has_x)
    if r.get("smiles") and Chem and mol is None:
        res["note"] = "; ".join(x for x in (res["note"], "SMILES not read") if x)
    if guard:
        res["note"] = "; ".join(x for x in (res["note"], guard) if x)

    # item 1 against the molecular formula when there is no structure
    formula = r.get("formula") or ""
    if mol is None and re.fullmatch(FORMULA, formula) and "H" in re.findall(r"[A-Z][a-z]?", r["formula"]):
        res["item1"], res["findings1"], res["H_reported"], res["H_structure"] = \
            check_item1_formula(r["description"], res["_sigs"], r["formula"], res["_mixture"])

    nfo = set()
    if mol is not None:
        molH = Chem.AddHs(mol)
        res["item1"], res["findings1"], res["H_reported"], res["H_structure"] = \
            check_item1(r["description"], res["_sigs"], molH, res["_mixture"])
        res["item6a"], res["findings6a"], nfo = check_item6a(res["_sigs"], mol)
        res["item4b"], res["findings4b"] = check_item4b(res["_sigs"], mol, res["_mixture"])   # v2
        if nfo:
            res["item6b"], res["findings6b"] = verdict_6b(res["_pairs"], nfo)
    if isinstance(res.get("H_reported"), float):
        # the sum of integrals is written rounded: 42.1, not 42.09999999999999
        res["H_reported"] = round(res["H_reported"], 6)

    q = reading_quality(r["description"], res["_sigs"])                        # v2.1
    res["reading"], res["reading_notes"] = q["level"], "; ".join(q["notes"])
    res["item6"] = combine_item6(res["item6a"], res["item6b"])
    res["item3_in6"] = item3_in6(res, nfo, mol)
    res["conclusion"], res["_class"] = conclusion(res)
    return res


# ===== Run =====

def print_stats(stats, rows_out):
    for k, v in stats.items():
        if k == "_class":
            continue
        print(f"  {k:7s} " + " | ".join(f"{n}: {c}" for n, c in sorted(v.items(), key=lambda x: -x[1])))
    cl, tot = stats.get("_class", {}), len(rows_out)
    pc = lambda n: f"{n} ({100 * n / tot:.0f} %)" if tot else str(n)
    print(f"  conclusions: inconsistent 1-4 {pc(cl.get('inconsistent 1-4', 0))} | 6 only {pc(cl.get('inconsistent 6 only', 0))}"
          f" | to check {pc(cl.get('to check', 0))} | no finding {pc(cl.get('no finding', 0))}  (screening - human verification required)")


def run(rows, out):
    if RDKIT_PROBLEM and any(r.get("smiles") for r in rows):
        print(RDKIT_PROBLEM + " - items 1 and 6(a) are not checked.")

    rows_out, stats = [], {}
    for r in rows:
        res = check_row(r)
        stats.setdefault("_class", {}).setdefault(res["_class"], 0)
        stats["_class"][res["_class"]] += 1
        for k in STAT_ITEMS:
            stats.setdefault(k, {}).setdefault(res[k], 0)
            stats[k][res[k]] += 1
        rows_out.append(res)

    print(f"{len(rows)} descriptions")
    print_stats(stats, rows_out)
    write_table(rows_out, stats, out)
    print(f"Saved: {out} (sheets " + "'checked' and 'summary'"
          + "; every finding must be checked by hand)")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Check 1H NMR descriptions against the assessment protocol "
                                 "(items 1, 3, 4(a), 6(a), 6(b)). Input: the table made by names_to_smiles.py, "
                                 "or SI PDF files (then only the text items are checked, without structures).")
    ap.add_argument("input", nargs="+", help="one table (.xlsx) or SI file(s) (.pdf)")
    ap.add_argument("-o", dest="out", default=DEFAULT_OUT, help=f"output table (default: {DEFAULT_OUT})")
    a = ap.parse_args()
    args, out = a.input, output_name(a.out)
    rows = from_table(args[0]) if len(args) == 1 and args[0].lower().endswith(".xlsx") else from_pdfs(args)
    run(rows, out)
