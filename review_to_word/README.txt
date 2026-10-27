README - export_docx.py (Review to Word)
========================================

Makes a Word report (A4 landscape, one compound per page) from the result table of check_descriptions,
checked_<file name>.xlsx: the structure (drawn with RDKit), the description with the flagged signals coloured,
and for every checklist item the verdict and the findings. run_all calls it for every checked file.

It only reads the table: it runs no check and changes no verdict.

By hand:
    python export_docx.py ..\results\SI_1\checked_SI_1.xlsx -o ..\results\SI_1 --lang en

Options: --help.
