"""Styles and contents of real 1H descriptions (development data only) for the realistic stress test.

Every description that V2.1 reads completely (reading marker green) gives
  - a STYLE: header, separator between signals, end, order of the parts inside the bracket, how the
    multiplicities, coupling constants and integrals are written, assignments;
  - a CONTENT: the signals as read (shift as written, multiplicity, J, integral, br/app).
The generator writes the content of one description in the style of another, so the forms of writing and
their frequencies (and the way they occur together) are those of the literature.

    python build_styles.py corpus.json styles.json      (then gzip -> realistic_styles.json.gz)
corpus.json = [{"src": journal, "desc": description text}, ...] from the result tables of the development data;
the corpus itself is not distributed (full descriptions), only the styles and contents derived from it.
"""
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "check_descriptions"))
import description_parser as dp                                   # noqa: E402
from read_quality import reading_quality                          # noqa: E402

NUMS = re.compile(r"\d+(?:\.\d+)?")


def template(text, values=None):
    """'J = 7.2, 1.5 Hz' -> 'J = {}, {} Hz'. With values: only the numbers equal to the values, in order, become
    placeholders ("J1 = 7.2 Hz" keeps the index 1); None if not all values are found."""
    text = text.replace("{", "\x01").replace("}", "\x02").rstrip(" ,;")    # literal braces ("^{3}J") kept
    if values is None:
        return NUMS.sub("{}", text)
    out, pos, k = [], 0, 0
    for m in NUMS.finditer(text):
        if k < len(values) and m.group(0) == values[k] and not re.search(r"J\s?$", text[:m.start()]):
            out.append(text[pos:m.start()] + "{}")
            pos, k = m.end(), k + 1
    out.append(text[pos:])
    return "".join(out) if k == len(values) else None


def split_inner(inner, sig):
    """Positions and kinds of the parts of a bracket: mult, J, nH, other (assignment)."""
    spans = []
    for jb in dp.J_BLOCK.finditer(inner):
        spans.append((jb.start(), jb.end(), "J", jb.group(0)))
    if len(spans) > 1:                                  # "J1 = 8.0 Hz, J2 = 2.0 Hz": one region
        spans = [(spans[0][0], spans[-1][1], "J", inner[spans[0][0]:spans[-1][1]])]
    if not spans:
        b = dp.BARE_J.search(inner)
        if b:
            spans.append((b.start(), b.end(), "J", b.group(0)))
    used = [(a, b) for a, b, _, _ in spans]
    ni = None
    for m in dp.INTEGRAL.finditer(inner):
        if not any(a <= m.start() < b for a, b in used):
            ni = m
            break
    if ni:
        spans.append((ni.start(), ni.end(), "nH", ni.group(0)))
        used.append((ni.start(), ni.end()))
    # the multiplicity: a comma-separated part outside J and integral that parse_mult accepts
    pos = 0
    for part in re.split(r"([,;])", inner):
        if part not in (",", ";") and part.strip():
            a = pos + len(part) - len(part.lstrip())
            b = a + len(part.strip())
            if not any(x <= a < y for x, y in used) and dp.parse_mult(part.strip()):
                spans.append((a, b, "mult", part.strip()))
                used.append((a, b))
                break
        pos += len(part)
    spans.sort()
    return spans


def main(src, dst):
    corpus = json.load(open(src, encoding="utf-8"))
    styles, contents = [], []
    mult_raw = {}                     # code+br+app -> Counter of raw spellings
    jtpl = {}                         # number of J -> Counter of templates
    for c in corpus:
        desc = c["desc"]
        if reading_quality(desc)["level"] != "green":
            continue
        d = dp.normalize_text(desc)
        body_start = d.find("δ") if "δ" in d else 0
        body = d[body_start:]
        for pat in (dp.TWO_D, dp.OTHER_NUCLEUS):
            cut = pat.search(body)
            if cut:
                body = body[:cut.start()]
        body = dp.cut_prose(body)
        ms = list(dp.SIGNAL.finditer(body))
        if len(ms) < 2 or dp.SHIFT_LIST.search(body):
            continue
        sigs = [dp.parse_signal(m) for m in ms]
        if any(s["Jhet"] or s["Japp"] or s["Jeq"] or s["mult"] is None or s["nH"] is None for s in sigs):
            continue
        # content
        cont = []
        for m, s in zip(ms, sigs):
            cont.append(dict(d1=m.group(1), d2=m.group(2), mult=s["mult"], app=s["app"], br=s["br"],
                             J=s["J"], nH=s["nH"]))
        # style
        seps = Counter(body[a.end():b.start()] for a, b in zip(ms, ms[1:]))
        sep = seps.most_common(1)[0][0]
        if len(sep) > 4 or re.search(r"\d", sep):
            continue
        order, jt, nht, mults, assign, joiners = None, {}, None, {}, [], Counter()
        for m, s in zip(ms, sigs):
            inner = m.group(3)
            spans = split_inner(inner, s)
            kinds = [k for _, _, k, _ in spans]
            last = 0
            for a, b, k, t in spans:
                gap = inner[last:a]
                if last and gap.strip(" ") in (",", ";"):
                    joiners[gap] += 1
                last = b
            rest = inner
            for a, b, k, t in sorted(spans, reverse=True):
                rest = rest[:a] + "\0" + rest[b:]
            others = [x.strip(" ,;") for x in rest.split("\0") if x.strip(" ,;")]
            others = [x for x in others if not re.search(r"\bJ|Hz|=|Δ|\d\.\d", x)]   # left-over constants are not assignments
            if others:
                assign.append(others[-1])
                kinds = kinds + ["assign"]
            if s["J"] and "J" in kinds and order is None:
                order = kinds
            for a, b, k, t in spans:
                if k == "J":
                    tp = template(t, s["J"])
                    if tp:
                        jt.setdefault(len(s["J"]), tp)
                        jtpl.setdefault(len(s["J"]), Counter())[tp] += 1
                elif k == "nH" and nht is None:
                    nht = template(t)
                elif k == "mult":
                    key = "%s|%d|%d" % (s["mult"], s["br"], s["app"])
                    mults.setdefault(key, t)
                    mult_raw.setdefault(key, Counter())[t] += 1
        if order is None or nht is None:
            continue
        pre = Counter(body[m.end(2) if m.group(2) else m.end(1):m.start(3) - 1] for m in ms).most_common(1)[0][0]
        dashes = Counter(body[m.end(1):m.start(2)] for m in ms if m.group(2))
        styles.append(dict(src=c["src"], header=desc[:desc.find(body[:20])] if body[:20] in desc else d[:body_start] + "δ ",
                           prefix=body[:ms[0].start()], sep=sep, tail=body[ms[-1].end():][:12], order=[k for i, k in enumerate(order) if k != "assign" and not (k == "J" and i and order[i - 1] == "J")],
                           assign_rate=len(assign) / len(ms), assign=assign[:20], J=jt, nH=nht, mult=mults,
                           joiner=(joiners.most_common(1)[0][0] if joiners else ", "),
                           pre=pre if len(pre) < 6 else "", dash=(dashes.most_common(1)[0][0] if dashes else "–")))
        contents.append(dict(src=c["src"], signals=cont))
    out = dict(styles=styles, contents=contents,
               mult_raw={k: dict(v) for k, v in mult_raw.items()}, J_templates={k: dict(v) for k, v in jtpl.items()})
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(len(corpus), "descriptions;", len(styles), "styles and contents")
    print("multiplicity spellings:", sum(len(v) for v in mult_raw.values()), "| J templates:",
          {k: len(v) for k, v in sorted(jtpl.items())})


if __name__ == "__main__":
    main(*sys.argv[1:3])
