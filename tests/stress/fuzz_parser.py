"""Stress test of the V2 description parser with synthetic 1H descriptions.

Each description is generated from a known list of signals (ground truth), written in a clean
canonical form, then rewritten with one or more "format noises" that do not change the meaning
(dashes, spaces, order of the parts in the bracket, copy-paste artefacts ...). The parser output is
compared with the ground truth signal by signal.

    python fuzz_parser.py N [seed]        -> fuzz_N.json + printed summary
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __import__("os").environ.get("PARSER_DIR", __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "..", "..", "check_descriptions")))
from description_parser import parse_description  # noqa: E402

LETTERS = {"d": 1, "t": 2, "q": 3, "p": 4}
MULTS = (["s"] * 14 + ["d"] * 16 + ["t"] * 9 + ["q"] * 5 + ["p"] * 2 + ["dd"] * 10 + ["dt"] * 4 +
         ["td"] * 4 + ["ddd"] * 4 + ["qd"] * 1 + ["dq"] * 1 + ["tt"] * 1 + ["sept"] * 1 + ["m"] * 18)


def n_j(code):
    if code in ("s", "m"):
        return 0
    if code == "sept":
        return 1
    return len(code)


def gen_signal(rng):
    mult = rng.choice(MULTS)
    app = mult in ("t", "q", "td", "dt") and rng.random() < 0.08
    br = mult in ("s", "d", "t") and rng.random() < 0.08
    rng_ = mult == "m" and rng.random() < 0.6
    s = round(rng.uniform(0.6, 11.5), 2)
    s2 = round(s - rng.uniform(0.02, 0.4), 2) if rng_ else None
    J = [round(rng.uniform(0.6, 17.5), 1) for _ in range(n_j(mult))]
    J.sort(reverse=True)
    nH = rng.choice([1, 1, 1, 1, 2, 2, 2, 3, 3, 4, 5, 6, 9])
    label = rng.choice(["ArH", "OCH3", "NH", "OH", "H-3", "H-2′", "CH2", "2 × CH3", "C6H5", "NCH2", "H-5, H-6",
                        "CO2CH2CH3", "SiMe3", "CHPh2", "H-1a", "H3-18"])
    return dict(s=s, s2=s2, mult=mult, app=app, br=br, J=J, nH=nH, label=label)


def fmt(v, dec):
    return f"{v:.{dec}f}"


# ---------- rendering with options ----------

def render(sigs, o):
    parts = []
    for g in sigs:
        shift = fmt(g["s"], o["sdec"])
        if g["s2"] is not None:
            shift = shift + o["range_dash"] + fmt(g["s2"], o["sdec"])
        if o["ppm_after_shift"]:
            shift += " ppm"
        m = g["mult"]
        if g["app"]:
            m = o["app_word"].format(m)
        if g["br"]:
            # "brd" exists, "brapp t" does not: the joined form only before a plain multiplicity
            m = (o["br_word"] if not (g["app"] and "{} " not in o["br_word"] and " {}" not in o["br_word"]) else "br {}").format(m)
        items = [m]
        if g["J"]:
            vals = [fmt(j, o["jdec"]) for j in g["J"]]
            if o["j_indexed"] and len(vals) > 1:
                items.append(", ".join(f"J{k} = {v}" for k, v in enumerate(vals, 1)) + o["hz_space"] + o["hz"])
                vals = None
            elif o["j_separate"] and len(vals) > 1:
                items.append(", ".join(f"J = {v}" + o["hz_space"] + o["hz"] for v in vals))
                vals = None
            elif o["j_nolabel"]:
                items.append(", ".join(vals) + o["hz_space"] + o["hz"])
                vals = None
        if g["J"] and vals is not None:
            if o["hz_each"]:
                jtxt = ", ".join(v + o["hz_space"] + o["hz"] for v in vals)
            else:
                jtxt = o["jsep"].join(vals) + o["hz_space"] + o["hz"]
            lab = o["jlabel_app"] if g["app"] and o["japp"] else o["jlabel"]
            items.append(lab + jtxt)
        nh = fmt(g["nH"], 0) + o["h_space"] + "H"
        items.append(nh)
        if o["assign"]:
            items.append(g["label"])
        if o["order"] == "nH_first":
            items = [items[-1]] + items[:-1]
        elif o["order"] == "nH_middle" and len(items) > 2:
            items = [items[0], nh] + [x for x in items[1:] if x != nh]
        inner = o["in_sep"].join(items)
        parts.append(shift + o["pre_bracket"] + o["br_open"] + inner + o["br_close"])
    head = o["head"]
    return head + o["sig_sep"].join(parts) + o["end"]


CLEAN = dict(range_dash="–", ppm_after_shift=False, app_word="app {}", br_word="br {}", hz_each=False,
             jsep=", ", hz_space=" ", jlabel="J = ", jlabel_app="J = ", japp=False, h_space="",
             order="normal", in_sep=", ", pre_bracket=" ", sig_sep=", ",
             head="1H NMR (400 MHz, CDCl3) δ ", end=".", jdec=1, sdec=2, j_indexed=False,
             j_separate=False, j_nolabel=False, assign=False, hz="Hz", br_open="(", br_close=")")

# each noise: name -> (option overrides) or a text function applied to the rendered string
OPTION_NOISES = {
    "dash_hyphen": dict(range_dash="-"),
    "dash_emdash": dict(range_dash="—"),
    "dash_minus": dict(range_dash="−"),
    "dash_spaced": dict(range_dash=" – "),
    "ppm_after_shift": dict(ppm_after_shift=True),
    "app_apparent": dict(app_word="apparent {}"),
    "app_pseudo": dict(app_word="pseudo-{}"),
    "app_like": dict(app_word="{}-like"),
    "br_broad": dict(br_word="broad {}"),
    "br_dot": dict(br_word="br. {}"),
    "hz_each": dict(hz_each=True),
    "hz_nospace": dict(hz_space=""),
    "j_nospace": dict(jlabel="J=", jlabel_app="J="),
    "j_noequal": dict(jlabel="J ", jlabel_app="J "),
    "j_colon": dict(jlabel="J: ", jlabel_app="J: "),
    "j_and": dict(jsep=" and "),
    "j_italic_index": dict(jlabel="3J = "),
    "j_hh": dict(jlabel="J(H,H) = "),
    "japp_label": dict(japp=True, jlabel_app="Japp = "),
    "h_space": dict(h_space=" "),
    "nH_first": dict(order="nH_first"),
    "semicolon_inside": dict(in_sep="; "),
    "no_space_before_bracket": dict(pre_bracket=""),
    "semicolon_between": dict(sig_sep="; "),
    "head_delta_H": dict(head="1H NMR (400 MHz, CDCl3): δH "),
    "head_delta_ppm": dict(head="1H NMR (400 MHz, CDCl3) δ (ppm): "),
    "head_no_delta": dict(head="1H NMR (400 MHz, CDCl3): "),
    "head_delta_eq": dict(head="1H NMR (CDCl3, 400 MHz) δ = "),
    "assignment_in_bracket": dict(assign=True),
    "j_indexed_J1_J2": dict(j_indexed=True),
    "j_each_labelled": dict(j_separate=True),
    "j_without_label": dict(j_nolabel=True),
    "shift_3_decimals": dict(sdec=3),
    "j_2_decimals": dict(jdec=2),
    "br_brd_style": dict(br_word="br{}"),
    "rsc_style_no_hz": dict(order="nH_first", jlabel="J ", jlabel_app="J ", hz="", hz_space="", head="1H NMR (400 MHz, CDCl3): δH "),
    "no_hz_unit": dict(hz="", hz_space=""),
    "square_brackets": dict(br_open="[", br_close="]"),
    "nH_middle": dict(order="nH_middle"),
    "no_comma_between": dict(sig_sep=" "),
    "ppm_at_end": dict(end=" ppm."),
}


def t_nbsp(s, rng):          # non-breaking spaces (Word)
    return s.replace(" ", " ") if rng.random() < 0.5 else re.sub(" ", lambda m: " " if rng.random() < 0.3 else " ", s)


def t_thin(s, rng):           # thin / narrow no-break spaces
    return re.sub(" ", lambda m: rng.choice([" ", " ", " "]), s)


def t_linebreak(s, rng):      # line break from a PDF, anywhere after the delta
    i = s.find("δ")
    pos = [m.start() for m in re.finditer(" ", s) if m.start() > i]
    if not pos:
        return s
    p = rng.choice(pos)
    return s[:p] + "\n" + s[p + 1:]


def t_linebreak_hyphen(s, rng):   # line break at a range dash: "7.35–\n7.28"
    return re.sub("–", "–\n", s, count=1)


def t_zwsp(s, rng):           # zero-width spaces / soft hyphens from copy-paste
    return re.sub(r"(?<=\d)(?=\.)|(?<=\()", lambda m: rng.choice(["​", "­", ""]), s)


def t_double_space(s, rng):
    return re.sub(" ", lambda m: "  " if rng.random() < 0.3 else " ", s)


def t_space_in_number(s, rng):    # "7. 26" from PDF text
    return re.sub(r"(?<![\d.])(\d{1,2}\.)(\d{2})(?=\s?[(–,])", lambda m: m.group(1) + " " + m.group(2) if rng.random() < 0.3 else m.group(0), s)


def t_superscript_1H(s, rng):
    return s.replace("1H NMR", rng.choice(["¹H NMR", "1 H NMR", "H NMR", "1H-NMR"]), 1)


def t_fullwidth_paren(s, rng):
    return s.replace("(", "（").replace(")", "）") if rng.random() < 0.2 else s


def t_decimal_comma(s, rng):      # European decimal comma (not expected to work; measured separately)
    return re.sub(r"(\d)\.(\d)", r"\1,\2", s)


def t_mult_upper(s, rng):
    return re.sub(r"\((\w+)", lambda m: "(" + m.group(1).upper() if rng.random() < 0.5 else m.group(0), s)


def t_tab(s, rng):
    return re.sub(" ", lambda m: "\t" if rng.random() < 0.2 else " ", s)


def t_hz_lower(s, rng):
    return s.replace("Hz", rng.choice(["hz", "HZ", "Hz"]))


def t_crlf(s, rng):
    i = s.find("δ")
    pos = [m.start() for m in re.finditer(" ", s) if m.start() > i]
    return s if not pos else (lambda p: s[:p] + "\r\n" + s[p + 1:])(rng.choice(pos))


def t_prime_variants(s, rng):
    return s.replace("′", rng.choice(["'", "’", "′"]))


def t_symbol_delta(s, rng):       # delta lost in copy from a Symbol font
    return s.replace("δ", rng.choice(["d", "", "", "δ"]))


TEXT_NOISES = {f.__name__[2:]: f for f in (t_nbsp, t_thin, t_linebreak, t_linebreak_hyphen, t_zwsp,
              t_double_space, t_space_in_number, t_superscript_1H, t_fullwidth_paren, t_decimal_comma,
              t_mult_upper, t_symbol_delta, t_tab, t_hz_lower, t_crlf, t_prime_variants)}
EXPECTED_TO_FAIL = {"decimal_comma"}   # not supported by design (reported apart)


def truth_of(g):
    return dict(shift=round((g["s"] + g["s2"]) / 2, 3) if g["s2"] is not None else g["s"],
                mult=g["mult"], app=g["app"], br=g["br"], J=[round(j, 1) for j in g["J"]],
                nH=float(g["nH"]))


def compare(truth, parsed):
    """List of problems, or [] if the parser read everything right."""
    probs = []
    if len(parsed) != len(truth):
        probs.append(f"signals {len(parsed)}/{len(truth)}")
        return probs
    for k, (t, p) in enumerate(zip(truth, parsed), 1):
        if abs(p["shift"] - t["shift"]) > 0.006:
            probs.append(f"#{k} shift {p['shift']} vs {t['shift']}")
        if p["mult"] != t["mult"]:
            probs.append(f"#{k} mult {p['mult']} vs {t['mult']}")
        if p["app"] != t["app"]:
            probs.append(f"#{k} app {p['app']} vs {t['app']}")
        if p["br"] != t["br"]:
            probs.append(f"#{k} br {p['br']} vs {t['br']}")
        pj = [float(x) for x in p["J"] + p["Japp"] + p["Jhet"]]
        if len(pj) != len(t["J"]) or any(abs(a - b) > 0.051 for a, b in zip(sorted(pj), sorted(t["J"]))):
            probs.append(f"#{k} J {pj} vs {t['J']}")
        if p["nH"] != t["nH"]:
            probs.append(f"#{k} nH {p['nH']} vs {t['nH']}")
    return probs


def main(n, seed=260626):
    rng = random.Random(seed)
    names = list(OPTION_NOISES) + list(TEXT_NOISES)
    rows = []
    per_noise = Counter()
    fail_noise = Counter()
    kinds = defaultdict(Counter)
    examples = defaultdict(list)
    clean_fail = 0
    for i in range(n):
        sigs = [gen_signal(rng) for _ in range(rng.randint(3, 14))]
        truth = [truth_of(g) for g in sigs]
        # baseline: the clean form must parse right
        clean = render(sigs, CLEAN)
        cprob = compare(truth, parse_description(clean)[1])
        if cprob:
            clean_fail += 1
        # one to three noises at once
        k = rng.choices([1, 2, 3], weights=[6, 3, 1])[0]
        chosen = rng.sample(names, k)
        o = dict(CLEAN)
        for nm in chosen:
            if nm in OPTION_NOISES:
                o.update(OPTION_NOISES[nm])
        text = render(sigs, o)
        for nm in chosen:
            if nm in TEXT_NOISES:
                text = TEXT_NOISES[nm](text, rng)
        prob = compare(truth, parse_description(text)[1])
        for nm in chosen:
            per_noise[nm] += 1
        if prob and not cprob:
            for nm in chosen:
                fail_noise[nm] += 1
                if len(examples[nm]) < 3 and k == 1:
                    examples[nm].append(dict(text=text, problems=prob[:3]))
            for p in prob:
                kinds["+".join(sorted(chosen))][re.sub(r"#\d+ (\w+).*", r"\1", p)] += 1
        rows.append(dict(i=i, noises=chosen, ok=not prob, clean_ok=not cprob, problems=prob[:5], text=text))
    single = {nm: [0, 0] for nm in names}
    for r in rows:
        if len(r["noises"]) == 1 and r["clean_ok"]:
            single[r["noises"][0]][0] += 1
            single[r["noises"][0]][1] += (not r["ok"])
    out = dict(n=n, seed=seed, clean_fail=clean_fail,
               failed=sum(1 for r in rows if not r["ok"] and r["clean_ok"]),
               single={k: v for k, v in single.items()}, examples=examples,
               rows=[r for r in rows if not r["ok"]][:400])
    json.dump(out, open(f"fuzz_{n}.json", "w"), ensure_ascii=False, indent=1)
    supported = [r for r in rows if r["clean_ok"] and not set(r["noises"]) & EXPECTED_TO_FAIL]
    bad_supported = sum(1 for r in supported if not r["ok"])
    print(f"N = {n}; clean form misread: {clean_fail}; noisy descriptions misread: {out['failed']} "
          f"({100 * out['failed'] / n:.1f} %)")
    print(f"SUMMARY misread without unsupported forms (decimal comma): {bad_supported} of {len(supported)} "
          f"({100 * bad_supported / max(len(supported), 1):.2f} %); clean form misread: {clean_fail}")
    print(f"{'noise (alone)':28s} {'cases':>6s} {'misread':>8s}")
    for nm, (c, f) in sorted(single.items(), key=lambda x: -x[1][1] / max(x[1][0], 1)):
        flag = "  (not supported by design)" if nm in EXPECTED_TO_FAIL else ""
        print(f"{nm:28s} {c:6d} {f:8d}  {100 * f / max(c, 1):5.0f} %{flag}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 260626)
