"""Cutting a compound name out of the SI text before or after its label. Used by extract_names.py."""

import re

from name_patterns import (LAB, NAME_JUNK, JUNK_CUT, DRAWING, SEG, AFTER_NAME, PROSE, CHEM_WORD,
                           NAME_START, NOT_NAME, PROSE_IN_NAME, NAME_LIKE)


# ===== Constants =====

NAME_TEXT_WINDOW = 500           # characters before a label in which its name is looked for
NAME_AFTER_WINDOW = 400          # characters after a label in which a name written after it is looked for
MIN_NAME_LENGTH = 4              # shorter text is not taken as a name
MIN_ALT_NAME_LENGTH = 8          # a name found after a closing bracket must be at least this long
MIN_REST_AFTER_NUMBER = 6        # a leading number is cut only if at least this much text follows
MIN_REST_AFTER_DRAWING = 4       # atom labels of a drawing are cut only if at least this much text follows
TIDY_PASSES = 3                  # stray text is removed in up to three passes

# "dipropyl- sulfamoyl", "1,2- dicarba": a line break after a hyphen inside a name
HYPHEN_BREAK = r"(?<=[A-Za-z0-9\)\]][-–])\s+(?=[a-z\d\(\[{])"
# CAS number after the name: "[1234-56-7]"
CAS_NUMBER = r"\s*\[\d{2,7}-\d{2}-\d\]$"
# a number (or percentage) standing alone before the name: "12 ", "85% "
LEADING_NUMBER = r"(?:^|\s)[\d.,%]+[a-z]?(?=\s)"
# a closing bracket followed by text: "(petroleum ether : ethyl acetate = 20:1) Phenyl ..."
AFTER_BRACKET = r"\)\s+(?=\S)"


def clean_name(s):
    """Rejoin hyphens broken at a line end, drop a CAS number and words such as "Synthesis of"."""
    s = re.sub(HYPHEN_BREAK, "", s)
    s = re.sub(CAS_NUMBER, "", s.strip())
    s = NAME_JUNK.sub("", s.strip(" .:;,•·"))
    return s


def drop_heading(name):
    """'Study on byproducts 1-(isoquinolin-1-yl)naphthalen-2-ol' -> '1-(isoquinolin-1-yl)naphthalen-2-ol'"""
    t = name.split(" ")
    for j, w in enumerate(t):
        if NAME_START.match(w):
            if j and all(PROSE.match(x) and not CHEM_WORD.match(x) for x in t[:j]):
                return " ".join(t[j:])
            return name
        if not PROSE.match(w) or CHEM_WORD.match(w):
            return name
    return name


def unwrap(name):
    """'(1-(tetrahydrofuran-2-yl)-1H-indazole)' -> without the outer brackets; 'name, 1g' -> 'name'"""
    name = re.sub(r"\^\{([^{}]*)\}", r"\1", name)                    # N^{4} -> N4 (superscript in the PDF)
    name = re.sub(r",\s*" + LAB + r"$", "", name)                    # label after the name: ", 1g"
    name = re.sub(r"\s\([^()\s]{1,12}(?:\s\S{1,6})?\)$|\s?\([^()]{1,15}$", "", name)  # "(rac-13)", unclosed "(12"
    name = re.sub(r"^(?:\((?:minor|major|SI)\)\s|\d{1,3}\)\s)", "", name)          # "(major) ", "3) "
    name = re.sub(r"^[^()]{0,30}\)\s+(?=\S)", "", name)   # v2: unbalanced start "main text) ", "[2]) "

    if name.startswith("(") and name.endswith(")"):
        depth = 0
        for i, c in enumerate(name):
            depth += c == "("
            depth -= c == ")"
            if depth == 0:
                return name[1:-1] if i == len(name) - 1 else name
    return name


def tidy(name):
    """Remove stray text at the start of a name candidate; '' if it does not look like a name."""
    name = unwrap(clean_name(name))
    for _ in range(TIDY_PASSES):
        cut = [m.end() for m in JUNK_CUT.finditer(name)]
        if cut:
            name = clean_name(name[cut[-1]:])

        nums = [m.end() for m in re.finditer(LEADING_NUMBER, name)]
        if nums and len(name) - nums[-1] >= MIN_REST_AFTER_NUMBER:
            name = clean_name(name[nums[-1]:])

        d = DRAWING.match(name)
        if d and len(name) - d.end() >= MIN_REST_AFTER_DRAWING:
            name = clean_name(name[d.end():])
    return drop_heading(name)


def ok_name(name):
    """The candidate looks like a compound name."""
    return (bool(name) and len(name) >= MIN_NAME_LENGTH and not NOT_NAME.search(name)
            and not PROSE_IN_NAME.search(name) and bool(NAME_LIKE.search(name)))


def name_before(before):
    """The name right before a label: the last segment of the text before it."""
    segs = SEG.split(before[-NAME_TEXT_WINDOW:])
    name = tidy(segs[-1]) if segs else ""
    if segs and not ok_name(name):
        # stray text such as "(petroleum ether : ethyl acetate = 20:1) Phenyl ...": the longest
        # part after a closing bracket that looks like a name
        seg = segs[-1]
        for m in re.finditer(AFTER_BRACKET, seg):
            alt = tidy(seg[m.end():])
            if len(alt) >= MIN_ALT_NAME_LENGTH and ok_name(alt):
                return alt
    return name


def name_after(after):
    """A name written after the label ("Product 4e: Name Prepared ...", "3an. Name. Yellow oil.")."""
    a = after[:NAME_AFTER_WINDOW]
    m = re.match(r"\s*[:.]?\s*", a)
    a = a[m.end():]
    seg = SEG.split(a)[0]

    lab = re.search(r"\s[\(\[]\s*" + LAB + r"\s*[\)\]](?=\s|$)", seg)   # another label in brackets
    if lab:
        seg = seg[:lab.start()]
    e = AFTER_NAME.search(" " + seg)
    if e:
        seg = seg[:max(0, e.start() - 1)]
    return tidy(seg)
