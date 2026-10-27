"""Checks that need the structure (RDKit): item 1 (proton count, also against a molecular formula)
and item 6(a) (magnetically non-equivalent protons). Used by check_descriptions.py."""

import re

from text_checks import AROMATIC_RANGE, MAX_HH_J

RDKIT_PROBLEM = ""
try:
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
except ImportError:
    Chem = None
    RDKIT_PROBLEM = "RDKit is not installed (pip install rdkit)"
except Exception as e:                        # e.g. RDKit and numpy versions do not match
    Chem = None
    RDKIT_PROBLEM = ("RDKit could not be loaded (" + type(e).__name__ + "); try: "
                     "python -m pip install --upgrade --force-reinstall numpy rdkit")


# ===== Constants =====

H_TOLERANCE = 0.06               # reported and expected numbers of protons are equal within this
MIN_B_CLUSTER = 3                # v2.1: boron atoms of a cluster (carborane) whose B-H may be left out
SYMMETRY_FACTORS = (2, 3, 4)     # integrals given for 1/2, 1/3 or 1/4 of a symmetric molecule
SOLVENT_WINDOW = 150             # characters at the start of a description searched for the solvent
SATURATED_RANGE = (0.5, 4.8)     # ppm: CH2 signals of saturated rings
CH2_PROTONS = (2, 4)             # integrals of one or two CH2 groups
MAX_HX_BONDS = 3                 # C...F/P at most 3 bonds apart -> H...F/P at most 4 bonds: H-X coupling possible

# Solvents in which exchangeable protons (NH, OH) are not seen
PROTIC = re.compile(r"CD3OD|D2O|methanol-d4|MeOD|CD3CO2D|acetic acid-d4|\bD\s?2\s?O\b", re.I)
# v2.1: the description lists only some signals ("characteristic peaks", "selected signals"): no proton count
PARTIAL = re.compile(r"characteristic (?:peaks|signals)|selected (?:peaks|signals|data)|diagnostic (?:peaks|signals)"
                     r"|partial (?:data|description)|key signals", re.I)
# The description says that a signal is not observed
NOT_OBSERVED = re.compile(r"not (?:been )?(?:observed|detected|visible|seen)|exchange|not assigned|overlap", re.I)
# Two neighbouring CH2 groups in a saturated ring
RING_CH2CH2 = Chem.MolFromSmarts("[CH2;R;!a]@-[CH2;R;!a]") if Chem else None
# Other protons that can appear at 6-9.6 ppm as "d, J": vinyl/aldehyde C-H, NH, OH
OTHER_LOWFIELD = Chem.MolFromSmarts("[$([CX3;!a;!H0]),$([#7,#8;!H0])]") if Chem else None


# ===== Item 1 =====

EXCH_ATOMS = ("N", "O", "S", "Cl", "Br", "I", "F")     # v2.1: halogens bear H only as the acid of a salt
QUAD_ATOMS = ("B",)               # protocol v1.2, item 1: protons on quadrupolar nuclei (B-H) not reported = subcategory
QUAD_SUBCAT = "subcategory: protons on quadrupolar nuclei not reported"


def quad_h(mol):
    """Protons on quadrupolar nuclei (B-H of boranes and carboranes) - v2.1."""
    n = 0
    for a in mol.GetAtoms():
        if a.GetSymbol() in QUAD_ATOMS:
            n += a.GetTotalNumHs() + sum(1 for x in a.GetNeighbors() if x.GetAtomicNum() == 1)
    return n


def h_counts(mol):
    """(all protons, exchangeable protons on N/O/S); deuterium is not counted.
    v2.1: the H of an acid in a salt written as a separate fragment ("Cl.CN1CCCC1", HBr, HI, HF) is exchangeable
    too (in the salt it is the N-H+ proton, often not seen)."""
    total = exch = 0
    for a in mol.GetAtoms():
        if a.GetAtomicNum() == 1:                 # explicit H atom (the molecule has AddHs)
            if a.GetIsotope() != 2:
                total += 1
                if any(n.GetSymbol() in EXCH_ATOMS for n in a.GetNeighbors()):
                    exch += 1
            continue
        h = a.GetTotalNumHs()                     # implicit H atoms
        total += h
        if a.GetSymbol() in EXCH_ATOMS:
            exch += h
    return total, exch


def integrals(sigs):
    """(list of integrals, message or None if one is missing)."""
    ints = [s["nH"] for s in sigs]
    if not sigs or any(x is None for x in ints):
        return ints, f"integral missing for {sum(1 for x in ints if x is None)} signal(s)"
    return ints, None


def check_item1_formula(desc, sigs, formula, mixture):
    """Item 1 without a structure: the reported protons against the H of the molecular formula
    (e.g. the neutral formula from the HRMS). Exchangeable protons cannot be identified."""
    total = sum(int(n or 1) for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula) if el == "H")
    n_b = sum(int(n or 1) for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", formula) if el == "B")
    ints, missing = integrals(sigs)
    if missing:
        return "cannot be determined", missing, None, total
    if PARTIAL.search(desc):                                                                   # v2.1
        return "cannot be determined", "only some signals are listed (partial description)", sum(ints), total

    rep = sum(ints)
    info = f"reported {rep:g} H; formula {formula} has {total} H (no structure: compared with the formula)"
    if abs(rep - total) < H_TOLERANCE:
        return "consistent", info + ("; mixture/rotamers" if mixture else ""), rep, total
    if mixture:
        return "mixture (check)", info, rep, total
    # v2.1: B-H of carboranes and boron clusters (C2B10H10) is broad and often not listed; with one or two B the
    # formula may be BF4-, Bpin, B2pin2 or a diboraarene without B-H, so a missing proton stays a finding
    if n_b >= MIN_B_CLUSTER and total - n_b - H_TOLERANCE <= rep < total:
        return QUAD_SUBCAT, info + "; B-H protons of a boron cluster (quadrupolar nucleus) may not be listed", rep, total
    if rep < total and PROTIC.search(desc[:SOLVENT_WINDOW]):        # v2.1: OH/NH not seen in D2O, CD3OD
        return ("subcategory: exchangeable proton not reported", info + "; protic solvent: exchangeable protons are "
                "not seen (their number is not known without a structure)", rep, total)
    if rep < total:
        return "inconsistent? (check)", info + "; fewer H: an exchangeable proton not reported, or a signal missing", rep, total
    return "inconsistent (check)", info, rep, total


def check_item1(desc, sigs, mol, mixture):
    """Item 1: the reported protons against the structure (mol with explicit H)."""
    total, exch = h_counts(mol)
    ints, missing = integrals(sigs)
    if missing:
        return "cannot be determined", missing, None, total
    if PARTIAL.search(desc):                                                                   # v2.1
        return "cannot be determined", "only some signals are listed (partial description)", sum(ints), total

    rep = sum(ints)
    info = f"reported {rep:g} H; structure {total} H ({exch} exchangeable)"
    if abs(rep - total) < H_TOLERANCE:
        return "consistent", info + ("; mixture/rotamers" if mixture else ""), rep, total
    if mixture:
        return "mixture (check)", info, rep, total
    if exch and total - exch - H_TOLERANCE <= rep < total:
        if PROTIC.search(desc[:SOLVENT_WINDOW]) or NOT_OBSERVED.search(desc):
            return "consistent", info + "; exchangeable protons: protic solvent or statement", rep, total
        return "subcategory: exchangeable proton not reported", info, rep, total
    quad = quad_h(mol)                                                                          # v2.1
    if quad and total - exch - quad - H_TOLERANCE <= rep < total:
        return QUAD_SUBCAT, info + f"; {quad} H on boron (quadrupolar nucleus)", rep, total
    for f in SYMMETRY_FACTORS:
        if abs(rep * f - total) < H_TOLERANCE or abs(rep * f - (total - exch)) < H_TOLERANCE:
            return "inconsistent? (check)", info + f"; integrals may be given for 1/{f} of a symmetric molecule", rep, total
    return "inconsistent (check)", info, rep, total


# ===== Item 6(a) =====

def ring_kind(ring, atoms, dist):
    """Name of an aromatic ring for the findings: monosubstituted phenyl, para-disubstituted benzene ..."""
    subs = [a.GetIdx() for a in atoms if a.GetTotalNumHs() == 0]
    carbocycle = all(a.GetSymbol() == "C" for a in atoms)
    if len(ring) == 6 and len(subs) == 1 and carbocycle:
        return "monosubstituted phenyl"
    if len(ring) == 6 and len(subs) == 2 and carbocycle and dist[subs[0]][subs[1]] == 3:
        return "para-disubstituted benzene"
    if len(ring) == 6 and any(a.GetSymbol() == "N" for a in atoms) and len(subs) == 2:
        return "4-substituted pyridine"
    return f"{len(ring)}-membered aromatic ring"


def magnetically_nonequivalent_rings(mol):
    """Aromatic rings containing chemically equivalent ring protons A, A' and a ring
    proton X with different topological distances to A and A' (J_AX != J_AX')."""
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
    dist = Chem.GetDistanceMatrix(mol)
    found, ring_h_atoms = [], set()
    for ring in mol.GetRingInfo().AtomRings():
        atoms = [mol.GetAtomWithIdx(i) for i in ring]
        if not all(a.GetIsAromatic() for a in atoms):
            continue
        ch = [a.GetIdx() for a in atoms if a.GetTotalNumHs() > 0]
        hit = any(i < j and ranks[i] == ranks[j] and any(x not in (i, j) and dist[i][x] != dist[j][x] for x in ch)
                  for i in ch for j in ch)
        if hit:
            ring_h_atoms.update(ch)
            found.append(ring_kind(ring, atoms, dist))
    return found, ring_h_atoms


def aromatic_hx_possible(mol):
    """True if some aromatic C-H is within four bonds of F or P (H-F / H-P coupling possible)."""
    dist = Chem.GetDistanceMatrix(mol)
    xs = [a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() in ("F", "P")]
    if not xs:
        return False
    hs = [a.GetIdx() for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetTotalNumHs() > 0]
    return any(dist[h][x] <= MAX_HX_BONDS for h in hs for x in xs)


def fmt_n(n):
    return "?" if n is None else f"{n:g}"


def first_order_aromatic(s):
    """An aromatic-range signal reported with first-order notation and an H-H J (not a CHF2 etc.)."""
    return (AROMATIC_RANGE[0] <= s["shift"] <= AROMATIC_RANGE[1] and s["mult"] not in (None, "m", "s")
            and s["J"] and not s["Japp"]
            and not any(float(v) > MAX_HH_J for v in s["Jhet_found"] + s["Jhet"]))


def check_item6a(sigs, mol):
    """Item 6(a): (verdict, findings, indices of signals that are not first-order)."""
    rings, ring_h = magnetically_nonequivalent_rings(mol)
    sat = bool(mol.HasSubstructMatch(RING_CH2CH2))
    # if every aromatic C-H of the molecule belongs to such rings, an aromatic
    # signal with first-order notation and J can only come from them: inconsistent
    arom_h = {a.GetIdx() for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetTotalNumHs() > 0}
    certain = bool(rings) and arom_h <= ring_h and not mol.HasSubstructMatch(OTHER_LOWFIELD)

    lines, certain_hit, idx = [], False, set()
    if rings:
        cand = [f"#{k} {s['shift']:.2f} ({'app ' if s['app'] else ''}{s['mult']}, J = {', '.join(s['J'])}, {fmt_n(s['nH'])}H)"
                for k, s in enumerate(sigs, 1) if first_order_aromatic(s)]
        if cand:
            if certain:
                certain_hit = True
                idx = {k - 1 for k, s in enumerate(sigs, 1) if first_order_aromatic(s)}
                lines.append(", ".join(sorted(set(rings))) + " (all protons at 6-9.6 ppm belong to "
                             "such rings); first-order signals with J: " + "; ".join(cand))
            else:
                lines.append(", ".join(sorted(set(rings))) + "; first-order signals with J (other protons "
                             "can appear at 6-9.6 ppm - assign by hand): " + "; ".join(cand))
    if sat:
        cand = [f"#{k} {s['shift']:.2f} ({s['mult']}, J = {', '.join(s['J'])}, {fmt_n(s['nH'])}H)"
                for k, s in enumerate(sigs, 1)
                if SATURATED_RANGE[0] <= s["shift"] <= SATURATED_RANGE[1] and s["mult"] not in (None, "m", "s", "d")
                and s["J"] and (s["nH"] or 0) in CH2_PROTONS and not s["Japp"]]
        if cand:
            lines.append("ring CH2-CH2; CH2 signals with J (ring or chain?): " + "; ".join(cand))

    if certain_hit:
        return "inconsistent", "\n".join(lines), idx
    return ("candidate (check)" if lines else "consistent"), "\n".join(lines), set()
