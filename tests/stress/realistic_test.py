"""Realistic reading stress test (v2.1).

The content of one published 1H description (shifts, multiplicities, constants, integrals) is written in the
style of another published description (header, separators, order of the parts in the bracket, spellings of
multiplicities, templates of the constants, assignments); the program must read back the content. Styles,
contents and spelling frequencies are in realistic_styles.json.gz, built by build_styles.py from the
development data only (Beilstein J. Org. Chem., ACS Omega, J. Org. Chem., Molecules; PMCID lists
DEVELOPMENT_DATA_*_PMCIDs.txt): 15,723 descriptions, of which the 12,830 read completely give the styles and
contents. The correct answer is known for every synthetic description.

This tests how robustly the program reads the forms that occur in the literature. It is not a measurement of
accuracy on new articles.

    python realistic_test.py N SEED [PARSER_DIR] [out.json]
PARSER_DIR = the check_descriptions folder of the version tested (default: this package).
"""
import gzip
import os
import importlib.util
import json
import random
import sys
from collections import Counter


def weighted(rng, counter):
    keys = list(counter)
    return rng.choices(keys, weights=[counter[k] for k in keys])[0]


def fill(tpl, values):
    out = tpl
    for v in values:
        out = out.replace("{}", v, 1)
    return out.replace("\x01", "{").replace("\x02", "}")


def nh_text(x):
    return ("%d" % x) if x == int(x) else ("%g" % x)


def render(rng, st, cont, mult_raw, jt):
    parts_out = []
    for sg in cont["signals"]:
        key = "%s|%d|%d" % (sg["mult"], sg["br"], sg["app"])
        if key in st["mult"]:
            mtxt = st["mult"][key]
        elif key in mult_raw:
            mtxt = weighted(rng, mult_raw[key])
        else:
            return None
        n = len(sg["J"])
        jtxt = ""
        if n:
            tpl = st["J"].get(str(n)) or (weighted(rng, jt[str(n)]) if str(n) in jt else None)
            if not tpl:
                return None
            jtxt = fill(tpl, sg["J"])
        ntxt = fill(st["nH"], [nh_text(sg["nH"])])
        pieces = []
        for k in st["order"]:
            if k == "mult":
                pieces.append(mtxt)
            elif k == "J" and jtxt:
                pieces.append(jtxt)
            elif k == "nH":
                pieces.append(ntxt)
        if n and "J" not in st["order"]:
            pieces.append(jtxt)
        if st["assign"] and rng.random() < st["assign_rate"]:
            pieces.append(rng.choice(st["assign"]))
        shift = sg["d1"] + (st["dash"] + sg["d2"] if sg["d2"] else "")
        parts_out.append(shift + " " + st["pre"].strip() + ("" if not st["pre"].strip() else " ") + "(" + st["joiner"].join(pieces) + ")")
    tail = st["tail"].split(" ")[0] if st["tail"].strip()[:1] in (".", ";") else "."
    return st["header"] + st["prefix"] + st["sep"].join(parts_out) + tail


def truth(cont):
    return [(round((float(s["d1"]) + float(s["d2"])) / 2 if s["d2"] else float(s["d1"]), 4), s["mult"], bool(s["br"]),
             bool(s["app"]), [float(x) for x in s["J"]], float(s["nH"])) for s in cont["signals"]]


def read(dp, text):
    return [(round(s["shift"], 4), s["mult"], bool(s["br"]), bool(s["app"]), [float(x) for x in s["J"]],
             None if s["nH"] is None else float(s["nH"])) for s in dp.parse_description(text)[1]]


HERE = os.path.dirname(os.path.abspath(__file__))
STYLES = os.path.join(HERE, "realistic_styles.json.gz")
DEFAULT_PARSER = os.path.normpath(os.path.join(HERE, "..", "..", "check_descriptions"))


def main(n, seed, parser_dir=DEFAULT_PARSER, out=None):
    data = json.load(gzip.open(STYLES, "rt", encoding="utf-8"))
    sys.path.insert(0, parser_dir)
    spec = importlib.util.spec_from_file_location("dp_tested", parser_dir + "/description_parser.py")
    dp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dp)
    rng = random.Random(seed)
    styles = [s for s in data["styles"] if "mult" in s["order"] and "nH" in s["order"]]
    contents = data["contents"]
    ok = bad = 0
    why = Counter()
    examples = []
    while ok + bad < n:
        st, ct = rng.choice(styles), rng.choice(contents)
        text = render(rng, st, ct, data["mult_raw"], data["J_templates"])
        if text is None:
            continue
        t, r = truth(ct), read(dp, text)
        if t == r:
            ok += 1
            continue
        bad += 1
        if len(t) != len(r):
            kind = "number of signals"
        else:
            diff = [i for i in range(len(t)) if t[i] != r[i]][0]
            names = ["shift", "multiplicity", "br", "app", "J", "integral"]
            kind = ", ".join(nm for k, nm in enumerate(names) if t[diff][k] != r[diff][k])
        why[kind] += 1
        if len(examples) < 300:
            examples.append(dict(text=text, kind=kind, style_src=st["src"]))
    print("SUMMARY realistic descriptions misread: %d of %d (%.2f %%)" % (bad, n, 100 * bad / n))
    for k, v in why.most_common(8):
        print("   ", v, k)
    if out:
        json.dump(dict(n=n, bad=bad, why=dict(why), examples=examples), open(out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]), int(a[1]), a[2] if len(a) > 2 else DEFAULT_PARSER, a[3] if len(a) > 3 else None)
