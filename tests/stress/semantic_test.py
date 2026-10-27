"""Semantic stress test of the text checks (items 3, 4(a), 6(b)) with synthetic first-order spin systems.

A consistent description is generated from a coupling graph: every constant appears in both partners,
the letter of each coupling follows the number of equivalent protons of the partner (1H -> d, 2H -> t,
3H -> q), and coupled signals are far apart (dnu/J >= 10 at 400 MHz). Then one known error is put in:

  clean      : nothing changed                         -> expected: no finding
  j_mismatch : one constant of a pair changed by 1-3 Hz -> item 3 inconsistent
  j_missing  : one constant removed from a signal with 2+ constants (multiplicity kept) -> item 4(a)
  j_extra    : a constant added to a singlet           -> item 4(a)
  strong     : two coupled signals moved close (dnu/J 1.5-5) -> item 6(b) inconsistent

    python semantic_test.py N [seed]
"""
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.environ.get("PARSER_DIR", __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "..", "check_descriptions")))
import text_checks as tc  # noqa: E402

LET = {1: "d", 2: "t", 3: "q"}
FREQ = 400


def gen_system(rng):
    n = rng.randint(4, 10)
    shifts, tries = [], 0
    while len(shifts) < n and tries < 1000:
        tries += 1
        s = round(rng.uniform(0.8, 8.6), 2)
        if all(abs(s - x) >= 0.45 for x in shifts):
            shifts.append(s)
    n = len(shifts)
    nH = [rng.choice([1, 1, 1, 2, 2, 3]) for _ in range(n)]
    used_J = []
    edges = {}
    for i in range(n):
        for j in range(i + 1, n):
            if nH[i] == 3 and nH[j] == 3:          # two methyl groups are never coupling partners
                continue
            if rng.random() < 0.28:
                for _ in range(50):
                    J = round(rng.uniform(1.0, 16.5), 1)
                    if all(abs(J - u) >= 0.7 for u in used_J):
                        break
                else:
                    continue
                used_J.append(J)
                edges[(i, j)] = J
    sigs = []
    for i in range(n):
        parts = []
        for (a, b), J in edges.items():
            if i in (a, b):
                partner = b if i == a else a
                parts.append((J, LET[nH[partner]]))
        parts.sort(key=lambda x: -x[0])
        if len(parts) > 3:                       # keep multiplicities readable: at most 3 couplings
            for J, _ in parts[3:]:
                for k in [k for k, v in edges.items() if v == J]:
                    del edges[k]
            return gen_system(rng)
        sigs.append(dict(s=shifts[i], nH=nH[i], parts=parts))
    return sigs, edges


def render(sigs):
    out = []
    for g in sigs:
        if g["parts"]:
            mult = "".join(l for _, l in g["parts"])
            js = ", ".join(f"{J:.1f}" for J, _ in g["parts"])
            out.append(f"{g['s']:.2f} ({mult}, J = {js} Hz, {g['nH']}H)")
        else:
            out.append(f"{g['s']:.2f} (s, {g['nH']}H)")
    return "1H NMR (400 MHz, CDCl3) δ " + ", ".join(out) + "."


def inject(sigs, edges, kind, rng):
    sigs = [dict(g, parts=list(g["parts"])) for g in sigs]
    if kind == "clean":
        return sigs, True
    if kind == "j_mismatch":
        cand = [i for i, g in enumerate(sigs) if g["parts"]]
        if not cand:
            return sigs, False
        i = rng.choice(cand); k = rng.randrange(len(sigs[i]["parts"]))
        J, l = sigs[i]["parts"][k]
        allJ = [x for g in sigs for x, _ in g["parts"]]
        for _ in range(50):
            new = round(J + rng.choice([-1, 1]) * rng.uniform(1.0, 3.0), 1)
            if new > 0.8 and all(abs(new - x) >= 0.6 for x in allJ):
                sigs[i]["parts"][k] = (new, l)
                return sigs, True
        return sigs, False
    if kind == "j_missing":
        cand = [i for i, g in enumerate(sigs) if len(g["parts"]) >= 2]
        if not cand:
            return sigs, False
        i = rng.choice(cand)
        sigs[i]["drop"] = rng.randrange(len(sigs[i]["parts"]))
        return sigs, True
    if kind == "j_extra":
        cand = [i for i, g in enumerate(sigs) if not g["parts"]]
        if not cand:
            return sigs, False
        i = rng.choice(cand); sigs[i]["extra"] = round(rng.uniform(1.0, 9.0), 1)
        return sigs, True
    if kind == "strong":
        if not edges:
            return sigs, False
        (a, b), J = rng.choice(list(edges.items()))
        ratio = rng.uniform(1.5, 5.0)
        sigs[b]["s"] = round(sigs[a]["s"] + rng.choice([-1, 1]) * ratio * J / FREQ, 3)
        return sigs, True


def render_err(sigs):
    out = []
    for g in sigs:
        parts = list(g["parts"])
        mult = "".join(l for _, l in parts) if parts else "s"
        js = [f"{J:.1f}" for J, _ in parts]
        if "drop" in g:
            js.pop(g["drop"])
        if "extra" in g:
            js.append(f"{g['extra']:.1f}")
        sh = f"{g['s']:.3f}" if round(g["s"], 2) != g["s"] else f"{g['s']:.2f}"
        out.append(f"{sh} ({mult}, J = {', '.join(js)} Hz, {g['nH']}H)" if js else f"{sh} ({mult}, {g['nH']}H)")
    return "1H NMR (400 MHz, CDCl3) δ " + ", ".join(out) + "."


TARGET = {"j_mismatch": ("item3", "inconsistent"), "j_missing": ("item4a", "inconsistent"),
          "j_extra": ("item4a", "inconsistent"), "strong": ("item6b", "inconsistent")}


def flagged(v):
    return v is not None and str(v).startswith("inconsistent")


def main(n, seed=1):
    rng = random.Random(seed)
    stats = defaultdict(Counter); ex = defaultdict(list)
    kinds = ["clean", "j_mismatch", "j_missing", "j_extra", "strong"]
    for _ in range(n):
        sigs, edges = gen_system(rng)
        kind = rng.choice(kinds)
        s2, ok = inject(sigs, edges, kind, rng)
        if not ok:
            continue
        text = render_err(s2)
        r = tc.check(text)
        st = stats[kind]; st["n"] += 1
        for item in ("item3", "item4a", "item6b"):
            if flagged(r.get(item)):
                st["flag_" + item] += 1
        if kind == "clean":
            if any(flagged(r.get(x)) for x in ("item3", "item4a", "item6b")):
                st["false_any"] += 1
                if len(ex["clean"]) < 5:
                    ex["clean"].append(dict(text=text, r={k: r.get(k) for k in ("item3", "item4a", "item6b", "findings3", "findings4a", "findings6b")}))
        else:
            item, _ = TARGET[kind]
            if flagged(r.get(item)):
                st["caught"] += 1
            elif len(ex[kind]) < 5:
                ex[kind].append(dict(text=text, r={k: r.get(k) for k in ("item3", "item4a", "item6b", "findings3", "findings4a", "findings6b")}))
            others = [x for x in ("item3", "item4a", "item6b") if x != item and flagged(r.get(x))]
            if others:
                st["side_flags"] += 1
    json.dump(dict(stats={k: dict(v) for k, v in stats.items()}, examples=ex),
              open(f"semantic_{n}_{seed}.json", "w"), ensure_ascii=False, indent=1)
    print(f"N = {n}, seed {seed}")
    for k in kinds:
        st = stats[k]
        if k == "clean":
            print(f"{k:11s} n={st['n']:6d}  any false finding: {st['false_any']} ({100*st['false_any']/max(st['n'],1):.2f} %)"
                  f"  [item3 {st['flag_item3']}, 4a {st['flag_item4a']}, 6b {st['flag_item6b']}]")
        else:
            item = TARGET[k][0]
            print(f"{k:11s} n={st['n']:6d}  caught under {item}: {st['caught']} ({100*st['caught']/max(st['n'],1):.1f} %)"
                  f"  other items also flagged: {st['side_flags']}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1)
