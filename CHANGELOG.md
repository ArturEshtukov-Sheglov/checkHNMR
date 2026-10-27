# Changelog

All notable changes to the tools. Newest first. For every version: what changed and whether it
changes the results. Dates are those of the code; the version used in the paper is marked.

## 2026-10-26 — V2.1.1-beta (launchers only; the check scripts are identical to V2.1-beta)

Changes that **do not change results**:
- `run_all.py` also writes a Word report for every checked file, `results\<file name>\checked_<file name>.docx`
  (Review to Word, `review_to_word/export_docx.py`): one compound per page, the structure, the description
  with the flagged signals coloured, the verdict and the findings for every item. The script only reads the
  result table `checked_<file name>.xlsx`, which stays as before. A Word report missing from an earlier run is
  made when `run_all` is started again.
- `python-docx` added to the packages that `run_all` checks and installs (`requirements.txt`) and to the Colab
  notebook.
- The SHA-256 of every check script (check_descriptions, extract_names, names_to_smiles, count_1H_descriptions,
  rename_SI, the tests and the style file of the realistic test) is the same as in V2.1-beta; only `run_all.py`
  changed and `review_to_word/export_docx.py` was added (SHA256_V2.1.1-beta_2026-10-26.txt).
- New repository **checkHNMR** for the local version of the checkHNMR website (the version used in the survey
  of Organic Letters and the registration files stay in the repository nmr-1h-description-tools). The
  repository is in English only (the Russian READMEs, changelog, command list and development log were not
  carried over); `INSTALL.md`: a step-by-step installation guide; `COMMANDS.md`, `DEVELOPMENT_LOG.md` and the
  lists of development articles moved to `docs/`; `data/README.txt` added; the files of version 1.1
  (SHA256_v1.1, EQUIVALENCE_v1.1) are in the repository nmr-1h-description-tools.

## 2026-10-26 — V2.1-beta (frozen 2026-10-26; a beta until its accuracy is measured on the test articles of the
## second data set; developed from 2026-10-23; NOT the version used in the paper)

Changes that **change results** (more descriptions read correctly), from a stress test with
synthetic descriptions (`tests/stress/fuzz_parser.py`): signals generated with a known answer, written
clean and then with "format noise" that does not change the meaning (copy-paste from PDF or Word).

- `check_descriptions` (`normalize_text`): before parsing, invisible characters (zero-width space, soft
  hyphen, BOM) are removed, full-width brackets "（ ）" become "( )", and every run of white space
  (double spaces, tabs, line breaks, no-break and thin spaces) becomes one space. A space right after a
  decimal point ("J = 7. 6 Hz") and a space inside a shift ("7.7 6 (d") are removed (PDF text).
- Constants written without "J" are read: "(t, 8.7 Hz, 2H)", "(dd, 8.4, 2.1 Hz, 1H)" (before: no constant,
  an item-4(a) finding).
- "pseudo-td" and "brd"/"brt" are read as app td and br d/br t.
- A named non-first-order system written instead of a multiplicity ("AB part of ABX system", "AA'BB'",
  "A2B2 system") is treated like "m": the number of its constants is not checked under item 4(a).
- Stress test, 10,000 synthetic descriptions (seed 260626; 1-3 noises each): misread V2.0.1 16.1 %,
  V2.1 3.1 %; all remaining misreads have a decimal comma ("7,26"), which is not supported (it cannot be
  told from the comma between values). Second seed (777): 14.8 % -> 3.0 %. Clean form: 0 misread
  (one generated description had the same signal twice; the parser keeps one, as before, on purpose).
- Regression on the 201 SI of the Organic Letters sample (for information; not a measure of accuracy):
  79 of 8,609 descriptions parsed differently, all inspected: constants now read (67), shifts with a
  space inside now right (15), a full-width bracket, br d with a no-break space; one extra "signal" from
  a figure caption that the extraction kept in a description (no multiplicity, no integral: no finding).
  Text checks: item 4(a) 66 false findings removed, 1 real one added ("7.41 (brd, 1H)", d without J);
  item 6(b) 10 new findings and item 3 4 new ones where constants were not read before.
- A signal written twice with exactly the same text is kept twice. Up to V2.0.1 (and in the frozen version)
  the repeat was dropped as a copy of the text; in published descriptions such repeats are different groups
  (two OMe of PMB groups, three TBS groups, keto and enol forms), and dropping one gave false item-1
  findings. 83 of 8,609 descriptions of the 201 SI (15 of the 982 selected) contain such a repeat.
  Found with the structure stress test (all its false item-1 findings came from this).
- Self-test: `python run_all.py --selftest` (or `run_tests.bat` / `run_tests.sh`) runs the unit tests and the
  three stress tests (fixed seed, 10,000 synthetic descriptions each by default, `-n` to change) and prints
  PASS/FAIL against fixed expectations. The structure test uses by default the structures of the development
  set (three J. Am. Chem. Soc. 2026 articles, `tests/stress/structures_dev.json`).
- Found on real SI of Beilstein J. Org. Chem. (open access, downloaded from PubMed Central): a 1H header
  followed directly by the delta ("1H NMR δ: 1.49 (s, 3H)") is a header (before, the whole SI gave 0
  descriptions); Cyrillic letters that look like Latin ones ("1Н NMR", "1Н", "°С" typed with a Russian
  keyboard layout) are read as Latin. On the 201 Org. Lett. SI: 8,610 -> 8,611 descriptions (one real
  description with the header "1H NMR δ" now found).
- Also read: signals in square brackets ("7.26 [d, J = 8.0 Hz, 2H]"); constants with neither "J" nor "Hz"
  ("(1H, ddd, 16.2, 12.2, 1.8)", RSC style; read only when the multiplicity needs constants); "2 × CH3" after
  the constants is not read as a constant.
- Stress tests in `tests/stress/`: `fuzz_parser.py` (format noise, 53 kinds), `semantic_test.py` (known errors
  put into consistent first-order spin systems: items 3, 4(a), 6(b)), `structure_test.py` (descriptions written
  from real structures with known errors: items 1, 4(b)).
- 11 new tests (54 in total).
- 2026-10-24, found on 32 more SI of Beilstein J. Org. Chem. 2025 (development data, `DEVELOPMENT_DATA_BJOC_PMCIDs.txt`):
  - `extract_names`: some SI give the HRMS of a compound BEFORE its 1H description ("HRMS ...; IR ...; 1H NMR ...").
    The HRMS of the next compound was then attached to each description, and labels were lost. The style is
    now decided for each file from the data: the formulas are attached both ways, and "before" is taken only
    when clearly more descriptions then have as many H in their integrals as in the formula. In such files
    the label is the nearest "Compound 7:" heading; "Compound 8 (Db1):" is read too.
  - `extract_names` (`hrms_formula`): the ion type is taken after "calcd" first; one written before it only
    when no other MS entry lies between ("MS (EI): [M]+: 406. HRMS (ESI): m/z calcd for ... [M+H]+" gave [M]+),
    and one written after it only before the next "found"/"calcd" ("[M]+ Calcd for ...; Found ... [M+H]+ Calcd").
  - `check_descriptions`: "quin", "dquin", "sep.d", "sep", "sex", "sxt" are read.
  - `run_all` cross-check: 13C descriptions without δ ("13C{1H} NMR (150 MHz, DMSO-d6): 153.0, 149.9, ...") are
    counted; HRMS values are halved before the comparison (one compound may have two or three ions).
  - `run_all` on Windows: result paths longer than 260 characters failed ("No such file or directory" when saving
    `compounds_<SI name>.xlsx` in a deep folder); the results folder now gets the "\\?\" long-path prefix.
  - `check_descriptions`, item 1: the H of an acid in a salt written as a separate fragment ("Cl.CN1CCCC1", HBr)
    is counted as exchangeable (it is the N-H+ proton); before, a hydrochloride without the N-H+ signal was
    "inconsistent" instead of "exchangeable proton not reported". None of the 982 selected descriptions has such a salt.
  - `check_descriptions`: a structure made by OPSIN from a name and marked FORMULA MISMATCH is not used when it has
    fewer C than the HRMS formula (the name of another compound, e.g. a reagent taken from the procedure) or is made
    of fragments each with the C of the formula (isomers named together); item 1 is then checked against the
    formula. Salts, ions and structures typed by a person are kept. On the 36 BJOC SI: 2 of 13 FORMULA MISMATCH rows.
    The 982 selected descriptions have reference structures (no OPSIN status): not affected.
  - 2026-10-24, batch 4 (78 more BJOC SI): 1H headers "1H NMR spectrum (400 MHz, DMSO-d6), δ, ppm:" and
    "δH (500 MHz, CDCl3):" are found (+90 descriptions in that batch; none added in the 201 Org. Lett. SI or the
    first 36 BJOC SI); "dbr", "bd", "bt", "bm", "tap", "m appears as t", "AB-q" are read; chains of equal
    constants with atom indices ("J4,3 = J4,5 = 7.2 Hz") count as two constants; a formula after "Elemental
    analysis/Anal. calcd for" is the neutral molecule (it took the ion type of a neighbouring MS line).
    Regression: parser 0 of 8,609 descriptions of the 201 SI changed; extraction 1 of 8,611 rows (SI056, Anal.
    formula now as written) and 4 of 599 BJOC rows (Anal. formulas of salts now read).
  - 2026-10-24, reading-quality marker (`check_descriptions/read_quality.py`; columns "read (text)" and "what was
    not read" at the end of the table 'checked'): the recognised signals are removed from the description and the
    rest is examined. Green: everything read; yellow: a shift-like number left over ("6.88+6.84 (s", "4.94, 4.87
    (ABq", a missing bracket), a signal without multiplicity or integral, a shift outside -5 to 21 ppm, or shifts
    out of order (3 or more breaks); red: header without any signal. For the "as read" preview of the website.
    Calibration: 201 Org. Lett. SI 8,300 green, 297 yellow, 12 red; BJOC batch 4 1,062 / 89 / 2; the yellow
    ones inspected are almost all author notation or text glued from the PDF. Per file (`run_all`, column
    'warning'): symbol-font characters that could not be mapped, unreadable characters, and little text per
    page when no description was read (a scan).
  - Found with the marker: 13C data in the same paragraph as the 1H data ("δC (125 MHz", "13C{1H) NMR") were read
    as 1H signals; the description now ends at the header of another nucleus (parser and extraction). Figure
    dash "‒" in ranges, "spt", "multiple peaks" and starred shifts "8.62* (" are read. Parser regression on the
    201 SI: 15 of 8,609 descriptions changed, all gains (13C values no longer 1H signals, septets, ranges).
  - Extraction regression of the new description end (header of another nucleus) on the 201 Org. Lett. SI and the
    114 BJOC SI: 61 of 10,363 descriptions changed, no description gained or lost; all now end before the 13C data
    they included before (SI167: "13C{1H) NMR"; PMC12456075: "δC (125 MHz"). The 982 selected descriptions are
    clean texts in the pass-3 table: not affected. Symbol-font "⊕" written for "+" ("[M+H]⊕") and list bullets
    are mapped; the per-file warning then fires on 10 of 315 SI.
  - Not shifts: a locant in a compound name glued to the description ("isoquinolin-5(6H)-one" was read as a signal
    at -5 ppm with 6H) and an SI page number between a shift and its bracket ("7.03 – 7.00 S-13 (m, 2H)" was read
    as -13 ppm; now 7.015 ppm). Parser regression on the 201 SI: 94 of 8,609 descriptions changed; 86 lose
    "signals" without multiplicity or integral made from names, captions and page numbers, 4 get the right shift.
  - `run_all` on Windows warns at the start when the folder of the tools is so deep that Excel (limit 259
    characters) could not open the result tables, and asks to move it to a short path such as C:\nmr\.
  - 2026-10-24, ACS Omega 2025 (175 SI, development data): headers "RMN 1H (" and "1H NMR of <name> (400 MHz"
    are found ("RMN 13C" ends a description). Count regression on the 201 Org. Lett. SI, 114 BJOC and 175 ACS Omega
    SI: +17 descriptions, all in three ACS Omega SI; no change elsewhere. `fetch_oa_si.py`: retries a broken
    download, logs it as "download failed" and tries it again on the next run; refuses the journals of the study.
  - 2026-10-24, J. Org. Chem. 2024-2025 (297 SI, development data): "stack", "overlapping m", "virt. d", "appt. d",
    "hep", "s(br.)", "A of AB"/"B of AB" and a proton label before the multiplicity ("Hb dd") are read; brackets two
    levels deep inside a signal ("P(OCH(CH3)2)2"); a 1H header followed at once by a second header (a header pasted
    from the processing software after the author's own) is not counted as a description. Regression: parser 2 of
    8,609 descriptions of the 201 SI changed (signals with nested brackets now read); count of descriptions: -1 in
    six Org. Lett. SI and three BJOC SI, all such doubled headers (none of them among the 982 selected
    descriptions, whose counts already excluded them). Two of these SI have different frequencies in the two
    headers (400 vs 500/600 MHz).
  - 2026-10-24, J. Org. Chem. (continued): "mc" and "overlap" read as m; an assignment in brackets after each
    constant is removed before reading; a 1H header is not a description when another 1H header comes before its
    first shift (sentences such as "1H NMR spectrum (400 MHz) shows two rotamers…", "1H NMR: 32% NMR yield…",
    captions); control characters and U+FFFE/U+FFFF removed from PDF text. Count regression on the 201 Org. Lett.,
    114 BJOC, 175 ACS Omega and 297 J. Org. Chem. SI: 16,180 -> 16,142 descriptions; every removed one inspected is
    such a sentence, caption or doubled header (in the 201 SI: 9, none among the 982 selected); +17 in ACS Omega
    from the new headers. Parser on the 201 SI: 2 descriptions changed (gains).
  - 2026-10-24, J. Org. Chem. article PDFs: the running page header of ACS journals is removed from the PDF text;
    a description also ends at "13C{1H} (" without "NMR", at "2H NMR" and at "■ ASSOCIATED CONTENT"; reading stops at
    a sentence after a signal when no further signal follows (procedure text after the description); "quasi d" read
    as apparent d. Regression: count of descriptions unchanged on all sets; parser on the 201 SI: 33 descriptions
    changed, all lose numbers of the following text read as signals (compound numbers, yields, references).
  - 2026-10-24, J. Org. Chem. article PDFs (all 300): several shifts with one bracket read as one signal per shift
    (integral to each for "each 3H" / "4 × 3H", otherwise shared equally); the multiplicity written before the
    bracket ("6.32 dd (1H") read; "hextet", "overlapped s"; fragments of a split page header removed; "gHSQCAD" and
    similar end the 1H data; the reading marker accepts shifts up to 21 ppm (chelated enol OH). Parser on the 201
    SI: 40 descriptions changed in total since the previous package, all gains (e.g. "2.85 and 2.7 (AB part of ABX
    system, 2H)" now two signals of 1H).
  - 2026-10-24, J. Org. Chem. run with structures: mixture words "diast", "dmajor/dminor", "2H d1"; B-H of boron
    clusters (3 B or more) or of B-H in the structure not listed = item-1 subcategory "protons on quadrupolar nuclei
    not reported" (protocol v1.2); "characteristic peaks" and similar partial descriptions:
    item 1 cannot be determined; a structure from a class word as the name (at most 8 heavy atoms, the description
    at least 3 times and 10 H larger; not mixtures) is not used; "pt" read as pseudo-triplet when the constants fit;
    shifts written with one bracket are exempt from 6(b). J. Org. Chem. (5,369 rows with structures): item 1
    inconsistent 613 -> 540, 4(a) 216 -> 196, 6(b) 809 -> 796. Verdict regression on the 201 Org. Lett. SI (8,323
    rows): 16 verdicts changed, none among the 982 selected; all from descriptions now read correctly.
  - 2026-10-25, J. Org. Chem. articles with structures: item 1 checked against the formula only, in D2O/CD3OD,
    with fewer H = subcategory "exchangeable proton not reported" (OH/NH are not seen; their number is unknown
    without a structure); "(dia 1, …" is a mixture word. Verdict regression on the 201 Org. Lett. SI: 16 more item-1
    verdicts "inconsistent? (check)" -> subcategory, all in D2O/CD3OD; 2 of them among the 982 (SI138_1, SI138_17,
    nucleosides in D2O, where the reviewer noted the exchanged NH).
  - 2026-10-25, Molecules (MDPI) articles: "8 arom. H" read as an integral; reading stops at any sentence after a
    signal when no signal follows; MDPI running header removed; "^{13}CNMR" ends the 1H data. Regression: count of
    descriptions unchanged on all sets (19,079 incl. the 300 J. Org. Chem. articles and Molecules); 201 Org. Lett.
    SI: one more verdict change among the 982 (SI115_29 item 1 cannot be determined -> consistent, junk after the
    description no longer read).
  - 2026-10-25, Molecules (continued): "13C HMR" / "13C (151MHz" end the 1H data; "~" range sign; signals without
    brackets; ", and" in shift lists; the integral of a list shared in the stated ratio. Regression: count unchanged
    (19,552 descriptions on all sets incl. 500 Molecules articles); 201 SI: no further verdict change.
  - 2026-10-25, Molecules selected with --term "CDCl3 OR DMSO-d6" (507 articles, 352 with 1H descriptions, 4,835
    descriptions; 90 % read completely): lists of ranges with one bracket; "nfod, Japp" read as m with J_app; "br-s",
    "complex", "comp", "c.s.", "oct" -> m; "exch" ignored; doubled bracket; "13C {H} (", ESI-MS, m/z, UV-vis and IR
    end the 1H data. Regression: count unchanged on all sets (24,387 descriptions); 201 SI: no further verdict change.
  - 2026-10-26: realistic stress test added to the self-test (tests/stress/realistic_test.py, build_styles.py,
    realistic_styles.json.gz): the content of a published description written in the style of another, with the
    forms of writing and their frequencies of the 15,723 development descriptions (the 12,830 read completely give
    the styles and contents). 100,000 descriptions (seed 260626): V2.1 misread 0.04 %, V2 7.02 %. It found reading
    errors, fixed: an assignment starting with a digit after the constants ("1′-CH2", "2CH2", "7,8-H", "5,9H",
    "8- CH3", "2 CH2NH3") read as a constant; "pt", "pq" without constants read as pentets (now pseudo-t, pseudo-q). Regression on
    the 201 Org. Lett. SI: false 4(a) findings removed for SI033_3 and SI183_6e (reference: consistent).
  - Regression on the 201 Org. Lett. SI (for information): parser 12 of 8,609 descriptions changed (septets and
    "dquin" now read); extraction 49 of 8,611 rows changed: SI035 (38) and SI181 (10) are files with the HRMS
    before the 1H description, where all earlier versions, the frozen one included, attached the formula of the
    neighbouring compound; one [M+NH4]+ formula (SI063) now right. The 10 descriptions of these two files in the
    selected 982 already had the right formulas and reference structures in the pass-3 table: the survey
    results are not affected.

## 2026-10-23 — V2.0.1: launchers only (results unchanged)

The checking scripts are unchanged (same SHA-256 as V2); only the launchers changed (and one comment
in `rename_SI.py`).

- `run_all.py` checks Python (3.10 or newer: the tested package versions have no builds for older
  Python) and the packages pymupdf, openpyxl, rdkit before the check. If a package is missing it asks
  `Install them now? [y/n]` and installs the versions from `requirements.txt` (if those have no build
  for the installed Python, the latest versions, with a warning). Where the system does not allow
  packages in its own Python (PEP 668, many Linux distributions), it creates a folder `.venv` next to
  the scripts, installs the packages there and restarts itself in it; later runs use `.venv`
  automatically.
- `run_all.py` tests the OPSIN web service before the run. Without it the descriptions are checked from
  the text only (items 3, 4(a), 6(b), item 1 from the HRMS formula) instead of not at all; such files
  are done again, with structures, on the next run when OPSIN answers.
- New `run_all.sh` for Linux and macOS (`bash run_all.sh`), the same as `run_all.bat`.
- `run_all.bat` no longer installs the packages itself (without asking); `run_all.py` does it.
- README, COMMANDS: Python 3.10 or newer; `run_all.sh`; README: "items 2, 5 and 7 are not checked,
  4(b) only partly" (it still said "2, 4(b) and 7").
- The folder `samples` (the table of the Organic Letters sample) is not part of V2; it will be published
  with the paper, together with version 1.1 used for the paper's results. Examples in the README files use
  `SAMPLE_TABLE.csv` and an article outside the sample.
- Tested: 43 tests pass; installation into an empty environment (answer "y"); a run without internet
  (text checks only).

## 2026-10-22/23 — V2 (release; NOT the version used in the paper)

Changes that **change results**; started on an SI outside the Organic Letters sample (development
set). Accuracy of version 2 is to be measured only on data not used to develop it (OSF update 1,
section 2c). The frozen version and version 1.1 are unchanged.

- `count_1H_descriptions`: characters typed in the Symbol font (digits, point, brackets, comma,
  space, Greek letters, ±, ×, °) are no longer lost — they come out of the PDF as private-use
  characters U+F0xx and are now converted (before, only δ, U+F064, was). Descriptions whose shifts
  begin with such characters were missed or read as ".03 (t" instead of "2.03 (t".
- `count_1H_descriptions`: a description ends also at "MS (m/z, %)" (mass-spectrum lines were read
  as signals).
- `extract_names`: descriptions of isomers of a mixture ("Major isomer.", "Minor isomer.",
  "2nd isomer.", "1st (major) isomer:") — the phrase is kept in the description (so the check sees a
  mixture); a non-major isomer gets the label of its compound ("4b-minor", flag "ISOMER of #n"), its
  name and the HRMS formula (given to all isomers when the HRMS follows the last one).
- `check_descriptions`: the index of the next coupling constant is no longer read as a value
  ("3J = 13.2 Hz, 3J = 10.6 Hz" gave "J = 3"; "³J₈,₁₂ = 8.2 Hz" gave extra values).
- `check_descriptions`: a chain of equal constants, "²J = ³J = 13.6 Hz", is one value standing for
  each J of the chain (dd with such a chain has its two constants for item 4(a)).
- `check_descriptions`: coupling constants written without "=" ("dd, J 8.4, 5.5 Hz") are read
  (before, none was read and every such signal was an item-4(a) finding).
- `extract_names`: HRMS with the formula before the word, "for [M+H]+ (C15H18NO2 +) calculated m/z
  244.1332" (only a real formula, C…H…, in brackets is taken).
- `extract_names`: a number in brackets in an IR block ("aromatic C-H (805)" after "IR"/"cm-1") is
  not a compound label.
- `check_descriptions`: a space after the decimal point inside a shift ("7.55–7. 08 (m") is read as
  7.08.
- `check_descriptions`: if the description says that it lists only some signals ("The other signals
  are overlapped with the signals of the major isomer"), a missing partner (item 3) is "may be among
  the signals not listed", not a likely inconsistency.
- Regression on the 201 SI of the Organic Letters sample (for information; not a measure of
  accuracy): extraction — same 8,609 descriptions, 12 files changed (Symbol characters, isomer
  labels, formulas); check — 58 item-4(a) findings removed (51 in one SI with indexed constants
  "³J₈,₁₂"), about 15 changes in items 3 and 6(b).
- 9 new tests (tests/test_v2_fixes.py). Development SI so far: ol3c04097 (Org. Lett. 2023), ol503595m
  (Org. Lett. 2014), cs5b02916 (ACS Catal. 2015).

Second set of changes (22.10, evening), started on three SI of J. Am. Chem. Soc. 2026 (ja5c20554,
ja6c04560, ja6c10875; added to the development set):

- `extract_names`: an ion type that is not simply M plus/minus an adduct is read as written:
  "[M-N2+H]+", "[M-OTf]+", "[M+H-H2O]+", "[M-(H2O)2+H]+", "[M-H+]-", "[M+HCOO]-", "[M+NH4+]". The
  molecular formula = the ion formula (checked against the calculated m/z) minus the written changes;
  known groups: Me, Et, OMe, OAc, OTf, OTs, Tf, Ts, NTf2. If a group is not a formula ("[M-Boc+H]+",
  "[M-CO2t-Bu+2H]+"), no formula is given ("fragment ion - molecular formula not derived"). Before,
  such ions were taken as the molecule, or an H was subtracted by the DBE rule — wrong for anions
  [M-H+]- (H subtracted instead of added), salts [M-OTs]+ (cation minus H), azides [M-N2+H]+ (N2 lost)
  and dehydrated ions [M-H2O]+ (diols seen as having fewer H).
- `extract_names`: the calculated m/z may be that of the 37Cl or 81Br isotopologue (CCl3, Br2
  compounds); such formulas were rejected as "mass does not match".
- `extract_names`: a neutral formula written with an ion type ("calcd for C16H12F5NO3S [M+H]+
  394.0531") is recognised by its mass and kept as the molecular formula.
- `extract_names`: the word "calculated mass" is not read as a formula ("mass") — the formula after
  "calcd for" must start with a capital letter.
- `extract_names`: "Trial 1:", "STEP 2:", "Entry 3", "Table 1:" etc. are not compound labels (HPLC
  traces "Racemic: Trial 1: Trial 2:" of the previous compound gave the label "1" to the next one).
- `extract_names`: labels of intermediates "1s-a", "7-b" are read; a range "(4a-h)", "(21a-b)" is not
  a label. When an entry has several labels and the procedure "affords 1s-b as ...", that label is
  the described compound.
- `extract_names`: a compound characterised only by a reference ("Characterization data matches
  literature precedent.") ends its entry; its label is no longer given to the next description
  (only if a label follows).
- `extract_names`: names no longer start with "main text) ", "[2]) " (unbalanced bracket) or with the
  end of a 13C assignment ("Methoxy carbon Tert-butyl ...").
- Regression on the 201 SI of the Organic Letters sample (for information): same 8,609
  descriptions; 125 files changed; formulas: 111 gained (neutral formula with ion type), 6 gained
  (81Br isotopologue), 88 changed (all checked by hand — ion types above; the new formulas are right),
  5 removed (Boc-type fragment ions); labels: 195 changed — of those among the 982 reference
  descriptions, 19 now right, 0 now wrong (7 wrong before and after, now empty). Full chain with a
  local OPSIN (same names table for both versions): item 1 "inconsistent" 512 -> 492 (26 false findings
  removed, new ones are mostly real, e.g. reported 7 H for 12), "no structure" 745 -> 696. Note: the
  reference labels of the 982 were used here to check label changes.
- 6 new tests (39 in total).

Third set of changes (22.10, night): item 4(b), checked partly.

- `check_descriptions` (new module `item4b.py`): item 4(b) - the multiplicity needs no more coupling
  partners than the structure provides - checked as an upper bound, without an assignment. For each
  first-order signal (not m, app, br, J_app) the letters give the number of partners (d 1, t 2, q 3,
  p 4, h (hextet) 5, sept 6); the J values give the bonds over which they can be: J >= 5 Hz - 2-3 bonds
  (4 through an allene), F/P up to 4 bonds; 1 <= J < 5 Hz - also 4 bonds if an unsaturated atom is on
  the path or the middle atom is in a ring (meta, allylic, benzylic, propargylic, W) and 5-bond
  homoallylic/homopropargylic or planar zigzag paths, F/P up to 6 bonds; J < 1 Hz - up to 5 bonds.
  Geminal partners only in CH2; N-H and O-H count; the reading of the letter order that needs fewest
  partners is taken. Candidate protons by shift (aromatic, vinyl, NH/OH, N-CH-O type sp3 C-H below
  7 ppm; aromatic from 5.5 ppm); a 3H/9H (6H/18H) d, t or dd in the aliphatic region is a set of
  equivalent CH3 (or CH2) groups. If no candidate has enough partners: "candidate (check)". Not checked:
  mixtures/rotamers, molecules with D, B, metals or NH4+-type N.
- New columns "item 4(b)" and "findings 4(b)"; "candidate (check)" is a "to check by hand" item in the
  conclusion; the conclusion text "items 2, 4(b) and 7 are not checked" is now "items 2 and 7 are not
  checked; 4(b) only as an upper bound". Excel formulas and Python give the same conclusion (172 rows
  recalculated in LibreOffice).
- Measured on the 982 reference descriptions with the reference structures (information, not a test
  set: the rules were tuned on them): 38 descriptions flagged, all real inconsistencies on inspection
  (19 recorded under 4(b) in the reference, 19 under other items, e.g. "t, J = 24.1 Hz"); 19 of the 48
  item-4(b) findings of the reference found; the rest need an assignment ("t" for an N-CH with one
  neighbour, "dd" for a benzylic CH2). On the 201 SI with structures from names: 224 descriptions
  flagged (some with a structure that is not the described compound).
- 3 new tests (42 in total).

Fourth change (23.10, night), from the SI ja6c10875 (development set):

- `check_descriptions`: a coupling constant above 25 Hz in a molecule without F, P or another
  spin-active heteronucleus (B, Si, Se, Sn, Pt, Rh, ...) - neither in the structure nor in the HRMS
  formula - is an item-3 inconsistency: "larger than any H-H coupling, and the structure has no F or P:
  impossible for this compound" (e.g. "3.82 (d, J = 1160.5 Hz, 3H)" for an OMe). Before, it was taken
  as a coupling to an absent 19F/31P ("partner unverifiable"). The formula guard keeps a wrong structure
  from a name (e.g. "indole" for a CH2F compound, J = 46.7 Hz) from giving a false finding.
- The finding text for a large J with F/P present but no 19F/31P description no longer prints a
  Python dictionary ("{'F': 'absent', ...}"); it reads "the partner must be 19F or 31P, whose
  descriptions do not show it (19F: absent, 31P: absent)".
- Regression on the 201 SI (structures from names): 38 descriptions get the new item-3 finding;
  the examples checked by hand are real (J = 25.1-1160.5 Hz with no F/P in structure and formula).
- 1 new test (43 in total). Review to Word: such signals are highlighted red.

## 2026-10-18b — version 1.1: code cleanup, results unchanged

Code reorganised after a review of the code by a software developer. **The behaviour is unchanged:**
on all 201 SI files of the Organic Letters sample every output table of version 1.1 is identical to
that of the frozen version 2026-10-18 (cell by cell: values and formulas, formats, colours, drop-down
lists; and the printed output). The results of the paper were obtained with the frozen version.

- The long comment at the start of each script moved to its README; each script starts with a short
  description and the command to run it.
- All regular expressions and numerical limits are named constants at the top of their module, each
  with a comment saying what it captures or means (e.g. `PAGE_HEADER_ZONE = 0.08`,
  `PAGE_NUMBER_RE`, `DNU_J_INCONSISTENT = 6`); long expressions are written in commented parts.
- `extract_names` is split into `extract_names.py`, `name_patterns.py`, `compound_names.py`,
  `hrms_formula.py`; `check_descriptions` into `check_descriptions.py`, `description_parser.py`,
  `text_checks.py`, `structure_checks.py`, `verdicts.py`, `excel_output.py`. Long functions are split
  into smaller ones. `count_1H_descriptions.py` stays one self-contained file (it can be pasted into a
  single Colab cell); `names_to_smiles.py` stays one file.
- Unused imports (`subprocess` in four scripts, `glob` in run_all, `sys` in rename_SI) and dead code
  (an unused pattern in extract_names, an unreachable branch and an unused variable in
  check_descriptions) removed.
- The start comment of extract_names said that it sets the flag CITATION; it sets only KNOWN? and
  REPEAT (CITATION is set by count_1H_descriptions). The comment is gone; the READMEs were correct.
- Found during the check, not changed (left for version 2, because it changes behaviour): on one SI
  (ol6c01204) count_1H_descriptions and check_descriptions with PDF input stop with an Excel error,
  because a control character from the PDF text reaches a cell; extract_names removes such characters.

SHA-256 of version 1.1:
```
256d5840a22c05d91e9ff85271be0abd7e34cbd2a1328d004c10bb89cb9e765f  run_all.py
5be0049894f5ac8893ab5c0308c76f9a88b043b4dd9a9f3886a0b80a2ba840c0  rename_SI/rename_SI.py
953b41edbfbbee6016132a3fbcb272f856c878694595849e4f11c83b7ddd7af8  count_1H_descriptions/count_1H_descriptions.py
6345cb469b964193d5cd51433fcdb8e329c1973c74d1ce86e307c5236d0a1310  extract_names/compound_names.py
561acc436d12a8d98d94d25b499a8f1a63a451b9ad70a271982e42a932666895  extract_names/extract_names.py
1886e63e5d41b025c304a1a368b6cbb0bac4e0295d50f28d99e05727d5261c6a  extract_names/hrms_formula.py
564fa837446e37b04096a8bd8c5dd6b5f02bb09151fc7c99d178d70524435893  extract_names/name_patterns.py
588a817f3b1aca6fda56df1169f33512bd1affefef60fac604c02a1ab552de29  names_to_smiles/names_to_smiles.py
872f6a7df56636ce3eaf230158d834f09724dd9654c7276e7fd27ee0058ee191  check_descriptions/check_descriptions.py
b506b296e75bfa479b2a48c24802c5c3b40a384001c87dc1423944923c17f90f  check_descriptions/description_parser.py
40bcfed6a8ef6a6e909969bef956c093684a3e9f1124d161e37c4989aa502035  check_descriptions/excel_output.py
e0ea3477b458fb834b30dadbaa8cd292032b4385f91839bbab16ee6e0e8b1a34  check_descriptions/structure_checks.py
a61a8d2256901ad31c331a5a759d6228607b069b9e54485822b5e202062536b0  check_descriptions/text_checks.py
a294e6e35922a6f56dca05a724d1a94b92d74cc69279ea573c6d38b88a28723c  check_descriptions/verdicts.py
```

## 2026-10-18 — version used in the paper (frozen)

### run_all
- On Windows the scripts started by run_all wrote their screen output in the local code page
  (e.g. cp1251) and stopped on compound labels with a prime (3k′); run_all now makes them write
  UTF-8, and the paths in run_log.txt are readable. Found in the 200-SI run (2 of 201 files).
  The measuring scripts and their results are unchanged.
- New test (24 in total). SHA-256 of run_all.py: 834b36df34de8419bcb94962b6dfbab36a60cc4448d5dc846576c80016db13d7.

## 2026-10-17d

### count_1H_descriptions
- Works again when the script is pasted into a Google Colab / Jupyter cell (the command-line
  parser of 2026-10-17c stopped on the notebook's own arguments). Results unchanged.
- SHA-256: 7c41621ee541eeb9e2137267fe6f85f9f8660f0e0814e027c24feed58cbc51f2; the other scripts
  are those of 2026-10-17c.

## 2026-10-17c

SHA-256 of the scripts of this version:
```
7d479b6d73f87e0228ee54f96339e0a02f93bcf41413e65da67428f86e7f2717  extract_names/extract_names.py
a1bde1a39ea614c9b55f05348ce462d4f5a2092bb89257ae2eca7426beecc257  names_to_smiles/names_to_smiles.py
00a39238bb4adb94853349f4fc010f06f131ff0f4bdf29735f8f3fa29e30a39a  check_descriptions/check_descriptions.py
8fd348675dc9d9e1d4106cd51fa374c963839332001208797b096d87418a0ef6  count_1H_descriptions/count_1H_descriptions.py
977067fe9728f297be38b998ff05014e033ce41fd1795501211a706c6dcdaf23  rename_SI/rename_SI.py
b07f820dd1fad137008d32893af3b46868850f63bcb34e35e1803f8793a9525a  run_all.py
```

### count_1H_descriptions (also used by extract_names and check_descriptions)
- Finds 1H descriptions written without δ ("1H NMR (300 MHz, CDCl3): 7.35 (m, 2H) …") and with
  δ typed in the Symbol font (extracted from the PDF as the private-use character U+F064).
  Effect on the 201 Organic Letters SI files: 8418 → 8610 descriptions (+192), none lost; in two
  files a label that had been shifted to the next entry by a missed description is now correct.
- The `file` column contains the file name also on Windows (it contained the full path).
- Labels with a curly apostrophe (5’) are recognised.
- Option `-o` for the name of the output tables.

### All scripts
- Command line with `argparse`; every script prints its options with `--help`. The commands used
  before work unchanged.
- No automatic installation of packages: a missing package stops the script with a message;
  tested versions in `requirements.txt`.

### check_descriptions
- Verdicts unchanged (checked on the 201 SI files).

### New
- `tests/`: 22 automatic tests on invented examples, including a generated demo PDF
  (`python -m pytest tests`, no internet needed).
- `COMMANDS.md`: every command of the chain explained step by step.

## 2026-10-17b

### check_descriptions
- Default output name `checked.xlsx` (was `checked_ru.xlsx` when `-o` was not given).
- The reported proton count is written rounded (42.1, not 42.09999999999999).
- Verdicts unchanged: on the 201 SI files only six proton-count cells changed by rounding.

## 2026-10-17

### extract_names
- A molar mass in brackets after "Calcd for <formula>" (elemental analysis) is no longer taken as
  a compound label. Effect on the 201 SI files: no change; on a test SI of another publisher two
  labels and names are now found.

### check_descriptions
- Compound multiplicities with a long name are read: heptd, septd, pentd, sextt …
  Effect on the 201 SI files: 11 cells changed in two files, all in item 4(a); one verdict changed
  from inconsistent to consistent (a "heptd" with two constants).

### Tried and rejected
- Pairing every coupling constant with its exactly equal partner before the 6(b) check: it removed
  a false pair in one example but also about 30 genuine strong-coupling flags in the Organic
  Letters set (equal constants recur in crowded aromatic and CH2 regions). Pairing constants
  reliably needs signal assignment or a spin-Hamiltonian analysis of the spectrum, which is
  outside the scope of the tool; the check stays conservative.
- Restricting H–F couplings to protons within three bonds of F: no gain without signal
  assignment, and wrong for benzylic 4J(H,F).

### New
- `rename_SI` works for any sample: the list of articles is read from a table in `samples/`
  (CSV or Excel) instead of being written in the code; `samples/OrgLett_2026H1.csv` (.xlsx) for
  the Organic Letters sample. Same output as before on a test set.
- `run_all.py`, `run_all.bat` (double-click on Windows; checks Python, installs the packages on the
  first run, retries the OPSIN step) and `run_all_Colab.ipynb` (Google Colab, no installation):
  the whole chain for every PDF in `data`, results in `results/`.
- README: what the tool is and is not (a first-pass consistency check, not a spectral analysis).

## 2026-10-16

### extract_names
- Finds many more compound names (new label forms, name before or after the label, removal of
  headings and drawing labels). On the 982 surveyed compounds that have a name in the SI: 64% →
  88% found (rules tuned on these compounds). Structures matching the HRMS formula over all
  descriptions: 3363 → 4336.

### names_to_smiles
- A name that OPSIN cannot read is retried without PDF line-break remnants
  (status "OK (name repaired)"). Structures matching the formula: 4336 → 4462.

### check_descriptions
- Item 1 is compared with the HRMS formula when no structure is available.
- Excel output: counts as formulas, drop-down lists of verdicts (a verdict corrected by hand
  updates the summary), conditional colours.
- Value "6(b) only: cannot be determined" (was counted as consistent by mistake).

## 2026-10-15

- First public version: `count_1H_descriptions` (MIT licence).
