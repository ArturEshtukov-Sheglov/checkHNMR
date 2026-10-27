README - rename_SI.py
=====================

Copies the SI files of a study sample into a new folder under the names used in the study tables:
SI001.pdf, SI002.pdf ... (three-digit Order of the article in the sample). The original files are
not changed. Needed only to reproduce the study tables; for checking your own SI files the names
do not matter.

1. The sample table
-------------------
A CSV or Excel (.xlsx, first sheet) file, one row per article (the table of the Organic Letters
sample, first half of 2026, will be published with the paper):

    order,doi,file_key
    1,10.1021/jacs.6c10875,ja6c10875_si_\d{3}

file_key is a regular expression (case-insensitive) that the name of the downloaded SI file of
this article contains. For ACS files such as ja6c10875_si_001.pdf it is ja6c10875_si_\d{3}; for
other publishers write the part of the file name that identifies the article.

2. How to run
-------------
    python rename_SI.py  FOLDER_WITH_SI_FILES  [OUTPUT_FOLDER]  --sample SAMPLE.csv

for example, from the repository folder:

    python rename_SI\rename_SI.py C:\Downloads\SI data --sample SAMPLE_TABLE.csv

Without OUTPUT_FOLDER the files go into FOLDER_WITH_SI_FILES\SI_renamed.

3. Rules
--------
- Several copies of the same file ("Pages from ..." or "... (1).pdf"): the largest copy without the
  prefix is taken; an article with only a "Pages from" copy is marked in the list.
- An article with several SI files (si_001, si_002) gives SI146_1.pdf, SI146_2.pdf.
- Word files (.docx) keep their extension (convert them to PDF before the other scripts).
- A file that matches the keys of several articles is skipped and listed.
- At the end the script lists what was copied and which Orders are missing.

Requirements: Python 3.9 or newer; openpyxl only for an Excel sample table.
