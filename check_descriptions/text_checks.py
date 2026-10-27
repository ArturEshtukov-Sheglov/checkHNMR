"""Checks made from the text of a description alone: items 3 (coupling partners),
4(a) (number of J) and 6(b) (strong coupling, dnu/J) of the pass-3 protocol.
Used by check_descriptions.py."""

import re

from description_parser import parse_description, hetero_info, f_pairs_strong, expected_j, decimals, normalize_text


# ===== Constants =====

MAX_HH_J = 25                    # Hz: a larger constant cannot be an H-H coupling (it is H-F or H-P)
HETERO_J_TOLERANCE = 0.6         # Hz: a 1H constant this close to a 19F/31P constant is taken as H-X
MIN_J_TOLERANCE = 0.3            # Hz: smallest tolerance for two equal constants (protocol, item 3)
EPS = 1e-9                       # rounding guard for float comparisons
AROMATIC_RANGE = (6.0, 9.6)      # ppm: signals that can be aromatic protons
DNU_J_INCONSISTENT = 6           # item 6(b): dnu/J below this is inconsistent with first order
DNU_J_FIRST_ORDER = 8            # item 6(b): dnu/J from 6 to below 8 is borderline, 8 or more is ok
NO_J_RATIO = 99                  # dnu/J written when J is 0
# Reverse check of 19F/31P constants that must show up in the 1H description:
GEMINAL_HF_RANGE = (40, 100)     # Hz: H-C-F (geminal) constants
ONE_BOND_PH_MIN = 150            # Hz: P-H constants above this are one-bond
BIG_J_MIN_TOLERANCE = 3.0        # Hz: tolerance for comparing such large constants...
BIG_J_REL_TOLERANCE = 0.1        # ...or 10 % of the value, whichever is larger
HIDDEN_RANGE = {"F": (3.8, 6.6), "P": (4.0, 9.0)}   # ppm: where the proton of an H-C-F / P-H resonates

# The description is of a mixture: a "pair" may be the same proton in two components
# v2: a description that says it lists only some signals ("The other signals are overlapped with the
# signals of the major isomer"): a missing partner may be one of the signals not listed
PARTIAL = re.compile(r"other signals (?:are|were) (?:overlapped|obscured|not (?:observed|resolved|listed))"
                     r"|overlap(?:ped|s)? with (?:the )?signals of", re.I)
MIXTURE = re.compile(r"isomer|rotamer|diastereomer|\bmajor\b|\bminor\b|mixture"
                     r"|\bdiast\b|\bd(?:major|minor)\b|(?-i:\b\d(?:\.\d+)?\s?H,?\s(?:d|dia|diast)\s?[12]\b)|\(\s?dia(?:st)?\.?\s?[12]\b|conformer", re.I)  # v2.1: "both diast", "dmajor", "[1H d1, 1H d2]"
NUCLEUS_NAME = {"F": "19F", "P": "31P"}


# ===== Coupling partners =====

def step_of(v, all_vals):
    """Reporting step of a constant: 1 Hz for '7', 0.1 or 0.5 Hz for '7.5', 0.01 Hz for '7.25'."""
    d = decimals(v)
    if d == 0:
        return 1.0
    if d == 1:
        one_dec = [x for x in all_vals if decimals(x) == 1]
        if one_dec and all(x.endswith((".0", ".5")) for x in one_dec):
            return 0.5
        return 0.1
    return 10 ** -d


def methyl_like(sig):
    """3H, 6H or 9H signal: a methyl group (or several equivalent ones)."""
    n = sig.get("nH")
    return n is not None and n >= 3 and abs(n / 3 - round(n / 3)) < 1e-6 and n <= 9


def can_pair(s, t):
    """Two methyl signals are never coupling partners of each other: their protons
    are at least four bonds apart; equal constants mean a common partner (e.g. the
    CH of an isopropyl group), not a mutual coupling."""
    return not (methyl_like(s) and methyl_like(t))


def same_j(a, b, all_vals):
    """Two constants are equal within the protocol tolerance (the larger of 0.3 Hz and the reporting step)."""
    return abs(float(a) - float(b)) <= max(MIN_J_TOLERANCE, step_of(a, all_vals), step_of(b, all_vals)) + EPS


def n_constants(s):
    """All constants reported for a signal (H-H, apparent, heteronuclear)."""
    return len(s["J"]) + len(s["Japp"]) + len(s["Jhet"]) + len(s.get("Jhet_found", []))


def verdict_6b(pairs, not_first_order):
    """Verdict of item 6(b) from the pairs of signals sharing a J. Pairs in which both
    signals belong to a system already found not first-order under 6(a)
    (indices in not_first_order) are not evaluated: dnu/J has no meaning there."""
    if not pairs:
        return "no pair (nothing to check)", "no pair of signals with a shared J - nothing to check"

    skipped = [p for p in pairs if p["i"] in not_first_order and p["j"] in not_first_order]
    used = [p for p in pairs if p not in skipped]
    lines = [p["text"] for p in used if p["status"] in ("INCONSISTENT", "borderline", "undetermined")]
    if skipped:
        lines.append(f"{len(skipped)} pair(s) not evaluated: both signals belong to a system that is not "
                     "first-order under 6(a)")
    if not used:
        return "not applicable (6(a))", "\n".join(lines)

    if any(p["status"] == "INCONSISTENT" for p in used):
        v = "inconsistent"
    elif any(p["status"] == "borderline" for p in used):
        v = "borderline (subcategory)"
    elif any(p["status"] == "undetermined" for p in used):
        v = "cannot be determined"
    else:
        v = "consistent"
        lines.insert(0, f"{len(used)} pair(s) of different signals with a shared J; all dnu/J >= 8 "
                        "or exempt (AB, J_app)")
    return v, "\n".join(lines)


# ===== Steps of check() =====

def het_text(het):
    """{'F': 'absent', 'P': 'decoupled'} -> '19F: absent, 31P: decoupled' (readable in the findings)."""
    return ", ".join(f"{NUCLEUS_NAME.get(n, n)}: {st}" for n, st in het.items())


def move_heteronuclear(sigs, het, hetJ, all_vals, arom_hx_possible, x_in_structure=None):
    """Constants of a 1H signal that are couplings to 19F/31P are moved from J to Jhet_found.
    Order of decisions for each constant: (1) J > 25 Hz cannot be an H-H coupling;
    (2) a constant found in another 1H signal is an H-H coupling; (3) otherwise, a
    constant equal to one in the heteronuclear description (within 0.6 Hz: only the presence
    of the splitting is checked for heteronuclei) is taken as H-X.
    v2: x_in_structure = False (the structure has no F or P): a constant above 25 Hz cannot be
    explained at all and is an item-3 inconsistency.
    Returns (inconsistencies for item 3, candidates for item 3, info lines)."""
    f3, cand3, info3 = [], [], []

    def has_h_partner(i, v):
        return any(j != i and can_pair(sigs[i], t) and any(same_j(v, w, all_vals) for w in t["J"] + t["Japp"])
                   for j, t in enumerate(sigs))

    for k, s in enumerate(sigs, 1):
        aromatic_signal = AROMATIC_RANGE[0] <= s["shift"] <= AROMATIC_RANGE[1]
        moved = [v for v in s["J"] if float(v) > MAX_HH_J or
                 (not has_h_partner(k - 1, v) and any(abs(float(v) - float(w)) <= HETERO_J_TOLERANCE for w in hetJ)
                  and (arom_hx_possible or not aromatic_signal))]
        s["J"] = [v for v in s["J"] if v not in moved]
        s["Jhet_found"] = moved
        for v in moved:
            why = ("larger than any H-H coupling" if float(v) > MAX_HH_J
                   else "no 1H partner, same value in the heteronuclear description")
            if float(v) > MAX_HH_J and x_in_structure is False:              # v2
                f3.append(f"#{k} {s['shift']:.2f}: J = {v} Hz - {why}, and the structure has no F or P: "
                          "impossible for this compound")
            elif float(v) > MAX_HH_J and not hetJ:
                cand3.append(f"#{k} {s['shift']:.2f}: J = {v} Hz - {why}; the partner must be 19F or 31P, "
                             f"whose descriptions do not show it ({het_text(het)}) - partner unverifiable")
            else:
                info3.append(f"info: #{k} {s['shift']:.2f}: J = {v} taken as coupling to 19F/31P ({why}) "
                             "- confirm with the structure")
    return f3, cand3, info3


def check_4a(sigs):
    """Item 4(a): the number of reported constants matches the multiplicity (m and AB are not checked)."""
    f4 = []
    for i, s in enumerate(sigs, 1):
        nJ = n_constants(s)
        if s["mult"] is None:
            if nJ:
                f4.append(f"#{i} {s['shift']:.2f}: J without multiplicity")
            continue
        exp = expected_j(s["mult"])
        if exp is None or s["mult"] == "AB":
            continue
        if nJ != exp and nJ + s.get("Jeq", 0) != exp:   # v2: "dd, 2J = 3J = 13.6 Hz" = two equal J
            f4.append(f"#{i} {s['shift']:.2f} ({s['mult']}): {nJ} J reported, {exp} expected")
    return f4


def check_3_partners(sigs, het, all_vals, partial=False):
    """Item 3: every H-H constant has a partner signal with the same constant; every H-X constant
    a heteronucleus that shows the splitting. Returns (findings, candidates for manual checking)."""
    f3, cand3 = [], []
    for i, s in enumerate(sigs):
        for v in s["J"]:
            partners = [j for j, t in enumerate(sigs)
                        if j != i and can_pair(s, t) and any(same_j(v, w, all_vals) for w in t["J"] + t["Japp"])]
            if partners:
                continue

            reason = []
            if any(t["mult"] in ("m", None) or (t["br"] and not t["J"]) for k, t in enumerate(sigs) if k != i):
                reason.append("partner may be an m/br signal")
            if partial:                                   # v2
                reason.append("partner may be among the signals not listed (the description says so)")
            # a heteronucleus can be the partner only if its coupling cannot be checked
            # (description absent or proton-decoupled); a proton-coupled 19F/31P description
            # without this constant shows that the coupling is not to the heteronucleus
            unverifiable_het = [n for n, st in het.items() if st == "decoupled"]
            if unverifiable_het:
                reason.append("may be a coupling to " + "/".join(NUCLEUS_NAME[n] for n in unverifiable_het)
                              + " (decoupled spectrum)")
            cand3.append(f"#{i+1} {s['shift']:.2f}: J = {v} - no partner"
                         + ("; " + "; ".join(reason) if reason else
                            " (no m/br signal, no unverifiable heteronucleus): likely item-3 inconsistency"))

        for v in s["Jhet"]:
            nuc = "P" if re.search(r"P", str(s["text"])) and not re.search(r"F", str(s["text"])) else "F"
            st = het.get(nuc, "absent")
            if st in ("absent", "decoupled"):
                cand3.append(f"#{i+1} {s['shift']:.2f}: J(H,X) = {v} - partner unverifiable (heteronuclear description {st})")
            elif st == "singlets":
                f3.append(f"#{i+1} {s['shift']:.2f}: J(H,X) = {v} but all {nuc} signals are singlets")
    return f3, cand3


def pairs_6b(sigs, freq, all_vals):
    """Item 6(b): pairs of different signals that share a constant, with dnu/J and a status."""
    seen, pairs = set(), []
    for i, s in enumerate(sigs):
        for v in s["J"]:
            for j, t in enumerate(sigs):
                if j <= i or not can_pair(s, t):
                    continue
                for w in t["J"] + t["Japp"]:
                    if not same_j(v, w, all_vals) or (i, j, v) in seen:
                        continue
                    seen.add((i, j, v))

                    if w in t["Japp"]:
                        pairs.append(dict(i=i, j=j, status="exempt"))       # apparent splitting
                        continue
                    # v2.1: written as an AB system, or two shifts given with one bracket ("2.85 and 2.70 (AB part
                    # of ABX system, J = 13.3 ...)"): the author describes them together, not as first-order signals
                    if s["mult"] == "AB" or t["mult"] == "AB" or \
                            (s.get("group") is not None and s.get("group") == t.get("group")):
                        pairs.append(dict(i=i, j=j, status="exempt"))
                        continue
                    if n_constants(s) == 1 and n_constants(t) == 1 and s["mult"] == "d" and t["mult"] == "d":
                        pairs.append(dict(i=i, j=j, status="exempt"))       # isolated AB pair
                        continue
                    if freq is None:
                        pairs.append(dict(i=i, j=j, status="undetermined",
                                          text=f"#{i+1}/#{j+1}: frequency not stated - cannot be determined"))
                        continue

                    dnu = abs(s["shift"] - t["shift"]) * freq
                    J = (float(v) + float(w)) / 2
                    r = dnu / J if J else NO_J_RATIO
                    status = "INCONSISTENT" if r < DNU_J_INCONSISTENT else "borderline" if r < DNU_J_FIRST_ORDER else "ok"
                    pairs.append(dict(i=i, j=j, status=status,
                                      text=f"#{i+1} {s['shift']:.2f} / #{j+1} {t['shift']:.2f}: J = {v}/{w}, "
                                           f"dnu = {dnu:.1f} Hz, dnu/J = {r:.1f} - {status}"))
    return pairs


def pairs_strong_ff(sigs, hetero_text):
    """Protons coupled to a strongly coupled 19F pair (A, B) are X parts of an ABX-type system;
    first-order notation with J is not valid for them. Returns pairs for item 6(b)."""
    pairs = []
    for ratio, jff, others in (f_pairs_strong(hetero_text) if hetero_text else []):
        if ratio >= DNU_J_FIRST_ORDER:
            continue
        status = "INCONSISTENT" if ratio < DNU_J_INCONSISTENT else "borderline"
        for k, s in enumerate(sigs):
            js = s["Jhet_found"] + s["Jhet"]
            if s["mult"] in (None, "m") or s["Japp"] or not js:
                continue
            if any(abs(float(v) - float(w)) <= HETERO_J_TOLERANCE for v in js for w in others):
                pairs.append(dict(i=k, j=k, status=status,
                                  text=f"#{k+1} {s['shift']:.2f}: coupled to two strongly coupled 19F "
                                       f"(J_FF = {jff:.1f} Hz, dnu/J_FF = {ratio:.1f}) - X part of an ABX-type "
                                       f"system reported with first-order J - {status}"))
    return pairs


def check_3_reverse(sigs, hetJ_lab):
    """A geminal H-F constant (40-100 Hz) or a one-bond P-H constant (> 150 Hz) reported in a
    proton-coupled 19F/31P description must appear as a splitting in a 1H signal; larger 19F
    constants (> 100 Hz) are F-F couplings and are not used. If an m/br signal lies where such a
    proton resonates, the partner is unverifiable, not missing. Returns (findings, candidates)."""
    f3, cand3 = [], []
    big_1h = [float(v) for s in sigs for v in s["Jhet_found"] + s["Jhet"] if float(v) > MAX_HH_J]
    for nuc, w in sorted(set(hetJ_lab), key=lambda x: float(x[1])):
        w_f = float(w)
        if not ((nuc == "F" and GEMINAL_HF_RANGE[0] <= w_f <= GEMINAL_HF_RANGE[1])
                or (nuc == "P" and w_f > ONE_BOND_PH_MIN)):
            continue
        if any(abs(w_f - x) <= max(BIG_J_MIN_TOLERANCE, BIG_J_REL_TOLERANCE * w_f) for x in big_1h):
            continue

        lo, hi = HIDDEN_RANGE[nuc]
        hidden = [t for t in sigs if (t["mult"] in ("m", None) or (t["br"] and not t["J"]))
                  and lo <= t["shift"] <= hi]
        msg = (f"{NUCLEUS_NAME[nuc]} description: J = {w} Hz ({'H-C-F' if nuc == 'F' else 'P-H'}), "
               f"but no 1H signal shows such a splitting")
        if hidden:
            cand3.append(msg + "; the proton may be in an m/br signal (partner unverifiable)")
        else:
            f3.append(msg)
    return f3, cand3


# ===== All text checks of one description =====

def check(desc, hetero_text="", arom_hx_possible=True, x_in_structure=None):
    """Items 3, 4(a) and 6(b) of one description; hetero_text = the 19F/31P descriptions after it;
    arom_hx_possible = False if no aromatic proton of the structure is near F or P."""
    desc, hetero_text = normalize_text(desc), normalize_text(hetero_text or "")    # v2.1
    freq, sigs = parse_description(desc.replace("−", "-"))
    het, hetJ, hetJ_lab = hetero_info(hetero_text) if hetero_text else ({"F": "absent", "P": "absent"}, [], [])
    all_vals = [v for s in sigs for v in s["J"] + s["Japp"]]

    fx3, cand3, info3 = move_heteronuclear(sigs, het, hetJ, all_vals, arom_hx_possible, x_in_structure)

    notes = []
    if not sigs:
        notes.append("no signals parsed")
    mixture = bool(MIXTURE.search(desc))
    if mixture:
        notes.append("mixture/rotamers: a 'pair' may be the same proton in two components")

    f4 = check_4a(sigs)
    f3, c3 = check_3_partners(sigs, het, all_vals, partial=bool(PARTIAL.search(desc)))
    f3 = fx3 + f3                                                                      # v2
    cand3 += c3

    pairs = pairs_6b(sigs, freq, all_vals) + pairs_strong_ff(sigs, hetero_text)
    v6, f6 = verdict_6b(pairs, set())
    v4 = "inconsistent" if f4 else "consistent"

    r3, rc3 = check_3_reverse(sigs, hetJ_lab)
    f3 += r3
    cand3 += rc3

    inc3_idx = {int(m.group(1)) - 1 for x in f3 + [c for c in cand3 if "likely item-3" in c]
                for m in [re.match(r"#(\d+) ", x)] if m}
    v3 = ("inconsistent (check)" if f3 or any("likely item-3" in x for x in cand3)
          else "partner unverifiable? (check)" if cand3 else "consistent")
    return dict(freq=freq, n_signals=len(sigs), item3=v3, item4a=v4, item6b=v6, _sigs=sigs, _mixture=mixture,
                _pairs=pairs, _inc3=inc3_idx, findings3="\n".join(f3 + cand3), info="\n".join(info3),
                findings4a="\n".join(f4), findings6b=f6, note="; ".join(notes))
