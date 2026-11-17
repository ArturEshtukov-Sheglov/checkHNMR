"""Stress test of the structure checks (item 1 and item 4(b)) with descriptions generated from real structures.

For each structure (SMILES from the OPSIN names table of the development data), a simplified first-order
description is written: protons are grouped by topologically equivalent heavy atoms; each group gets a
shift typical of its kind, an integral equal to its number of H, and a multiplicity from its vicinal
neighbours (3 bonds; one letter per neighbouring group: 1H d, 2H t, 3H q; more than 3 groups or more than
6 partners -> m). NH/OH: br s, not coupled. Long-range couplings are not written.

  clean     : expected item 1 consistent, item 4(b) not flagged
  h_wrong   : the integral of one signal changed by 1-3     -> item 1 inconsistent
  methyl_s  : (v2.1.3) the signal of a CH3 next to a carbon with H (d, t, ...) is written as a singlet
              -> item 4(b) candidate (lower bound for methyl groups)
  ch_methyl : (v2.1.4) the CH next to a CH3 doublet is written as a doublet with the CH3 constant only
              -> item 4(b) candidate (missed when a multiplet without J could be that CH)
  mult_more : one signal gets two more partners than its proton can have (extra "t", J >= 6 Hz)
              -> item 4(b) candidate (an upper-bound check: misses are expected when another proton
              of the same kind could have that many partners)

    python structure_test.py N [seed]
"""
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.environ.get("PARSER_DIR", __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "..", "check_descriptions")))
from rdkit import Chem, RDLogger  # noqa: E402
RDLogger.DisableLog("rdApp.*")
import text_checks as tc  # noqa: E402
from structure_checks import check_item1  # noqa: E402
from item4b import check_item4b, checkable  # noqa: E402

LET = {1: "d", 2: "t", 3: "q"}


def kind_shift(atom, rng):
    sym = atom.GetSymbol()
    if sym in ("N", "O", "S"):
        return round(rng.uniform(1.5, 9.5), 2), True
    if atom.GetIsAromatic():
        return round(rng.uniform(6.6, 8.4), 2), False
    hyb = atom.GetHybridization()
    if hyb == Chem.HybridizationType.SP2:
        if any(n.GetSymbol() == "O" and atom.GetBondBetweenAtoms if False else False for n in atom.GetNeighbors()):
            pass
        if any(b.GetBondType() == Chem.BondType.DOUBLE and b.GetOtherAtom(atom).GetSymbol() == "O" for b in atom.GetBonds()):
            return round(rng.uniform(9.5, 10.1), 2), False       # aldehyde
        return round(rng.uniform(4.9, 6.6), 2), False
    if hyb == Chem.HybridizationType.SP:
        return round(rng.uniform(2.0, 3.2), 2), False
    het = any(n.GetSymbol() in ("O", "N") for n in atom.GetNeighbors())
    if het:
        return round(rng.uniform(3.0, 4.6), 2), False
    if atom.GetTotalNumHs() == 3:
        return round(rng.uniform(0.8, 2.5), 2), False
    return round(rng.uniform(1.1, 2.9), 2), False


def build(smi, rng):
    mol = Chem.MolFromSmiles(smi)
    if mol is None or mol.GetNumHeavyAtoms() > 45 or not checkable(mol):
        return None
    if any(a.GetFormalCharge() for a in mol.GetAtoms()) or any(a.GetSymbol() not in "CHNOSFClBrI" and a.GetSymbol() not in ("Cl", "Br") for a in mol.GetAtoms()):
        return None
    if any(a.GetSymbol() in ("F", "P") for a in mol.GetAtoms()):
        return None                                  # H-F couplings are not generated
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False, includeChirality=False))
    groups = defaultdict(list)
    for a in mol.GetAtoms():
        if a.GetTotalNumHs():
            groups[ranks[a.GetIdx()]].append(a.GetIdx())
    if len(groups) < 2:
        return None
    info = {}
    for g, atoms in groups.items():
        a0 = mol.GetAtomWithIdx(atoms[0])
        shift, exch = kind_shift(a0, rng)
        info[g] = dict(atoms=atoms, nH=sum(mol.GetAtomWithIdx(i).GetTotalNumHs() for i in atoms), shift=shift,
                       exch=exch, arom=a0.GetIsAromatic(), atom=a0)
    # vicinal neighbour groups (heavy atoms bonded; skip N/O/S protons)
    nb = defaultdict(set)
    for g, d in info.items():
        if d["exch"]:
            continue
        for i in d["atoms"]:
            for n in mol.GetAtomWithIdx(i).GetNeighbors():
                h = ranks[n.GetIdx()]
                if h in info and not info[h]["exch"] and h != g:
                    nb[g].add(h)
    # coupled groups must be far apart (first order): resample shifts
    for g in nb:
        for h in nb[g]:
            for _ in range(20):
                if abs(info[g]["shift"] - info[h]["shift"]) >= 0.35:
                    break
                # a new shift of the same kind (an aromatic H stays in the aromatic range, etc.)
                info[h]["shift"] = kind_shift(info[h]["atom"], rng)[0]
    Jpair = {}
    for g in nb:
        for h in nb[g]:
            key = tuple(sorted((g, h)))
            if key not in Jpair:
                both_ar = info[g]["arom"] and info[h]["arom"]
                Jpair[key] = round(rng.uniform(7.2, 8.8) if both_ar else rng.uniform(5.5, 16.0), 1)
    sigs = []
    for g, d in info.items():
        if d["exch"]:
            sigs.append(dict(shift=d["shift"], nH=d["nH"], mult="br s", J=[], g=g))
            continue
        parts = []
        for h in nb[g]:
            # partner count per atom of this group: H on the neighbour atoms bonded to ONE atom of the group
            i = d["atoms"][0]
            cnt = sum(mol.GetAtomWithIdx(n.GetIdx()).GetTotalNumHs() for n in mol.GetAtomWithIdx(i).GetNeighbors()
                      if ranks[n.GetIdx()] == h)
            if cnt:
                parts.append((Jpair[tuple(sorted((g, h)))], cnt))
        parts.sort(key=lambda x: -x[0])
        if not parts:
            sigs.append(dict(shift=d["shift"], nH=d["nH"], mult="s", J=[], g=g))
        elif len(parts) > 3 or sum(c for _, c in parts) > 6 or any(c > 3 for _, c in parts):
            sigs.append(dict(shift=d["shift"], nH=d["nH"], mult="m", J=[], g=g))
        else:
            sigs.append(dict(shift=d["shift"], nH=d["nH"], mult="".join(LET[c] for _, c in parts),
                             J=[j for j, _ in parts], g=g))
    return mol, sigs


def render(sigs):
    out = []
    for s in sorted(sigs, key=lambda x: -x["shift"]):
        if s["J"]:
            out.append(f"{s['shift']:.2f} ({s['mult']}, J = {', '.join(f'{j:.1f}' for j in s['J'])} Hz, {s['nH']}H)")
        else:
            out.append(f"{s['shift']:.2f} ({s['mult']}, {s['nH']}H)")
    return "1H NMR (400 MHz, CDCl3) δ " + ", ".join(out) + "."


def main(n, seed=1):
    rng = random.Random(seed)
    # a JSON file {name: SMILES}; by default the structures of the development set (three J. Am. Chem. Soc.
    # 2026 articles outside the survey sample), or any other set given in STRUCTURES_JSON
    table = json.load(open(os.environ.get("STRUCTURES_JSON", os.path.join(os.path.dirname(os.path.abspath(__file__)), "structures_dev.json"))))
    smiles = sorted({v if isinstance(v, str) else (v.get("smiles") if isinstance(v, dict) else v[0])
                     for v in table.values() if v})
    smiles = [s for s in smiles if s and isinstance(s, str)]
    st = defaultdict(Counter); ex = defaultdict(list)
    done = 0
    while done < n:
        smi = rng.choice(smiles)
        b = build(smi, rng)
        if not b:
            continue
        mol, sigs = b
        kind = rng.choice(["clean", "h_wrong", "methyl_s", "ch_methyl", "mult_more"])
        if kind == "h_wrong":
            k = rng.randrange(len(sigs)); old = sigs[k]["nH"]
            sigs[k] = dict(sigs[k], nH=max(1, old + rng.choice([-2, -1, 1, 2, 3])))
            if sigs[k]["nH"] == old:
                continue
        if kind == "methyl_s":                       # v2.1.3
            cand = [k for k, s in enumerate(sigs) if s["mult"] not in ("s", "m", "br s") and s["nH"] % 3 == 0
                    and mol.GetAtomWithIdx(next(i for i, g in enumerate(Chem.CanonicalRankAtoms(mol, breakTies=False, includeChirality=False)) if g == s["g"])).GetTotalNumHs() == 3]
            if not cand:
                continue
            k = rng.choice(cand)
            sigs[k] = dict(sigs[k], mult="s", J=[])
        if kind == "ch_methyl":                      # v2.1.4
            pairs = [(k, i) for k, s in enumerate(sigs) if s["mult"] == "d" and s["nH"] % 3 == 0
                     for i, t in enumerate(sigs) if i != k and s["J"][0] in t["J"] and "q" in t["mult"]
                     and t["nH"] in (1, s["nH"] // 3)]
            if not pairs:
                continue
            k, i = rng.choice(pairs)
            jm = round(rng.uniform(6.0, 7.6), 1)    # a realistic 3J(CH3, CH) (the generator draws 5.5-16 Hz)
            sigs[k] = dict(sigs[k], J=[jm])
            sigs[i] = dict(sigs[i], mult="d", J=[jm])
        if kind == "mult_more":
            cand = [k for k, s in enumerate(sigs) if s["mult"] not in ("m", "br s") and len(s["J"]) < 3]
            if not cand:
                continue
            k = rng.choice(cand)
            s = sigs[k]
            mult = s["mult"] if s["mult"] != "s" else ""
            sigs[k] = dict(s, mult=mult + "t", J=s["J"] + [round(rng.uniform(6.0, 7.5), 1)])
        done += 1
        text = render(sigs)
        res = tc.check(text)
        molH = Chem.AddHs(mol)
        i1 = check_item1(text, res["_sigs"], molH, res["_mixture"])[0]
        i4b = check_item4b(res["_sigs"], mol, res["_mixture"])[0]
        c = st[kind]; c["n"] += 1
        c["item1_flag"] += i1.startswith("inconsistent")
        c["item4b_flag"] += i4b.startswith("candidate")
        c["item3_flag"] += str(res.get("item3", "")).startswith("inconsistent")
        c["item4a_flag"] += str(res.get("item4a", "")).startswith("inconsistent")
        if kind == "clean" and (i1.startswith("inconsistent") or i4b.startswith("candidate")) and len(ex["clean"]) < 8:
            ex["clean"].append(dict(smiles=smi, text=text, item1=i1, item4b=i4b))
        if kind == "mult_more" and not i4b.startswith("candidate") and len(ex["mult_more"]) < 8:
            ex["mult_more"].append(dict(smiles=smi, text=text, item4b=i4b))
    json.dump(dict(stats={k: dict(v) for k, v in st.items()}, examples=ex), open(f"structure_{n}_{seed}.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"N = {n}, seed {seed}")
    for k in ("clean", "h_wrong", "methyl_s", "ch_methyl", "mult_more"):
        c = st[k]; m = max(c["n"], 1)
        print(f"{k:10s} n={c['n']:6d}  item 1 flagged {c['item1_flag']} ({100*c['item1_flag']/m:.1f} %), "
              f"item 4(b) flagged {c['item4b_flag']} ({100*c['item4b_flag']/m:.1f} %), "
              f"item 3 {c['item3_flag']}, item 4(a) {c['item4a_flag']}")


# ===== v2.1.5: counting of large couplings, width test, range of J, sets of equivalent protons =====
# A second pass with its own random sequence (the pass above is unchanged). The constants are drawn within the
# Table-4 range of each pair (aromatic ortho 7.2-8.8 Hz as above; cis/trans, diene, HC(=O)-CH= within their
# bounds; other pairs 5.5-12 Hz), and the full check (check_descriptions.check_row) is run.
#   clean15   : expected no finding of the new rules
#   arom_more : an aromatic signal gets one more large constant ("t", 7.0-8.5 Hz)  -> counting (A, or B by the guard)
#   arom_less : an aromatic doublet is written as a singlet                          -> width test (A, or B by the guard)
#   j_range   : an aromatic ortho constant set to 11-14 Hz in both signals           -> range of J (no bound when an
#               NH/OH or a proton with partners outside Table 4 can stand at the shift: misses are expected)
#   symmetry  : a 2H signal of two equivalent protons of one aromatic ring is split into two 1H signals -> item 1
#               (or, when other protons can take the place, counting under item 4(b))

def build15(smi, rng):
    import width_count as wc
    b = build(smi, rng)
    if not b:
        return None
    mol, sigs = b
    molH = Chem.AddHs(mol)
    dist = Chem.GetDistanceMatrix(molH)
    benz = wc.benzenoid_rings(molH)
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False, includeChirality=False))
    by_g = {s["g"]: s for s in sigs}
    hof = lambda a: [n.GetIdx() for n in molH.GetAtomWithIdx(a).GetNeighbors() if n.GetSymbol() == "H"]
    jnew = {}
    for s in sigs:
        if not s["J"]:
            continue
        a = next(i for i, r in enumerate(ranks) if r == s["g"])
        arom = mol.GetAtomWithIdx(a).GetIsAromatic()
        for nb in mol.GetAtomWithIdx(a).GetNeighbors():
            h = ranks[nb.GetIdx()]
            if h not in by_g or h == s["g"] or not hof(nb.GetIdx()) or not hof(a):
                continue
            key = tuple(sorted((s["g"], h)))
            if key in jnew:
                continue
            if arom and nb.GetIsAromatic():
                jnew[key] = round(rng.uniform(7.2, 8.8), 1)
                continue
            pb = wc.pair_bounds(molH, dist, benz, hof(a)[0], hof(nb.GetIdx())[0])
            if pb and pb[1] is not None and pb[2]:
                jnew[key] = round(rng.uniform(max(pb[0], 0.5), pb[1]), 1)
            else:
                jnew[key] = round(rng.uniform(5.5, 12.0), 1)
    # the constants of build() are replaced pair by pair (same order of the letters: largest first)
    out = []
    for s in sigs:
        if not s["J"]:
            out.append(s)
            continue
        a = next(i for i, r in enumerate(ranks) if r == s["g"])
        parts = []
        for nb in mol.GetAtomWithIdx(a).GetNeighbors():
            h = ranks[nb.GetIdx()]
            key = tuple(sorted((s["g"], h)))
            if key in jnew and not any(p[2] == h for p in parts):
                cnt = sum(n.GetTotalNumHs() for n in mol.GetAtomWithIdx(a).GetNeighbors() if ranks[n.GetIdx()] == h)
                if cnt:
                    parts.append((jnew[key], cnt, h))
        parts.sort(key=lambda x: -x[0])
        if not parts or len(parts) > 3 or sum(c for _, c, _ in parts) > 6 or any(c > 3 for _, c, _ in parts):
            out.append(s)
            continue
        out.append(dict(s, mult="".join(LET[c] for _, c, _ in parts), J=[j for j, _, _ in parts], arom=mol.GetAtomWithIdx(a).GetIsAromatic(),
                        pairs={h: j for j, _, h in parts}))
    return mol, out


def main15(n, seed=1):
    import check_descriptions as cd
    from width_count import COUNT_A, WIDTH_B, RANGE_A, RANGE_B, SYMMETRY
    rng = random.Random(seed + 1515)
    table = json.load(open(os.environ.get("STRUCTURES_JSON", os.path.join(os.path.dirname(os.path.abspath(__file__)), "structures_dev.json"))))
    smiles = sorted({v if isinstance(v, str) else (v.get("smiles") if isinstance(v, dict) else v[0])
                     for v in table.values() if v})
    smiles = [s for s in smiles if s and isinstance(s, str)]
    kinds = ["clean15", "arom_more", "arom_less", "j_range", "symmetry"]
    st = defaultdict(Counter); ex = defaultdict(list)
    done = 0
    while done < n:
        smi = rng.choice(smiles)
        b = build15(smi, rng)
        if not b:
            continue
        mol, sigs = b
        kind = rng.choice(kinds)
        ar = [k for k, s in enumerate(sigs) if s.get("arom") and s["J"]]
        if kind == "arom_more":
            if not ar:
                continue
            k = rng.choice(ar)
            sigs[k] = dict(sigs[k], mult=sigs[k]["mult"] + "t", J=sigs[k]["J"] + [round(rng.uniform(7.0, 8.5), 1)])
        if kind == "arom_less":
            cand = [k for k in ar if sigs[k]["mult"] == "d"]
            if not cand:
                continue
            k = rng.choice(cand)
            sigs[k] = dict(sigs[k], mult="s", J=[])
        if kind == "j_range":
            pairs = [(k, i) for k in ar for i in ar if i != k and sigs[i]["g"] in sigs[k].get("pairs", {})]
            if not pairs:
                continue
            k, i = rng.choice(pairs)
            jo = sigs[k]["pairs"][sigs[i]["g"]]
            jn = round(rng.uniform(11.0, 14.0), 1)
            for x in (k, i):
                js = [jn if j == jo else j for j in sigs[x]["J"]]
                order = sorted(range(len(js)), key=lambda t: -js[t])
                sigs[x] = dict(sigs[x], J=[js[t] for t in order], mult="".join(sigs[x]["mult"][t] for t in order))
        if kind == "symmetry":
            ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False, includeChirality=False))
            rings = mol.GetRingInfo().AtomRings()
            same_ring = lambda g: any(all(i in r for i in [a for a, x in enumerate(ranks) if x == g]) for r in rings)
            cand = [k for k in ar if sigs[k]["nH"] == 2 and same_ring(sigs[k]["g"])]
            if not cand:
                continue
            k = rng.choice(cand)
            s = sigs[k]
            sigs[k] = dict(s, nH=1, shift=round(s["shift"] + 0.03, 2))
            sigs.append(dict(s, nH=1, shift=round(s["shift"] - 0.03, 2)))
        done += 1
        text = render(sigs)
        res = cd.check_row(dict(id="t", description=text, smiles=smi, hetero="", formula="", opsin_status=""))
        f4 = res["findings4b"].split("\n")
        c = st[kind]; c["n"] += 1
        cnt = any(x.startswith(COUNT_A) for x in f4); wid = any(x.startswith(WIDTH_B) for x in f4)
        rng_a = any(x.startswith(RANGE_A) for x in f4); rng_b = any(x.startswith(RANGE_B) for x in f4)
        sym = SYMMETRY in res["findings1"]
        c["count"] += cnt; c["width"] += wid; c["range"] += rng_a or rng_b; c["sym"] += sym
        c["any"] += cnt or wid or rng_a or rng_b or sym
        if kind == "clean15" and (cnt or wid or rng_a or rng_b or sym) and len(ex["clean15"]) < 8:
            ex["clean15"].append(dict(smiles=smi, text=text, f4=res["findings4b"], f1=res["findings1"]))
    json.dump(dict(stats={k: dict(v) for k, v in st.items()}, examples=ex), open(f"structure15_{n}_{seed}.json", "w"),
              ensure_ascii=False, indent=1)
    for k in kinds:
        c = st[k]; m = max(c["n"], 1)
        print(f"v215 {k:9s} n={c['n']:6d}  any new-rule finding {c['any']} ({100*c['any']/m:.1f} %): counting {c['count']}, "
              f"width {c['width']}, range {c['range']} ({100*c['range']/m:.1f} %), item 1 sets {c['sym']} ({100*c['sym']/m:.1f} %)")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    main15(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1)          # v2.1.5
