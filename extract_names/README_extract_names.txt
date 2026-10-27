README - extract_names.py
=========================

checkHNMR, local version V2.1.1-beta (see VERSION and CHANGELOG.md in the main folder for the
changes since version 1.1, which this description was first written for)

Author: Artur V. Eshtukov-Shcheglov
The code was written with the assistance of Claude Opus 5.5 (Anthropic) and was
reviewed and tested by the author.


1. Purpose
----------
The script reads Supporting Information (SI) PDF files and, for every text
1H NMR description, takes

    - the compound label (e.g. 3a, S1b, (Rs,2R)-3l);
    - the compound name, in any of the usual forms
          2-Chloro-3-phenylcyclobut-2-en-1-one (3a) Following GP1, ...
          2-Chloro-3-phenylcyclobut-2-en-1-one 3a: white solid, ...
          3a. 2-Chloro-3-phenylcyclobut-2-en-1-one. White solid, ...
          Product 3a: 2-Chloro-3-phenylcyclobut-2-en-1-one Prepared ...
          2-Chloro-3-phenylcyclobut-2-en-1-one 3a The compound was ...
          2-Chloro-3-phenylcyclobut-2-en-1-one According to GP1 ...
              afforded 3a as ...
      Text that the PDF puts before the name is removed: section headings
      ("Study on byproducts", "3.8.5 ..."), atom labels of a structure
      drawing ("N H O Ph"), HPLC tables, page headers. A second description
      of the same label (another solvent, rotamers) gets the name of the
      first;
    - the HRMS formula ("calcd for C12H6ClF3NO [M+H]+") converted to the
      neutral formula of the compound.

The result, compounds.xlsx, can be given directly to names_to_smiles.py, which
converts the names into structures (SMILES) with OPSIN and checks them against
the formulas.

How the formula is obtained:
    - the adduct is removed: [M+H]+, [M+Na]+, [M+K]+, [M+NH4]+, [M+Li]+,
      [M+Ag]+; for [M-H]- one H is added; [M]+ is taken as it is;
    - forms such as "[C23H29OP+Na]+" (neutral formula plus adduct) are
      recognised;
    - the formula is accepted only if its monoisotopic mass agrees with the
      calculated m/z given in the SI (within 0.02). This check also resolves
      isotope labels that lost their superscript in the PDF text
      (e.g. "C15H2210B11B8FP" = C15H22 10B 11B8 F P);
    - if the ion type is not written, it is inferred from the parity of the
      double-bond equivalent, and the row is marked in the "note" column.


2. IMPORTANT - the result must be checked by hand
--------------------------------------------------
Names are cut from PDF text by simple rules. A name may be incomplete, may
start with a section heading, or may be missing.

Test on the 982 compounds selected in the survey (200 SI), whose names
were copied from the SI by hand:
    799 of them have a name in the SI text; the script found it exactly for
        663 and with small differences (spaces, hyphens) for 38 - 701 of 799
        (88 %; version of 15 October: 509, 64 %);
    a wrong name (usually of a neighbouring compound) was given for 26;
    no name for 72.
These compounds were also used to develop the rules, so for other SIs the
share may be lower.
On all 8417 1H descriptions of the 200 SI, OPSIN (names_to_smiles.py)
turned the names into structures whose formula agrees with the HRMS for
4336 descriptions (version of 15 October: 3363).
Most missing names are not errors of the script: many SIs give no compound
name at all, only the label (e.g. "2e, white solid, ..."). For such compounds
the structure must be taken from the schemes in the SI.

Rows with a text in the "note" column must be checked in the PDF.


3. Requirements
---------------
Python 3.9 or newer.
The modules name_patterns.py, compound_names.py and hrms_formula.py must be in
the folder of extract_names.py.
count_1H_descriptions.py must be in the same folder or, as in the GitHub
repository, in the neighbouring folder count_1H_descriptions/ (the script
uses its functions to find the 1H descriptions).
Packages:
    pymupdf   (reads the PDF files)
    openpyxl  (writes the Excel table)
Install them once:  python -m pip install -r requirements.txt  (from the main
folder)  or  python -m pip install pymupdf openpyxl
If a package is missing, the script stops and says which one.


4. How to run
-------------
Windows (terminal in Visual Studio, VS Code or PowerShell)
   1. Put extract_names.py, its modules name_patterns.py, compound_names.py and
      hrms_formula.py, and count_1H_descriptions.py in one folder (or keep the
      folder layout of the GitHub repository).
   2. In the terminal, go to that folder:
          cd "C:\path\to\the\folder"
   3. Run the script with one or several SI files:
          python extract_names.py "C:\path\to\SI_1.pdf" "C:\path\to\SI_2.pdf"
      (If the PDF is in the same folder, the file name alone is enough.)
      To give the result table another name, add -o and the name:
          python extract_names.py SI_213.pdf -o compounds_213.xlsx
   4. Optionally, convert the names into structures:
          python names_to_smiles.py compounds.xlsx


5. Output
---------
On screen, for each SI file: the number of 1H descriptions, of names found
and of formulas found.

compounds.xlsx (or the name given after -o) in the folder where the script
was run (one row per 1H description):
    id            SI file name + label, e.g. ol6c00150_3da
    name          compound name as written in the SI ("" = not found)
    formula       neutral molecular formula in Hill order
    description   text of the 1H description
    hetero        19F / 31P descriptions of the same compound (for
                  heteronuclear couplings)
    file          SI file name
    index         number of the description in SI order
    label         compound label ("" = not found)
    ion_formula   formula as written in the SI after "calcd for"
    ion           ion type, e.g. [M+H]+ ("?" = not written in the SI)
    flags         KNOWN? (text near the description says the compound is
                  known) / REPEAT (the same label already has a description)
    note          what must be checked by hand

A table with the same name is overwritten every time the script is run; use
-o to keep the results of several runs. Descriptions flagged
KNOWN? or REPEAT are listed too; delete them if they are not needed.


6. Troubleshooting
------------------
"Permission denied: compounds.xlsx"
    The table is open in Excel. Close it and run the script again.

"count_1H_descriptions.py not found"
    Put count_1H_descriptions.py in the same folder as extract_names.py, or
    keep the folder layout of the GitHub repository.

note "no compound name in the SI text (label only?)"
    The SI gives only the label. Take the structure from the scheme.

note "name taken from the first description of this label"
    The description has no heading of its own (e.g. a second solvent); the
    name of the first description with the same label is used.

note "name may start with a section heading - check"
    The name begins with text such as "1.2.10 Synthesis of ...". Delete the
    heading by hand.

note "formula not parsed or mass does not match"
    The HRMS formula is written in an unusual form, or the calculated m/z in
    the SI does not agree with the formula. Check in the PDF.


7. Limitations
--------------
- Names that are split by a line break with a hyphen are joined with the
  hyphen ("dipropyl- sulfamoyl" -> "dipropyl-sulfamoyl"); a real hyphen and
  a line-break hyphen cannot be told apart.
- A name given only in a scheme or in a table is not found.
- When one heading names two compounds ("Name A (21) and Name B (22)"), or
  a compound is only mentioned in a table of contents, the name may be
  missed or taken from a neighbouring compound. Always compare the name
  with the label.
- Only HRMS written as "calcd (for) <formula>" is read; elemental analysis
  and low-resolution MS are not used.
- Metal complexes: if the ion type is not written, no formula is given.
