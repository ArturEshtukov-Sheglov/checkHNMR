README - names_to_smiles.py
===========================

checkHNMR, local version V2.1.3-beta (see VERSION and CHANGELOG.md in the main folder for the
changes since version 1.1, which this description was first written for)

Author: Artur V. Eshtukov-Shcheglov
The code was written with the assistance of Claude Opus 5.5 (Anthropic) and was
reviewed and tested by the author.


1. Purpose
----------
The script converts compound names into structures. It reads a table of
compounds (id, name and, optionally, the expected molecular formula), sends
each name to the free OPSIN web service of the European Bioinformatics
Institute (https://www.ebi.ac.uk/opsin/) and writes the structure it returns
as a SMILES string.

If RDKit is installed, the script also computes the molecular formula of each
structure and compares it with the expected formula (for example, the neutral
formula behind the HRMS ion reported in the SI). Formulas are compared by the
number of atoms of each element, so the order of elements does not matter.

If OPSIN cannot read a name, the script tries it once more with remnants of
line breaks in the PDF text removed:
    "...-3-(2-methoxyphenyl) propanoate"  ->  "...-3-(2-methoxyphenyl)propanoate"
    "2,2-difluoro- 4-methoxybutanamide"   ->  "2,2-difluoro-4-methoxybutanamide"
    "cyclooc-ta[1,2,3-cd]indole"          ->  "cycloocta[1,2,3-cd]indole"
    "bis (phenylsulfonyl)"                ->  "bis(phenylsulfonyl)"
(hyphens after tert, sec, iso, cis, trans, di, bis ... are kept). Such rows
are marked "OK (name repaired)"; the name column is not changed. On the
names of all 8417 descriptions of the survey (200 SI) this gave 126 more
structures whose formula agrees with the HRMS.

The input table can be made with extract_names.py (column names match).


2. IMPORTANT - the result must be checked by hand
--------------------------------------------------
OPSIN reads systematic (IUPAC-type) names only. Trivial names, abbreviations
that OPSIN does not know, typos and some stereodescriptors fail or may be
misread.

    FAILED            no structure; draw it by hand (e.g. in ChemDraw)
    FORMULA MISMATCH  the structure does not have the expected formula;
                      check the name and the structure

A matching formula does not prove that the structure is right (isomers have
the same formula); it only catches gross errors.

Test (names taken by extract_names.py from the SI of two articles):
    article 1, ordinary organic compounds (27 descriptions): 24 names were
        converted, and all 24 structures had the expected formula; the
        3 failures were text that extract_names.py had taken by mistake
        (section headings instead of names);
    article 2, carboranes (26 descriptions): no name was converted; OPSIN
        does not read the names of boron clusters (closo-, nido-,
        dicarbadodecaborane); one compound had no name in the SI.


3. Requirements
---------------
Python 3.9 or newer and an internet connection (OPSIN is a web service).
Packages:
    openpyxl  (reads and writes Excel tables)
    rdkit     (formula check; optional - without it formulas are not checked)
Install them once:  python -m pip install -r requirements.txt  (from the main
folder)  or  python -m pip install openpyxl rdkit


4. Input table
--------------
Excel (.xlsx) or CSV (comma, semicolon or tab), first row = column names:
    id        any identifier, e.g. ol6c00150_3da
    name      compound name exactly as given in the SI
    formula   optional; expected neutral formula, e.g. C12H5ClF3NO
Other columns are ignored. In an .xlsx file the first (active) sheet is read.


5. How to run
-------------
Windows (terminal in Visual Studio, VS Code or PowerShell)
   1. Put names_to_smiles.py and the table in one folder.
   2. In the terminal, go to that folder:
          cd "C:\path\to\the\folder"
   3. Run:
          python names_to_smiles.py compounds.xlsx
      To give the result table another name, add -o and the name:
          python names_to_smiles.py compounds_213.xlsx -o smiles_213.xlsx

The script waits 0.5 s between requests so as not to overload the free
service; 100 names take at least one minute.


6. Output
---------
On screen: a line per compound with its status, and at the end the number of
names converted without problems.

names_to_smiles_result.xlsx (or the name given after -o) in the folder where
the script was run:
    all columns of the input table (e.g. id, name, formula, description,
    hetero from extract_names.py), followed by
    smiles               structure returned by OPSIN ("" = not converted)
    formula_rdkit        formula of that structure
    opsin_status         OK / OK (name repaired) / GIVEN / FAILED: <reason> /
                         ...; FORMULA MISMATCH

A SMILES already written in a "smiles" column of the input table (e.g. a
structure drawn by hand where OPSIN failed) is kept, marked GIVEN, and only
checked against the formula. The result table is the input of
check_descriptions.py.

A table with the same name is overwritten every time the script is run; use
-o to keep the results of several runs.


7. Troubleshooting
------------------
"FAILED: no connection"
    No internet connection, or the OPSIN service is not reachable from your
    network. Try again later or from another network.

"Close names_to_smiles_result.xlsx in Excel and run again."
    The result table is open in Excel. Close it, or give another name with -o.

"RDKit not installed - formulas will not be checked"
    Install it (pip install rdkit) if the formula check is needed.


8. Limitations
--------------
- Only names are converted; structures given only in schemes are not read.
- OPSIN may return a structure for a misspelled or ambiguous name that is
  not the intended compound; the formula check catches only some of these.
- Charged species, salts and metal complexes may give formulas that differ
  from the expected neutral formula.
