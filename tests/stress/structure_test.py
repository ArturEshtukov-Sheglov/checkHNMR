"""Stress test of the structure checks (item 1 and item 4(b)) with descriptions generated from real structures.

For each structure (SMILES from the OPSIN names table of the development data), a simplified first-order
description is written: protons are grouped by topologically equivalent heavy atoms; each group gets a
shift typical of its kind, an integral equal to its number of H, and a multiplicity from its vicinal
neighbours (3 bonds; one letter per neighbouring group: 1H d, 2H t, 3H q; more than 3 groups or more than
6 partners -> m). NH/OH: br s, not coupled. Long-range couplings are not written.

  clean     : expected item 1 consistent, item 4(b) not flagged
  h_wrong   : the integral of one signal changed by 1-3     -> item 1 inconsistent
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
        kind = rng.choice(["clean", "h_wrong", "mult_more"])
        if kind == "h_wrong":
            k = rng.randrange(len(sigs)); old = sigs[k]["nH"]
            sigs[k] = dict(sigs[k], nH=max(1, old + rng.choice([-2, -1, 1, 2, 3])))
            if sigs[k]["nH"] == old:
                continue
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
    for k in ("clean", "h_wrong", "mult_more"):
        c = st[k]; m = max(c["n"], 1)
        print(f"{k:10s} n={c['n']:6d}  item 1 flagged {c['item1_flag']} ({100*c['item1_flag']/m:.1f} %), "
              f"item 4(b) flagged {c['item4b_flag']} ({100*c['item4b_flag']/m:.1f} %), "
              f"item 3 {c['item3_flag']}, item 4(a) {c['item4a_flag']}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1)
