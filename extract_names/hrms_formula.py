"""Neutral molecular formula of a compound from its HRMS entry in the SI text.

"HRMS (ESI) m/z calcd for C12H6ClF3NO [M+H]+ 272.0084, found 272.0087" -> C12H5ClF3NO.
The ion formula is accepted only if its monoisotopic mass agrees with the calculated m/z.
Used by extract_names.py.
"""

import re


# ===== Constants =====

MZ_TOLERANCE = 0.02              # Da: the ion formula must reproduce the calculated m/z this well
ION_WINDOW = 60                  # characters before/after "calcd for <formula>" searched for "[M+H]+"
MZ_WINDOW = 120                  # characters after "calcd for <formula>" searched for the m/z value
MAX_FORMULA_VARIANTS = 50        # limit of isotope-splitting variants tried per formula

# Monoisotopic masses of the most abundant isotopes
MASS = {"H": 1.0078250, "D": 2.0141018, "B": 11.0093054, "C": 12.0, "N": 14.0030740, "O": 15.9949146,
        "F": 18.9984032, "Na": 22.9897693, "Si": 27.9769265, "P": 30.9737615, "S": 31.9720707,
        "Cl": 34.9688527, "K": 38.9637069, "Li": 7.0160040, "Br": 78.9183376, "I": 126.9044727,
        "Se": 79.9165218, "Fe": 55.9349421, "Co": 58.9331976, "Ni": 57.9353462, "Cu": 62.9295989,
        "Zn": 63.9291448, "Ge": 73.9211774, "Ru": 101.9043441, "Rh": 102.9054980, "Pd": 105.9034804,
        "Ag": 106.9050916, "Sn": 119.9021966, "Ir": 192.9629216, "Pt": 194.9647917, "Au": 196.9665688}
# Masses of isotopes that SI formulas give explicitly, e.g. ^{10}B, ^{81}Br, ^{13}C
ISO = {("B", 10): 10.0129370, ("B", 11): 11.0093054, ("Br", 79): 78.9183376, ("Br", 81): 80.9162897,
       ("Cl", 35): 34.9688527, ("Cl", 37): 36.9659026, ("C", 13): 13.0033548, ("H", 2): 2.0141018,
       ("N", 15): 15.0001089}
# isotope numbers that can lose their superscript in the PDF text ("H2210B" = H22 + 10B)
SPLITTABLE_ISOTOPES = ("10", "11", "79", "81", "35", "37", "13", "15")
# atoms added to the neutral molecule in an [M+X]+ ion
ADDUCT = {"H": {"H": 1}, "Na": {"Na": 1}, "K": {"K": 1}, "Li": {"Li": 1},
          "Ag": {"Ag": 1}, "NH4": {"N": 1, "H": 4}}
# elements counted when the ion type has to be inferred from the double-bond equivalent
DBE_MINUS = ("H", "D", "F", "Cl", "Br", "I", "Na", "K", "Li")      # monovalent: -1 each
DBE_PLUS = ("N", "P", "B")                                         # trivalent: +1 each
NON_METALS = {"C", "H", "D", "N", "O", "S", "Se", "F", "Cl", "Br", "I", "P", "B", "Si", "Na", "K", "Li"}


# ===== Patterns =====

# "calcd for C12H6ClF3NO", "Calculated for: [C23H29OP+Na]", "calc. for ^{13}CC5H6": group 1 = formula
CALC = re.compile(
    r"(?i:calc(?:ulate)?d?)\.?\s*"              # "calcd", "calc.", "calculated"
    r"(?:for|For|FOR)?\s*:?\s*"                 # optional "for" and ":"
    r"\(?\s*\[?\s*"                             # optional "(" or "[" before the formula
    r"((?:\^\{\d+\})?[A-Z][A-Za-z0-9\^\{\}]*)")  # the formula (capital first letter: v2, not "mass")
# ion type: "[M+H]+", "(M+Na)+", "[M-H]-", "[M]+"; group 1 = sign, group 2 = adduct, group 3 = charge
ION = re.compile(
    r"[\[\(]\s*M\s*"
    r"(?:([+\-−–])\s*(NH4|Na|K|Li|Ag|H))?"     # optional "+H", "+Na", "-H"
    r"\s*[\]\)]\s*(?:\^\{?)?"
    r"([+\-−–])?"                               # charge sign, may be a superscript
)
# adduct inside the bracket of the formula: "[C23H29OP+Na]+" -> sign, adduct
BRACKET_ADDUCT = re.compile(r"^\s*([+\-−–])\s*(NH4|Na|K|Li|Ag|H)\s*\]")
# one element of a formula: optional isotope ^{13}, symbol, count
TOKEN = re.compile(r"(?:\^\{(\d+)\})?([A-Z][a-z]?)(\d*)")
# charge or radical signs at the end of an ion formula
FORMULA_TAIL = r"[+\-−–•·\s]+$"
# digits between two element symbols, e.g. "2210" in "H2210B"
DIGITS_BEFORE_ELEMENT = r"(?<=[A-Za-z])(\d+)(?=[A-Z])"
# the calculated m/z: 2-4 digits, a point, 3-5 decimals
MZ_VALUE = r"(\d{2,4}\.\d{3,5})"


# ===== Formulas =====

def parse_formula(f):
    """'C22H29^{10}B2^{11}B8BrP+' -> ({'C':22,...,'B':10,...}, monoisotopic mass); None if not parsable."""
    f = re.sub(FORMULA_TAIL, "", f)
    if "".join(t.group(0) for t in TOKEN.finditer(f)) != f:
        return None

    counts, mass = {}, 0.0
    for iso, el, n in TOKEN.findall(f):
        n = int(n) if n else 1
        if el not in MASS:
            return None
        counts[el] = counts.get(el, 0) + n
        mass += n * ISO.get((el, int(iso)), MASS[el]) if iso else n * MASS[el]
    return counts, mass


def candidates(f):
    """The formula as written, and variants in which isotope numbers that lost their
    superscript ('H2210B' = H22 + 10B, 'B11B8' = B + 11B8) are separated again."""
    out, todo = [f], [f]
    while todo:
        g = todo.pop()
        for m in re.finditer(DIGITS_BEFORE_ELEMENT, g):
            el = re.match(r"[A-Z][a-z]?", g[m.end():]).group(0)
            d = m.group(1)
            for iso in SPLITTABLE_ISOTOPES:
                if (el, int(iso)) in ISO and len(d) > len(iso) and d.endswith(iso):
                    h = g[:m.start()] + d[:-len(iso)] + "^{" + iso + "}" + g[m.end():]
                    if h not in out and len(out) < MAX_FORMULA_VARIANTS:
                        out.append(h)
                        todo.append(h)
    return out


def hill(c):
    """Formula in Hill order: C, H, then the other elements alphabetically."""
    first = ["C", "H"] if "C" in c else []
    order = first + sorted(k for k in c if k not in first)
    return "".join(k + (str(c[k]) if c[k] != 1 else "") for k in order if c.get(k, 0) > 0)


def neutral_without_ion_type(counts, ion_f):
    """No "[M+H]+" given: the ion type is inferred from the parity of the double-bond equivalent."""
    dbe2 = 2 * counts.get("C", 0) + 2 * counts.get("Si", 0) + 2 \
           - sum(counts.get(x, 0) for x in DBE_MINUS) \
           + sum(counts.get(x, 0) for x in DBE_PLUS)
    if set(counts) - NON_METALS:
        return "", ion_f, "", "ion type not found"
    if dbe2 % 2 == 0:
        return hill(counts), ion_f, "?", "ion type not given - formula taken as neutral (even DBE)"
    el = "Na" if counts.get("Na") else "K" if counts.get("K") else "H"
    if not counts.get(el):                           # v2.1: no H to take away ("C6F5I"): no formula derived
        return "", ion_f, "?", "ion type not given and the formula has no H - molecular formula not derived"
    counts[el] -= 1
    return hill(counts), ion_f, "?", f"ion type not given - assumed [M+{el}]+ (half-integer DBE)"


# v2: the formula before the word: "for [M+H]+ (C15H18NO2+) calculated m/z 244.1332" is read as
# "calculated for C15H18NO2+ m/z 244.1332"
FORMULA_BEFORE_CALC = re.compile(
    r"\(\s*((?:\^\{\d+\})?C\d{0,3}(?:\^\{\d+\})?H\d{0,3}[A-Za-z0-9\^\{\}]*)"   # a formula: C.., H..
    r"\s?[+\-−]?\s*\)\s*((?i:calc(?:ulate)?d?\.?))(?!\s*(?i:for))")


# v2: an ion written as M plus/minus several groups: "[M-N2+H]+", "[M-OTf]+", "[M+H-H2O]+",
# "[M-(H2O)2+H]+", "(M - H2O) + H]+", "[M-H+]-", "[M-Boc+H]+". The molecular formula is the ion formula
# minus the written changes, if every group is a formula or a known group; otherwise it is not derived
# (e.g. "[M-Boc+H]+", where the lost group is not always what the label says).
ION_EXPR = re.compile(r"[\[\(]\s*\(?\s*M(?![a-z])[^\]\n]{0,40}?\]")
FRAGMENT = re.compile(r"[\[\(]\s*M\s*(?:\+\s*(?:NH4|Na|K|Li|Ag|H)\s*)?[\-−–]\s*(?!H\s*\+?\s*[\]\)])(?=[\(A-Z])")
GROUPS = {"Me": "CH3", "Et": "C2H5", "OMe": "CH3O", "OAc": "C2H3O2", "OTf": "CF3O3S", "OTs": "C7H7O3S",
          "NTf2": "C2F6NO4S2", "Ts": "C7H7O2S", "Tf": "CF3O2S"}
ION_TERM = re.compile(r"([+\-])(\d*)(?:\(([A-Za-z0-9]+)\)(\d*)|([A-Z][A-Za-z0-9]*))")


def ion_changes(expr):
    """'[M-(H2O)2+H]' -> {'H': -3, 'O': -2} (what the ion has in addition to M); None if not parsable."""
    e = re.sub(r"\s", "", expr).replace("−", "-").replace("–", "-")
    e = re.sub(r"^[\[\(]\(?M", "", e).rstrip("]")
    e = re.sub(r"\)(?!\d)", "", e)                      # "(M-H2O)+H" -> "-H2O+H"
    e = re.sub(r"(?<=[A-Za-z0-9\)])[+\-]$", "", e)       # charge inside the bracket: "[M-H+]"
    if not e:
        return {}
    pos, out = 0, {}
    for t in ION_TERM.finditer(e):
        if t.start() != pos:
            return None
        pos = t.end()
        group = t.group(3) or t.group(5)
        n = int(t.group(2) or 1) * int(t.group(4) or 1)
        p = parse_formula(GROUPS.get(group, group))
        if p is None:
            return None
        for el, k in p[0].items():
            out[el] = out.get(el, 0) + (n * k if t.group(1) == "+" else -n * k)
    return out if pos == len(e) else None


# v2: the calculated m/z may be that of the most abundant isotopologue: 37Cl / 81Br instead of 35Cl / 79Br
ISOTOPOLOGUE_SHIFT = {"Cl": 36.9659026 - 34.9688527, "Br": 80.9162897 - 78.9183376}


def isotopologue_match(p, shift, mz):
    """v2: the mass agrees with m/z if some Cl or Br atoms are 37Cl / 81Br (k Cl and j Br replaced)."""
    counts = p[0]
    for k in range(counts.get("Cl", 0) + 1):
        for j in range(counts.get("Br", 0) + 1):
            if (k or j) and abs(p[1] + shift + k * ISOTOPOLOGUE_SHIFT["Cl"]
                                + j * ISOTOPOLOGUE_SHIFT["Br"] - mz) < MZ_TOLERANCE:
                return k, j
    return None


def formula_from_ion(seg, m, ion_f, ion_text, changes):
    """v2: neutral formula = ion formula (checked against m/z) minus the changes written in the ion type."""
    mz = re.search(MZ_VALUE, seg[m.end(): m.end() + MZ_WINDOW])
    for cand in candidates(ion_f):
        p = parse_formula(cand)
        if p is None:
            continue
        note = ""
        if mz is None:
            note = "calculated m/z not found - formula not checked"
        elif abs(p[1] - float(mz.group(1))) >= MZ_TOLERANCE:
            iso = isotopologue_match(p, 0.0, float(mz.group(1)))
            if not iso:
                continue
            note = "m/z of an isotopologue"
        counts = dict(p[0])
        for el, k in changes.items():
            counts[el] = counts.get(el, 0) - k
        if any(v < 0 for v in counts.values()):
            return "", ion_f, ion_text, "ion type does not fit the formula"
        if any(k for el, k in changes.items() if el != "H" and k) or sum(changes.values()) < 0:
            note = "; ".join(x for x in (note, "molecular formula from the ion " + ion_text) if x)
        return hill(counts), ion_f, ion_text, note
    return "", ion_f, ion_text, "formula not parsed or mass does not match"


def neutral_formula(seg):
    """Find 'calcd for <formula>' and the ion type nearby; return (neutral, ion formula, ion, note).
    The parsed ion formula is accepted only if its mass agrees with the calculated m/z (±0.02)."""
    seg = FORMULA_BEFORE_CALC.sub(r"\2 for \1", seg)                     # v2
    m = CALC.search(seg)
    if not m:
        return "", "", "", "no HRMS formula found"

    ion_f = m.group(1)
    # v2.1: "Elemental analysis calcd for C25H30N2O6: C 66.06" / "Anal. Calcd for": the formula of the neutral
    # molecule; an ion type nearby belongs to a mass spectrum
    if re.search(r"(?i)(?:elemental\s+analysis|\banal\.?)\s*(?:\([^)]{0,20}\))?\s*:?\s*$", seg[max(0, m.start() - 40):m.start()]):
        p = parse_formula(re.sub(FORMULA_TAIL, "", ion_f))
        if p is not None:
            return hill(dict(p[0])), ion_f, "", "formula of an elemental analysis (neutral molecule)"
    near = seg[max(0, m.start() - ION_WINDOW): m.end() + ION_WINDOW]
    # v2: an ion type that ION does not read ("[M-N2+H]+", "[M-H+]-"): nearest "[M...]" to "calcd"
    pos = m.start() - max(0, m.start() - ION_WINDOW)
    # v2.1: the ion type written after "calcd" first; one written before it only if no other MS entry lies
    # between ("MS (EI): [M]+: 406. HRMS (ESI): m/z calcd for ... [M+H]+": the [M]+ is of the low-resolution MS)
    # an ion type after the formula belongs to it only if no "found"/"calcd" of another value comes between
    pend = m.end() - max(0, m.start() - ION_WINDOW)
    ions = [x for x in ION.finditer(near)
            if (x.start() >= pos and not re.search(r"(?i)found|calc", near[pend:x.start()]))
            or (x.start() < pos and not re.search(r"\bMS\b", near[x.end():pos]))]
    i = next((x for x in ions if x.start() >= pos), ions[-1] if ions else None)
    expr = min((x for x in ION_EXPR.finditer(near) if x.start() >= pos or not re.search(r"\bMS\b", near[x.end():pos])),
               key=lambda x: abs(x.start() - pos), default=None)
    if expr and (i is None or (abs(expr.start() - pos) <= abs(i.start() - pos)
                               and not ION.fullmatch(expr.group(0)))):
        if i is not None and i.start() == expr.start():
            expr = None
    else:
        expr = None
    if expr is not None:
        ch = ion_changes(expr.group(0))
        tail = re.match(r"(?:\^\{?)?[+\-−–]?", near[expr.end():]).group(0)
        if ch is None:
            if FRAGMENT.match(expr.group(0)):
                return "", ion_f, expr.group(0) + tail, "fragment ion - molecular formula not derived"
        else:
            return formula_from_ion(seg, m, ion_f, expr.group(0) + tail, ch)
    mz = re.search(MZ_VALUE, seg[m.end(): m.end() + MZ_WINDOW])

    b = BRACKET_ADDUCT.match(seg[m.end():])           # "[C23H29OP+Na]+": neutral formula + adduct
    shift = 0.0
    if b:
        shift = sum(n * MASS[el] for el, n in ADDUCT[b.group(2)].items()) * (1 if b.group(1) == "+" else -1)

    # v2: the formula may be the NEUTRAL molecule although an ion type is given
    # ("calcd for C16H12F5NO3S [M+H]+ 394.0531"): its mass then needs the adduct to reach m/z
    neutral_shift = None
    if i and i.group(2) and not b:
        a_mass = sum(n * MASS[el] for el, n in ADDUCT[i.group(2)].items())
        neutral_shift = a_mass if i.group(1) == "+" else -a_mass

    parsed, note, as_neutral = None, "", False
    for cand in candidates(ion_f):
        p = parse_formula(cand)
        if p is None:
            continue
        if mz is None or abs(p[1] + shift - float(mz.group(1))) < MZ_TOLERANCE:
            parsed = p
            if mz is None:
                note = "calculated m/z not found - formula not checked"
            break
        found = False
        for sh, neu in ((shift, False), (neutral_shift, True)):                  # v2
            if sh is None or mz is None:
                continue
            if neu and abs(p[1] + sh - float(mz.group(1))) < MZ_TOLERANCE:
                parsed, as_neutral, note, found = p, True, "formula given for the neutral molecule", True
                break
            iso = isotopologue_match(p, sh, float(mz.group(1)))
            if iso:
                parsed, as_neutral, found = p, neu, True
                note = "m/z of the %s isotopologue" % " + ".join(
                    x for x in (("%d x 37Cl" % iso[0]) if iso[0] else "",
                                ("%d x 81Br" % iso[1]) if iso[1] else "") if x)
                if neu:
                    note += "; formula given for the neutral molecule"
                break
        if found:
            break
    if parsed is None:
        return "", ion_f, i.group(0) if i else "", "formula not parsed or mass does not match"

    counts = dict(parsed[0])
    if as_neutral:                                    # v2
        return hill(counts), ion_f, i.group(0), note
    if b:
        return hill(counts), ion_f, "[M" + b.group(1) + b.group(2) + "]", note
    if not i:
        return neutral_without_ion_type(counts, ion_f)

    sign, add = i.group(1), i.group(2)
    if add is not None:
        if sign == "+":
            for el, n in ADDUCT[add].items():
                counts[el] = counts.get(el, 0) - n
        else:                                         # [M-H]-
            counts["H"] = counts.get("H", 0) + 1
    if any(v < 0 for v in counts.values()):
        return "", ion_f, i.group(0), "adduct does not fit the formula"
    return hill(counts), ion_f, i.group(0), note
