# Running the tools step by step (command line)

This page is for readers who want to repeat every step themselves, e.g. reviewers. The simplest way
to run everything at once is `run_all.bat` (Windows, double-click), `bash run_all.sh` (Linux, macOS) or `python run_all.py`; the
commands below do exactly the same, one script at a time, so that every intermediate table can be
inspected.

Commands are given for **Windows PowerShell**; on macOS and Linux use `/` instead of `\` in paths
and `python3` instead of `python` if needed. All commands are run from the main folder of the
repository (the folder with `README.md`) unless stated otherwise.

## 0. Requirements

- Python 3.10 or newer (tested with Python 3.11).
- Packages (tested versions in `requirements.txt`):
  ```
  python -m pip install -r requirements.txt
  ```
  `pymupdf` reads the PDF text, `openpyxl` writes the Excel tables, `rdkit` reads the structures
  (SMILES) for items 1 and 6(a).
- An internet connection for step 3 (`names_to_smiles` uses the OPSIN web service).
- Typical time: installation 1–3 min; about 1 min per SI file for the whole chain.

Optional, to make sure the code is exactly the version used in the paper: compare the SHA-256
hashes of the scripts with those given in the paper / registration:
```
Get-FileHash extract_names\extract_names.py, names_to_smiles\names_to_smiles.py, check_descriptions\check_descriptions.py -Algorithm SHA256
```
(macOS/Linux: `shasum -a 256 extract_names/extract_names.py ...`)

Optional, automatic tests on small invented examples (a few seconds, no internet):
```
python -m pip install pytest
python -m pytest tests
```
Every script prints its options with `--help`.

## 1. Input files

Put the SI files (PDF) into the folder `data`. Any file names work. Word files (.docx) must
first be saved as PDF.

To reproduce the tables of the Organic Letters survey with the study names (`SI001.pdf` …),
download the SI files of the articles listed in the sample table (column `doi`; the table of the Organic Letters sample (first half of 2026) will be published with the paper) and
copy them into `data` under the study names:
```
python rename_SI\rename_SI.py FOLDER_WITH_DOWNLOADED_SI data --sample SAMPLE_TABLE.csv
```
The original files are not changed; the script lists what was copied and which articles are
missing. Details: `rename_SI\README_rename_SI.txt`.

## 2. Find the 1H NMR descriptions, names and formulas — `extract_names`

For one SI file (here `data\SI001.pdf`); the output folder is created first:
```
New-Item -ItemType Directory -Force results\SI001 | Out-Null
python extract_names\extract_names.py data\SI001.pdf -o results\SI001\compounds_SI001
```
Output: `compounds_SI001.xlsx`, one row per text 1H NMR description: compound label and name,
neutral formula from the HRMS data, the description itself, the 19F/31P descriptions of the same
compound, notes. Check the column `note`. `-o` sets the output file name (`.xlsx` is added).

Optional cross-check of the number of descriptions (the same detection rules, without names):
```
python count_1H_descriptions\count_1H_descriptions.py data\SI001.pdf
```
It prints a summary and writes `1H_descriptions.xlsx` and `1H_descriptions.csv` into the current folder (another name: `-o NAME`).

## 3. Structures from the names — `names_to_smiles`

```
python names_to_smiles\names_to_smiles.py results\SI001\compounds_SI001.xlsx -o results\SI001\smiles_SI001
```
Output: `smiles_SI001.xlsx` = the same table plus `smiles`, `formula_rdkit` and `opsin_status`.
Each name is converted by OPSIN and the structure is compared with the HRMS formula. Rows that
are not `OK` have no structure; a SMILES can be typed into the column `smiles` by hand before
step 4 (it is kept). If the OPSIN web service does not answer, run the command again.

## 4. Check the descriptions — `check_descriptions`

```
python check_descriptions\check_descriptions.py results\SI001\smiles_SI001.xlsx -o results\SI001\checked_SI001
```
Output: `checked_SI001.xlsx` with two sheets:
- `checked` — one row per description: verdict per checklist item (1, 3, 4(a), 6(a), 6(b)),
  findings with the numbers behind each verdict, the reported and structural proton counts;
- `summary` — counts per item (Excel formulas over the sheet `checked`, so a verdict corrected by
  hand updates the summary).

What each item means and how the verdicts are reached: `check_descriptions\README_check_descriptions.txt`.
Every finding is a pointer to check, not a verdict on the structure.

## 5. All files at once

The same three steps for every PDF in `data` (one line, so that it is not broken when pasted):
```
Get-ChildItem data\*.pdf | ForEach-Object { $n = $_.BaseName; New-Item -ItemType Directory -Force "results\$n" | Out-Null; Write-Host "=== $n ==="; python extract_names\extract_names.py $_.FullName -o "results\$n\compounds_$n"; if (Test-Path "results\$n\compounds_$n.xlsx") { python names_to_smiles\names_to_smiles.py "results\$n\compounds_$n.xlsx" -o "results\$n\smiles_$n" }; if (Test-Path "results\$n\smiles_$n.xlsx") { python check_descriptions\check_descriptions.py "results\$n\smiles_$n.xlsx" -o "results\$n\checked_$n" } }
```
macOS/Linux (bash):
```
for f in data/*.pdf; do n=$(basename "$f" .pdf); mkdir -p "results/$n"; echo "=== $n ==="; python3 extract_names/extract_names.py "$f" -o "results/$n/compounds_$n" && python3 names_to_smiles/names_to_smiles.py "results/$n/compounds_$n.xlsx" -o "results/$n/smiles_$n" && python3 check_descriptions/check_descriptions.py "results/$n/smiles_$n.xlsx" -o "results/$n/checked_$n"; done
```
This gives the same tables as `python run_all.py` (which in addition skips files already done,
retries the OPSIN step and writes `results\run_summary.csv` and `results\run_log.txt`).

## 6. What to compare

The tables of the paper were made with these commands on the SI files listed in
the sample table of the survey (published with the paper). The study data released with the paper contain, for every selected
description, the description text, the structure used, the verdicts of the tool and of the
human assessment; they can be compared row by row with `checked_SI###.xlsx`. Structures from the
OPSIN web service can differ slightly if the service is updated; the study data give the SMILES
that were used.
