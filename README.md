# checkHNMR — local version

[![DOI](https://zenodo.org/badge/1436401764.svg)](https://doi.org/10.5281/zenodo.23749627)

Website: **[checkhnmr.org](https://checkhnmr.org)** (the same checks in the browser, up to 20 compounds). Archived code: [doi:10.5281/zenodo.23749627](https://doi.org/10.5281/zenodo.23749627) (all versions).

Version **V2.1.3-beta** (31 October 2026). The same checks as the checkHNMR website, on your own computer:
for more than 20 compounds, for Supporting Information files without SMILES (structures are made from the
compound names), and for data you prefer not to open in a browser.

checkHNMR checks that the numbers in a ¹H NMR description agree with each other and with the structure.
It cannot tell whether they were actually measured: a description can pass every check and still be wrong
or invented. **Only the raw data (FID) can show that. Authors: deposit your FIDs. Journals and reviewers:
ask for them.**

Author: Artur V. Eshtukov-Shcheglov, Independent Researcher, Moscow.
The code was written with the assistance of Claude Opus 5.5 (Anthropic) and was reviewed and tested by the author.
License: MIT (see [LICENSE](LICENSE)).

## Installation and first run

**New to Python? Follow the step-by-step guide: [INSTALL.md](INSTALL.md).** In short:

1. Install Python 3.10 or newer (Windows: tick "Add python.exe to PATH" in the installer).
2. Download this repository (green **Code** button → **Download ZIP**) and unpack it.
3. Put the PDF files to be checked into the folder `data`.
4. Double-click `run_all.bat` (Windows) or run `bash run_all.sh` (Linux, macOS). The first time, answer `y`
   when it offers to install the packages it needs.
5. Open the results in the folder `results\<file name>\`.

No installation at all: **[open the notebook in Google Colab](https://colab.research.google.com/github/ArturEshtukov-Sheglov/checkHNMR/blob/main/run_all_Colab.ipynb)** and run its three cells. The files are then processed on Google servers: fine for published SI, not for unpublished data.

## What you get

For every PDF in `data`, the folder `results\<file name>\` contains:

| File | What it is |
|---|---|
| `checked_<file name>.docx` | **The Word report**: one compound per page, with the structure, the description (flagged signals coloured) and the verdict and findings for every checklist item. Start here |
| `checked_<file name>.xlsx` | The same results as a table, with all columns |
| `compounds_<file name>.xlsx`, `smiles_<file name>.xlsx` | Intermediate tables: the descriptions, names, formulas and structures found in the PDF |

and `results\run_summary.csv` (descriptions and structures per file) and `results\run_log.txt` (details of every
step). Files already done are skipped, so an interrupted run can simply be started again; `--redo` recomputes
everything.

Structures are made from the compound names with the OPSIN web service, so the computer must be online. Without
an internet connection the descriptions are checked from the text only (items 3, 4(a), 6(b), and item 1 from
the HRMS formula); start `run_all` again when online and these files are done again with structures.

## What is checked and what is not

The checks follow the checklist in Section 5.1 of the preprint
([doi:10.26434/chemrxiv.15010060/v1](https://doi.org/10.26434/chemrxiv.15010060/v1)); the detailed criteria are
those of the registered protocol, version 1.2 ([doi:10.17605/OSF.IO/EQ9AH](https://doi.org/10.17605/OSF.IO/EQ9AH)).

| Item | Status |
|---|---|
| 1. Signals and proton count | Partly: the number of protons (needs a structure or an HRMS formula); whether every signal has a place needs an assignment |
| 2. Chemical shifts | Not checked |
| 3. Coupling partners | Checked; for H–F and H–P couplings only the presence of the splitting in the ¹⁹F/³¹P description |
| 4. Multiplicity and neighbours | Checked; 4(b) partly (without an assignment: a multiplicity that no proton of the structure can have, and a methyl singlet that only a CH3 next to a C–H could give) |
| 5. Couplings and resolution | Not checked (needs the line width of the spectrum) |
| 6. First-order notation | Checked; 6(a) needs a structure, 6(b) the spectrometer frequency |
| 7. Apparent multiplicity | Not checked (needs an assignment) |

The tools are a first-pass check of a written description, not a spectral analysis: every finding is a pointer
for the chemist to check, and the final decision is made by a person looking at the spectrum. Details:
[check_descriptions/README_check_descriptions.txt](check_descriptions/README_check_descriptions.txt).

## Checking the tools themselves

Double-click `run_tests.bat` (Windows) or run `bash run_tests.sh` / `python run_all.py --selftest`. It runs the
unit tests and four stress tests with synthetic descriptions (a few minutes, no SI files needed) and prints one
table with PASS/FAIL for each check. Stress tests are not accuracy measurements: they show how robustly the tool
reads the forms that occur in the literature, with the correct answer known for every synthetic description.

## Folders

| Folder | What it does |
|---|---|
| [data](data/) | Put the PDF files here (they are not part of the repository) |
| `run_all.py`, `run_all.bat`, `run_all.sh`, `run_all_Colab.ipynb` | Run the whole check on every PDF in `data` |
| `run_tests.bat`, `run_tests.sh` | Check the tools themselves (self-test) |
| [count_1H_descriptions](count_1H_descriptions/) | Finds all text ¹H NMR descriptions in a PDF, with compound labels |
| [extract_names](extract_names/) | For every ¹H description: compound name, neutral formula (from HRMS), the description and the ¹⁹F/³¹P descriptions |
| [names_to_smiles](names_to_smiles/) | Converts compound names into structures (SMILES) with OPSIN and checks them against the formulas |
| [check_descriptions](check_descriptions/) | The checks (items 1, 3, 4, 6) |
| [review_to_word](review_to_word/) | Makes the Word report from the result table; it only reads the table and changes no verdict |
| [rename_SI](rename_SI/) | For reproducing a study: copies downloaded SI files under the names used in the study tables |
| [tests](tests/) | Unit tests and stress tests used by the self-test |
| [docs](docs/) | Running the scripts one at a time ([COMMANDS.md](docs/COMMANDS.md)), the development log ([DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md)) and the lists of articles used as development data ([docs/development_data](docs/development_data/)) |

Every script prints its options with `--help`, e.g. `python check_descriptions/check_descriptions.py --help`.

## Versions

The history of changes is in [CHANGELOG.md](CHANGELOG.md). V2.1.3-beta differs from V2.1-beta in the
launchers (the Word report, V2.1.1-beta), in one reading fix (V2.1.2-beta: the non-first-order notation
nfod/nfot/nfom and sums of constants such as "J_o + J_p" are read as apparent values) and in one new check
(V2.1.3-beta: item 4(b) also finds a methyl singlet that only a CH3 next to a carbon with H could give; the
Excel table and the Word report list items 2, 5 and 7 as not checked). It is a beta until its accuracy has been measured
on test articles that were not used in its development.

The tools were first developed for a survey of ¹H NMR descriptions in Organic Letters (first half of 2026). The
version used in that survey (frozen 17.10.2026, v1.1) and the registration files are in a separate repository,
[nmr-1h-description-tools](https://github.com/ArturEshtukov-Sheglov/nmr-1h-description-tools).

Inspired by checkCIF (IUCr). checkHNMR is not affiliated with or endorsed by the IUCr or the American Chemical Society.
