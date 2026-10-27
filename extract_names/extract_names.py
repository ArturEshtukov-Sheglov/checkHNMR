"""Compound labels, names and HRMS formulas for every 1H NMR description in SI PDF files.

For each description found by count_1H_descriptions.py: the compound label and name, the neutral
formula from the HRMS ion, the description itself and the 19F/31P descriptions after it.
The output table is the input of names_to_smiles.py and check_descriptions.py.
Name forms recognised, test results and limitations: README_extract_names.txt in this folder.

    python extract_names.py SI_1.pdf [SI_2.pdf ...] [-o compounds.xlsx]

Author: Artur V. Eshtukov-Shcheglov. Code written with the assistance of Claude Opus 5.5
(Anthropic); reviewed and tested by the author. Version 1.1 (October 2026).
"""

import os
import re
import sys
import warnings

# count_1H_descriptions.py is looked for in this folder, then in the sibling
# folder ../count_1H_descriptions/ (layout of the GitHub repository)
_here = os.path.dirname(os.path.abspath(__file__))
_dirs = (_here, os.path.join(_here, "..", "count_1H_descriptions"))
for _d in _dirs:
    if os.path.isfile(os.path.join(_d, "count_1H_descriptions.py")):
        sys.path.insert(0, os.path.abspath(_d))
        break
else:
    sys.exit("count_1H_descriptions.py not found. Looked in:\n  "
             + "\n  ".join(os.path.abspath(d) for d in _dirs)
             + "\nPut it in the same folder as extract_names.py or in the folder ../count_1H_descriptions/")

from count_1H_descriptions import (pdf_text, is_description_header, H1, KNOWN, DESC_END, DESC_END_SKIP,
                                   KNOWN_WINDOW_BEFORE, KNOWN_WINDOW_AFTER, MAX_DESCRIPTION)
from name_patterns import (is_label_range, NOT_LABEL_BEFORE, DATA_BY_REFERENCE, LABEL_PAREN, LABEL_COLON, LABEL_CPD, LABEL_DOT, LABEL_BARE, AFFORD_LABEL,
                           CALCD_MASS, FOUND, HEADING, HETERO_DESC)
from compound_names import name_before, name_after, ok_name
from hrms_formula import neutral_formula

warnings.filterwarnings("ignore", message=".*mkl-service.*")
try:
    import openpyxl
except ImportError:
    sys.exit("The package openpyxl is missing. Install the packages with:\n    python -m pip install -r requirements.txt\n(or: python -m pip install pymupdf openpyxl rdkit)")


# ===== Constants =====

ENTRY_WINDOW = 4000              # characters before a 1H header searched for the label and name
CALCD_WINDOW = 60                # characters before a label checked for "Calcd for C13H13BrF6"
MAX_NAME_LENGTH = 300            # longer names are cut to their last 300 characters

OUTPUT_COLUMNS = ["id", "name", "formula", "description", "hetero", "file", "index", "label",
                  "ion_formula", "ion", "flags", "note"]
COLUMN_WIDTHS = (22, 60, 18, 80, 40, 24, 7, 8, 24, 12, 16, 30)


# ===== Analysis =====

IR_BEFORE = re.compile(r"\bIR\b|\bFT-?IR\b|cm\s?[-−–]\s?1|cm\^\{[-−–]1\}|ν\s?max", re.I)
IR_WINDOW = 400          # characters before a bracketed number searched for an IR block


def label_candidates(region):
    """Labels in the text before a description, as (start, end, label), in text order."""
    cands = [(m.start(), m.end(), m.group(1)) for m in LABEL_PAREN.finditer(region)]
    cands += [(m.start(), m.end(), m.group(1)) for m in LABEL_COLON.finditer(region)]
    cands += [(m.start(1), m.end(), m.group(1)) for m in LABEL_CPD.finditer(region)]
    if not cands:      # "3an. Name. Yellow oil." only if no other label form is present
        cands = [(m.start(), m.end(), m.group(1)) for m in LABEL_DOT.finditer(region)]
    if not cands:      # "Name 25 The compound was obtained ..."
        cands = [(m.start(), m.end(), m.group(1)) for m in LABEL_BARE.finditer(region)]

    # not a label: the molar mass in "Calcd for C13H13BrF6 (362.01): C 43.00 ..." (elemental analysis)
    cands = [c for c in cands if not CALCD_MASS.search(region[max(0, c[0] - CALCD_WINDOW): c[0]])]
    # v2: not a label: an IR band in brackets, "aromatic C-H (805)" after "IR (...)" / "cm-1"
    cands = [c for c in cands if not (re.fullmatch(r"\d{3,4}", c[2])
                                      and IR_BEFORE.search(region[max(0, c[0] - IR_WINDOW): c[0]]))]
    # v2: not a label: "Trial 1:", "STEP 2:", "Entry 3"
    cands = [c for c in cands if not NOT_LABEL_BEFORE.search(region[max(0, c[0] - 15): c[0]])]
    cands = [c for c in cands if not is_label_range(c[2])]     # v2: "(4a-h)" is a range
    cands.sort()
    return cands


def label_and_name(region, before_style=False):
    """(label, name, note) of the entry whose 1H description follows the text region."""
    cands = label_candidates(region)
    # v2.1: in a file with the HRMS before the 1H description the region starts at the previous description
    # and may hold labels of the procedure; an explicit "Compound 7:" heading nearest to the header wins
    cpd = list(LABEL_CPD.finditer(region)) if before_style else []
    if cpd:
        c = cpd[-1]
        name = name_after(region[c.end():])
        return c.group(1), (name if ok_name(name) else ""), ("" if ok_name(name) else "no compound name in the SI text (label only?)")
    label, name, note = "", "", ""
    if cands:
        # the entry heading is the FIRST label after the previous entry's data
        ls, le, label = cands[0]
        # v2: several compounds in one entry ("STEP 2: synthesis of X (1s-b) ... from 1s-a ... to afford
        # 1s-b as"): the label of the product that the procedure affords is the described one
        a = AFFORD_LABEL.search(region)
        if a and len(cands) > 1:
            same = [c for c in cands if c[2] == a.group(1)]
            if same:
                ls, le, label = same[0]
        name = name_before(region[:ls])
        if not ok_name(name):
            alt = name_after(region[le:])
            name = alt if ok_name(alt) else ""
    else:
        # no label in the heading: "Name According to GP ... afforded 3h as ..."
        name = name_after(region)
        if not ok_name(name):
            name = ""
        a = AFFORD_LABEL.search(region)
        if a:
            label = a.group(1)
        else:
            note = "label not found"

    if not name:
        note = "; ".join(x for x in (note, "no compound name in the SI text (label only?)") if x)
    elif HEADING.search(name):
        note = "name may start with a section heading - check"
    elif len(name) > MAX_NAME_LENGTH:
        name, note = name[-MAX_NAME_LENGTH:], "name may be too long - check"
    return label, name, note


# v2: a description of one isomer of a mixture, written right after "Major isomer.", "Minor isomer.",
# "2nd isomer.", "1st (major) isomer:" etc. The phrase belongs to the description (it says that the
# compound is a mixture); a non-major isomer gets the label of the compound it belongs to.
ISOMER_BEFORE = re.compile(
    r"\b((?:major|minor|second|third|other|\d\s?(?:st|nd|rd|th))(?:\s?\((?:major|minor)\))?"
    r"\s?(?:isomer|diastereomer|diastereoisomer|rotamer|regioisomer)s?)\s?[.:]?\s?$", re.I)
ISOMER_WINDOW = 50       # characters before the 1H header searched for the isomer phrase


# v2.1: some SI give the HRMS of a compound BEFORE its 1H description ("HRMS ...; IR ...; 1H NMR ...").
# The style is decided for the whole file from the data: the HRMS formulas are attached to the descriptions
# both ways (after each header / before it), and the way in which more descriptions have as many H in their
# integrals as in the formula wins. "Before" is taken only when it is clearly better.
INTEGRAL = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d)?)\s?H(?![a-z])")
FORMULA_H = re.compile(r"H(\d*)(?![a-z])")
HRMS_BEFORE_MIN_GAIN = 2         # "before" must give at least this many more agreeing descriptions ...
HRMS_BEFORE_SHARE = 2 / 3        # ... and agree for at least this share of the descriptions with a formula


def description_end(S, h, nxt):
    e = DESC_END.search(S, h + DESC_END_SKIP)
    return e.start() if e and e.start() < nxt and e.start() - h < MAX_DESCRIPTION else min(nxt, h + MAX_DESCRIPTION)


def h_agrees(desc, formula):
    if not formula:
        return None
    m = FORMULA_H.search(formula)
    nf = int(m.group(1) or 1) if m else 0
    return abs(sum(float(x) for x in INTEGRAL.findall(desc)) - nf) <= 1    # one exchangeable H may be missing


def hrms_before_style(S, heads, ends):
    after = before = n_before = 0
    for k, h in enumerate(heads):
        nxt = heads[k + 1] if k + 1 < len(heads) else len(S)
        desc = S[h + DESC_END_SKIP:ends[k]]             # without the header "1H NMR"
        fa = neutral_formula(S[h:nxt])[0]
        fb = neutral_formula(S[(ends[k - 1] if k else max(0, h - ENTRY_WINDOW)):h])[0]
        after += bool(h_agrees(desc, fa))
        before += bool(h_agrees(desc, fb))
        n_before += bool(fb)
    return before >= after + HRMS_BEFORE_MIN_GAIN and before >= HRMS_BEFORE_SHARE * max(n_before, 1)


def analyse(path):
    """One row per 1H description of the SI file."""
    S = pdf_text(path)
    heads = [m.start() for m in H1.finditer(S) if is_description_header(S, m.start())]
    ends = [description_end(S, h, heads[k + 1] if k + 1 < len(heads) else len(S)) for k, h in enumerate(heads)]
    before_style = hrms_before_style(S, heads, ends)
    rows, seen = [], {}
    prev_end = 0
    base = None
    for k, h in enumerate(heads):
        nxt = heads[k + 1] if k + 1 < len(heads) else len(S)

        # the entry of this description starts after the HRMS "found" value of the previous one
        region_start = max(prev_end, h - ENTRY_WINDOW)
        if before_style:                             # v2.1: the entry starts after the previous description
            region_start = max(ends[k - 1] if k else 0, h - ENTRY_WINDOW)
        f_prev = list(FOUND.finditer(S, region_start, h))
        if f_prev and not before_style:
            region_start = f_prev[-1].end()
        # v2: compounds characterised only by a reference ("data matches literature") end before this entry
        refs = list(DATA_BY_REFERENCE.finditer(S, region_start, h))
        if refs and label_candidates(S[refs[-1].end(): h]):     # only if the entry's own label follows
            region_start = refs[-1].end()
        label, name, note = label_and_name(S[region_start: h], before_style)
        iso = ISOMER_BEFORE.search(S[max(0, h - ISOMER_WINDOW): h])
        iso_start = h - ISOMER_WINDOW + iso.start(1) if iso and h >= ISOMER_WINDOW else h
        iso_minor = bool(iso) and not re.match(r"(?:major|1\s?st)\b", iso.group(1), re.I) \
            and "(major)" not in iso.group(1).lower()

        # HRMS of this compound: between this header and the next one, or (v2.1) in a file that gives the
        # HRMS before the 1H description: between the end of the previous description and this header
        if before_style:
            neutral, ion_f, ion, n2 = neutral_formula(S[(ends[k - 1] if k else max(0, h - ENTRY_WINDOW)): h])
        else:
            neutral, ion_f, ion, n2 = neutral_formula(S[h: nxt])

        flags = []
        if iso_minor and base is not None:          # v2: another isomer of the previous compound
            b = rows[base]
            tag = re.sub(r"\s|\(.*?\)|isomers?|diastereo|rotamer|regio", "", iso.group(1), flags=re.I).lower()
            label = (b["label"] or str(b["index"])) + "-" + (tag or "iso")
            name = b["name"]
            if b["formula"]:                         # one compound: one formula
                neutral, ion_f, ion = b["formula"], b["ion_formula"], b["ion"]
            elif neutral:                            # HRMS follows the last isomer: give it to all
                for r in rows[base:]:
                    r["formula"], r["ion_formula"], r["ion"] = neutral, ion_f, ion
            note = ""
            flags.append("ISOMER of #%d" % b["index"])
        if KNOWN.search(S[max(0, h - KNOWN_WINDOW_BEFORE): h + KNOWN_WINDOW_AFTER]):
            flags.append("KNOWN?")
        if label and not name and label in seen and rows[seen[label] - 1]["name"]:
            name, note = rows[seen[label] - 1]["name"], "name taken from the first description of this label"
        if label:
            if label in seen:
                flags.append("REPEAT of #%d" % seen[label])
            else:
                seen[label] = k + 1
        prev_end = h
        if not iso_minor:
            base = k                                # v2: the last entry that is not a minor isomer

        e = DESC_END.search(S, h + DESC_END_SKIP)
        d_end = e.start() if e and e.start() < nxt and e.start() - h < MAX_DESCRIPTION else min(nxt, h + MAX_DESCRIPTION)
        rows.append(dict(file=path.replace("\\", "/").split("/")[-1], index=k + 1, label=label,
                         name=name, formula=neutral, ion_formula=ion_f, ion=ion,
                         description=S[iso_start if iso else h:d_end].strip(),   # v2: with the isomer phrase
                         hetero=" ".join(m.group(0) for m in HETERO_DESC.finditer(S[d_end:nxt])),
                         flags="; ".join(flags), note="; ".join(x for x in (note, n2) if x)))
    return rows


# ===== Output =====

def output_name(name):
    """The output file name given with -o; '.xlsx' is added if missing."""
    return name if name.lower().endswith(".xlsx") else name + ".xlsx"


def save_table(rows, out):
    """One row per description; the id is '<SI file name>_<label or number>'."""
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "compounds"
    ws.append(OUTPUT_COLUMNS)
    for r in rows:
        stem = re.sub(r"(_si_\d+)?\.pdf$", "", r["file"], flags=re.I)
        r["id"] = f"{stem}_{r['label'] or r['index']}"
        # control characters from the PDF text are not allowed in Excel cells
        ws.append([ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v
                   for v in (r[c] for c in OUTPUT_COLUMNS)])
    for col, w in zip("ABCDEFGHIJKL", COLUMN_WIDTHS):
        ws.column_dimensions[col].width = w

    try:
        wb.save(out)
    except PermissionError:
        sys.exit(f"Close {out} in Excel and run again.")
    print(f"\nSaved: {out} (check the 'note' column; delete rows you do not need)")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="For every text 1H NMR description in SI PDF files: compound "
                                 "label and name, neutral formula from HRMS, the description and the 19F/31P "
                                 "descriptions. One row per description in an Excel table.")
    ap.add_argument("pdf", nargs="+", help="SI file(s) in PDF format")
    ap.add_argument("-o", dest="out", default="compounds.xlsx", help="output table (default: compounds.xlsx)")
    a = ap.parse_args()

    rows = []
    for f in a.pdf:
        r = analyse(f)
        rows += r
        print(f"{f.split('/')[-1]}: {len(r)} descriptions, names found {sum(1 for x in r if x['name'])}, "
              f"formulas found {sum(1 for x in r if x['formula'])}")
    save_table(rows, output_name(a.out))


if __name__ == "__main__":
    main()
