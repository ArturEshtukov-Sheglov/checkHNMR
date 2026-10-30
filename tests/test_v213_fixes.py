"""V2.1.3-beta: item 4(b) lower bound for methyl groups; items 2, 5 and 7 shown as "not checked" in the
Excel table and the Word report."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", d) for d in ("check_descriptions", "review_to_word")]

import check_descriptions as cd  # noqa: E402


def item4b(smiles, desc):
    r = dict(id="t", description=desc, smiles=smiles, hetero="", formula="", opsin_status="")
    res = cd.check_row(r)
    return res["item4b"], res["findings4b"]


H = "1H NMR (400 MHz, CDCl3) δ "


def test_methyl_next_to_ch_as_singlet_is_found():
    # CH3 on the CH of an aziridine reported as a singlet; the OCH3 singlet is not named
    v, f = item4b("COC=1C=C(C=CC1)C1N(C1C)S(=O)(=O)OCC(Cl)(Cl)Cl",
                  "1H NMR (600 MHz, CDCl3) δ 7.29 (t, J = 7.7 Hz, 1H), 6.92 (d, J = 8.2 Hz, 1H), 6.90 – 6.86 (m, 2H), "
                  "4.95 – 4.83 (m, 2H), 4.04 (d, J = 7.3 Hz, 1H), 3.82 (s, 3H), 3.35 – 3.21 (m, 1H), 1.15 (s, 3H).")
    assert v == "candidate (check)"
    assert "#8 1.15" in f and "3.82" not in f
    # the same description with the doublet: no finding
    v, f = item4b("COC=1C=C(C=CC1)C1N(C1C)S(=O)(=O)OCC(Cl)(Cl)Cl",
                  "1H NMR (600 MHz, CDCl3) δ 7.29 (t, J = 7.7 Hz, 1H), 6.92 (d, J = 8.2 Hz, 1H), 6.90 – 6.86 (m, 2H), "
                  "4.95 – 4.83 (m, 2H), 4.04 (d, J = 7.3 Hz, 1H), 3.82 (s, 3H), 3.35 – 3.21 (m, 1H), "
                  "1.15 (d, J = 5.6 Hz, 3H).")
    assert v == "consistent" and f == ""


def test_ethyl_and_ch_methyl_as_singlet():
    assert item4b("CCOC(C)=O", H + "4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (s, 3H).")[0] == "candidate (check)"
    assert item4b("CCOC(C)=O", H + "4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (t, J = 7.1 Hz, 3H).")[0] == "consistent"
    v, f = item4b("CC(C(=O)OC)C(C1=CC=CC=C1)=O",
                  H + "7.97 – 7.90 (m, 2H), 7.59 – 7.50 (m, 1H), 7.48 – 7.39 (m, 2H), 4.37 (q, J = 7.1 Hz, 1H), "
                      "3.64 (s, 3H), 1.44 (s, 3H).")
    assert v == "candidate (check)" and "#6 1.44" in f


def test_singlets_that_are_allowed():
    # diastereotopic SiMe2 of TBS (two singlets, one of them below 0 ppm)
    assert item4b("[Si](C)(C)(C(C)(C)C)O[C@@H](C=O)C",
                  "1H NMR (500 MHz, CDCl3) δ 9.61 (d, J = 1.3 Hz, 1H), 4.09 (qd, J = 6.9, 1.2 Hz, 1H), "
                  "1.27 (d, J = 6.9 Hz, 3H), 0.92 (s, 9H), 0.10 (s, 3H), 0.09 (s, 3H).")[0] != "candidate (check)"
    # TIPS written as one singlet of 21 H (CH and CH3 nearly isochronous)
    assert item4b("BrCC#C[Si](C(C)C)(C(C)C)C(C)C", H + "3.95 (s, 2H), 1.07 (s, 21H).")[0] != "candidate (check)"
    # the CH2 envelope of a long chain written as a singlet of 18 H
    assert item4b("P(OCC)(OCC)(=S)SCCCCCCCCCCCC",
                  H + "4.26–4.08 (m, 4H), 2.89–2.81 (m, 2H), 1.70–1.62 (m, 2H), 1.39–1.34 (m, 6H), 1.25 (s, 18H), "
                      "0.88 (t, J = 7.2 Hz, 3H).")[0] != "candidate (check)"
    # acetonide and tBu: singlets from CH3 on quaternary carbons
    assert item4b("CC1(C)OCC(CO)O1", H + "4.25 (m, 1H), 4.03 (dd, J = 8.2, 6.6 Hz, 1H), 3.79 (dd, J = 8.2, 6.4 Hz, 1H), "
                  "3.72 (m, 1H), 3.60 (m, 1H), 2.10 (br s, 1H), 1.44 (s, 3H), 1.37 (s, 3H).")[0] != "candidate (check)"
    # a broad singlet is not counted
    assert item4b("CCOC(C)=O", H + "4.12 (q, J = 7.1 Hz, 2H), 2.05 (s, 3H), 1.26 (br s, 3H).")[0] != "candidate (check)"


def test_not_checked_items_in_excel_and_word():
    import excel_output as eo
    import export_docx as ed
    assert eo.COLS.index("item2") == eo.COLS.index("item1") + 1
    assert eo.COLS.index("item5") == eo.COLS.index("item4b") + 1
    assert eo.COLS.index("item7") == eo.COLS.index("item6b") + 1
    assert all(eo.NOT_CHECKED[k] == "not checked" for k in ("item2", "item5", "item7"))
    assert ed.TOOL_NOT_CHECKED == {"2": "1", "5": "4(b)", "7": "6(b)"}
    for lang in ("en", "ru"):
        assert all(k in ed.TOOL_NAMES[lang] and k in ed.TOOL_NOT_CHECKED_TEXT[lang] for k in ("2", "5", "7"))
