"""Tests of the version-2.1 fixes (text pasted from PDF, Word or other programs), on invented examples.
They come from the stress test with synthetic descriptions (fuzz test, 23.10.2026)."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))

import description_parser as dp  # noqa: E402
import text_checks as tc  # noqa: E402


def sig(text):
    return dp.parse_description("1H NMR (400 MHz, CDCl3) δ " + text)[1]


def test_double_spaces_tabs_line_breaks():
    s = sig("2.59–2.45  (m, 4H),\t6.05 (br\td,\nJ = 9.7 Hz, 6H)")
    assert [x["shift"] for x in s] == [2.52, 6.05]
    assert s[1]["mult"] == "d" and s[1]["br"] and s[1]["J"] == ["9.7"]


def test_no_break_and_thin_spaces():
    s = sig("8.90 (br d, J = 6.8 Hz, 1H), 6.32 (s, 6H)")
    assert s[0]["mult"] == "d" and s[0]["br"] and s[0]["J"] == ["6.8"] and s[1]["nH"] == 6


def test_invisible_characters():
    s = sig("6​.67 (­p, J = 10​.0 Hz, 1H), 4.97 (​dt, J = 12­.5, 4.9 Hz, 5H)")
    assert [x["shift"] for x in s] == [6.67, 4.97]
    assert s[0]["mult"] == "p" and s[1]["J"] == ["12.5", "4.9"]


def test_fullwidth_brackets():
    s = sig("1.55（m, 1H), 4.24 （br t, J = 2.1 Hz, 4H）")
    assert len(s) == 2 and s[1]["mult"] == "t" and s[1]["J"] == ["2.1"]


def test_constants_without_J_symbol():
    s = sig("4.92 (t, 8.7 Hz, 2H), 7.19 (dd, 8.3, 5.5 Hz, 2H), 6.10 (dd, 8.3 Hz, 5.5 Hz, 1H)")
    assert s[0]["J"] == ["8.7"] and s[1]["J"] == ["8.3", "5.5"] and s[2]["J"] == ["8.3", "5.5"]
    assert s[0]["nH"] == 2                       # the integral is not read as a constant


def test_space_after_decimal_point_in_J_and_inside_shift():
    s = sig("7.56 (t, J = 7. 6 Hz, 1H), 7.7 6 (d, J = 8.0 Hz, 1H)")
    assert s[0]["J"] == ["7.6"]
    assert s[1]["shift"] == 7.76


def test_pseudo_with_hyphen_and_brd():
    s = sig("1.82 (pseudo-td, J = 9.5, 8.0 Hz, 1H), 5.02 (brd, J = 9.9 Hz, 1H)")
    assert s[0]["mult"] == "td" and s[0]["app"]
    assert s[1]["mult"] == "d" and s[1]["br"]


def test_named_non_first_order_system_is_not_counted_for_4a():
    d = "1H NMR (300 MHz, CDCl3): δ 3.02–2.82 (AB part of ABX system, 2H, 16.1, 4.3, 5.5 Hz)"
    assert dp.parse_description(d)[1][0]["mult"] == "m"
    assert tc.check(d)["item4a"] != "inconsistent"


def test_clean_text_unchanged():
    d = "1H NMR (400 MHz, CDCl3) δ 7.26 (dd, J = 8.4, 2.1 Hz, 1H), 3.80 (s, 3H)."
    assert dp.normalize_text(d) == d


def test_square_brackets_rsc_style_and_multiplier():
    s = sig("7.26 [d, J = 8.0 Hz, 2H], 4.75 [brd, J = 13.2 Hz, 1H], 5.05 ppm [s, 2H]")
    assert [(x["shift"], x["mult"]) for x in s] == [(7.26, "d"), (4.75, "d"), (5.05, "s")]
    s = sig("0.84 (1H, ddd, 16.2, 12.2, 1.8), 1.43 (1H, d, 4.1)")     # neither J nor Hz
    assert s[0]["J"] == ["16.2", "12.2", "1.8"] and s[1]["J"] == ["4.1"] and s[0]["nH"] == 1
    s = sig("2.16 (d, 6H, J = 6.8 Hz, 2 × CH3)")                      # "2 ×" is not a constant
    assert s[0]["J"] == ["6.8"] and s[0]["nH"] == 6


def test_citation_in_square_brackets_is_not_a_signal():
    assert sig("7.26 (s, 1H); data as reported [12].") and len(sig("7.26 (s, 1H); data as reported [12].")) == 1


def test_cyrillic_lookalikes_and_header_without_bracket():
    s = sig("4.55 (ddd, J = 12.6, 5.4, 1.8 Hz, 1Н, H-4A)")          # Cyrillic "Н" in the integral
    assert s[0]["nH"] == 1 and s[0]["mult"] == "ddd"
    sys.path.insert(0, os.path.join(ROOT, "count_1H_descriptions"))
    import count_1H_descriptions as cnt
    assert cnt.H1.search("1H NMR δ: 1.49 (s, 3H, Me)")             # header followed directly by delta
    assert "1Н NMR".translate(cnt.HOMOGLYPHS) == "1H NMR"


def test_quin_and_dotted_septet():
    s = sig("1.61 (quin, J = 7.4 Hz, 2H), 2.01 (sep.d, J1 = 6.9 Hz, J2 = 5.1 Hz, 1H), 1.20 (dquin, J = 8.0, 6.5 Hz, 1H)")
    assert [x["mult"] for x in s] == ["p", "septd", "dp"]
    assert tc.check("1H NMR (400 MHz, CDCl3) δ 1.61 (quin, J = 7.4 Hz, 2H).")["item4a"] != "inconsistent"


def _extract():
    for sub in ("extract_names", "count_1H_descriptions"):
        p = os.path.join(ROOT, sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    import hrms_formula as hf
    import extract_names as en
    return hf, en


def test_ion_type_of_a_separate_low_resolution_ms_entry_is_not_used():
    hf, _ = _extract()
    seg = "MS (EI): [M]+: 306 (1 Cl). HRMS (ESI): m/z calcd. for C14H13ClNO3S [M+H]+: 310.0299, found: 310.0301."
    assert hf.neutral_formula(seg)[0] == "C14H12ClNO3S"
    seg = "HRMS (ESI) m/z: [M – H]^{-} calcd for C10H11N2O4 223.0724; found 223.0720."   # ion before calcd
    assert hf.neutral_formula(seg)[0] == "C10H12N2O4"
    # the ion type after the value belongs to the next value
    seg = "HRMS (ESI) m/z: [M]+ Calcd for C10H16O3 184.1099; Found 184.1100. [M+H]+ Calcd for C10H17O3 185.1178"
    assert hf.neutral_formula(seg)[0] == "C10H16O3"


def test_hrms_before_the_1h_description():
    _, en = _extract()
    entry = ("Compound {n}: Name {n}: procedure ... to afford {n} as a white solid. HRMS (ESI) m/z: [M + H]+ calcd for "
             "{f} {mz}; found {mz}. IR (neat) 2973. 1H NMR (400 MHz, CDCl3) δ 7.26 (s, 1H), 3.80 (s, 3H), {extra}. "
             "13C NMR (101 MHz, CDCl3) δ 170.1, 128.0, 52.0. ")
    # three compounds: C9H13NO2 (M+H C9H14NO2 168.1019), C10H15NO2 (C10H16NO2 182.1176), C11H17NO2 (C11H18NO2 196.1332)
    S = entry.format(n=3, f="C9H14NO2", mz="168.1019", extra="2.10 (s, 9H)") + \
        entry.format(n=5, f="C10H16NO2", mz="182.1176", extra="2.10 (s, 11H)") + \
        entry.format(n=7, f="C11H18NO2", mz="196.1332", extra="2.10 (s, 13H)")
    heads = [m.start() for m in en.H1.finditer(S)]
    ends = [en.description_end(S, h, heads[k + 1] if k + 1 < len(heads) else len(S)) for k, h in enumerate(heads)]
    assert en.hrms_before_style(S, heads, ends)
    assert en.label_and_name(S[ends[0]:heads[1]], True)[0] == "5"
    assert en.LABEL_CPD.search("Compound 8 (Db1): N-(2-amino)ethyl")


def test_acid_of_a_salt_is_exchangeable():
    sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))
    from rdkit import Chem
    import structure_checks as sc
    assert sc.h_counts(Chem.AddHs(Chem.MolFromSmiles("Cl.CN1CCCC1"))) == (12, 1)
    assert sc.h_counts(Chem.AddHs(Chem.MolFromSmiles("FC(F)(F)c1ccccc1"))) == (5, 0)    # C-F has no H


def test_structure_from_the_name_of_another_compound_is_not_used():
    sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))
    import check_descriptions as cd
    from rdkit import Chem
    d = "1H NMR (400 MHz, CDCl3) δ 7.26 (s, 5H), 4.10 (q, J = 7.1 Hz, 2H), 1.20 (t, J = 7.1 Hz, 3H)."
    reagent = dict(id="x", description=d, hetero="", smiles="CCOC(=O)C", formula="C10H10O2",
                   opsin_status="OK; FORMULA MISMATCH")
    assert cd.name_structure_guard(Chem.MolFromSmiles(reagent["smiles"]), reagent)[0] is None
    isomers = dict(reagent, smiles="Cc1ccccc1C.Cc1cccc(C)c1", formula="C8H10")
    assert cd.name_structure_guard(Chem.MolFromSmiles(isomers["smiles"]), isomers)[0] is None
    salt = dict(reagent, smiles="CN1CCCC1.Cl", formula="C5H11N")               # salt: kept
    assert cd.name_structure_guard(Chem.MolFromSmiles(salt["smiles"]), salt)[0] is not None
    given = dict(reagent, opsin_status="GIVEN")                                   # typed by a person: kept
    assert cd.name_structure_guard(Chem.MolFromSmiles(given["smiles"]), given)[0] is not None


def test_headers_spectrum_and_delta_h():
    sys.path.insert(0, os.path.join(ROOT, "count_1H_descriptions"))
    import count_1H_descriptions as cnt
    for t in ("1H NMR spectrum (400 MHz, DMSO-d6), δ, ppm: 12.17 (s, 1H, COOH), 7.97 (s, 1H, NH)",
              "1H NMR spectrum, (400 MHz, DMSO-d6), δ, ppm (J, Hz): 2.38 (3H, s, CH3S); 4.63-4.69 (1H, m, CH)",
              "δH (500 MHz, CDCl3): 14.55 (1H, s, OHenol), 5.06 (1H, s, 2-Henol)"):
        m = cnt.H1.search(t)
        assert m and cnt.is_description_header(t, m.start())
    t = "Figure S5. 1H NMR spectrum (CDCl3) of 1h 9 8 7 6 5 4 3 2 1 0 ppm"           # a caption
    assert not any(cnt.is_description_header(t, m.start()) for m in cnt.H1.finditer(t))


def test_more_multiplicity_forms_and_indexed_chains():
    s = sig("11.20 (dbr, J = 6.6 Hz, 1H), 7.99 (bd, J = 7.8 Hz, 1H), 4.11 (tap, J = 10.2 Hz, 1H), "
            "3.71 (m appears as t, 4H, J = 4.5 Hz), 3.67 (AB-q, J = 17.0 Hz, 2H), 2.10 (bm, 2H)")
    assert [(x["mult"], x["app"], x["br"]) for x in s] == [("d", False, True), ("d", False, True), ("t", True, False),
                                                           ("t", True, False), ("AB", False, False), ("m", False, True)]
    d = "1H NMR (400 MHz, CDCl3) δ 7.53 (dd, 1H, H-4, J4,3 = J4,5 = 7.2 Hz), 7.10 (t, J = 7.2 Hz, 2H)."
    assert tc.check(d)["item4a"] == "consistent"


def test_elemental_analysis_formula_is_neutral():
    hf, _ = _extract()
    seg = "Mass spectrum (ESI), m/z: 453 (100) [M-H]^{–}. Elemental analysis calcd for C25H30N2O6: C 66.06, H 6.65"
    assert hf.neutral_formula(seg)[0] == "C25H30N2O6"


def test_reading_quality_marker():
    from read_quality import reading_quality
    ok = "1H NMR (400 MHz, CDCl3) δ 7.26 (d, J = 8.4 Hz, 2H), 3.80 (s, 3H)."
    assert reading_quality(ok)["level"] == "green"
    glued = "1H NMR (400 MHz, CDCl3) δ 7.26 (d, J = 8.4 Hz, 2H), 6.88+6.84 (s, 2H), 3.80 (s, 3H)."
    q = reading_quality(glued)
    assert q["level"] == "yellow" and "6.88" in q["unread"]
    assert reading_quality("1H NMR (400 MHz, CDCl3) δ")["level"] == "red"
    procedure = ok + " Concentrated HCl (4.15 mL) was added to glycine ester (6.98 g, 50 mmol)."
    assert reading_quality(procedure)["level"] == "green"          # numbers of the procedure are not data
    tms = "1H NMR (400 MHz, CDCl3) δ 7.26 (d, J = 8.4 Hz, 2H), 0.95 (s, 9H), -0.10 (s, 6H)."
    assert reading_quality(tms)["level"] == "green"                # negative shifts of SiMe are real


def test_13c_data_after_the_1h_data_are_not_signals():
    d = ("δH (500 MHz, CDCl3) 7.82 (2H, d, J 9.0 Hz, 3,5-H2), 7.10 (2H, d, J 9.0 Hz, 2,6-H2). "
         "δC (125 MHz, CDCl3) 150.0 (C-1), 139.7 (C-3,5)")
    assert [x["shift"] for x in dp.parse_description(d)[1]] == [7.82, 7.10]
    d = "1H NMR (400 MHz, CDCl3) δ 1.13‒1.21 (m, 2H), 2.38 (spt, J = 6.9 Hz, 1H)."     # figure dash, "spt"
    s = dp.parse_description(d)[1]
    assert s[0]["range"] and s[1]["mult"] == "sept"


def test_name_locants_and_page_numbers_are_not_shifts():
    s = sig("0.89 (m, 3H). 2-Bromo-6-butylpyrido[2,1:2,3]imidazo[4,5-c]isoquinolin-5(6H)-one (8a) Yellow solid")
    assert [x["shift"] for x in s] == [0.89]
    s = sig("8.04 S-21 (dt, J = 8.2, 1.1 Hz, 1H), 7.51 SI-27 (t, J = 7.6 Hz, 2H), -0.10 (s, 6H)")
    assert [(x["shift"], x["mult"]) for x in s] == [(8.04, "dt"), (7.51, "t"), (-0.1, "s")]


def test_rmn_and_nmr_of_x_headers():
    sys.path.insert(0, os.path.join(ROOT, "count_1H_descriptions"))
    import count_1H_descriptions as cnt
    for t in ("RMN 1H (400MHz, DMSOd6, δ (ppm)): 10.02 (s, 1H); 7.91 (d, J= 8.2 Hz, 2H)",
              "1H NMR of PDIEH (400 MHz, CDCl3) δ (ppm): 8.59 (d, J = 8 Hz, 4 H), 8.48 (d, J = 8 Hz, 4 H)"):
        m = cnt.H1.search(t)
        assert m and cnt.is_description_header(t, m.start())
    t = "1H NMR spectrum of ethylmaltol (1) and physical appearance: 1H NMR (400 MHz, CDCl3): δ 7.70 (d, J = 5.5 Hz, 1H)"
    assert sum(cnt.is_description_header(t, m.start()) for m in cnt.H1.finditer(t)) == 1
    d = "RMN 1H (400MHz, DMSOd6, δ (ppm)): 10.02 (s, 1H). RMN 13C (100MHz, DMSOd6, δ (ppm)): 167.68 (C=O); 138.73 (C-Cl)"
    assert [x["shift"] for x in dp.parse_description(d)[1]] == [10.02]


def test_joc_forms_stack_labels_nested_and_double_header():
    s = sig("7.59 – 7.41 (stack, 3H), 5.39 (Hb dd, J = 5.9, 1.7 Hz, 1H), 7.79 (virt. d, J = 8.3 Hz, 2H), "
            "2.37 (s(br.), 1H), 3.89 (A of AB, J = 13.0 Hz, 1H), 3.61 (hep, J = 6.3 Hz, 1H), "
            "4.84–4.71 (m, 2H, P(OCH(CH3)2)2)")
    assert [(x["mult"], x["app"], x["br"]) for x in s] == [("m", False, False), ("dd", False, False), ("d", True, False),
                                                           ("s", False, True), ("AB", False, False),
                                                           ("sept", False, False), ("m", False, False)]
    sys.path.insert(0, os.path.join(ROOT, "count_1H_descriptions"))
    import count_1H_descriptions as cnt
    t = "1H NMR (400 MHz, DMSO-d6, 298 K): δ = 1H NMR (400 MHz, DMSO) δ 11.35 (s, 1H), 9.90 (s, 1H), 8.54 (dd, J = 8.2, 1.4 Hz, 1H)"
    assert [cnt.is_description_header(t, m.start()) for m in cnt.H1.finditer(t)] == [False, True]


def test_mc_assigned_constants_and_sentence_headers():
    s = sig("7.94 (mc, 2H), 3.60 (HB: td, J = 6.7 (eqB–axA), 6.7 (eqB–axC), 1.2 (eqB–eqD), 1H)")
    assert s[0]["mult"] == "m" and s[1]["mult"] == "td" and s[1]["J"] == ["6.7", "6.7", "1.2"]
    sys.path.insert(0, os.path.join(ROOT, "count_1H_descriptions"))
    import count_1H_descriptions as cnt
    for t in ("1H NMR spectrum (400 MHz, CDCl3) shows two rotamers in a 1:2.3 ratio. For the major rotamer: "
              "1H NMR (400 MHz, CDCl3) δ 8.19 (s, 1H), 7.62 (dd, J = 14.7, 11.1 Hz, 1H)",
              "1H NMR: 32% NMR yield using bromoform as an internal standard. 1H NMR (400 MHz, CDCl3): δ 3.51 (t, J = 6.8 Hz, 2H)"):
        assert [cnt.is_description_header(t, m.start()) for m in cnt.H1.finditer(t)] == [False, True]


def test_article_text_ends_and_page_header():
    s = sig("δ 6.20 (t, J = 5.7 Hz, 1H), 2.08 (d, J = 5.7 Hz, 1H, SH). Spectral data matched literature reports. "
            "To a solution of thiol 23 (1.50 g, 2.45 mmol)")
    assert [x["shift"] for x in s] == [6.2, 2.08]
    s = sig("δ: 8.25 (1H, m), 5.07 (2H, s). 13C{1H} (150 MHz, CDCl3) δ: 148.4, 79.8. carbamate 10.^{19} T")
    assert [x["shift"] for x in s] == [8.25, 5.07]
    s = sig("δ 7.92 (d, J = 8.0 Hz, The Journal of Organic Chemistry pubs.acs.org/joc Article "
            "https://doi.org/10.1021/acs.joc.4c01729 J. Org. Chem. 2024, 89, 15048−15061 15055 2H), 7.10 (s, 1H)")
    assert [(x["shift"], x["nH"]) for x in s] == [(7.92, 2.0), (7.1, 1.0)]
    s = sig("δ 7.2 (d, J = 8.0 Hz, 1H). Rotamer B: δ 7.1 (d, J = 8.0 Hz, 1H)")
    assert len(s) == 2


def test_quasi_is_apparent():
    s = sig("δ 7.38 (quasi d, J = 8.8 Hz, 2H)")
    assert s[0]["mult"] == "d" and s[0]["app"]


def test_shift_lists_and_mult_before_bracket():
    s = sig("δ 2.09, 2.08, 2.01 (3× s, each 3H, OAc), 8.14 and 7.82 (2 s, 1H, rotamer)")
    assert [(x["shift"], x["mult"], x["nH"]) for x in s] == [(2.09, "s", 3.0), (2.08, "s", 3.0), (2.01, "s", 3.0),
                                                            (8.14, "s", 0.5), (7.82, "s", 0.5)]
    s = sig("δ = 6.32 dd (1H, J = 17.7 and 10.2 Hz, H-5), 1.63 (hextet, J = 7.6 Hz, 2H)")
    assert [(x["shift"], x["mult"]) for x in s] == [(6.32, "dd"), (1.63, "sext")]


def test_pt_pseudo_triplet():
    s = sig("δ 4.13 (pt, J = 7.0 Hz, 1H), 1.50 (pt, J = 7.0, 2.0 Hz, 2H)")
    assert (s[0]["mult"], s[0]["app"]) == ("t", True) and s[1]["mult"] == "pt"


def test_item1_partial_boron_and_mixture_words():
    sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))
    from structure_checks import check_item1_formula
    from text_checks import MIXTURE
    d = "1H NMR (400 MHz, CDCl3, characteristic peaks) δ 5.84 (tt, J = 56.3, 4.4 Hz, 1H), 5.30 (d, J = 4.2 Hz, 1H)"
    assert check_item1_formula(d, sig(d), "C13H14F2O4", False)[0] == "cannot be determined"
    d = "δ " + ", ".join("%.2f (s, 3H)" % (7 - i * 0.3) for i in range(7)) + ", 1.10 (m, 22H)"
    assert check_item1_formula(d, sig(d), "C25H53B10N", False)[0] == "subcategory: protons on quadrupolar nuclei not reported"
    assert MIXTURE.search("7.51–7.41 (m, 2H, both diast)") and MIXTURE.search("(m, 18H, dmajor and dminor)")


def test_jointly_written_shifts_are_not_first_order_pairs():
    sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))
    from text_checks import pairs_6b
    d = "1H NMR (300 MHz, CDCl3) δ 2.85 and 2.70 (AB part of ABX system, 2H, JAB = 13.3, JAX = 1.3, JBX = 5.2 Hz)"
    sigs = sig(d)
    assert len(sigs) == 2 and sigs[0]["group"] == sigs[1]["group"] == 0
    vals = [v for s in sigs for v in s["J"]]
    assert all(p["status"] == "exempt" for p in pairs_6b(sigs, 300, vals))


def test_formula_item1_in_protic_solvent_and_dia_words():
    sys.path.insert(0, os.path.join(ROOT, "check_descriptions"))
    from structure_checks import check_item1_formula
    from text_checks import MIXTURE
    d = "1H NMR (400 MHz, D2O) δ 5.62 (s, 1H), 4.62−4.57 (m, 2H), 4.38−4.33 (m, 1H), 4.31−4.23 (m, 3H) ppm."
    assert check_item1_formula(d, sig(d), "C7H10O6", False)[0].startswith("subcategory")
    assert MIXTURE.search("δ 6.20 (dia 1, d, J = 6.3 Hz, 1H)")


def test_mdpi_forms():
    s = sig("δ 4.01, 4.27 (2d, 2H, J = 12.8 Hz, CH2Ph), 7.32–7.43 (m, 8 arom. H) ppm.")
    assert [(x["shift"], x["nH"]) for x in s] == [(4.01, 1.0), (4.27, 1.0), (7.375, 8.0)]
    s = sig("δ 1.40–1.30 (m, 1H). 6-(4-Hydroxy)hexyl propionate (5b) was prepared from 3 (300 mg, 1.28 mmol), "
            "Molecules 2025, 30, 4508 15 of 24 [Cu2I2]")
    assert len(s) == 1
    s = sig("δ: 5.21 (t, J = 3.2 Hz, 1H, CH), 0.86 (m, 24H); ^{13}CNMR (CDCl3) δ: 177.8, 18.5, 17.3, 15.7;")
    assert len(s) == 2


def test_mdpi_forms_2():
    s = sig("δ 9.33 (s, 1H), 7.69~7.61 (m, 4H), 3.78 (s, 3H); 13C  (151MHz, DMSO-d6) δ 187.37, 126.75 (q, J = 30.5 Hz)")
    assert [x["shift"] for x in s] == [9.33, 7.65, 3.78]
    s = sig("δ 6.22 s, 1H (H-6), δ 3.52 hep, J = 7.1 Hz, 1H (H-8), δ 1.33 d, J = 7.1 Hz, 6H (H-9)")
    assert [(x["mult"], x["nH"]) for x in s] == [("s", 1.0), ("sept", 1.0), ("d", 6.0)]
    s = sig("δ 8.19, 8.08, and 7.72 (3br t, 3:1:1, J = 5.5 Hz, 1H)")
    assert [x["nH"] for x in s] == [0.6, 0.2, 0.2]
    assert len(sig("δ 7.28–7.23 (4H, m, NH). 13C HMR (100 MHz, CDCl3) δ: 180.28 (C=O), 139.56 (C, C-1)")) == 1


def test_mdpi_forms_3():
    s = sig("δ 2.20 (s, 3H), 2.64–2.77, 2.90–3.04 (2m, 2H, COCH2), 3.93–4.04 (m, 2H)")
    assert [(round(x["shift"], 3), x["nH"]) for x in s] == [(2.2, 3.0), (2.705, 1.0), (2.97, 1.0), (3.985, 2.0)]
    s = sig("δ 7.76 (nfod, Japp = 8.3 Hz, 2H), 3.85 (br-d, J = 7.0 Hz, 4H), 9.87 ((brs, 1H, NH)")
    assert [(x["mult"], x["br"]) for x in s] == [("m", False), ("d", True), ("s", True)] and s[0]["Japp"] == ["8.3"]
    assert len(sig("δ 1.15 (d, J = 6.7 Hz, 12H). ESI-MS: [m/z] = 580.2021 (M2+) (calcd: 580.21 (M2+).")) == 1


def test_mdpi_forms_4():
    s = sig("δ 2.19–2.29 (c.s., 2H, NH), 1.83–1.64 (comp, 2H), 2.26 (oct, J = 6.9 Hz, 1H), 7.32 (exch br s, 2H); "
            "3.48 (s, 3H). 13C {H} (100 MHz, CD2Cl2, ppm): δ 155.94 (s); 145.94–145.89 (t, J = 3 Hz)")
    assert [x["mult"] for x in s] == ["m", "m", "m", "s", "s"]


def test_j_values_stop_at_assignment_locants():
    for t, j in (("δ 7.05 (2H, d, J = 8.3 Hz, 1′-CH2)", ["8.3"]), ("δ 7.93 (d, 1H, J = 8.4 Hz, 2CH2)", ["8.4"]),
                 ("δ 2.21 (dd, 1H, J = 11.2, 6.3 Hz, 7,8-H)", ["11.2", "6.3"]),
                 ("δ 7.12 (dd, 1H, J = 8.3 Hz, 2.7, 2^{4},3^{4}-H)", ["8.3", "2.7"]),
                 ("δ 3.1 (t, J = 7.2Hz, 2H)", ["7.2"]), ("δ 7.1 (dd, J = 8, 2 Hz, 2H)", ["8", "2"])):
        assert sig(t)[0]["J"] == j, t


def test_integer_locants_after_constants_and_pt_without_j():
    for t, j in (("δ 4.98 (1H, dd, J = 6.4, 2.7, 5-OH)", ["6.4", "2.7"]), ("δ 7.14 (td, 1H, J = 7.6, 1.8 Hz, 5,9H)", ["7.6", "1.8"]),
                 ("δ 6.59 (1H, t, J = 7.6 Hz, 8- CH3)", ["7.6"]), ("δ 5.86 (d, 1 H, J = 3.1 Hz, 2 CH2NH3)", ["3.1"]),
                 ("δ 7.1 (ddd, J = 8, 2, 1 Hz, 2H)", ["8", "2", "1"])):
        assert sig(t)[0]["J"] == j, t
    s = sig("δ 2.18 (pt, 2H)")
    assert (s[0]["mult"], s[0]["app"]) == ("t", True)
