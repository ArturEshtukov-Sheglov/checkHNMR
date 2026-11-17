"""V2.1.4-beta: item 4(b) - the CH next to a CH3 doublet must show at least a quartet for that J.
All descriptions are constructed for the test (no published description is used)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", d) for d in ("check_descriptions", "review_to_word")]

import check_descriptions as cd  # noqa: E402
from item4b import METHYL_PARTNER  # noqa: E402


def item4b(smiles, desc):
    r = dict(id="t", description=desc, smiles=smiles, hetero="", formula="", opsin_status="")
    res = cd.check_row(r)
    return res["item4b"], res["findings4b"]


H = "1H NMR (400 MHz, CDCl3) δ "
PHET = "CC(O)c1ccccc1"                       # 1-phenylethanol
LACT = "CC(O)C(=O)OCC"                       # ethyl lactate
IBP = "CC(C)C(=O)c1ccccc1"                   # isobutyrophenone


def test_ch_next_to_methyl_doublet_reported_as_doublet():
    v, f = item4b(PHET, H + "7.38 – 7.25 (m, 5H), 4.89 (d, J = 6.5 Hz, 1H), 1.90 (br s, 1H), 1.49 (d, J = 6.5 Hz, 3H).")
    assert v == "candidate (check)" and METHYL_PARTNER in f and "#2 4.89" in f
    v, f = item4b(PHET, H + "7.38 – 7.25 (m, 5H), 4.89 (t, J = 6.5 Hz, 1H), 1.90 (br s, 1H), 1.49 (d, J = 6.5 Hz, 3H).")
    assert v == "candidate (check)" and METHYL_PARTNER in f


def test_correct_quartet_and_hidden_partner():
    assert item4b(PHET, H + "7.38 – 7.25 (m, 5H), 4.89 (q, J = 6.5 Hz, 1H), 1.90 (br s, 1H), 1.49 (d, J = 6.5 Hz, 3H).") \
        == ("consistent", "")
    # the CH reported as a multiplet without J: cannot be checked, no finding
    v, f = item4b(PHET, H + "7.38 – 7.25 (m, 5H), 4.92 – 4.85 (m, 1H), 1.90 (br s, 1H), 1.49 (d, J = 6.5 Hz, 3H).")
    assert METHYL_PARTNER not in f


def test_ethyl_quartet_with_close_j_is_not_the_partner():
    # OCH2 (q, 7.1 Hz, 2H) has a J within the tolerance of the CH3 doublet but is not its CH
    v, f = item4b(LACT, H + "4.27 (d, J = 6.9 Hz, 1H), 4.23 (q, J = 7.1 Hz, 2H), 2.90 (br s, 1H), 1.41 (d, J = 6.9 Hz, 3H), "
                            "1.29 (t, J = 7.1 Hz, 3H).")
    assert v == "candidate (check)" and "#1 4.27" in f
    assert item4b(LACT, H + "4.27 (q, J = 6.9 Hz, 1H), 4.23 (q, J = 7.1 Hz, 2H), 2.90 (br s, 1H), "
                            "1.41 (d, J = 6.9 Hz, 3H), 1.29 (t, J = 7.1 Hz, 3H).") == ("consistent", "")


def test_isopropyl():
    assert item4b(IBP, H + "7.95 (d, J = 7.6 Hz, 2H), 7.55 (t, J = 7.4 Hz, 1H), 7.46 (t, J = 7.6 Hz, 2H), "
                           "3.56 (sept, J = 6.8 Hz, 1H), 1.22 (d, J = 6.8 Hz, 6H).")[1] == ""
    v, f = item4b(IBP, H + "7.95 (d, J = 7.6 Hz, 2H), 7.55 (t, J = 7.4 Hz, 1H), 7.46 (t, J = 7.6 Hz, 2H), "
                           "3.56 (d, J = 6.8 Hz, 1H), 1.22 (d, J = 6.8 Hz, 6H).")
    assert METHYL_PARTNER in f


def test_two_methyl_doublets_and_ch_multiplet():
    # 2-methyl-1-phenylpropan-1-ol: the iPr CH is a multiplet; the CH(OH) doublet has a J close to the CH3 J
    v, f = item4b("CC(C)C(O)c1ccccc1", H + "7.36 – 7.24 (m, 5H), 4.35 (d, J = 6.9 Hz, 1H), 1.95 (m, 1H), 1.80 (br s, 1H), "
                                           "1.00 (d, J = 6.7 Hz, 3H), 0.79 (d, J = 6.8 Hz, 3H).")
    assert METHYL_PARTNER not in f


def test_no_ch3_ch_in_structure():
    # CH3-P doublet: no CH next to a CH3, not checked by this rule
    v, f = item4b("COP(C)(=O)OC", H + "3.75 (d, J = 11.1 Hz, 6H), 1.49 (d, J = 17.6 Hz, 3H).")
    assert METHYL_PARTNER not in f


# ===== open-chain CH2-CH2: protocol v1.2, item 6(a), subcategory "formally non-first-order, flexible chain"

def item6(smiles, desc):
    r = dict(id="t", description=desc, smiles=smiles, hetero="", formula="", opsin_status="")
    res = cd.check_row(r)
    return res["item6a"], res["item6"], res["findings6a"], res["conclusion"] if "conclusion" in res else None


def test_open_chain_triplets_are_a_subcategory():
    a, i6, f, _ = item6("CC(=O)OCCc1ccccc1", H + "7.34 – 7.19 (m, 5H), 4.28 (t, J = 7.1 Hz, 2H), 2.94 (t, J = 7.1 Hz, 2H), "
                                               "2.03 (s, 3H).")
    assert a == "subcategory: flexible chain" and i6 == a
    assert "#2 4.28" in f and "#3 2.94" in f
    # the same chain as multiplets: nothing to report (v2.1.5: no J at all and an "m" - item 6 not applicable)
    a, i6, f, _ = item6("CC(=O)OCCc1ccccc1", H + "7.34 – 7.19 (m, 5H), 4.31 – 4.25 (m, 2H), 2.97 – 2.91 (m, 2H), "
                                               "2.03 (s, 3H).")
    assert a in ("consistent", "not applicable: no coupling constants are reported") and f == ""


def test_inner_chain_ch2_and_ethyl():
    # butyl: inner CH2 as p and sext belong to the subcategory; an ethyl q/t alone does not
    a, _, f, _ = item6("CCCCOC(C)=O", H + "4.06 (t, J = 6.7 Hz, 2H), 2.04 (s, 3H), 1.60 (p, J = 6.8 Hz, 2H), "
                                          "1.38 (sext, J = 7.4 Hz, 2H), 0.93 (t, J = 7.4 Hz, 3H).")
    assert a == "subcategory: flexible chain" and "1.60" in f and "1.38" in f and "0.93" not in f
    assert item6("CCOC(C)=O", H + "4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (t, J = 7.1 Hz, 3H).")[0] == "consistent"


def test_ring_ch2ch2_unchanged():
    # morpholine ring CH2-CH2 stays a candidate (check), as before
    a, _, _, _ = item6("O=C(c1ccccc1)N1CCOCC1", H + "7.45 – 7.36 (m, 5H), 3.75 (t, J = 4.6 Hz, 4H), 3.50 (t, J = 4.6 Hz, 4H).")
    assert a == "candidate (check)"


def test_subcategory_is_not_an_inconsistency():
    r = dict(id="t", description=H + "7.34 – 7.19 (m, 5H), 4.28 (t, J = 7.1 Hz, 2H), 2.94 (t, J = 7.1 Hz, 2H), 2.03 (s, 3H).",
             smiles="CC(=O)OCCc1ccccc1", hetero="", formula="", opsin_status="")
    res = cd.check_row(r)
    from verdicts import conclusion
    text, cls = conclusion(res)
    assert cls == "no finding"
