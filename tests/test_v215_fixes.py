"""V2.1.5-beta: item 4(b) - counting of large couplings (strict letter reading) and the width test.
All descriptions are constructed for the test (no published description is used)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", d) for d in ("check_descriptions", "review_to_word")]

import check_descriptions as cd  # noqa: E402

COUNT = "cannot be distributed over the protons of the structure"
H = "1H NMR (400 MHz, CDCl3) δ "
BRANISOLE = "COc1ccc(Br)cc1"                 # 4-bromoanisole: two AA' pairs, one large (ortho) J each
TOLUATE = "COC(=O)c1ccc(C)cc1"               # methyl 4-methylbenzoate: L of the protons next to CH3 is 4.4 Hz
BNOH = "OCc1ccccc1"                          # benzyl alcohol
FANISOLE = "COc1ccc(F)cc1"                   # 4-fluoroanisole
MEONAPH = "COc1ccc2ccccc2c1"                 # 2-methoxynaphthalene


def check(smiles, desc):
    r = dict(id="t", description=desc, smiles=smiles, hetero="", formula="", opsin_status="")
    return cd.check_row(r)


def counting(smiles, desc):
    res = check(smiles, desc)
    lines = [x for x in res["findings4b"].split("\n") if COUNT in x]
    return res["item4b"], (lines[0] if lines else "")


def test_correct_description_has_no_counting_finding():
    v, f = counting(BRANISOLE, H + "7.37 (d, J = 9.0 Hz, 2H), 6.78 (d, J = 9.0 Hz, 2H), 3.77 (s, 3H).")
    assert f == "" and v in ("consistent", "nothing to check")


def test_too_many_large_couplings():
    # two overlapped doublets of a para-disubstituted ring written as "dd": no proton has two large couplings
    v, f = counting("COc1ccc(cc1)Sc1ccc(Br)cc1", H + "7.37 (d, J = 8.4 Hz, 2H), 6.90 (dd, J = 8.6, 7.7 Hz, 4H), "
                                                  "6.82 (d, J = 8.9 Hz, 2H), 3.80 (s, 3H).")
    assert v == "inconsistent" and f.startswith("item 4(b): ") and "#2 6.90" in f and "2 large" in f
    # "p" for a monosubstituted phenyl: no proton of the ring has four large couplings
    v, f = counting(BNOH, H + "7.33 (p, J = 7.0 Hz, 5H), 4.68 (s, 2H), 1.80 (br s, 1H).")
    assert v == "inconsistent" and "#1 7.33" in f
    res = check(BNOH, H + "7.33 (p, J = 7.0 Hz, 5H), 4.68 (s, 2H), 1.80 (br s, 1H).")
    assert res["_class"] == "inconsistent 1-4" and "4(b)" in res["conclusion"]


def test_two_signals_must_be_read_otherwise():
    v, f = counting(MEONAPH, H + "7.78 – 7.72 (m, 3H), 7.43 (dt, J = 8.2, 6.8 Hz, 1H), 7.33 (dt, J = 8.2, 6.8 Hz, 1H), "
                                "7.18 – 7.12 (m, 2H), 3.92 (s, 3H).")
    assert v == "inconsistent" and "2 of them must be read otherwise" in f and "#2 7.43" in f and "#3 7.33" in f


def test_too_few_large_couplings_width_test():
    # a singlet for a proton with an ortho coupling, no signal nearby: W_s + tau = 0.2 Hz < L_X = 6.5 Hz
    v, f = counting(BRANISOLE, H + "7.37 (s, 2H), 6.78 (d, J = 9.0 Hz, 2H), 3.77 (s, 3H).")
    assert v == "inconsistent" and "#1 7.37" in f
    # another signal within 3 x J_max (16 Hz < 27 Hz): strong coupling cannot be excluded
    v, f = counting(BRANISOLE, H + "7.37 (s, 2H), 7.33 (d, J = 9.0 Hz, 2H), 3.77 (s, 3H).")
    assert v == "candidate (check)" and f.startswith("item 4(b) width: ") and "3 x J_max (9 Hz)" in f
    # no frequency: the guard cannot be applied
    v, f = counting(BRANISOLE, "1H NMR (CDCl3) δ 7.37 (s, 2H), 6.78 (d, J = 9.0 Hz, 2H), 3.77 (s, 3H).")
    assert v == "candidate (check)" and "the frequency is not stated" in f


def test_width_covers_a_doublet_with_small_j():
    # protons next to CH3: L = 6.5 - 3 x 0.7 = 4.4 Hz; "d, J = 4.5 Hz": W_s + tau = 4.75 Hz >= 4.4 Hz
    v, f = counting(TOLUATE, H + "7.93 (d, J = 8.2 Hz, 2H), 7.23 (d, J = 4.5 Hz, 2H), 3.90 (s, 3H), 2.40 (s, 3H).")
    assert f == ""
    # "d, J = 3.5 Hz": 3.75 Hz < 4.4 Hz
    v, f = counting(TOLUATE, H + "7.93 (d, J = 8.2 Hz, 2H), 7.23 (d, J = 3.5 Hz, 2H), 3.90 (s, 3H), 2.40 (s, 3H).")
    assert v == "inconsistent" and "#2 7.23" in f


def test_meta_fluorine_may_add_one_large_coupling():
    base = H + "6.97 (t, J = 8.7 Hz, 2H), {}, 3.77 (s, 3H)."
    assert counting(FANISOLE, base.format("6.83 (dd, J = 9.2, 4.5 Hz, 2H)"))[1] == ""
    assert counting(FANISOLE, base.format("6.83 (dd, J = 9.2, 6.5 Hz, 2H)"))[1] == ""
    v, f = counting(FANISOLE, base.format("6.83 (ddd, J = 9.2, 8.0, 6.5 Hz, 2H)"))
    assert v == "inconsistent" and "#2 6.83" in f


def test_no_counting_finding_when_shifts_or_symmetry_are_the_problem():
    # "3,77" is read as 77 ppm: no shift windows, no finding of item 4(b)
    assert counting(BRANISOLE, H + "7.37 (d, J = 9.0 Hz, 2H), 6.78 (d, J = 9.0 Hz, 2H), 3,77 (s, 3H).")[1] == ""
    # a para-disubstituted ring as four 1H signals: the integrals do not fit the sets of equivalent protons;
    # this is not a matter of the multiplicities
    assert counting(BRANISOLE, H + "7.39 (d, J = 9.0 Hz, 1H), 7.35 (d, J = 9.0 Hz, 1H), 6.80 (d, J = 9.0 Hz, 1H), "
                                   "6.76 (d, J = 9.0 Hz, 1H), 3.77 (s, 3H).")[1] == ""


def test_proton_stands_only_at_a_possible_shift():
    # the aromatic singlet cannot be filled by the CH2 protons (they cannot stand at 7.31 ppm)
    v, f = counting("CC1(CC(C)(C)C)C(=O)N(c2ccccc2)c2ccccc12",
                    "1H NMR (500 MHz, CDCl3) δ 7.50 (t, J = 7.8 Hz, 2H), 7.42 – 7.34 (m, 3H), 7.27 (s, 1H), "
                    "7.18 (t, J = 7.6 Hz, 1H), 7.06 (t, J = 7.5 Hz, 1H), 6.85 (d, J = 7.8 Hz, 1H), "
                    "2.20 (d, J = 14.0 Hz, 1H), 1.92 (d, J = 14.0 Hz, 1H), 1.40 (s, 3H), 0.72 (s, 9H).")
    assert v == "inconsistent" and "#3 7.27" in f and "each proton only at shifts where it can stand" in f
