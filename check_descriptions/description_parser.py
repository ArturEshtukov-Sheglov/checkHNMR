"""Reading a written 1H NMR description into signals: shift, multiplicity, coupling constants,
integral. Also the 19F/31P descriptions that follow it. Used by check_descriptions.py."""

import re


# ===== Constants =====

FREQ_WINDOW = 120                # characters at the start of a description searched for "400 MHz"
HETERO_FREQ_WINDOW = 80          # the same for a 19F description
HETERO_BLOCK = 600               # longest 19F/31P description read (characters)
F_BLOCK = 800                    # longest 19F description read for strongly coupled F pairs
STRONG_FF = 100                  # Hz: a 19F constant above this is an F-F coupling (e.g. CHF2)
SAME_FF_J = 0.5                  # Hz: two F-F constants this close are the same coupling


# ===== Patterns =====

DASH = "–—−-"
NUM = r"-?\d+(?:\.\d+)?"                         # a number: "7", "7.26", "-116.2"
FREQ = re.compile(r"(\d{2,4}(?:\.\d+)?)\s?MHz", re.I)
# One signal: "7.41 (d, J = 6.9 Hz, 2H)" or a range "7.35-7.28 (m, 2H)";
# group 1 = shift, group 2 = end of the range, group 3 = text in the brackets
SIGNAL = re.compile(
    r"(?<![\d.])(?<![A-Za-z])(?<![A-Za-z]-)"      # v2.1: not a locant of a name: "isoquinolin-5(6H)-one"
    r"(" + NUM + r")"                            # shift, not the end of a longer number
    r"(?:\s?[" + DASH + r"]\s?(" + NUM + r"))?"  # optional end of a range
    r"\s?(?:,\s?(?=\())?"                        # optional comma before the bracket: "7.41, (d ..."
    r"(?:ppm\s?)?"
    r"\(([^()]*(?:\((?:[^()]|\([^()]*\))*\)[^()]*)*)\)")   # the bracket; inner brackets two levels deep (v2.1)
# Coupling constants inside a signal: "J = 8.2, 1.5 Hz", "3J(H,F) = 8.2 Hz", "J_app = 7.0 Hz", "N = 8.8 Hz";
# group "label" = the J symbol with its index, group "vals" = the values
J_BLOCK = re.compile(
    r"(?P<label>(?:\d\s?)?J\s?"                  # "J", "3J"
    r"(?:_?\{?app\}?|app"                        # apparent: "J_app", "Japp"
    r"|\([^()=]{1,12}\)"                         # nuclei in brackets: "J(H,F)"
    r"|_?\{?[A-Za-z0-9′'’,\-–]{1,10}\}?)?"       # index: "J_HF", "J_{2,3}"
    r"|N)"                                       # "N" (sum of two constants)
    r"\s?(?:=|:|(?<=J)\s(?=\d))\s?"               # v2: also "J 8.4, 5.5 Hz" (no "=")
    r"(?P<vals>(?:" + NUM + r"(?![\d.])(?![′'’″^]|[-–][A-Za-z]|[A-GI-Z]|H(?![z\s]|$))(?:(?<=\.\d)|(?<=\.\d\d)|(?<=\.\d\d\d)|(?!,\s?\d+[′'’]?[-–]|,\s?\d+H\b|\s?[-–]\s|\s(?!Hz)[A-Z(×]))(?!\s?H\b)(?!\s?\^?J)(?!\s?[×x*]\s?[A-Z(])\s?(?:Hz)?\s?(?:,|and|&)?\s?)+)",  # v2.1: not "2 × CH3"  # values; "2H" is not one,
    # and (v2) neither is the index of the next constant: "3J = 13.2 Hz, 3J = 10.6 Hz", nor (v2.1) a locant of
    # an assignment after the constants: "J = 8.3 Hz, 1′-CH2", "J = 8.0 Hz, 4-CH", "2CH2", "7,8-H"
    re.I)
# v2: "2J = 3J = 13.4 Hz", "^{2}J =^{3}J = 13.6 Hz": two or more J symbols written equal to one value
# v2.1: also with atom indices: "J4,3 = J4,5 = 7.2 Hz", "J1,3 = J1,3 = 7.2 Hz"
J_CHAIN = re.compile(r"((?:(?:\^\{\d\}|\d)?\s?J(?:\s?\d{1,2}\s?,\s?\d{1,2}(?![\d.]))?\s?=\s?){2,})(" + NUM + r")")
INTEGRAL = re.compile(r"(\d+(?:\.\d+)?)\s?(?:(?:arom|ar|aromatic|olefinic|vinyl|ring)\.?\s)?H\b")  # "2H", "1.5 H"; v2.1: "8 arom. H"
BARE_VALUE = re.compile(r"(?<![\w.′'’-])\d{1,2}\.\d{1,2}(?![\w.′'’])")     # v2.1: "16.2" alone in the bracket
# v2.1: values with "Hz" but without a J symbol: "8.7 Hz", "8.4, 2.1 Hz", "8.4 Hz, 2.1 Hz"
BARE_J = re.compile(r"(?<![\w.])(?:\d+(?:\.\d+)?\s?(?:Hz)?\s?(?:,|and)\s?)*\d+(?:\.\d+)?\s?Hz\b", re.I)
# words for multiplicities and the code used here
MULT_WORDS = {"singlet": "s", "doublet": "d", "triplet": "t", "quartet": "q", "quintet": "p",
              "pentet": "p", "quint": "p", "sextet": "sext", "septet": "sept", "hept": "sept",
              "heptet": "sept", "multiplet": "m", "mult": "m", "hextet": "sext"}
# 2D experiments after the 1H description ("NOESY ...") are not part of it
# v2.1: the start of the data of another nucleus: "13C NMR (", "13C{1H} NMR", "δC (125 MHz", "19F NMR"
OTHER_NUCLEUS = re.compile(r"(?<![0-9A-Za-z])(?:13\s?C|19\s?F|31\s?P|11\s?B|29\s?Si)\s?(?:\{[^})]*[})])?\s?-?\s?NMR"
                           r"|δ\s?[CFPB]\s?\(|RMN\s?(?:de\s?)?(?:13\s?C|19\s?F|31\s?P)"
                           r"|(?<![0-9A-Za-z])13\s?C\s?\{\s?1?\s?H\s?\}\s?\("    # v2.1: "13C{1H} (150 MHz", "13C {H} (100 MHz" without "NMR"
                           r"|(?<![\w.,(])2\s?H\s?NMR|■|ASSOCIATED CONTENT"      # v2.1: "2H NMR"; end of an ACS article
                           r"|(?<![0-9A-Za-z])13\s?C\s{0,2}(?:H?MR\b|\((?=\s?\d{2,3}\s?MHz|\s?[A-Z]{2}|\s?DMSO))"
                           r"|\bESI-?MS\b|\[?m/z\]?\s?=|\bUV-?[Vv]is\b|\bFT-?IR\b|\bIR\s?\((?:KBr|ATR|neat|film|cm)")   # v2.1  # v2.1: "13C HMR", "13C (151MHz"
# v2.1: the description ends and the text goes on ("…(m, 5H) ppm. General Procedure A…", "…1H, SH). Spectral data
# matched…  To a solution of thiol 23 (1.50 g"): a sentence end after a signal, a new sentence, and no further signal
PROSE_END = re.compile(r"\)\s?(?:ppm)?\s?\.\s+(?=\S)")       # v2.1: also "6-(4-(…)hexyl propionate (5b) was prepared"
NEXT_SIGNAL = re.compile(r"\d\.\d{1,3}\s?(?:\(|[–—−-]\s?\d)")
PROSE_LOOKAHEAD = 150


# v2.1: several shifts with one bracket: "2.09, 2.08, 2.01, 1.98 (4× s, each 3H, OAc)", "8.14 and 7.82 (2 s, 1H,
# rotamer)", "4.00, 3.95 (AB system, J = 12.9 Hz, 2H)", "5.18/5.17 (2H, AB-system)". Read as one signal per shift
# with the same bracket; the integral is given to each shift when written "each 3H" or "4 × 3H", otherwise the
# integral is shared equally (the sum stays as written)
LIST_ITEM = r"\d{1,2}\.\d{1,3}(?:\s?[–—−-]\s?\d{1,2}\.\d{1,3})?"        # v2.1: a shift or a range ("2.64–2.77, 2.90–3.04 (2m")
SHIFT_LIST = re.compile(r"(?<![\d.,/–—−-])(" + LIST_ITEM + r")((?:\s?(?:,\s?and|,|/|and|&)\s?" + LIST_ITEM + r"(?![\d.]))+)"
                        r"\s?\(((?:[^()]|\([^()]{0,20}\)){0,200})\)")
EACH = re.compile(r"\b(?:each|ea\.?)\s?(\d+(?:\.\d+)?\s?H)\b|(?<![\d.])\d+\s?[×x]\s?(\d+(?:\.\d+)?\s?H)\b"
                  r"|(\d+(?:\.\d+)?\s?H)\s?each\b")
LIST_COUNT = re.compile(r"(?<![\w.])\d\s?[×x]?\s?(?=(?:br\.?\s?)?[sdtqm]{1,4}\b)")       # "4× s", "2 s", "2 q"


def _expand(m):
    shifts = [m.group(1)] + re.findall(LIST_ITEM, m.group(2))
    inner = m.group(3)
    if re.fullmatch(r"\s?\d+\s?C\s?", inner):                 # 13C data: "92.7, 70.0 (2C)"
        return m.group(0)
    each = EACH.search(inner)
    if each:
        inner = EACH.sub(lambda e: next(g for g in e.groups() if g), inner)
    else:
        nh = INTEGRAL.search(inner)
        if nh:
            # the integral is shared equally, or in the ratio given with the list ("3br t, 3:1:1, J = 5.5 Hz, 1H")
            ratio = re.search(r"(?<![\d.])(\d+(?:\.\d+)?(?:\s?:\s?\d+(?:\.\d+)?)+)(?![\d.])", inner)
            parts = [float(x) for x in re.split(r"\s?:\s?", ratio.group(1))] if ratio else []
            if len(parts) != len(shifts) or not sum(parts):
                parts = [1.0] * len(shifts)
            else:
                inner = (inner[:ratio.start()] + inner[ratio.end():]).replace(",,", ",").replace(", ,", ",")
                nh = INTEGRAL.search(inner)
            total = float(nh.group(1))
            out = []
            for x, w in zip(shifts, parts):
                part = inner[:nh.start()] + ("%g" % round(total * w / sum(parts), 2)) + "H" + inner[nh.end():]
                out.append("%s (%s)" % (x, LIST_COUNT.sub("", part, count=1).strip(" ,")))
            return ", ".join(out)
    inner = LIST_COUNT.sub("", inner, count=1).strip(" ,")
    return ", ".join("%s (%s)" % (x, inner) for x in shifts)


def expand_shift_lists(body, spans=None):
    """The body with each shift list written out; spans (a list) receives the (start, end) of each written-out
    list in the new body, so the signals of one list can be recognised (item 6(b): described together)."""
    if spans is None:
        return SHIFT_LIST.sub(_expand, body)
    out, last = [], 0
    for m in SHIFT_LIST.finditer(body):
        out.append(body[last:m.start()])
        new = _expand(m)
        start = sum(len(x) for x in out)
        out.append(new)
        if new != m.group(0):
            spans.append((start, start + len(new)))
        last = m.end()
    out.append(body[last:])
    return "".join(out)


# v2.1: the multiplicity written before the bracket: "7.43−7.25 m (10H, Har), 6.32 dd (1H, J = 17.7 Hz)"
MULT_BEFORE = re.compile(r"(\d\.\d{1,3})\s((?:br\.?\s?)?(?:[sdtqmp]{1,5}|sext|sept|br\.?))\s\((?=\s?\d)")


def cut_prose(body):
    """The body up to the end of the last sentence of signals (v2.1)."""
    for m in PROSE_END.finditer(body):
        if not NEXT_SIGNAL.search(body, m.end(), m.end() + PROSE_LOOKAHEAD):
            return body[:m.start() + 1]
    return body
TWO_D = re.compile(r"\b(?:2D|NOESY|ROESY|COSY|HSQC|HMBC|NOE)\b|\bg?(?:HSQC|HMBC|COSY)\w*")   # v2.1: "gHSQCAD"
# the end of a 19F/31P description: the next NMR header or HRMS
HETERO_END = r"(?=\b1[13]\s?C\b|\b19\s?F\b|\b31\s?P\b|\b11\s?B\b|HRMS|$)"


# ===== Text normalisation (v2.1) =====

# characters that are invisible in the text but split numbers and words (copy-paste from PDF/Word)
INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")
# full-width punctuation (East Asian input methods) -> ASCII
FULLWIDTH = str.maketrans({"（": "(", "）": ")", "，": ", ", "；": "; ", "＝": "=", "：": ": "})
# v2.1: Cyrillic letters that look like Latin ones ("1Н NMR", "1Н", "°С" typed with a Russian keyboard
# layout) -> Latin; otherwise "1Н NMR" is not found and "1Н" is not read as an integral
HOMOGLYPHS = str.maketrans("АВЕКМНОРСТХаеорсухі", "ABEKMHOPCTXaeopcyxi")
SPACES = re.compile(r"\s+")
POINT_SPACE = re.compile(r"(?<=\d\.) (?=\d)")                        # a space right after a decimal point
# a signal written in square brackets: the bracket must start like a multiplicity or an integral
SQUARE_SIGNAL = re.compile(r"(\d(?: ?ppm)?) ?\[((?:br[dtq]{0,3}|app|apparent|broad|pseudo|bs|brs|sept|sext|hept|[dtqmpsh]{1,5}|\d+(?:\.\d+)? ?H)\b[^\[\]]{0,150})\]")
SPLIT_SHIFT = re.compile(r"(?<![\d.])(\d{1,2}\.\d) (\d)(?= ?\()")     # a space between the 2 decimals of a shift                      # any run of spaces, tabs, line breaks, no-break or thin spaces


J_ASSIGNED = re.compile(r"(\d\.\d{1,2})\s?\((?=[A-Za-z])[^()]{1,30}\)")
PAGE_IN_SIGNAL = re.compile(r"(\d\.\d{1,3})\s+S(?:I)?\s?-?\s?\d{1,3}\s+\(")
STAR_SHIFT = re.compile(r"(\d\.\d{1,3})\*\s?\(")
OTHER_DASHES = str.maketrans({"\u2010": "-", "\u2011": "-", "\u2012": "–", "\u2015": "–", "\u2043": "-"})


# v2.1: the running header of an ACS journal page, read into the middle of a description that goes over a page:
# "The Journal of Organic Chemistry pubs.acs.org/joc Article https://doi.org/10.1021/acs.joc.4c01729
#  J. Org. Chem. 2024, 89, 15048−15061 15055"
JOURNAL_HEADER = re.compile(r"(?:The )?(?:[A-Z][A-Za-z&]*,? ){0,6}[A-Z][A-Za-z&]*\s+pubs\.acs\.org/\w+\s+"
                            r"(?:Featured )?(?:Article|Note|Letter|Perspective|Communication|Review)\s+"
                            r"https?://doi\.org/\S+\s+[A-Z][A-Za-z. ]{1,40}?\s?\d{4},\s?\d+,\s?\d+\s?[−–-]\s?\d+\s+\d+\s?")

# v2.1: MDPI running header "Molecules 2025, 30, 4508 15 of 24"
MDPI_HEADER = re.compile(r"\b[A-Z][A-Za-z.]*(?: [A-Z][A-Za-z.]*){0,4} (?:19|20)\d\d, \d{1,3}, \d{1,6} \d{1,3} of \d{1,3}\b")
ISOTOPE_GLUED = re.compile(r"\^\{(1|2|11|13|15|19|29|31)\}(?=(?:H|C|F|P|B|N|Si)(?:NMR|\s|\{|-|$))")   # "^{13}CNMR"
JOURNAL_FRAGMENT = re.compile(r"\s?\bThe Journal of\b(?!\s+[A-Z][a-z])")


TILDE_RANGE = re.compile(r"(\d\.\d{1,3})\s?[~～]\s?(\d{1,2}\.\d)")
NO_BRACKET = re.compile(r"(?<=δ )(\d{1,2}\.\d{1,3}) ((?:br\.? ?)?(?:[sdtqmp]{1,5}|hep|sept|sext|quint))"
                        r"((?:, J = [\d., and]+ ?Hz)?), (\d+(?:\.\d+)?H)\b")


def normalize_text(desc):
    """v2.1: one form for text pasted from PDF, Word or other programs: no invisible characters,
    ASCII brackets, and every run of white space (tabs, line breaks, no-break and thin spaces) one space."""
    desc = INVISIBLE.sub("", desc).translate(FULLWIDTH).translate(HOMOGLYPHS)
    desc = ISOTOPE_GLUED.sub(r"\1", MDPI_HEADER.sub(" ", JOURNAL_FRAGMENT.sub("", JOURNAL_HEADER.sub(" ", desc))))             # v2.1: page header of an ACS article inside the description
    desc = desc.translate(OTHER_DASHES)              # v2.1: "1.13‒1.21 (m" (figure dash) -> "1.13–1.21"
    desc = re.sub(r"\(\((?=[a-z])", "(", desc)       # v2.1: "9.87 ((brs, 1H"
    desc = TILDE_RANGE.sub("\\1–\\2", desc)         # v2.1: "7.72~7.60 (m" (Chinese range sign)
    desc = NO_BRACKET.sub(r"\1 (\2\3, \4)", desc)    # v2.1: "δ 6.22 s, 1H (H-6), δ 3.52 hep, J = 7.1 Hz, 1H"
    desc = STAR_SHIFT.sub(r"\1 (", desc)            # v2.1: "8.62* (1H, dd" (minor isomer marked) -> "8.62 (1H, dd"
    desc = PAGE_IN_SIGNAL.sub(r"\1 (", desc)        # v2.1: "7.03 – 7.00 S-13 (m, 2H)" (SI page number glued)
    desc = SPACES.sub(" ", desc).strip()
    desc = POINT_SPACE.sub("", desc)                 # "J = 7. 6 Hz" -> "J = 7.6 Hz" (PDF text)
    desc = SPLIT_SHIFT.sub(r"\1\2", desc)           # "7.7 6 (d" -> "7.76 (d" (PDF text)
    return SQUARE_SIGNAL.sub(r"\1 (\2)", desc)       # "7.26 [d, J = 8.0 Hz, 2H]" -> "7.26 (d, ...)"


# ===== Signals =====

def decimals(v):
    """Number of decimals of a value as written: '7.26' -> 2."""
    return len(v.split(".")[1]) if "." in v else 0


def parse_mult(part):
    """Return (code, apparent, broad) for a multiplicity text, or None if the part is not one."""
    r = _parse_mult(part)
    if r is None:                                    # v2.1: a proton label first: "Hb dd", "Ha br s"
        m = re.match(r"\s*H[A-Za-z0-9′'’]{1,3}\s?:?\s+(.+)$", part)
        if m:
            r = _parse_mult(m.group(1))
    return r


def _parse_mult(part):
    t = part.strip().lower()
    # v2.1: "m appears as t" = app t; "tap" = t app; "dbr", "bd", "bt" = br d, br d, br t; "AB-q" = AB
    t = re.sub(r"^m\s+appears?\s+as\s+(?:an?\s+)?", "app ", t)
    t = re.sub(r"\b(?:virt|appt|quasi)\b\.?\s?", "app ", t)                                   # "virt. d", "appt. d", "quasi d" (v2.1)
    t = re.sub(r"^([dtqsm])\s?\(\s?br\.?\s?\)$", r"br \1", t)                           # "s(br.)"
    t = re.sub(r"\b([dtq]{1,3})ap\b\.?", r"app \1", t)
    t = re.sub(r"\b([dtq]{1,3})br\b\.?", r"br \1", t)
    t = re.sub(r"\bb(?=[dtq]{1,3}\b|m\b)", "br ", t)
    t = re.sub(r"\bab\s?-\s?q\b", "abq", t)
    t = re.sub(r"[~]", " app ", t)
    t = re.sub(r"\bap\.?\s?(?=[dtq]\b|[dtq]{2,}\b)", "app ", t)
    t = re.sub(r"-like\b", " app", t)

    app = bool(re.search(r"\b(app|apparent|pseudo|ps)\b\.?", t))
    t = re.sub(r"\b(app|apparent|pseudo|ps)\b\.?-?", " ", t)       # v2.1: also "pseudo-td"
    t = re.sub(r"\bbr-(?=[sdtqm])", "br ", t)                                           # v2.1: "br-s", "br-d"
    t = re.sub(r"\bbr(?=[dtq]{1,3}\b)", "br ", t)                     # v2.1: "brd", "brt" = "br d", "br t"
    br = bool(re.search(r"\b(br|broad)\b\.?|\bbs\b|\bbrs\b", t))
    t = re.sub(r"\b(br|broad)\b\.?", " ", t)
    t = re.sub(r"\bbrs\b|\bbs\b", "s", t)
    t = t.strip(" .")

    # v2.1: short and dotted forms: "quin", "dquin", "sep.d", "sept.", "sex", "sxt"
    t = re.sub(r"quin(?:tet|t)?\.?(?=[dtq]{0,3}\b)", "p", t)
    t = re.sub(r"\b(?:sep|sept|hept)\.\s?(?=[dtq]{1,3}\b)", "sept", t)
    t = re.sub(r"\b(?:sep|spt|hep)\b\.?", "sept", t)
    t = re.sub(r"^overlapp(?:ed|ing)\s+(?=[sdtq]{1,4}$)", "", t)                       # v2.1: "overlapped s"
    t = re.sub(r"\b(?:d2o\s)?exch(?:angeable)?\.?\s+", "", t)                       # v2.1: "exch br s"
    t = re.sub(r"^(?:complex|comp\.?|c\.\s?s\.?|oct(?:et)?\.?)$", "m", t)            # v2.1: "complex", "c.s.", "octet" -> m
    t = re.sub(r"^nfod$", "m", t)               # v2.1: Hoye's "not first-order doublet" with J_app: a multiplet
    t = re.sub(r"^(?:stack|overlapping\s+m(?:ultiplets?)?|overlapped\s+m|overlap|mc|m\s?c)$", "m", t)   # v2.1: "stack" (UK), "mc" (DE) = m
    t = re.sub(r"^[ab]\s+of\s+(?:an?\s+)?ab(?:\s+(?:system|quartet|q))?$", "ab", t)       # "A of AB", "B of AB"
    t = re.sub(r"^multiple\s+peaks$", "m", t)
    t = re.sub(r"\b(?:sex|sxt)\b\.?", "sext", t)
    # compound forms with a long multiplet name: "heptd", "septd", "pentd", "sextt"
    t = re.sub(r"\b(?:heptet|hept|septet|sept)(?=[dtq]{1,3}\b)", "sept", t)
    t = re.sub(r"\b(?:sextet|sext)(?=[dtq]{1,3}\b)", "sext", t)
    t = re.sub(r"\b(?:pentet|pent|quintet|quint)(?=[dtq]{1,3}\b)", "p", t)
    for w, c in MULT_WORDS.items():
        t = re.sub(r"\b" + w + r"s?\b", c, t)
    t = t.replace(" ", "")

    if t in ("ab", "abq", "abquartet", "absystem"):
        return ("AB", app, br)
    # v2.1: a named non-first-order system ("AB part of ABX system", "AA'BB'", "A2B2 system"): the
    # constants are not those of a first-order multiplet, so their number is not checked (like "m")
    if len(t) < 40 and re.search(r"abx|abc|aa[′'’]?bb|aa[′'’]?xx|a2b2|a2x2", t) and re.fullmatch(r"[a-z0-9′'’]+", t):
        return ("m", app, br)
    # s, m, sext, sept, septd, dd, ddt, dq, ... and "dm", "tm"
    if re.fullmatch(r"s|m|sext|sept|(?:sext|sept)[dtq]{1,3}|[dtqph]{1,5}|[dtqp]{1,4}m", t):
        return (t, app, br)
    return None


def expected_j(code):
    """Number of coupling constants a multiplicity needs: s 0, d 1, dd 2, septd 2; m: None (not checked)."""
    if code in ("s", "m", "AB"):
        return {"s": 0, "m": None, "AB": 1}[code]
    if code in ("sext", "sept"):
        return 1
    if code[:4] in ("sext", "sept"):
        return 1 + len(code[4:])
    return len(code.rstrip("m"))


def parse_signal(m):
    """A SIGNAL match -> dict with shift, multiplicity, J (H-H), Japp (apparent), Jhet (to F/P), nH."""
    d1, d2, inner = m.group(1), m.group(2), m.group(3)
    shift = (float(d1) + float(d2)) / 2 if d2 else float(d1)
    sig = dict(text=m.group(0), shift=shift, range=bool(d2), mult=None, app=False, br=False,
               J=[], Japp=[], Jhet=[], nH=None, problems=[], Jeq=0)

    # v2: a chain of equal constants, "2J = 3J = 13.4 Hz": the value stands for every J in the chain;
    # read as one constant, and the number of extra equal ones is kept for item 4(a)
    sig["Jeq"] = 0
    for ch in J_CHAIN.finditer(inner):
        sig["Jeq"] += len(re.findall(r"J", ch.group(1))) - 1
    inner = J_CHAIN.sub(lambda ch: "J = " + ch.group(2), inner)
    # v2.1: an assignment in brackets after a constant: "J = 6.7 (eqB–axA), 6.7 (eqB–axC), 1.2 Hz"
    inner = J_ASSIGNED.sub(r"\1", inner)
    rest = inner
    for jb in J_BLOCK.finditer(inner):
        label = jb.group("label")
        vals = re.findall(NUM, jb.group("vals"))
        lab = re.sub(r"\s", "", label)
        if re.search(r"app", lab, re.I) or lab.upper() == "N":
            sig["Japp"] += vals
        elif re.search(r"[FP]", re.sub(r"^\d?J", "", lab)):
            sig["Jhet"] += vals
        else:
            sig["J"] += vals
        rest = rest.replace(jb.group(0), " ")

    # v2.1: constants written without "J": "(t, 8.7 Hz, 2H)", "(dd, 8.4, 2.1 Hz, 1H)"
    if not (sig["J"] or sig["Japp"] or sig["Jhet"]):
        bare = BARE_J.search(rest)
        if bare:
            sig["J"] += re.findall(NUM, bare.group(0))
            rest = rest.replace(bare.group(0), " ")

    ni = INTEGRAL.search(rest)
    if ni:
        sig["nH"] = float(ni.group(1))
        rest = rest.replace(ni.group(0), " ")

    # v2.1: values with neither "J" nor "Hz" ("(1H, ddd, 16.2, 12.2, 1.8)"): numbers with a decimal point
    # left in the bracket after the integral, read only if the multiplicity needs constants
    if not (sig["J"] or sig["Japp"] or sig["Jhet"]):
        bare = BARE_VALUE.findall(rest)
        if bare:
            for part in re.split(r"[,;]", rest):
                p = parse_mult(part)
                if p:
                    need = expected_j(p[0])
                    if need and need >= 1 and len(bare) <= need + 1:
                        sig["J"] += bare
                        rest = BARE_VALUE.sub(" ", rest)
                    break

    for part in re.split(r"[,;]", rest):
        p = parse_mult(part)
        if p:
            sig["mult"], sig["app"], sig["br"] = p
            break
    # v2.1: "pt", "ptdd" = pseudo-triplet (J. Org. Chem.: "4.13 (pt, J = 7.0 Hz)"), not a pentet of triplets:
    # read so when the constants are one fewer than a pentet needs and as many as the rest needs
    mu = sig["mult"]
    if mu and len(mu) > 1 and mu[0] == "p" and mu[1] in "dtq" and expected_j(mu) is not None \
            and (len(sig["J"]) == expected_j(mu) - 1 == expected_j(mu[1:])
                 or (mu in ("pt", "pq", "pd") and not (sig["J"] or sig["Japp"]))):   # "pt, 2H" without J: pseudo-t
        sig["mult"], sig["app"] = mu[1:], True
    return sig


def parse_description(desc):
    """(spectrometer frequency or None, list of signals) of one 1H description."""
    desc = normalize_text(desc)                  # v2.1
    fm = FREQ.search(desc[:FREQ_WINDOW])
    freq = float(fm.group(1)) if fm else None
    body = desc[desc.find("δ"):] if "δ" in desc else desc
    cut = TWO_D.search(body)
    if cut:
        body = body[:cut.start()]
    cut = OTHER_NUCLEUS.search(body)                 # v2.1: 13C (or 19F, 31P) data written after the 1H data
    if cut:
        body = body[:cut.start()]
    body = cut_prose(body)                            # v2.1
    body = MULT_BEFORE.sub(r"\1 (\2, ", body)       # v2.1
    spans = []
    body = expand_shift_lists(body, spans)            # v2.1

    # v2: a space after the decimal point inside a shift ("7.55–7. 08 (m") is read as 7.08
    body = re.sub(r"(?<![\d.])(\d{1,2}\.)\s(\d{1,3})(?=\s?[(," + DASH + r"])", r"\1\2", body)
    # v2.1: a signal written twice is kept twice. Up to V2.0.1 a repeated identical signal was dropped as
    # a copy of the text; in the published descriptions such repeats are different groups with the same
    # signal (the OMe of two PMB groups, three TBS groups, keto and enol forms), and dropping one gave
    # false item-1 findings.
    sigs = []
    for m in SIGNAL.finditer(body):
        sig = parse_signal(m)
        sig["group"] = next((k for k, (a, b) in enumerate(spans) if a <= m.start() < b), None)   # v2.1
        sigs.append(sig)
    return freq, sigs


# ===== 19F / 31P descriptions =====

def hetero_info(text):
    """19F / 31P descriptions after the 1H description.
    Returns (state, hetJ, labelled): state = {'F': ..., 'P': ...} with 'absent', 'decoupled',
    'split' (some signal shows splitting) or 'singlets'; hetJ = coupling constants
    reported in proton-coupled 19F/31P descriptions; labelled = the same as (nucleus, value)."""
    text = text.replace("−", "-")
    state, hetJ, labelled = {}, [], []
    for nuc, pat in (("F", r"19\s?F"), ("P", r"31\s?P")):
        blocks = list(re.finditer(pat + r"\s?(\{[^}]*\})?\s?(?:-\s?)?(?:NMR)?(.{0,%d}?)" % HETERO_BLOCK + HETERO_END,
                                  text, re.S))
        if not blocks:
            state[nuc] = "absent"
            continue
        coupled = [bl for bl in blocks if not (bl.group(1) and "H" in bl.group(1))]   # not "19F{1H}"
        if not coupled:
            state[nuc] = "decoupled"
            continue

        mults = []
        for bl in coupled:
            for inner in re.findall(r"\(([^()]*)\)", bl.group(2)):
                m = parse_mult(inner.split(",")[0])
                if m:
                    mults.append(m)
                for jb in J_BLOCK.finditer(inner):
                    vals = re.findall(NUM, jb.group("vals"))
                    hetJ += vals
                    labelled += [(nuc, v) for v in vals]
        state[nuc] = "split" if any(x[0] != "s" for x in mults) else "singlets"
    return state, hetJ, labelled


def f_pairs_strong(text):
    """Strongly coupled 19F pairs: two signals of a 19F description that share a
    constant > 100 Hz (F-F, e.g. the diastereotopic F of a CHF2 group). Returns a list
    of (ratio, J_FF, set of the other constants of the two signals = their couplings to H)."""
    out = []
    text = text.replace("−", "-")
    text = re.sub(r"-\s+(?=\d)", "-", text)                    # "- 116.23" -> "-116.23"
    for bl in re.finditer(r"19\s?F\s?(\{[^}]*\})?\s?(?:-\s?)?(?:NMR)?(.{0,%d}?)" % F_BLOCK + HETERO_END, text, re.S):
        fm = FREQ.search(bl.group(2)[:HETERO_FREQ_WINDOW])
        if not fm:
            continue
        freq = float(fm.group(1))
        sigs = []
        for m in SIGNAL.finditer(bl.group(2)):
            vals = [v for jb in J_BLOCK.finditer(m.group(3)) for v in re.findall(NUM, jb.group("vals"))]
            sigs.append((float(m.group(1)), vals))

        for a in range(len(sigs)):
            for b in range(a + 1, len(sigs)):
                for v in sigs[a][1]:
                    for w in sigs[b][1]:
                        if float(v) > STRONG_FF and abs(float(v) - float(w)) <= SAME_FF_J:
                            J = (float(v) + float(w)) / 2
                            ratio = abs(sigs[a][0] - sigs[b][0]) * freq / J
                            others = {x for x in sigs[a][1] + sigs[b][1] if float(x) <= STRONG_FF}
                            out.append((ratio, J, others))
    return out
