"""Tests of the version-2 fixes, on invented examples (no published text).

The fixes: characters of the Symbol font, the index of a coupling constant, a chain of equal
constants, a space after the decimal point, descriptions of isomers of a mixture, a description
that says it lists only some signals."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("count_1H_descriptions", "check_descriptions", "extract_names"):
    sys.path.insert(0, os.path.join(ROOT, d))

import count_1H_descriptions as cnt
import description_parser as dp
import text_checks as tc
import extract_names as ex  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "extract_names"))


def test_symbol_font_digits_and_brackets():
    raw = ".15 (t, 2H), d, 3H"
    out = cnt.SYMBOL_FONT_RE.sub(lambda m: cnt.SYMBOL_FONT_MAP.get(m.group(0), m.group(0)), raw)
    assert out == "2.15 (t, 2H), 1.50 (d, 3H)"
    assert cnt.SYMBOL_FONT_MAP[""] == "α" and cnt.SYMBOL_FONT_MAP[""] == "±"


def test_index_of_next_constant_is_not_a_value():
    _, sigs = dp.parse_description("δ 3.40 (ddd, 1H, 3J = 12.0 Hz, 3J = 9.5 Hz, 3J = 4.0 Hz)")
    assert sigs[0]["J"] == ["12.0", "9.5", "4.0"]
    _, sigs = dp.parse_description("δ 4.10 (dt, 3J1,2 = 7.0 Hz, 4J1,3 = 1.5 Hz, 1H)")
    assert sigs[0]["J"] == ["7.0", "1.5"]


def test_chain_of_equal_constants():
    _, sigs = dp.parse_description("δ 2.20 (dd, 1H, ^{2}J =^{3}J = 13.0 Hz), 1.90 (t, 1H, 2J = 3J = 12.5 Hz)")
    assert [s["J"] for s in sigs] == [["13.0"], ["12.5"]]
    assert tc.check_4a(sigs) == []          # dd: two equal J; t: one J


def test_space_after_decimal_point():
    _, sigs = dp.parse_description("δ 7.40–7. 05 (m, 5H), 3. 66 (s, 3H)")
    assert [round(s["shift"], 3) for s in sigs] == [7.225, 3.66]


def test_isomer_phrase():
    assert ex.ISOMER_BEFORE.search("Minor isomer. ")
    assert ex.ISOMER_BEFORE.search("1st (major) isomer. ")
    assert ex.ISOMER_BEFORE.search("3nd isomer.")              # misprint for 3rd
    assert not ex.ISOMER_BEFORE.search("as a mixture of isomers was stirred. ")


def test_partial_description_partner_unverifiable():
    desc = ("Minor isomer. 1H NMR (300 MHz, CDCl3): δ 1.50 (d, 3H, J = 6.5 Hz) ppm. "
            "The other signals are overlapped with the signals of the major isomer.")
    assert tc.PARTIAL.search(desc)
    _, sigs = dp.parse_description(desc)
    f3, c3 = tc.check_3_partners(sigs, {"F": "absent", "P": "absent"}, ["6.5"], partial=True)
    assert f3 == [] and not any("likely item-3" in c for c in c3)


def test_constants_without_equals_sign():
    _, sigs = dp.parse_description("δ 7.40 (dd, J 8.4, 5.5 Hz, 2H), 1.10 (t, J 7.5 Hz, 3H)")
    assert [s["J"] for s in sigs] == [["8.4", "5.5"], ["7.5"]]
    assert tc.check_4a(sigs) == []


def test_formula_before_calculated():
    import hrms_formula as hf
    neutral, ion_f, ion, _ = hf.neutral_formula(
        "HRMS (ESI+): for [M+H]+ (C10H14NO +) calculated m/z 164.1070, found m/z 164.1072")
    assert (neutral, ion_f) == ("C10H13NO", "C10H14NO")
    # "(ESI) calcd for ..." must not be read as a formula before the word
    neutral, _, _, _ = hf.neutral_formula("HRMS (ESI) calcd for C10H14NO [M+H]+ 164.1070, found 164.1072")
    assert neutral == "C10H13NO"


def test_ir_band_is_not_a_label():
    region = ("HRMS found 164.1072. IR (cm-1): NH (3410), C-H (2950), aromatic C-H (812). "
              "N-Benzyl-4-methylaniline (2c) A flask was charged ")
    assert [c[2] for c in ex.label_candidates(region)] == ["2c"]


# ----- second set of v2 fixes (22.10.2026), invented examples -----

from hrms_formula import neutral_formula, ion_changes  # noqa: E402


def test_fragment_ion_formula_of_molecule():
    # loss of water from a diol: the molecule is the ion plus H2O
    f = neutral_formula("HRMS (ESI) m/z: [M-H2O]+ Calcd for C10H11O+, 147.0804; found 147.0801.")
    assert f[0] == "C10H13O2" and "from the ion" in f[3]
    # azide: [M-N2+H]+
    assert neutral_formula("HRMS calcd for C7H8N [M-N2+H]+ 106.0651, found 106.0650")[0] == "C7H7N3"
    # deprotonation written with the charge inside: not a fragment
    assert ion_changes("[M - H+]") == {"H": -1}


def test_fragment_ion_with_abbreviation_gives_no_formula():
    f = neutral_formula("HRMS m/z: [M-Boc+H]+ Calcd for C8H10NO2 152.0706; found 152.0705.")
    assert f[0] == "" and "fragment ion" in f[3]


def test_isotopologue_and_neutral_formula_with_ion_type():
    # m/z given for the 37Cl isotopologue of a CCl3 compound
    f = neutral_formula("HRMS m/z: [M+H]+ Calcd for C3H4Cl3O2 178.9247; found 178.9245.")
    assert f[0] == "C3H3Cl3O2" and "isotopologue" in f[3]
    # neutral formula written with [M+H]+
    f = neutral_formula("HRMS m/z: [M+H]+ Calcd for C8H8O2 137.0603; found 137.0601.")
    assert f[0] == "C8H8O2" and "neutral molecule" in f[3]


def test_calculated_mass_word_is_not_a_formula():
    f = neutral_formula("matches the calculated mass for the structure. MS m/z: [M]+ Calcd for C9H10 118.0783; found")
    assert f[0] == "C9H10"


def test_trial_and_step_are_not_labels():
    region = "Racemic: Trial 1: Trial 2: 4-methylbenzaldehyde (5c) Prepared via the general procedure. "
    assert ex.label_and_name(region)[0] == "5c"
    region = ("STEP 1: synthesis of ethyl 4-oxobutanoate (7-a) was used crude. STEP 2: synthesis of "
              "4-oxobutanoic acid (7-b) To a flask ... to afford 7-b as a white solid (50 mg). ")
    assert ex.label_and_name(region)[0] == "7-b"


def test_label_range_and_unbalanced_name_start():
    from name_patterns import is_label_range
    from compound_names import unwrap
    assert is_label_range("4a-h") and is_label_range("21a-b")
    assert not is_label_range("1s-a") and not is_label_range("7-a")
    assert unwrap("main text) dimethyl 2-phenylmalonate") == "dimethyl 2-phenylmalonate"
    assert unwrap("[2]) methyl (E)-3-phenylacrylate") == "methyl (E)-3-phenylacrylate"


# ----- item 4(b), upper bound of coupling partners (22.10.2026), invented examples -----

def _4b(desc, smiles):
    from rdkit import Chem
    from item4b import check_item4b
    _, sigs = dp.parse_description(desc)
    return check_item4b(sigs, Chem.MolFromSmiles(smiles))[0]


def test_4b_impossible_tt_in_benzo_ring():
    tetralin = "C1CCC2=CC=CC=C2C1"
    assert _4b("δ 7.10 (tt, J = 7.5, 1.2 Hz, 1H)", tetralin).startswith("candidate")
    assert _4b("δ 7.10 (td, J = 7.5, 1.2 Hz, 1H)", tetralin) == "consistent"


def test_4b_zigzag_and_homopropargylic_couplings_allowed():
    assert _4b("δ 8.10 (dt, J = 8.4, 1.1 Hz, 1H)", "c1ccc2ncccc2c1") == "consistent"      # quinoline H-8
    assert _4b("δ 1.80 (d, J = 2.4 Hz, 3H)", "CC#CC1CCCCC1") == "consistent"              # CH3-C#C-CH


def test_4b_methyl_reported_with_too_many_partners():
    assert _4b("δ 0.95 (dd, J = 6.8, 2.0 Hz, 6H)", "CC(C)CCO").startswith("candidate")   # iPr CH3 as dd
    assert _4b("δ 0.95 (d, J = 6.8 Hz, 6H)", "CC(C)CCO") == "consistent"
    assert _4b("δ 3.80 (d, J = 1.2 Hz, 3H)", "COC(=O)c1ccccc1").startswith("candidate")  # OMe as d
    assert _4b("δ 0.60 (q, J = 8.0 Hz, 6H)", "CC[Si](CC)(CC)OC") == "consistent"         # SiEt3 CH2


def test_large_j_impossible_without_f_or_p():
    import check_descriptions as cd
    desc = "1H NMR (600 MHz, CDCl3) δ 7.25 (d, J = 8.8 Hz, 2H), 6.90 (d, J = 8.8 Hz, 2H), 3.82 (d, J = 1160.5 Hz, 3H)"
    res = cd.check_row(dict(id="x", description=desc, hetero="", smiles="COc1ccc(C)cc1", formula=""))
    assert res["item3"].startswith("inconsistent") and "impossible for this compound" in res["findings3"]
    # the same J with fluorine in the HRMS formula (structure from a wrong name): not called impossible
    res = cd.check_row(dict(id="x", description=desc, hetero="", smiles="COc1ccc(C)cc1", formula="C8H9FO"))
    assert "impossible" not in res["findings3"] and "{" not in res["findings3"]
