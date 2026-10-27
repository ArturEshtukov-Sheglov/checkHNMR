"""How completely a 1H description was read (v2.1): the marker for the "as read" preview.

The recognised signals are removed from the text of the description; what is left is examined.
A shift-like number (0-16 with a decimal point) or "Hz" left over means that part of the description
was not read as signals. The marker does not need to know which notation was not understood.

    level  green   every number of the description was read as part of a signal
           yellow  something was not read (listed in 'unread'), or a signal lacks its multiplicity or
                   integral, a shift lies outside -5 to 21 ppm, or the shifts are out of order
                   (lines of the PDF text glued in the wrong order)
           red     a description header but no signal was read
"""
import re

from description_parser import (SIGNAL, TWO_D, OTHER_NUCLEUS, DASH, normalize_text, cut_prose, expand_shift_lists, MULT_BEFORE)  # noqa: F401

# a left-over number that looks like the start of a signal: "6.88+6.84 (s", "4.97, 4.91 (ABq", "7.26 (" ,
# "1.13-1.21 (m"; numbers of the procedure text ("4.15 mL", "2.5 mmol") are not
SHIFT_LIKE = re.compile(r"(?<![\w.])(-?\d{1,2}\.\d{1,3})(?![\d.])"
                        r"(?=\s?(?:[+,–—−-]\s?-?\d{1,2}\.\d{1,3}\s?)*\(|\s?[+,]\s?\d{1,2}\.\d"
                        r"|\s?\+|\s?[,–—−-]\s{2,}|\s?[,–—−-]\s?$)")   # the rest of the signal was read: "6.88+[6.84 (s]"
HZ_LEFT = re.compile(r"\d\s?Hz\b")                # a constant left outside the signals read
MIN_SHIFT, MAX_SHIFT = -5.0, 21.0                     # SiMe3 near -0.1, metal hydrides lower; chelated enol OH up to ~20
MIN_CHARS_PER_PAGE = 200         # less text per page: a scan or images
MIN_LOST = 5                      # fewer lost characters are not reported (a stray symbol)
ORDER_BREAKS_ALLOWED = 2          # an NH/OH or solvent-overlap signal put first or last is normal


def body_of(desc):
    """The part of the description that parse_description reads (same steps)."""
    body = desc[desc.find("δ"):] if "δ" in desc else desc
    for pat in (TWO_D, OTHER_NUCLEUS):
        cut = pat.search(body)
        if cut:
            body = body[:cut.start()]
    body = expand_shift_lists(MULT_BEFORE.sub(r"\1 (\2, ", cut_prose(body)))
    return re.sub(r"(?<![\d.])(\d{1,2}\.)\s(\d{1,3})(?=\s?[(," + DASH + r"])", r"\1\2", body)


def order_breaks(shifts):
    """Number of places where the shifts change direction against the main direction of the list."""
    if len(shifts) < 3:
        return 0
    steps = [b - a for a, b in zip(shifts, shifts[1:]) if b != a]
    if not steps:
        return 0
    down = sum(s < 0 for s in steps) >= sum(s > 0 for s in steps)
    return sum((s > 0) if down else (s < 0) for s in steps)


def reading_quality(desc, sigs=None):
    """dict(level, signals, unread, notes) for one 1H description (text as in the SI)."""
    from description_parser import parse_description
    d = normalize_text(desc)
    if sigs is None:
        sigs = parse_description(desc)[1]
    body = body_of(d)
    residue = SIGNAL.sub(" ", body)
    # the header "(400 MHz, CDCl3)" and the solvent residual "7.26 ppm" written in the header are not data
    head_end = body.find(":") if 0 <= body.find(":") < 40 else 0
    unread = [x for x in SHIFT_LIKE.findall(residue[head_end:]) if MIN_SHIFT <= float(x) <= MAX_SHIFT]
    notes = []
    if not sigs:
        return dict(level="red", signals=0, unread=unread, notes=["header found, no signal read"])
    no_mult = [s["shift"] for s in sigs if not s.get("mult")]
    no_int = [s["shift"] for s in sigs if s.get("nH") is None]
    out = [s["shift"] for s in sigs if not MIN_SHIFT <= s["shift"] <= MAX_SHIFT]
    breaks = order_breaks([s["shift"] for s in sigs])
    if unread:
        notes.append("not read: " + ", ".join(unread[:6]) + (" ..." if len(unread) > 6 else ""))
    if HZ_LEFT.search(residue):
        notes.append("'Hz' outside the signals read")
    if no_mult:
        notes.append("no multiplicity: " + ", ".join("%g" % x for x in no_mult[:4]))
    if no_int:
        notes.append("no integral: " + ", ".join("%g" % x for x in no_int[:4]))
    if out:
        notes.append("shift outside -5-21 ppm: " + ", ".join("%g" % x for x in out[:4]))
    if breaks > ORDER_BREAKS_ALLOWED:
        notes.append("shifts out of order (%d breaks): lines glued in the wrong order?" % breaks)
    return dict(level="yellow" if notes else "green", signals=len(sigs), unread=unread, notes=notes)


def file_quality(text, n_pages, n_descriptions=None):
    """Problems of a whole PDF text (as the tools read it, symbol-font characters already mapped):
    no text layer (only reported when no description was read), characters that could not be read."""
    notes = []
    if n_pages and len(text) / n_pages < MIN_CHARS_PER_PAGE and not n_descriptions:
        notes.append("little text per page and no description read: a scan or images? "
                     "Save the PDF from Word, or upload the table")
    pua = len(re.findall(r"[\ue000-\uf8ff]", text))
    bad = text.count("\ufffd")
    if pua >= MIN_LOST:
        notes.append("%d characters of a symbol font could not be read (δ, digits or brackets may be lost)" % pua)
    if bad >= MIN_LOST:
        notes.append("%d unreadable characters (\ufffd)" % bad)
    return notes
