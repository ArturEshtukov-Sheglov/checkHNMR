"""Verdict words and the conclusion for one description (section 10 of the protocol, limited to
the items the script checks). The Excel formulas in excel_output.py use the same words."""


# Words the verdicts are made of; the Excel formulas (conclusion, item 6, colours, summary) look for them
W = dict(cons="consistent", inc="inconsistent", chk="check", border="borderline", subcat="subcategory",
         nostruct="no structure", only6b="6(b) only", cbd="cannot be determined", nopair="no pair",
         na="not applicable", unver="unverifiable", cand="candidate", mix="mixture", yes="yes",
         border_full="borderline (subcategory)",
         head_inc="INCONSISTENT: ", item="item ", items="items ", subst=" (substantive)",
         notation="item 6 (first-order notation)",
         several=". Several substantive items are inconsistent: a check against the raw data (FID) is strongly advised",
         one=(". The description does not agree with itself or with the structure: a check against the spectrum "
              "in the SI or the raw data (FID) is advisable"),
         also=". Also to check by hand: ", also_pn=False,
         head_chk="TO CHECK BY HAND: ", tail_chk=" (no inconsistency found so far)",
         nof="NO INCONSISTENCY FOUND by the automatic checks (items 2, 5 and 7 are not checked; 4(b) only in part)")

SUBSTANTIVE = (("1", "item1"), ("3", "item3"), ("4(a)", "item4a"))      # items 1-4 checked by the script
TO_CHECK = (("1", "item1"), ("3", "item3"), ("4(b)", "item4b"), ("6(a)", "item6a"))         # v2: 4(b)         # items that can be left to a person


def is_inc(v):
    """The verdict is 'inconsistent' (not 'inconsistent?')."""
    v = (v or "").lower()
    return v.startswith("inconsistent") and "?" not in v


def is_check(v):
    """The verdict leaves the decision to a person."""
    v = (v or "").lower()
    return any(x in v for x in ("unverifiable", "candidate", "?", "mixture")) or v == "check"


def conclusion(res):
    """Conclusion for one description. Returns (text, class)."""
    subst = [n for n, k in SUBSTANTIVE if is_inc(res.get(k))]
    nota = ["6"] if is_inc(res.get("item6")) else []
    check = [n for n, k in TO_CHECK if is_check(res.get(k))]

    if subst or nota:
        parts = []
        if subst:
            parts.append(("items " if len(subst) > 1 else "item ") + ", ".join(subst) + " (substantive)")
        if nota:
            parts.append("item 6 (first-order notation)")
        text = "INCONSISTENT: " + "; ".join(parts)
        if len(subst) >= 2:
            text += (". Several substantive items are inconsistent: a check against the raw data (FID) "
                     "is strongly advised")
        elif subst:
            text += (". The description does not agree with itself or with the structure: a check against "
                     "the spectrum in the SI or the raw data (FID) is advisable")
        if check:
            text += ". Also to check by hand: " + ", ".join(check)
        res["_n_subst"] = len(subst)
        return text, ("inconsistent 1-4" if subst else "inconsistent 6 only")

    if check:
        return (("TO CHECK BY HAND: items " if len(check) > 1 else "TO CHECK BY HAND: item ") + ", ".join(check)
                + " (no inconsistency found so far)", "to check")
    return (W["nof"],
            "no finding")


def conclusion_text(res):
    """The conclusion as the Excel formula will show it (used for the row height and for tests)."""
    subst = [n for n, k in SUBSTANTIVE if is_inc(res.get(k))]
    nota = is_inc(res.get("item6"))
    check = [n for n, k in TO_CHECK if is_check(res.get(k))]
    pn = lambda xs: (W["items"] if len(xs) > 1 else W["item"]) + ", ".join(xs)

    if subst or nota:
        text = W["head_inc"] + (pn(subst) + W["subst"] if subst else "") + ("; " if subst and nota else "") \
            + (W["notation"] if nota else "")
        text += W["several"] if len(subst) >= 2 else W["one"] if subst else ""
        if check:
            text += W["also"] + (pn(check) if W["also_pn"] else ", ".join(check))
        return text
    if check:
        return W["head_chk"] + pn(check) + W["tail_chk"]
    return W["nof"]


def combine_item6(a, b):
    """Item 6 from 6(a) and 6(b): inconsistent if either is; the same rule as the Excel formula."""
    if a == "inconsistent" or b == "inconsistent":
        return "inconsistent"
    if "check" in a or "borderline" in b:
        return "check" if "check" in a else "borderline (subcategory)"
    if b == "cannot be determined" and a in ("consistent", "no structure"):
        return "cannot be determined" if a == "consistent" else "6(b) only: cannot be determined"
    if a == "no structure":
        return "6(b) only: " + ("consistent" if b != "cannot be determined" else b)
    return "consistent"
