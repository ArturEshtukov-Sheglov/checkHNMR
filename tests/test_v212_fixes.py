"""Tests of the V2.1.2-beta fixes: the non-first-order notation of Tang, Xu and Hoye (Molecules 2025, 30, 2610):
nfod, nfot, nfom with J_app, and a sum of constants written as the splitting (J_o + J_p). Invented examples."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))

import description_parser as dp  # noqa: E402
import text_checks as tc  # noqa: E402


def sig(text):
    return dp.parse_description("1H NMR (400 MHz, CDCl3) δ " + text)[1]


def test_nfod_nfot_nfom_are_multiplets():
    s = sig("7.76 (nfod, Japp = 8.3 Hz, 2H), 7.30 (nfot, J_app = 7.6 Hz, 1H), 7.10 (nfom, 2H)")
    assert [x["mult"] for x in s] == ["m", "m", "m"]
    assert [x["Japp"] for x in s] == [["8.3"], ["7.6"], []] and all(not x["J"] for x in s)


def test_sum_of_constants_is_apparent():
    s = sig("7.10 (nfod, J_o + J_p = 8.6 Hz, 2H), 7.05 (app d, 3J + 5J = 8.5 Hz, 2H), 6.80 (nfod, Jo+Jp = 8.5 Hz, 2H)")
    assert [x["Japp"] for x in s] == [["8.6"], ["8.5"], ["8.5"]] and all(not x["J"] for x in s)


def test_hoye_notation_gives_no_findings():
    r = tc.check("1H NMR (500 MHz, CDCl3) δ 7.30 (nfot, Japp = 7.6 Hz, 1H), 7.10 (nfod, J_o + J_p = 8.6 Hz, 2H), "
                 "6.95 (nfom, 2H), 3.80 (s, 3H).")
    assert r["item3"] == "consistent" and r["item4a"] == "consistent"


def test_ordinary_constants_unchanged():
    s = sig("7.05 (dd, J = 8.5, 2.0 Hz, 1H), 6.80 (d, J = 2.0 Hz, 1H), 6.70 (d, J = 8.5 Hz, 1H), "
            "4.10 (q, 2J = 3J = 7.1 Hz, 2H)")
    assert [x["J"] for x in s] == [["8.5", "2.0"], ["2.0"], ["8.5"], ["7.1"]] and all(not x["Japp"] for x in s)
