"""v2.1.5: item 4(b) - counting large couplings and the multiplet-width test.

The justification of the width test, the bounds of Table 4 and the guard are in
docs/development/width_criterion/checkHNMR_V2.1.5_width_test.pdf; the numbers there are reproduced by the code
in that folder.  This module only applies the rule.

Structure side.  For every proton of the structure:
  k    - the number of non-equivalent partners with a coupling that is certainly at least 6 Hz ("large"):
         ortho H-H in a benzenoid ring (not next to a ring heteroatom), H-C=C-H outside small rings, H-C(sp2)-C(sp2)-H
         across an open-chain single bond (dienes, HC(=O)-CH=), ortho H-F.  A proton whose couplings may lie on either
         side of 6 Hz (sp3 C-H with vicinal partners, NH/OH, five-membered and pyridine-type rings, protons near P or
         aliphatic F, allenes, an equivalent partner with a large coupling) is "flexible": it can stand in any signal.
  L_X  - the lower bound on the width of its multiplet (Table 4 of the note): the sum of the minima of the large
         1H-1H couplings, minus |min| of the small ones that can be negative, plus |J|min of the large H-19F couplings.
         Partners are the protons within five bonds (the widest range of the upper-bound check of item 4(b)).  A 1H
         partner outside Table 4 within four bonds, or at five bonds on a homoallylic or a planar (zigzag) path that
         does not cross a single bond outside a ring, makes L_X unknown (X is not tested); any other partner outside
         Table 4 at five bonds is subtracted with 1 Hz.  19F couplings are zero with 19F decoupling; H-P couplings
         have no bounds yet and contribute 0.

Signal side.  The letters give the order of the constants, largest first (s: number of reported splittings with
J >= 6 Hz; W_s = sum n_k J_k; tau = sum n_k h_k / 2 + 0.2 Hz, h_k the reporting step).  m, br, app, apparent J and
signals with heteronuclear constants are not counted.

The rule.  The signals must be distributed over the protons of the structure (integrals; equivalent protons
together where the molecule forces it) so that a proton stands only in a signal with s = k, or with s < k if
W_s + tau >= L_X or if a large-coupling partner stands in the same signal (a nearly isochronous AB pair), and only at
a shift where it can stand (the shift windows of the upper-bound check of item 4(b): aromatic protons from 5.5 ppm,
sp3 C-H above the aromatic range only next to a heteroatom or two unsaturated atoms).  A proton
meta to an aromatic F may also stand in a signal with s = k + 1 (meta H-F up to 10 Hz).  If no distribution exists,
the verdict is "inconsistent".  If a distribution exists once the width condition is lifted for signals that have
another signal within c * J_max Hz (c = 3: the guard; J_max = the upper bound of the largest coupling), the verdict
is "candidate (check)".  Only for descriptions whose proton count (item 1) is consistent, without mixtures.
"""

import re
from collections import Counter
from itertools import combinations

try:
    from rdkit import Chem
except Exception:                                  # RDKit missing: structure_checks reports it
    Chem = None

from text_checks import step_of
from item4b import candidates, h_atoms

LARGE = 6.0                # Hz: a "large" coupling
GUARD_C = 3.0              # the guard: a neighboring signal closer than c * J_max lifts the width condition
TAU_EXTRA = 0.2            # Hz: added to the rounding tolerance of the reported width
FIVE_BOND_SMALL = 1.0      # Hz: |5J| of a partner outside Table 4 on a non-zigzag, non-homoallylic path
SEARCH_BUDGET = 300000     # steps of the distribution search; beyond this no finding is given
LET = {"d": 1, "t": 2, "q": 3, "p": 4, "h": 5}

# Table 4 of the note: (min, max) in Hz; None = no bound used
ORTHO = (6.5, 9.0)
ORTHO_FUSED_12 = (8.0, 9.0)             # naphthalene H-1/H-2
ORTHO_FUSED_23 = (5.0, 9.0)             # naphthalene H-2/H-3
META, PARA = (1.0, 3.0), (0.0, 1.0)
CIS, TRANS = (4.0, 12.0), (12.5, 19.0)
GEM_C, GEM_HET = (0.0, 4.0), (-4.0, 4.0)   # 2J of =CH2: C substituents / O, F or unknown
ALLYLIC = (-1.8, -0.7)
BENZYLIC_CH3 = {4: (-0.7, -0.7), 5: (0.3, 0.3), 6: (-0.6, -0.6)}       # ortho 4J, meta 5J, para 6J
BENZYLIC_CH = {4: (-1.75, None), 5: (0.0, None), 6: (-1.75, None)}     # CH2 or CH on the ring
DIENE = (9.5, 12.0)
CHO_CH = (5.5, 10.0)
NH_CH = (0.0, 10.3)                     # range rule only: the minimum is not used (positive: contributes 0)
HF_ORTHO, HF_META = (6.0, 12.0), (5.0, 10.0)                           # magnitudes

RANGE = re.compile(r"^\s*(\d+\.\d+)\s*[–\-−—~]+\s*(\d+\.\d+)")
DECOUPLED = re.compile(r"1\s?H\s?\{\s?(?:1\s?H\s?,\s?)?((?:19\s?F|31\s?P)(?:\s?,\s?(?:19\s?F|31\s?P))?)\s?\}", re.I)


# ===== Structure =====

def h_of(m, a):
    """Indices of the H atoms bonded to atom a (molecule with explicit H)."""
    return [n.GetIdx() for n in m.GetAtomWithIdx(a).GetNeighbors() if n.GetSymbol() == "H"]


def bond_in_ring(m, a, b):
    return any(a in r and b in r for r in m.GetRingInfo().AtomRings())


def sym_classes(m, marks=None):
    """Topological symmetry classes of the atoms (iterative refinement of atom invariants by the sorted
    (bond type, neighbor class) lists); marks: {atom: label} added to the invariant.  The same code runs on the
    desktop and on the website, so the classes do not depend on the RDKit build."""
    marks = marks or {}
    inv = [(a.GetSymbol(), a.GetFormalCharge(), a.GetIsotope(), len(a.GetNeighbors()), a.GetIsAromatic(), a.IsInRing(),
            marks.get(a.GetIdx(), 0)) for a in m.GetAtoms()]
    bt = {}
    for b in m.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        bt[(i, j)] = bt[(j, i)] = str(b.GetBondType())
    nbr = {a.GetIdx(): [n.GetIdx() for n in a.GetNeighbors()] for a in m.GetAtoms()}

    def classes(keys):
        order = {k: n for n, k in enumerate(sorted(set(keys), key=repr))}
        return [order[k] for k in keys]
    cls = classes(inv)
    while True:
        new = classes([(cls[i], tuple(sorted((bt[(i, j)], cls[j]) for j in nbr[i]))) for i in range(len(inv))])
        if len(set(new)) == len(set(cls)):
            return new
        cls = new


def eq_ranks(m):
    """Symmetry classes, except that two identical groups on the same end of a C=C (gem-diaryl alkene,
    C=C(COPh)2) are cis and trans to different groups and are not equivalent."""
    marks = {}
    for _ in range(20):
        ranks = sym_classes(m, marks)
        changed = False
        for b in m.GetBonds():
            if b.GetBondType() != Chem.BondType.DOUBLE:
                continue
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            for x, y in ((i, j), (j, i)):
                ny = [n.GetIdx() for n in m.GetAtomWithIdx(y).GetNeighbors() if n.GetIdx() != x]
                nx = [n.GetIdx() for n in m.GetAtomWithIdx(x).GetNeighbors() if n.GetIdx() != y]
                if (len(ny) == 2 and ranks[ny[0]] == ranks[ny[1]] and m.GetAtomWithIdx(ny[0]).GetSymbol() != "H"
                        and (len(nx) == 1 or (len(nx) == 2 and ranks[nx[0]] != ranks[nx[1]]))):
                    marks[ny[0]] = len(marks) + 1
                    changed = True
                    break
            if changed:
                break
        if not changed:
            return ranks
    return ranks


def planar(atom):
    return atom.GetIsAromatic() or atom.GetHybridization() in (Chem.HybridizationType.SP2, Chem.HybridizationType.SP)


def benzenoid_rings(m):
    return [set(r) for r in m.GetRingInfo().AtomRings()
            if len(r) == 6 and all(m.GetAtomWithIdx(i).GetIsAromatic() and m.GetAtomWithIdx(i).GetSymbol() == "C" for i in r)]


def fused(m, ring):
    """Atoms of the ring shared with another six-membered aromatic ring (naphthalene, quinoline): only there do the
    ortho couplings alternate (H-1/H-2 8-9 Hz, H-2/H-3 5-7 Hz).  A benzene ring fused to a saturated or a
    five-membered ring (tetralin, indane, indole) keeps the benzene bounds."""
    other = [set(r) for r in m.GetRingInfo().AtomRings()
             if len(r) == 6 and set(r) != ring and all(m.GetAtomWithIdx(i).GetIsAromatic() for i in r)]
    return {i for i in ring if any(i in r for r in other)}


def ortho_bounds(m, ca, cb, ring):
    """Bounds of an ortho coupling in a benzenoid ring: naphthalene-type H-1/H-2 and H-2/H-3 in a fused ring."""
    fz = fused(m, ring)
    if not fz:
        return ORTHO
    near = [i for i in (ca, cb) if any(n.GetIdx() in fz for n in m.GetAtomWithIdx(i).GetNeighbors())]
    return ORTHO_FUSED_12 if near else ORTHO_FUSED_23


def has_double_o(atom, m):
    return any(n.GetSymbol() == "O" and m.GetBondBetweenAtoms(atom.GetIdx(), n.GetIdx()).GetBondType() == Chem.BondType.DOUBLE
               for n in atom.GetNeighbors())


def pair_bounds(m, dist, benz, x, y):
    """Table-4 class of the H...H pair x, y: (min, max, large) or None if the pair is not in Table 4."""
    cx, cy = m.GetAtomWithIdx(x).GetNeighbors()[0], m.GetAtomWithIdx(y).GetNeighbors()[0]
    ix, iy = cx.GetIdx(), cy.GetIdx()
    d = int(dist[x][y])
    for r in benz:
        if ix in r and iy in r and ix != iy:
            if d == 3:
                return ortho_bounds(m, ix, iy, r) + (True,)
            return (META if d == 4 else PARA) + (False,)
    if cx.GetSymbol() == "C" and cy.GetSymbol() == "C":
        if ix == iy:
            if cx.GetHybridization() == Chem.HybridizationType.SP2 and not cx.GetIsAromatic():
                other = [n for n in cx.GetNeighbors() if n.GetSymbol() != "H"]
                dbl = [n for n in other if m.GetBondBetweenAtoms(ix, n.GetIdx()).GetBondType() == Chem.BondType.DOUBLE]
                if dbl:                                     # =CH2: substituents on the other end of the C=C
                    far = [n for n in dbl[0].GetNeighbors() if n.GetIdx() != ix]
                    if far and all(n.GetSymbol() == "C" for n in far):
                        return GEM_C + (False,)
                    return GEM_HET + (False,)
            return None
        b = m.GetBondBetweenAtoms(ix, iy)
        small_ring = any(ix in r and iy in r and len(r) <= 5 for r in m.GetRingInfo().AtomRings())
        if b is not None and b.GetBondType() == Chem.BondType.DOUBLE and not small_ring and d == 3:
            # cis or trans: from the path geometry the script does not know which; use the cis minimum and
            # the trans maximum unless E/Z is fixed by a ring (then cis)
            if bond_in_ring(m, ix, iy):
                return CIS + (True,)
            return (CIS[0], TRANS[1], True)
        if (b is not None and b.GetBondType() == Chem.BondType.SINGLE and not bond_in_ring(m, ix, iy) and d == 3
                and not cx.GetIsAromatic() and not cy.GetIsAromatic()
                and cx.GetHybridization() == Chem.HybridizationType.SP2 and cy.GetHybridization() == Chem.HybridizationType.SP2):
            if has_double_o(cx, m) or has_double_o(cy, m):
                return CHO_CH + (True,)
            return DIENE + (True,)
        if d == 4:                                          # allylic: H-C=C-C(sp3)-H
            for a, c in ((cx, cy), (cy, cx)):
                if a.GetHybridization() == Chem.HybridizationType.SP2 and not a.GetIsAromatic() \
                        and c.GetHybridization() == Chem.HybridizationType.SP3:
                    for nb in a.GetNeighbors():
                        bd = m.GetBondBetweenAtoms(a.GetIdx(), nb.GetIdx())
                        if bd.GetBondType() == Chem.BondType.DOUBLE and m.GetBondBetweenAtoms(nb.GetIdx(), c.GetIdx()) is not None:
                            return ALLYLIC + (False,)
        for a, c in ((cx, cy), (cy, cx)):                   # benzylic: ring H ... H on an sp3 C bonded to the ring
            if c.GetHybridization() == Chem.HybridizationType.SP3 and d in (4, 5, 6):
                ring = [r for r in benz if a.GetIdx() in r and any(n.GetIdx() in r for n in c.GetNeighbors())]
                if ring:
                    nh = len(h_of(m, c.GetIdx()))
                    lo, hi = (BENZYLIC_CH3 if nh == 3 else BENZYLIC_CH)[d]
                    return (lo, hi, False)
    for a, c in ((cx, cy), (cy, cx)):                       # NH-CH(sp3): range rule only
        if a.GetSymbol() == "N" and c.GetSymbol() == "C" and c.GetHybridization() == Chem.HybridizationType.SP3 and d == 3:
            return NH_CH + (False,)
    return None


def zigzag_or_homoallylic(m, x, y):
    """5-bond path H-A-B-C-D-H: homoallylic (B=C), or all of A..D planar without a single bond outside a ring."""
    a, b = m.GetAtomWithIdx(x).GetNeighbors()[0].GetIdx(), m.GetAtomWithIdx(y).GetNeighbors()[0].GetIdx()
    path = list(Chem.GetShortestPath(m, a, b))
    if len(path) != 4:
        return True
    mid = m.GetBondBetweenAtoms(path[1], path[2])
    if mid is not None and mid.GetBondType() in (Chem.BondType.DOUBLE, Chem.BondType.TRIPLE):
        return True
    if not all(planar(m.GetAtomWithIdx(i)) for i in path):
        return False
    for i, j in zip(path, path[1:]):
        bd = m.GetBondBetweenAtoms(i, j)
        if bd.GetBondType() == Chem.BondType.SINGLE and not bond_in_ring(m, i, j):
            return False                                   # rotatable: not held planar
    return True


def width_bound(m, dist, benz, ranks, x, decoupled):
    """(L_X, J_max) of proton x, or (None, None) if X is not tested."""
    large = small = hetero = 0.0
    jmax = 0.0
    for y in range(m.GetNumAtoms()):
        if y == x or m.GetAtomWithIdx(y).GetSymbol() != "H":
            continue
        d = dist[x][y]
        if d > 6:
            continue
        pb = pair_bounds(m, dist, benz, x, y)
        if pb is None:
            if d <= 4 or (d == 5 and zigzag_or_homoallylic(m, x, y)):
                return None, None
            if d == 5:
                small += FIVE_BOND_SMALL
            continue
        lo, hi, is_large = pb
        if is_large:
            if ranks[y] == ranks[x]:
                return None, None                         # equivalent partner with a large coupling: strongly coupled
            large += lo
            jmax = max(jmax, hi or 0.0)
        elif lo is not None and lo < 0:
            small += -lo
    if "F" not in decoupled:
        for f in m.GetAtoms():
            if f.GetSymbol() != "F" or not any(n.GetIsAromatic() for n in f.GetNeighbors()):
                continue
            ring_c = f.GetNeighbors()[0].GetIdx()
            c_x = m.GetAtomWithIdx(x).GetNeighbors()[0].GetIdx()
            if not any(ring_c in r and c_x in r for r in benz):
                continue
            d = dist[x][f.GetIdx()]
            if d == 3:
                hetero += HF_ORTHO[0]
            elif d == 4:
                hetero += HF_META[0]
    return large - small + hetero, (jmax or None)


# ===== Range of the coupling constants (v2.1.5) =====

MAX_HH = 25.0             # Hz: no H-H coupling is larger (the rule of v2; used when a partner is not in Table 4)
RANGE_TOL = 0.3           # Hz: tolerance of the upper bound, or the reporting step if larger
OUT_OF_RANGE = "larger than any coupling of the protons that can stand at this shift"
RANGE_A, RANGE_B = "item 4(b) range: ", "item 4(b) range, at the limit: "     # prefixes of the findings (A, B)
COUNT_A, WIDTH_B = "item 4(b): ", "item 4(b) width: "


def range_max(m, dist, benz, x, decoupled, flip):
    """Largest |J| that proton x can show: the upper bounds of Table 4 over its H partners; MAX_HH if an H-H partner
    is not in Table 4 (within 4 bonds, or a homoallylic / zigzag 5-bond path) or x is on N, O or S; infinity if
    an F or P is within 7 bonds and not decoupled (H-F and H-P couplings are not checked by range). flip: x is
    one of a pair of ring protons made equivalent by the turning of the ring (an AA'XX'-type half: the reported
    splitting can be N = J_ortho + J_para)."""
    for xa in m.GetAtoms():
        if xa.GetSymbol() in ("F", "P") and xa.GetSymbol() not in decoupled and dist[x][xa.GetIdx()] <= 7:
            return float("inf")
    c = m.GetAtomWithIdx(x).GetNeighbors()[0]
    if c.GetSymbol() != "C":
        return MAX_HH                                     # NH, OH, SH: partners not in Table 4
    best = 0.0
    for y in range(m.GetNumAtoms()):
        if y == x or m.GetAtomWithIdx(y).GetSymbol() != "H":
            continue
        d = dist[x][y]
        if d > 6:
            continue
        pb = pair_bounds(m, dist, benz, x, y)
        if pb is None:
            if d <= 4 or (d == 5 and zigzag_or_homoallylic(m, x, y)):
                return MAX_HH
            hi = FIVE_BOND_SMALL if d == 5 else 0.0
        else:
            lo, hi, large = pb
            hi = max(abs(v) for v in (lo, hi) if v is not None)
            if large and flip and d == 3 and any(c.GetIdx() in r for r in benz):
                hi += PARA[1]                             # N = J_ortho + J_para
        best = max(best, hi)
    return best


def check_ranges(sigs, desc, mol):
    """Every reported constant must fit at least one coupling of the protons that can stand at the signal's shift:
    J <= bound - no finding; bound < J <= bound + tolerance - 'candidate (check)'; beyond - 'inconsistent'.
    tolerance = max(0.3 Hz, reporting step). Constants written as H-X couplings are not checked; constants above
    25 Hz moved to H-X by size are, when the compound has F or P. Returns (verdict, findings) with verdict '', 'candidate (check)' or 'inconsistent'."""
    if not any(sg["J"] or sg.get("Jhet_found") for sg in sigs):
        return "", ""
    m = Chem.AddHs(mol)
    dec = decoupled_nuclei(desc)
    dist = Chem.GetDistanceMatrix(m)
    benz = benzenoid_rings(m)
    hs = h_atoms(mol)
    flip, memo = [None], {}

    def flips():                                          # ring protons in pairs that the turning of the ring makes equivalent
        if flip[0] is None:
            flip[0] = {u["atom"] for u in units_of(m, dec) if u["g"] == 2}
        return flip[0]

    def bound(a, use_flip):
        key = (a, use_flip and a in flips())
        if key not in memo:
            memo[key] = range_max(m, dist, benz, h_of(m, a)[0], dec, key[1])
        return memo[key]

    all_vals = [v for sg in sigs for v in sg["J"] + sg["Japp"]]
    has_fp = any(a.GetSymbol() in ("F", "P") for a in mol.GetAtoms())
    inc, cand = [], []
    for n, sg in enumerate(sigs, 1):
        if sg["shift"] is None:
            continue
        # constants above 25 Hz were moved to H-X by size; without F or P item 3 reports them (impossible)
        vals = list(sg["J"]) + ([v for v in sg.get("Jhet_found", []) if float(v) > MAX_HH] if has_fp else [])
        if not vals:
            continue
        mt = RANGE.match(sg.get("text") or "")
        xs = (float(mt.group(1)), float(mt.group(2))) if mt else (sg["shift"],)
        if not all(SHIFT_LIMITS[0] < x < SHIFT_LIMITS[1] for x in xs):
            continue
        win = set().union(*(candidates(mol, x, hs) for x in xs))
        cap = sg.get("nH") or 0
        cands = [a for a in win if h_of(m, a) and (not cap or (3 if len(h_of(m, a)) == 3 else 1) <= cap + 1e-9)]
        if not cands:
            continue
        top = max(float(v) for v in vals)
        b = 0.0
        for a in cands:                                   # stop as soon as one candidate allows the largest constant
            b = max(b, bound(a, False))
            if b >= top:
                break
        if b < top:                                       # pairs of a turning ring: N = J_ortho + J_para
            b = max([b] + [bound(a, True) for a in cands
                           if a in flips() and (not cap or 2 <= cap + 1e-9)])
        for v in vals:
            j = float(v)
            tol = max(RANGE_TOL, step_of(v, all_vals))
            if j <= b + 1e-9:
                continue
            txt = f"#{n} {sg['shift']:.2f}: J = {v} Hz - {OUT_OF_RANGE} (upper bound {b:g} Hz; tolerance {tol:g} Hz)"
            (cand if j <= b + tol + 1e-9 else inc).append(txt)
    lines = [RANGE_A + x for x in inc] + [RANGE_B + x for x in cand]
    return ("inconsistent" if inc else "candidate (check)" if cand else ""), "\n".join(lines)


def proton_classes(m, ranks, benz, dist):
    """k (number of large couplings) or None (flexible), the large-coupling partners, and whether the proton is
    meta to an aromatic F, for every H atom."""
    out = {}
    rings = m.GetRingInfo().AtomRings()
    hetero_x = [a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() == "P"
                or (a.GetSymbol() == "F" and not any(n.GetIsAromatic() for n in a.GetNeighbors()))]
    ar_f = [a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() == "F" and any(n.GetIsAromatic() for n in a.GetNeighbors())]
    for h in m.GetAtoms():
        if h.GetSymbol() != "H":
            continue
        hi = h.GetIdx()
        c = h.GetNeighbors()[0]
        part = set()
        meta_f = any(dist[hi][f] == 4 for f in ar_f)
        if c.GetSymbol() != "C" or any(dist[hi][x] <= 4 for x in hetero_x):
            out[hi] = (None, part, meta_f)                 # NH/OH/SH, or near P / aliphatic F
            continue
        nh_c = len(h_of(m, c.GetIdx()))
        if c.GetHybridization() == Chem.HybridizationType.SP3:
            vic = any(h2.GetSymbol() == "H" for nb in c.GetNeighbors() if nb.GetIdx() != hi for h2 in nb.GetNeighbors())
            out[hi] = ((0 if (nh_c == 3 and not vic) else None), part, meta_f)
            continue
        if any(nb.GetHybridization() == Chem.HybridizationType.SP for nb in c.GetNeighbors()):
            out[hi] = (None, part, meta_f)                 # allene / ketene: 4J(H,H) about 6-7 Hz
            continue
        flexible, k = False, 0
        for nb in c.GetNeighbors():
            if nb.GetIdx() == hi:
                continue
            if c.GetIsAromatic() and nb.GetIsAromatic():  # ortho H-F (F on the ring, not CF3)
                k += sum(1 for x in nb.GetNeighbors() if x.GetSymbol() == "F")
            for h2 in nb.GetNeighbors():
                if h2.GetSymbol() != "H" or h2.GetIdx() == hi:
                    continue
                if ranks[h2.GetIdx()] == ranks[hi]:
                    flexible = True                        # equivalent vicinal partner (AA'BB'): second order at any dnu
                    continue
                b = m.GetBondBetweenAtoms(c.GetIdx(), nb.GetIdx())
                r6 = [r for r in rings if c.GetIdx() in r and nb.GetIdx() in r and len(r) == 6]
                small = [r for r in rings if c.GetIdx() in r and nb.GetIdx() in r and len(r) <= 5]
                sp2 = all(x.GetHybridization() == Chem.HybridizationType.SP2 for x in (c, nb))
                if c.GetIsAromatic() and nb.GetIsAromatic() and r6:
                    near_het = any(m.GetAtomWithIdx(y).GetSymbol() != "C" for r in r6 for y in r
                                   for x in (c.GetIdx(), nb.GetIdx()) if dist[x][y] == 1)
                    if near_het:
                        flexible = True                    # pyridine-type H2-H3, pyranone H5-H6: 4-6 Hz
                    else:
                        k += 1
                        part.add(h2.GetIdx())
                elif b.GetBondType() == Chem.BondType.DOUBLE and not small:
                    k += 1
                    part.add(h2.GetIdx())                  # H-C=C-H, cis or trans
                elif sp2 and not small and not bond_in_ring(m, c.GetIdx(), nb.GetIdx()) \
                        and not (c.GetIsAromatic() or nb.GetIsAromatic()):
                    k += 1
                    part.add(h2.GetIdx())                  # H-C(sp2)-C(sp2)-H across an open-chain single bond
                else:
                    flexible = True
        out[hi] = (None if flexible else k, part, meta_f)
    return out


def flip_ring(m, r, rings):
    """An unfused six-membered ring with one attachment point or two in para positions: a 180-degree flip
    about the axis through them swaps H-2/H-6 and H-3/H-5 at any rate of rotation."""
    ring_set = set(r)
    if len(r) != 6 or any(sum(1 for q in rings if x in q) > 1 for x in r):
        return False
    seq = [r[0]]
    while len(seq) < 6:
        nxt = [n.GetIdx() for n in m.GetAtomWithIdx(seq[-1]).GetNeighbors() if n.GetIdx() in ring_set and n.GetIdx() not in seq]
        if not nxt:
            return False
        seq.append(nxt[0])
    special = [i for i, x in enumerate(seq) if m.GetAtomWithIdx(x).GetSymbol() != "C"
               or any(n.GetSymbol() != "H" and n.GetIdx() not in ring_set for n in m.GetAtomWithIdx(x).GetNeighbors())]
    return len(special) == 1 or (len(special) == 2 and special[1] - special[0] == 3)


def units_of(m, decoupled):
    """Groups of equivalent protons with: size, granule g (how the group may be split between signals), k,
    L_X, J_max, meta to aromatic F, and the units of their large-coupling partners."""
    ranks = eq_ranks(m)
    dist = Chem.GetDistanceMatrix(m)
    benz = benzenoid_rings(m)
    rings = [tuple(r) for r in m.GetRingInfo().AtomRings()]
    cls = proton_classes(m, ranks, benz, dist)
    by = {}
    for h, (k, part, mf) in cls.items():
        by.setdefault(ranks[h], []).append(h)
    units = []
    for r, members in by.items():
        ks = {cls[h][0] for h in members}
        k = ks.pop() if len(ks) == 1 else None
        h0 = members[0]
        c = m.GetAtomWithIdx(h0).GetNeighbors()[0]
        nhc = len(h_of(m, c.GetIdx()))
        if c.GetSymbol() == "C" and nhc == 3:
            g = 3
        elif c.GetSymbol() == "C" and nhc == 1 and c.GetHybridization() != Chem.HybridizationType.SP3:
            per_ring, ok = Counter(), True
            for h in members:
                ca = m.GetAtomWithIdx(h).GetNeighbors()[0].GetIdx()
                rs = [rr for rr in rings if ca in rr and flip_ring(m, rr, rings)]
                if not rs:
                    ok = False
                    break
                per_ring[rs[0]] += 1
            g = 2 if ok and set(per_ring.values()) == {2} else 1
        else:
            g = 1
        L, jmax = (width_bound(m, dist, benz, ranks, h0, decoupled) if k is not None else (None, None))
        units.append(dict(size=len(members), k=k, g=g, L=L, jmax=jmax, rank=r, meta_f=cls[h0][2], atom=c.GetIdx(),
                          prank={ranks[p] for h in members for p in cls[h][1]}))
    rk = {u["rank"]: n for n, u in enumerate(units)}
    for u in units:
        u["partners"] = {rk[p] for p in u["prank"] if p in rk}
    return units


# ===== Signals =====

def signal_side(s, all_vals):
    """(s, W_s, tau) under the strict reading of letters and constants, or None if the signal is not counted."""
    mult = (s.get("mult") or "").strip().lower()
    if s.get("Japp") or s.get("Jhet") or s.get("Jhet_found") or s.get("app") or s.get("br") or not mult:
        return None
    if mult == "s":
        return 0, 0.0, TAU_EXTRA
    mult = mult.replace("sext", "h").replace("sept", "X")
    if not re.fullmatch(r"[dtqph]+", mult):
        return None
    counts = [LET[c] for c in mult]
    js = sorted(s["J"], key=float, reverse=True)       # the letters give the order of the couplings, largest first
    if len(js) != len(counts):
        return None
    big = sum(n for n, j in zip(counts, js) if float(j) >= LARGE)
    width = sum(n * float(j) for n, j in zip(counts, js))
    tau = sum(n * step_of(j, all_vals) / 2 for n, j in zip(counts, js)) + TAU_EXTRA
    return big, width, tau


def signal_items(sigs):
    """[(index, signal, side or None, nH, shift)]; None if an integral is fractional.  Ranges that touch (one ends
    where the next begins) are one multiplet divided by integration and are merged."""
    all_vals = [v for s in sigs for v in s.get("J", [])]
    items = []
    for n, sg in enumerate(sigs):
        nh = sg.get("nH")
        if not nh:
            continue
        if abs(nh - round(nh)) > 0.05:
            return None
        m = RANGE.match(sg.get("text", ""))
        rng = tuple(sorted(map(float, m.groups()))) if m else None
        if rng and items and items[-1][5] and min(abs(items[-1][5][0] - rng[1]), abs(items[-1][5][1] - rng[0])) <= 0.02:
            p = items.pop()
            lo, hi = min(p[5][0], rng[0]), max(p[5][1], rng[1])
            items.append((p[0], p[1], None, p[3] + round(nh), (lo + hi) / 2, (lo, hi)))
            continue
        items.append((n, sg, signal_side(sg, all_vals), round(nh), sg["shift"], rng))
    return items


# ===== Distribution =====

def max_flow(units, allowed, caps):
    """Maximum number of protons that can be placed, ignoring the groups of equivalent protons."""
    U, S = len(units), len(caps)
    N = U + S + 2
    src, snk = U + S, U + S + 1
    cap = {}
    adj = [[] for _ in range(N)]

    def edge(x, y, c):
        if (x, y) not in cap:
            adj[x].append(y)
            adj[y].append(x)
            cap.setdefault((y, x), 0)
        cap[(x, y)] = cap.get((x, y), 0) + c

    for a, u in enumerate(units):
        edge(src, a, u["size"])
        for b in range(S):
            if allowed[a][b]:
                edge(a, U + b, u["size"])
    for b in range(S):
        edge(U + b, snk, caps[b])
    flow = 0
    while True:
        prev = {src: None}
        queue = [src]
        for x in queue:
            for y in adj[x]:
                if y not in prev and cap[(x, y)] > 0:
                    prev[y] = x
                    queue.append(y)
        if snk not in prev:
            return flow
        path, y = [], snk
        while prev[y] is not None:
            path.append((prev[y], y))
            y = prev[y]
        f = min(cap[e] for e in path)
        for x, y in path:
            cap[(x, y)] -= f
            cap[(y, x)] += f
        flow += f


def feasible(units, items, free, windows):
    """Can the items be filled by the units?  free: set of item indices where the width condition is lifted;
    windows: for every item, the heavy atoms whose protons can stand at its shift (the shift windows of item 4(b)).
    Returns True, False, or None (search budget exceeded)."""
    U, S = len(units), len(items)
    allowed = [[False] * S for _ in range(U)]
    relaxed = set()
    for a, u in enumerate(units):
        for b, (n, sg, side, cap, shift, rng) in enumerate(items):
            if u["g"] > cap or u["atom"] not in windows[b]:
                continue
            s = side[0] if side else None
            if s is None or u["k"] is None or u["k"] == s or (u["meta_f"] and s == u["k"] + 1):
                allowed[a][b] = True
            elif u["k"] > s:
                width_ok = b in free or u["L"] is None or side[1] + side[2] >= u["L"] - 1e-9
                if width_ok:
                    allowed[a][b] = True
                elif cap >= u["g"] + 1 and u["partners"]:
                    allowed[a][b] = True                   # a large-coupling partner in the same signal
                    relaxed.add((a, b))
    caps = [it[3] for it in items]
    if sum(caps) != sum(u["size"] for u in units):
        return None
    if max_flow(units, allowed, caps) < sum(caps):
        return False                               # not even the proton numbers fit (granularity ignored)
    # interchangeable units (same allowed signals and group size, no partner condition) are merged
    watch = {a for a, b in relaxed} | {p for a, b in relaxed for p in units[a]["partners"]}
    merged, seen = [], {}
    for a, u in enumerate(units):
        key = (u["g"], tuple(allowed[a]))
        if a in watch:
            merged.append((a, u["size"], u["g"]))
        elif key in seen:
            i = seen[key]
            merged[i] = (merged[i][0], merged[i][1] + u["size"], u["g"])
        else:
            seen[key] = len(merged)
            merged.append((a, u["size"], u["g"]))
    U = len(merged)
    order = sorted(range(U), key=lambda i: sum(allowed[merged[i][0]]))
    place = {}
    budget = [SEARCH_BUDGET]
    failed = set()

    def partner_ok():
        for (a, b) in relaxed:
            if place.get((a, b), 0) and not any(place.get((p, b), 0) for p in units[a]["partners"]):
                return False
        return True

    def go(i):
        budget[0] -= 1
        if budget[0] < 0:
            raise TimeoutError
        if i == U:
            return all(c == 0 for c in caps) and partner_ok()
        key = (i, tuple(caps), tuple(sorted((k, x) for k, x in place.items() if k[0] in watch)))
        if key in failed:
            return False
        a, size, g = merged[order[i]]
        n = size // g
        targets = [b for b in range(S) if allowed[a][b] and caps[b] >= g]

        def spread(t, left):
            budget[0] -= 1
            if budget[0] < 0:
                raise TimeoutError
            if left == 0:
                return go(i + 1)
            if t == len(targets):
                return False
            b = targets[t]
            most = min(left, caps[b] // g)
            for x in range(most, -1, -1):
                caps[b] -= x * g
                if x:
                    place[(a, b)] = x
                ok = spread(t + 1, left - x)
                caps[b] += x * g
                place.pop((a, b), None)
                if ok:
                    return True
            return False
        ok = spread(0, n)
        if not ok:
            failed.add(key)
        return ok

    try:
        return go(0)
    except TimeoutError:
        return None


def decoupled_nuclei(desc):
    m = DECOUPLED.search(desc[:200] if desc else "")
    if not m:
        return set()
    return {"F" if "19" in x else "P" for x in re.split(r"\s?,\s?", m.group(1))}


def describe(items, units, culprits, together, windows_used):
    ks = Counter()
    flex = 0
    for u in units:
        if u["k"] is None:
            flex += u["size"]
        else:
            ks[u["k"]] += u["size"]
    struct = ", ".join(f"{n} with {k}" for k, n in sorted(ks.items()))
    parts = []
    for b in culprits:
        n, sg, side, cap, shift, rng = items[b]
        js = ", ".join(sg["J"])
        txt = f"#{n + 1} {sg['shift']:.2f} ({sg['mult']}{', J = ' + js if js else ''}, {cap}H): {side[0]} large"
        if side[0]:
            txt += f", width {side[1]:.1f} Hz"
        parts.append(txt)
    head = (f"the description cannot be distributed over the protons of the structure "
            f"(large couplings: J >= 6 Hz; protons of the structure: {struct}; others {flex}, not tested"
            + ("; each proton only at shifts where it can stand" if windows_used else "") + ")")
    if not parts:
        return head
    if together > 1:
        return head + f"; signals without a place ({together} of them must be read otherwise): " + "; ".join(parts)
    if len(parts) > 1:
        return head + "; signals without a place (reading any one of them otherwise removes the finding): " + "; ".join(parts)
    return head + "; signal without a place: " + parts[0]


SYMMETRY = "the integrals cannot be divided among the sets of equivalent protons of the structure"


def symmetry_text(units, items):
    """v2.1.5, item 1: the integrals do not fit the groups that must stand whole in one signal."""
    ch3 = sum(u["size"] // 3 for u in units if u["g"] == 3)
    pairs = sum(u["size"] // 2 for u in units if u["g"] == 2)
    whole = ", ".join(x for x in (f"{ch3} CH3 (3H{' each' if ch3 > 1 else ''})" if ch3 else "",
                                  f"{pairs} pair{'s' if pairs > 1 else ''} of ring protons (2H{' each' if pairs > 1 else ''})"
                                  if pairs else "") if x)
    ints = ", ".join(f"{it[3]:g}" for it in items)
    return (f"item 1: {SYMMETRY} (whole in one signal: {whole or 'none'}; integrals of the signals: {ints}). "
            "A CH3 group gives one signal, and so do the two ortho or the two meta protons of a ring that turns about "
            "its axis; the structure may be another compound (an isomer), or the rotation of the ring is slow")


SHIFT_LIMITS = (-5.0, 20.0)   # ppm: outside this a shift is a reading error (e.g. "3,47"); no shift windows then
CULPRIT_TRIALS = 400          # feasibility runs at most when naming the signals that block the distribution


def relax(items, bs):
    return [(it[0], it[1], None, it[3], it[4], it[5]) if b in bs else it for b, it in enumerate(items)]


def gap(a, b):
    """Distance in ppm between two signals (ranges: between their nearest edges)."""
    a0, a1 = a[5] if a[5] else (a[4], a[4])
    b0, b1 = b[5] if b[5] else (b[4], b[4])
    a0, a1 = min(a0, a1), max(a0, a1)
    b0, b1 = min(b0, b1), max(b0, b1)
    return max(0.0, b0 - a1, a0 - b1)


def check_counting(sigs, desc, mol, freq):
    """(verdict, findings): 'inconsistent', 'candidate (check)', 'symmetry' (a finding of item 1) or ''
    (no finding / not counted)."""
    items = signal_items(sigs)
    if not items or not any(it[2] is not None for it in items):
        return "", ""
    m = Chem.AddHs(mol)
    dec = decoupled_nuclei(desc)
    units = units_of(m, dec)
    if sum(u["size"] for u in units) != sum(it[3] for it in items):
        return "", ""
    # shift windows (as in the upper-bound check of item 4(b)); they are dropped when the description cannot meet
    # them even with every multiplicity ignored: that is a matter of shifts or of the structure, not of item 4(b)
    everywhere = {u["atom"] for u in units}
    hs = h_atoms(mol)
    windows = []
    for it in items:
        xs = (it[5][0], it[5][1]) if it[5] else (it[4],)
        if all(SHIFT_LIMITS[0] < x < SHIFT_LIMITS[1] for x in xs):
            windows.append(set().union(*(candidates(mol, x, hs) for x in xs)))
        else:
            windows.append(everywhere)
    used = True
    loose = relax(items, set(range(len(items))))
    if feasible(units, loose, set(), windows) is not True:
        windows, used = [everywhere] * len(items), False
        # not even the integrals fit the sets of equivalent protons: not a matter of item 4(b) but of item 1
        r = feasible(units, loose, set(), windows)
        if r is None:
            return "", ""
        if r is False:
            return "symmetry", symmetry_text(units, items)
    first = feasible(units, items, set(), windows)
    if first is None or first:
        return "", ""
    # the guard: the width condition is lifted for a signal with another signal within c * J_max Hz, J_max of the
    # protons that could stand in it with more large couplings than it shows
    allmax = max((u["jmax"] for u in units if u["jmax"]), default=0.0)
    unguarded, guards = set(), {}
    for b, it in enumerate(items):
        if it[2] is None:
            continue
        jm = max((u["jmax"] for u in units if u["jmax"] and u["k"] is not None and u["k"] > it[2][0]
                  and u["atom"] in windows[b] and u["g"] <= it[3]), default=allmax)
        guards[b] = jm
        if freq is None:
            unguarded.add(b)
            continue
        near = min((gap(it, o) for c, o in enumerate(items) if c != b), default=1e9) * freq
        if near <= GUARD_C * jm:
            unguarded.add(b)
    second = feasible(units, items, unguarded, windows) if unguarded else False
    if second is None:
        return "", ""
    # which counted signals block the distribution: the smallest sets (one or two signals) whose relaxation
    # removes the finding; their union is named
    counted = [b for b, it in enumerate(items) if it[2] is not None]
    culprits, together, trials = set(), 0, 0
    for size in (1, 2):
        for combo in combinations(counted, size):
            trials += 1
            if trials > CULPRIT_TRIALS:
                break
            if feasible(units, relax(items, set(combo)), set(), windows):
                culprits |= set(combo)
        if culprits:
            together = size
            break
    text = describe(items, units, sorted(culprits), together, used)
    if second:
        named = sorted(unguarded & culprits) or sorted(unguarded)
        jm = max(guards[b] for b in named)
        return "candidate (check)", (WIDTH_B + text + "; a neighboring signal is within "
                                     f"{GUARD_C:g} x J_max ({jm:g} Hz)" + ("" if freq else " or the frequency is not stated")
                                     + ", so strong coupling cannot be excluded")
    return "inconsistent", COUNT_A + text
