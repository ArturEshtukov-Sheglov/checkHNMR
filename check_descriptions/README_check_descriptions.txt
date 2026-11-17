README - check_descriptions.py
==============================

checkHNMR, local version V2.1.5-beta (see VERSION and CHANGELOG.md in the main folder for the
changes since version 1.1, which this description was first written for)

Author: Artur V. Eshtukov-Shcheglov
The code was written with the assistance of Claude Opus 5.5 (Anthropic) and was
reviewed and tested by the author.


1. Purpose
----------
The script checks 1H NMR descriptions against the pass-3 assessment protocol
(v1.2). It reads the table made by extract_names.py and names_to_smiles.py
(one row per description: id, description, hetero, smiles ...).

From the structure (rows with a SMILES; RDKit needed):

    1     the number of reported protons (sum of the integrals) is compared
          with the structure. Equal to all protons: consistent. Equal to the
          non-exchangeable protons only: subcategory "exchangeable proton not
          reported", unless the solvent is protic (CD3OD, D2O ...) or the
          description says the signal was not observed. Integrals equal to
          1/2 (1/3 ...) of the structure are marked (symmetric molecule?).
          Rows WITHOUT a SMILES but with a molecular formula (column
          "formula", e.g. the neutral formula from the HRMS given by
          extract_names.py) are checked against the H of the formula:
          equal - consistent; more protons reported - "inconsistent
          (check)"; fewer - "inconsistent? (check)", because the formula
          does not tell which protons are exchangeable (an NH or OH may
          simply not be reported). "findings 1" then says "compared with
          the formula".
    6(a)  aromatic rings with magnetically non-equivalent protons are found
          from the structure: chemically equivalent ring protons A and A'
          whose distances to another ring proton X differ (J_AX != J_AX'),
          e.g. para-disubstituted benzenes, phenyl groups, 4-pyridyl and
          symmetric ortho-disubstituted rings; 3,5-disubstituted rings (A2X)
          are not included. If such a ring is present, aromatic signals
          (6-9.6 ppm) reported with first-order notation and J are found.
          If all protons that can appear there belong to such rings (no other
          aromatic C-H, no vinyl or aldehyde C-H, no NH or OH), the item is
          inconsistent; otherwise the signals are listed as candidates and
          assigned by hand. Saturated
          ring CH2-CH2 fragments are reported in the same way.

From the text of the description alone:

    4(a)  the number of reported coupling constants matches the multiplicity
          (one J for d, t, q, p, sext, sept; two for dd, dt, td; three for
          ddd, and so on). A multiplicity without J (e.g. "d, 1H") and a J
          without multiplicity are mismatches. Signals reported as m are not
          checked.
    6(b)  two signals that share a coupling constant are treated as coupling
          partners; their separation in Hz (dnu) is computed from the shifts
          (midpoint for a range) and the spectrometer frequency:
              dnu/J < 6      inconsistent
              6 <= dnu/J < 8 borderline (separate subcategory)
              dnu/J >= 8     first-order notation accepted
          Isolated two-spin (AB) pairs - two doublets that report no other
          coupling - and splittings reported as apparent (J_app, N) are
          exempt.
          Heteronuclear case: if two signals of the 19F description share a
          constant above 100 Hz (F-F, e.g. the diastereotopic F of a CHF2
          group), dnu/J_FF is computed from the 19F shifts and frequency. If
          it is below 6 (6-8: borderline), 1H signals coupled to these F are
          X parts of an ABX-type system, and first-order notation with J for
          them is inconsistent.
    3     every coupling constant is looked for in the other signals of the
          description, within the tolerance of the protocol (the larger of
          0.3 Hz and the reporting step of the two values).

Coupling constants above 25 Hz are taken as couplings to a heteronucleus (no
H-H coupling is that large). A constant without a 1H partner that equals a
constant of the proton-coupled 19F or 31P description is also taken as a
coupling to the heteronucleus; such cases are listed in the "info" column.
With a structure, aromatic constants are not taken as H-F/H-P if no aromatic
proton is within four bonds of F or P (e.g. a remote CF3 group).
Reverse check: a geminal H-C-F constant (40-100 Hz) or a one-bond P-H
constant (> 150 Hz) in a proton-coupled 19F/31P description must appear as a
splitting in a 1H signal; if it does not, item 3 is inconsistent, unless an
m/br signal lies where such a proton resonates (then partner unverifiable).
19F constants above 100 Hz are F-F couplings and are not used.


2. IMPORTANT - the result must be checked by hand
--------------------------------------------------
What the script is and what it is not. It is a first-pass consistency check
of a written description, not a spectral analysis. Its job is to show where a
description disagrees with itself or with the structure (proton count, number
of constants for the multiplicity, a constant without a partner, a
non-first-order system written as first-order), so that the chemist knows where
to look. It does not try to assign every coupling constant to its partner: from
the text alone the partner is often ambiguous (assignments are rarely given and
partners may be hidden in multiplets), and in non-first-order systems the line
spacings are not the true coupling constants. Extracting them would require
fitting the spectrum with the spin Hamiltonian (total line-shape analysis),
which is outside the scope of this tool. Every flag is a pointer to check, not a
verdict; the final decision is made by a person looking at the spectrum.

The script is a screening aid. Items 2 (chemical shifts) and 7 (accidental
equality of coupling constants) are not checked. Item 6(a) is checked only for
rows with a SMILES, item 1 for rows with a SMILES or a molecular formula
("no structure" otherwise).

Item 3 cannot be decided from the text alone. A constant without a partner is
an inconsistency only if its partner is not reported as a multiplet (m) or a
broad signal (br) and is not a heteronucleus whose coupling cannot be checked.
A heteronucleus is taken as a possible partner only if its description is
absent or proton-decoupled (e.g. 19F{1H}); a proton-coupled 19F/31P description
without this constant shows that the coupling is not to the heteronucleus.
The script therefore gives two levels:
    "inconsistent (check)"           no partner, no m/br signal and no
                                     unverifiable heteronuclear coupling;
    "partner unverifiable? (check)"  no partner, but the partner may be an m or
                                     br signal or a heteronucleus in a
                                     proton-decoupled spectrum.

Item 6(b) follows the protocol rule that two signals sharing a coupling
constant are partners. Two methyl signals (3H, 6H or 9H) are never taken as
partners of each other: their protons are at least four bonds apart, and an
equal constant means a common partner (e.g. the CH of an isopropyl group),
not a mutual coupling. Other signals may also share a constant only through a
common third proton; all pairs must be checked against the structure.

Descriptions of mixtures and rotamers are marked in the "note" column: a
"pair" may then be the same proton in two components.

Test on the SI of one article (27 descriptions, 24 with a SMILES from OPSIN):
    item 1     24 of 24 consistent;
    item 6(a)  all four descriptions marked by hand as inconsistent under
               6(a) (para-disubstituted benzenes) found; also phenoxy and
               phthalimide groups; the m-tolyl compound (aromatic signals
               reported as m) consistent.
Test against 10 descriptions assessed by hand (two articles):
    item 4(a)  10 of 10 in agreement;
    item 6(b)  10 of 10 in agreement;
    item 3     4 of the 5 signals classified by hand as "partner unverifiable"
               were found; the fifth was matched by chance to a signal with a
               constant of the same value.


2a. What the script can and cannot do
-------------------------------------
The script does not assign signals to the protons of the structure. Its
reliability therefore differs between items. Agreement with the assessment of
the 27 descriptions of one SI (first pass by Claude, checked by the author):

    item 1     24 of 24 descriptions with a structure (3 without a SMILES)
    item 4(a)  27 of 27 (the one difference was item 4(b), not checked)
    item 6(a)  24 of 24 descriptions with a structure
    item 6(b)  27 of 27
    item 3     22 of 27

Reliable (close to an assessment by hand): items 1 and 6(a) where a SMILES is
given, 4(a) and 6(b). Item 1 from the formula alone is a weaker check: a
missing NH or OH cannot be told from a missing C-H signal.

Indicative only: item 3. Clear mismatches of coupling constants are found,
but an inconsistency can be MISSED when a constant matches an unrelated
signal by chance, and an inconsistency cannot be CONFIRMED when the partner
may be hidden in a multiplet ("partner unverifiable?").

Version 2: item 4(b) (more partners than the structure provides) is checked
PARTLY, as an upper bound and without an assignment: "candidate (check)" if no
proton of the structure of a kind that fits the shift could have the reported
multiplicity (e.g. "tt" of a benzo-ring proton that has only one meta
neighbour; "dd" for an isopropyl CH3; "d, J = 1.2 Hz" for an OMe). A
multiplicity impossible for its own proton but possible for another proton of
the molecule is NOT found. On the 982 reference descriptions of the Organic
Letters sample (reference structures) it flagged 38 descriptions, all real
inconsistencies (19 recorded under item 4(b) in the reference, 19 under other
items), and found 19 of the 48 item-4(b) findings of the reference; the others
need an assignment. Not part of the frozen version used in the paper.

Version 2.1.3: item 4(b) also has a lower bound for methyl groups. A CH3 next
to a carbon that carries a proton (CH3-CH, CH3-CH2, CH3-CH=) is always split
(3J about 7 Hz). Every singlet below 4.5 ppm must be given by its own groups of
the structure that can be singlets (CH3 on a quaternary or aromatic carbon, on
C=O, O, N, S or Si; isolated CH2, CH and XH; for singlets of 6 H or more also
the CH2 envelope of a chain); if the singlets of 3, 6, 9 ... H cannot all be
explained and the structure has a CH3 that must be split, the verdict is
"candidate (check)" and the finding names the singlet(s) that may be the
wrong one. Diastereotopic CH3 (SiMe2 of TBS, acetonides, C(CH3)2) may give two
singlets; CH3 next to a CH or CH2 bonded to Si (TIPS, TES) is not counted
(deceptively simple). Broad singlets and mixtures are not counted. On 5,120
development descriptions with structures (J. Org. Chem. 2024-2025) it gave 34
findings: real errors of the description (e.g. "4.37 (q, J = 7.1 Hz, 1H) ...
1.44 (s, 3H)" for CH-CH3), structures that do not match the description, and
mixtures not declared; the other items did not change.

Version 2.1.4: two more checks for descriptions with a structure.
Item 4(b): the proton next to a CH3 doublet. A CH3 doublet (3, 6 or 9 H below
4.5 ppm, one J of 5.0-8.5 Hz) shows that its coupling to the CH is resolved, so
the CH must show at least a quartet for that constant. If every signal that
reports the constant (1 H, up to 6.5 ppm; 7.6 ppm if =CH-CH3 is possible) shows
fewer than three partners for it ("d", "dd", "t") and no multiplet without
constants could be the CH, the verdict is "candidate (check)".
Item 6(a): CH2-CH2 of an open chain (X-CH2-CH2-Y and the inner CH2 of alkyl
chains) written with a first-order multiplicity (t, p, sext, td, tt ...) and J
gives the subcategory "flexible chain" (protocol v1.2: formally AA'XX', usually
deceptively simple; not an inconsistency), when the structure has no
saturated-ring CH2-CH2. On 5,120 development descriptions with structures:
3 new item-4(b) findings (all real errors), 260 subcategories, no other change.

Version 2.1.5: item 4(b) checks the multiplicities against the structure, and
item 1 the integrals against its sets of equivalent protons.
Reading of a multiplicity (strict): every letter counts ("dd" is two
couplings, "t" two equal ones), the constants in decreasing order go with the
letters in the written order, and a constant of 6 Hz or more is "large".
Each proton of the structure has k large couplings to protons (pairs of Table 4
of the width note, docs/development/width_criterion; ortho H-F counts, meta H-F
may add one: k or k+1). The signals must be distributed over the protons so
that every proton stands at a shift where it can stand (the shift windows of
the upper bound of item 4(b)), the integrals fill every signal, and every
signal shows the large couplings of its protons:
  - more large couplings than the protons have: not allowed;
  - fewer: allowed only if the signal is wide enough for them (the width test:
    W_s + tau >= L_X, L_X = the sum of the lower bounds of the large couplings
    of X minus the negative small ones, plus ortho/meta H-F; W_s = the sum of
    the reported constants with their letters; tau = half the reporting steps
    + 0.2 Hz), or if a large-coupling partner stands in the same signal;
  - a proton with a partner outside Table 4 within 4 bonds, or on a
    homoallylic or planar zigzag 5-bond path, is not tested for "fewer"; a
    5-bond partner outside Table 4 otherwise subtracts 1 Hz from L_X; NH, OH,
    protons near P or an aliphatic F can stand in any signal.
If no distribution exists, item 4(b) is "inconsistent"; if it exists only when
the width test is lifted for a signal with another signal within 3 x J_max Hz
(strong coupling possible) or without a stated frequency, "candidate (check)".
Range of J: every constant must fit at least one coupling of the protons that
can stand at the shift of its signal (upper bounds of Table 4: ortho 9.0 Hz,
10.0 Hz for N = J_ortho + J_para of a ring that turns about its axis, meta 3,
para 1, cis/trans up to 19, diene 12, HC(=O)-CH= 10, ...; 25 Hz when a partner
is outside Table 4 or the proton is on N, O or S; no bound near F or P).
Above the bound by up to max(0.3 Hz, reporting step): "candidate (check)";
more: "inconsistent". Note: Pretsch gives 6.5-8.5 Hz for ortho; the bound here
is wider because correct descriptions in the development data reach 9.0 Hz
(1H signals) and 10.0 Hz (2H doublets of para rings, N = J_ortho + J_para).
Item 1: if the integrals cannot be divided among the groups that must stand
whole in one signal (a CH3; the two ortho or the two meta protons of a ring
that turns about its axis), even with multiplicities and shifts ignored, item 1
is "inconsistent (check)" (e.g. a para-disubstituted ring as four 1H signals:
another compound, or slow rotation of the ring).
19F/31P: a description that gives only shifts ("19F NMR d -110.2") no longer
counts as "all singlets"; an H-X partner is then unverifiable (item 3
"partner unverifiable? (check)"), unless the compound has no F/P.
No coupling constants: when a description reports no coupling constant at
all and at least one "m", items 3, 4(a) and 6 are "not applicable: no coupling
constants are reported" and the conclusion is "NOT CHECKED by items 3, 4(a)
and 6 ..." instead of "NO INCONSISTENCY FOUND". On the development data
(8,540 rows, 300 J. Org. Chem. 2024-2025 articles; 5,136 with a SMILES):
item 4(b) becomes inconsistent in 75 descriptions (31 of them were candidate
before) and candidate in 20; item 1 inconsistent in 7; 629 descriptions are
"not checked"; 35 item-3 verdicts go from inconsistent to partner
unverifiable (details in CHANGELOG.md).

Not checked: items 2 (chemical shifts), 5 (couplings and resolution) and 7 (apparent multiplicity).
The subcategory "flexible chain" under 6(a) is found only when the structure has
no saturated-ring CH2-CH2 (otherwise the ring check lists the CH2 signals for a
person to assign) (see Limitations).

In short: a red verdict is almost always a real finding that needs only to be
confirmed; a green verdict under item 3 is not a guarantee; items 2, 5 and 7
(and 4(b) beyond what it checks) are always assessed by a person.


3. Requirements
---------------
Python 3.9 or newer; the packages openpyxl and, for items 1 and 6(a), RDKit:
python -m pip install -r requirements.txt (from the main folder; tested
versions) or python -m pip install openpyxl rdkit. If openpyxl is missing, the
script stops and says so.
The modules description_parser.py, text_checks.py, structure_checks.py,
verdicts.py and excel_output.py must be in the folder of check_descriptions.py.
For PDF input, count_1H_descriptions.py must be in the same folder or, as in
the GitHub repository, in the neighbouring folder count_1H_descriptions/.


4. How to run
-------------
Windows (terminal in Visual Studio, VS Code or PowerShell), in the folder of
the script:

   From SI PDF files directly (text-only checks; items 1 and 6(a) are not
   checked because there is no structure):
          python check_descriptions.py "C:\path\to\SI_1.pdf" "C:\path\to\SI_2.pdf"

   The usual chain (one table passes through all three scripts):
          python ..\extract_names\extract_names.py SI_213.pdf -o compounds_213
          python ..\names_to_smiles\names_to_smiles.py compounds_213.xlsx -o smiles_213
          python check_descriptions.py smiles_213.xlsx -o checked_213
      Any table works if it has a column whose header contains "description";
      optional columns: "id", "smiles", "formula" (molecular formula, used
      for item 1 where there is no SMILES), and one whose header contains
      "hetero" or "19F" (the 19F/31P descriptions).

   To give the result table another name, add -o and the name:
          python check_descriptions.py SI_213.pdf -o checked_213.xlsx


5. Output
---------
On screen: the number of descriptions and of findings per item.

checked.xlsx (or the name given after -o) has two sheets.

Sheet "checked", one row per description (the header row is frozen and has
filters; verdicts are coloured: green = consistent, yellow = to check by hand
or separate subcategory, red = inconsistent, grey = no structure or cannot be
determined):
    id          identifier (SI file + label, or from the input table)
    conclusion  by the rule of section 10 of the protocol, limited to the
                items checked (human verification required):
                INCONSISTENT: items ... - if one of items 1-4 is concerned, a
                  check against the spectrum in the SI or the raw data (FID)
                  is advisable, because the description does not agree with
                  itself or with the structure; if two or more of items 1-4
                  are concerned, a check against the raw data is strongly
                  advised;
                TO CHECK BY HAND: items ... - nothing inconsistent found, but
                  some items could not be decided;
                NO INCONSISTENCY FOUND by the automatic checks - this does not
                  mean that the description is correct: items 2, 5 and 7
                  are not checked, 4(b) only in part, and item 3
                  can be missed.
    item 1      consistent / subcategory: exchangeable proton not reported /
                subcategory: protons on quadrupolar nuclei not reported (B-H, v2.1) /
                inconsistent (check) / inconsistent? (check) / mixture (check) /
                no structure / cannot be determined
    item 3      consistent / partner unverifiable? (check) /
                inconsistent (check)
    item 3 finding only in signals not first-order (6)
                yes / partly / no: whether the item-3 inconsistencies lie only
                in signals already inconsistent under item 6 (constants read
                as line spacings of a non-first-order system). Item 3 stays
                inconsistent; the column allows these cases to be reported
                separately.
    item 4(a)   consistent / inconsistent
    item 6      first-order notation, the verdict of item 6 as a whole:
                inconsistent if 6(a) or 6(b) is inconsistent. The two are
                independent checks of the same item (a para-disubstituted
                benzene is not first-order at any field, whatever dnu/J; strong
                coupling also occurs without magnetic non-equivalence).
                "6(b) only: ..." = no structure, so 6(a) was not checked.
    6(a)        consistent / inconsistent / candidate (check) / no structure
    6(b)        consistent / borderline (subcategory) / inconsistent /
                cannot be determined (no frequency) /
                no pair (nothing to check): no two signals share a J /
                not applicable (6(a)): the only pairs belong to a system that
                is not first-order under 6(a) (e.g. the two doublets of a
                para-disubstituted benzene); dnu/J has no meaning there, and
                such pairs are never counted as consistent under 6(b). Pairs
                of other signals in the same description are still checked.
    findings 1, 3, 4(a), 6(a), 6(b)
                the signals concerned (#number and shift) and the reason; for
                6(b) also when there was nothing to check ("no pair of signals
                with a shared J") or how many pairs passed
    H reported, H structure
                sum of the integrals; number of protons in the structure
                (or in the formula, if there is no structure)
    MHz         spectrometer frequency ("" = not stated)
    signals     number of signals read from the description
    note        e.g. mixture/rotamers, no signals read
    info        constants taken as couplings to 19F/31P
    smiles      structure used (from the input table)
    description the description as read

Sheet "summary": one row per item, one column per kind of verdict (number of
descriptions), and the shares of the conclusions: inconsistent under items
1-4, inconsistent under item 6 only, to check by hand, no inconsistency found.
These shares are screening figures, not the result of an assessment.
A table per SI file follows: number of descriptions, number and share
inconsistent under items 1-4, and descriptions with two or more such items.
SI files with a quarter or more of such descriptions, or with a description
with two or more such items, are marked red (a check of the raw data of the
article is advisable). The threshold of a quarter is a choice of the script,
not part of the assessment protocol.

All numbers on the sheet "summary" are Excel formulas (COUNTIF) over the sheet
"checked"; click a cell to see how it is counted. On the sheet "checked" the
columns "conclusion" and "item 6" are formulas too, and the colours follow the
cell contents. To correct a verdict by hand, choose it from the drop-down list
in the cell (items 1, 3, 4(a), 6(a), 6(b)): item 6, the conclusion, the colours
and the summary change at once. Another value can be typed after a warning;
the column "check: not classified" of the summary shows verdicts that fit none
of the kinds (e.g. a typo) and should be empty. The formulas work in Excel 2010
and later and in LibreOffice.

A table with the same name is overwritten every time the script is run; use
-o to keep the results of several runs.


6. Troubleshooting
------------------
"Permission denied" / "Close ... in Excel"
    The result table is open in Excel. Close it, or give another name with -o.

n_signals is 0 or much smaller than expected
    The description is written in a form the script does not read (e.g.
    signals without parentheses), or the PDF text is broken. Check by hand.

Strange findings in one description
    Text of a scheme or figure may have been mixed into the description in the
    PDF. Compare with the PDF.


7. Limitations
--------------
- Spectra are not used. Without a SMILES only the text checks are made,
  and item 1 is compared with the formula if one is given.
- Item 6(a) lists candidate signals; the script does not assign signals to
  protons of the structure.
- Flexible open-chain fragments (X-CH2-CH2-Y): since version 2.1.4 CH2 signals
  in first-order notation are reported as the subcategory "flexible chain"
  when the structure has an open-chain CH2-CH2 and no saturated-ring CH2-CH2.
  Without an assignment the script cannot tell which CH2 signal belongs to
  the chain, so a CH2 triplet of another fragment may be listed too; the
  subcategory does not change the conclusion. The terminal CH3 of n-pentyl and
  longer chains (perturbed by virtual coupling) is not recognised.
- Item 4(b), proton next to a CH3 doublet (2.1.4): a CH that may hide in a
  multiplet without constants, or a broad or apparent signal, is not checked.
- Item 4(b), counting and width (2.1.5): no assignment is made; a proton that
  can stand in a signal "absorbs" it. Signals written as m, br, app or with a
  J_app, and descriptions with fractional integrals (rotamers, mixtures), are
  not counted. Protons with partners outside Table 4 are not tested for
  "fewer large couplings", and their range bound is 25 Hz; near F or P there
  is no range bound (H-F and H-P constants are not checked by range).
- A constant may be matched by chance to an unrelated signal with the same
  value; such a coupling is then taken as having a partner.
- Coupling constants given only as subscript labels without values
  (e.g. "J2,3 = J3,4") are read only where a value follows.
