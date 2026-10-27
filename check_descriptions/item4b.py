"""v2: item 4(b) - the multiplicity needs no more coupling partners than the structure provides.

Without an assignment the script does not know which proton a signal belongs to. It checks a weaker,
necessary condition: is there ANY proton of the structure (of the right kind for the shift) that has
enough possible partners for the reported multiplicity? If none has, the multiplicity is impossible
for this structure ("tt" of an aromatic proton whose ring has no proton with two meta neighbours).

Possible partners are counted generously (upper bound), by the number of bonds between the nuclei:
  J >= BIG_J        : 2-3 bonds (geminal, vicinal; 4 through an allene), F/P up to 4 bonds;
  SMALL_J <= J < BIG_J: up to 4 bonds if a planar atom is on the path or the middle atom is in a ring
                        (meta, allylic, benzylic, W) and 5-bond homoallylic paths
                        or planar zigzag paths through sp2/aromatic atoms only (H-8...H-4 of quinoline),
                        F/P up to 6 bonds (long-range and through-space H-F);
  J < SMALL_J       : up to 5 bonds, F/P up to 7 bonds.
Geminal partners are counted only in CH2 groups (in CH3 they are equivalent). Protons on N and O
count as partners. The order in which the constants are written is not trusted: the reading that
needs the fewest partners is taken. Signals with m, app, br, J_app, and molecules with nuclei that
split without being counted here (D, B, metals, NH4+-type N) are not checked."""

from itertools import permutations

try:
    from rdkit import Chem
except Exception:                                  # RDKit missing: structure_checks reports it
    Chem = None

from text_checks import AROMATIC_RANGE

BIG_J = 5.0          # Hz: at least this large -> 2-3 bonds (F/P: up to 4 bonds)
SMALL_J = 1.0        # Hz: at least this large -> up to 4 bonds (+ 5-bond homoallylic or planar zigzag paths)
LETTERS = {"d": 1, "t": 2, "q": 3, "p": 4, "h": 5}    # "h" = hextet (MestReNova), 6 lines
LONG = {"sext": 5, "sept": 6}
SPIN_HALF_X = ("F", "P")
ALLOWED = {"C", "H", "N", "O", "S", "F", "P", "Cl", "Br", "I", "Si", "Se"}
LOWFIELD_OTHER = Chem.MolFromSmarts("[$([CX3;!a;!H0]),$([CX2;!H0]),$([#7,#8;!H0])]") if Chem else None
# sp3 C-H that can be at >= 6 ppm: next to N/O/S/halogen (N-CH-O, imide N-CH) or to two unsaturated atoms
LOWFIELD_SP3 = Chem.MolFromSmarts("[CX4;!H0;$(*[#7,#8,#16,F,Cl,Br,I]),$(*(~[a,$([#6]=*)])~[a,$([#6]=*)])]") if Chem else None
SP3_UP_TO = 7.0     # ppm: sp3 C-H (N-CH-O, imide N-CH) are considered up to here
AROMATIC_FROM = 5.5  # ppm: aromatic protons are considered from here (shielded rings, e.g. 5.99)


def partner_counts(code):
    """'ddt' -> [1, 1, 2]; 'septd' -> [6, 1]; None if not a pure first-order code."""
    for k, n in LONG.items():
        if code.startswith(k):
            rest = code[len(k):]
            return [n] + [LETTERS[c] for c in rest] if all(c in LETTERS for c in rest) else None
    if code and all(c in LETTERS for c in code):
        return [LETTERS[c] for c in code]
    return None


def checkable(mol):
    """The molecule has no nuclei that split signals without being counted here."""
    for a in mol.GetAtoms():
        if a.GetSymbol() not in ALLOWED or a.GetIsotope() == 2:
            return False
        if a.GetSymbol() == "N" and a.GetFormalCharge() > 0 and a.GetTotalNumHs() > 0:
            return False                            # NH4+-type: 14N splitting can be seen
    return True


def h_atoms(mol):
    """Heavy atoms carrying H: {index: number of H}."""
    return {a.GetIdx(): a.GetTotalNumHs() for a in mol.GetAtoms() if a.GetAtomicNum() > 1 and a.GetTotalNumHs()}


def homoallylic(mol, path):
    """A 5-bond H...H path H-C-X=Y-C-H or H-C-C#C-C-H (path = heavy atoms A, X, Y, B): homoallylic or homopropargylic."""
    if len(path) != 4:
        return False
    b = mol.GetBondBetweenAtoms(path[1], path[2])
    return b is not None and b.GetBondType() in (Chem.BondType.DOUBLE, Chem.BondType.TRIPLE)   # 5J through C=C or C#C


def planar(atom):
    """Unsaturated atom: aromatic, sp2 or sp (allylic, benzylic, propargylic 4J; zigzag 5J of about 1 Hz)."""
    return atom.GetIsAromatic() or atom.GetHybridization() in (Chem.HybridizationType.SP2, Chem.HybridizationType.SP)


def pools(mol, a, hs, dist):
    """Numbers of possible partners of a proton on atom a: (big, small, tiny), nested."""
    big = small = tiny = 0
    if hs[a] == 2:                                   # geminal partner in CH2 (diastereotopic)
        big += 1; small += 1; tiny += 1
    for b, n in hs.items():
        if b == a:
            continue
        d = dist[a][b]                               # bonds between the heavy atoms; H...H = d + 2
        if d == 1:
            big += n; small += n; tiny += n
        elif d == 2:
            tiny += n
            path = Chem.GetShortestPath(mol, a, b)
            mid = path[1]
            # 4J of 1 Hz or more: allylic, benzylic, meta (a planar atom on the path) or W in a ring;
            # in an open saturated chain 4J is below 1 Hz
            if any(planar(mol.GetAtomWithIdx(i)) for i in path) or mol.GetAtomWithIdx(mid).IsInRing():
                small += n
            if sum(bd.GetBondType() == Chem.BondType.DOUBLE for bd in mol.GetAtomWithIdx(mid).GetBonds()) == 2:
                big += n                             # allene: 4J(H,H) about 6-7 Hz
        elif d == 3:
            tiny += n
            path = list(Chem.GetShortestPath(mol, a, b))
            if homoallylic(mol, path) or all(planar(mol.GetAtomWithIdx(i)) for i in path):
                small += n
    for x in mol.GetAtoms():
        if x.GetSymbol() in SPIN_HALF_X:
            d = dist[a][x.GetIdx()]                  # H...X = d + 1
            if d <= 3:
                big += 1
            if d <= 5:                               # H...F up to 6 bonds: long-range and through-space
                small += 1
            if d <= 6:
                tiny += 1
    return big, small, tiny


METHYL_SHIFT = 4.5   # ppm: a 3H/6H/9H/18H d, t or dd below this is one or more CH3 (6H, 18H: or CH2)


def candidates(mol, shift, hs, nH=None, need_total=0):
    """Atoms whose protons can give a signal at this shift (and integral: 3n H in the aliphatic
    region = CH3 groups, if the molecule has any)."""
    # only for d, t, dd (at most 2 partners): a 3H "tq" or "dddd" is more often overlapped ring protons
    if nH and shift < METHYL_SHIFT and abs(nH / 3 - round(nH / 3)) < 0.01 and nH >= 3 and need_total <= 2:
        # CH3 (or, for 6H/18H, CH2) groups whose set of topologically equivalent groups supplies the
        # integral: one CH3 for 3H, the two CH3 of an iPr for 6H, the three CH2 of SiEt3 for 6H
        ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False, includeChirality=False))
        size = {}
        for i in hs:
            size[ranks[i]] = size.get(ranks[i], 0) + 1
        kinds = (3, 2) if abs(nH / 2 - round(nH / 2)) < 0.01 else (3,)
        groups = {i for i, n in hs.items() if n in kinds and size[ranks[i]] * n >= nH - 0.01}
        if groups:
            return groups
    arom = {i for i in hs if mol.GetAtomWithIdx(i).GetIsAromatic()}
    het = {i for i in hs if mol.GetAtomWithIdx(i).GetSymbol() in ("N", "O", "S")}
    if shift >= AROMATIC_RANGE[0]:
        other = {m[0] for m in mol.GetSubstructMatches(LOWFIELD_OTHER)} if LOWFIELD_OTHER else set(hs)
        sp3 = ({m[0] for m in mol.GetSubstructMatches(LOWFIELD_SP3)} if LOWFIELD_SP3 else set(hs)) \
            if shift < SP3_UP_TO else set()
        return arom | other | het | sp3
    return (set(hs) - arom) | het | (arom if shift >= AROMATIC_FROM else set())


def needs(counts, js):
    """Fewest partners (big, big+small, total) over the readings of which letter goes with which J."""
    best = None
    for perm in set(permutations(counts)):
        big = sum(n for n, j in zip(perm, js) if j >= BIG_J)
        small = sum(n for n, j in zip(perm, js) if SMALL_J <= j < BIG_J)
        need = (big, big + small, sum(perm))
        if best is None or need < best:
            best = need
    return best


def check_item4b(sigs, mol, mixture=False):
    """(verdict, findings). Verdict: 'consistent', 'candidate (check)', 'not checked: ...'."""
    if mol is None:
        return "no structure", ""
    if mixture:
        return "not checked: mixture/rotamers", ""
    if not checkable(mol):
        return "not checked: nuclei not counted (D, B, metal, NH4+)", ""
    hs = h_atoms(mol)
    dist = Chem.GetDistanceMatrix(mol)
    pool = {a: pools(mol, a, hs, dist) for a in hs}
    found, n_checked = [], 0
    for k, s in enumerate(sigs, 1):
        if s["mult"] in (None, "s", "m", "AB") or s["app"] or s["br"] or s["Japp"]:
            continue
        counts = partner_counts(s["mult"])
        js = [float(v) for v in s["J"] + s["Jhet"]]
        if counts is None or len(js) != len(counts):
            continue                                 # number of J: item 4(a)
        n_checked += 1
        need = needs(counts, js)
        cand = candidates(mol, s["shift"], hs, s["nH"], need[2])
        if not any(pool[a][0] >= need[0] and pool[a][1] >= need[1] and pool[a][2] >= need[2] for a in cand):
            best = max((pool[a] for a in cand), default=(0, 0, 0))
            found.append(f"#{k} {s['shift']:.2f} ({s['mult']}, J = {', '.join(s['J'] + s['Jhet'])}): needs "
                         f"{need[0]} partner(s) within 3 bonds, {need[1]} within 4, {need[2]} in all; "
                         f"no proton of the structure at this shift has that many (best: {best[0]}/{best[1]}/{best[2]})")
    if found:
        return "candidate (check)", "\n".join(found)
    return ("consistent" if n_checked else "nothing to check"), ""
