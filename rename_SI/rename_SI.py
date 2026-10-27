"""Copy the SI files of a study sample into a new folder under the names used in the study tables:
SI001.pdf, SI002.pdf ... (three-digit Order of the article in the sample). The original files are
not changed. The sample is described by a table (CSV or Excel .xlsx), one row per article:

    order,doi,file_key
    1,10.1021/jacs.6c10875,ja6c10875_si_\\d{3}

file_key is a regular expression (case-insensitive) that the name of the downloaded SI file of this
article contains, e.g. "ja6c10875_si_\\d{3}" for ACS files such as ja6c10875_si_001.pdf. It can be
adapted to any publisher's file names; the table of the Organic Letters sample is published with the paper.

    python rename_SI.py  FOLDER_WITH_SI_FILES  [OUTPUT_FOLDER]  --sample SAMPLE.csv

Several copies of the same file (a prefix such as "Pages from " or " (1)" at the end): the largest
copy without the prefix is taken. An article with several SI files (si_001, si_002) gives
SI146_1.pdf, SI146_2.pdf. Word files (.docx) keep their extension. At the end the script lists what
was copied and which Orders are missing.
"""
import csv
import os
import re
import shutil

EXT = (".pdf", ".docx")
PREFIX = re.compile(r"^pages\s+from\s+", re.I)
COPY_SUFFIX = re.compile(r"\s*\(\d+\)$")

def read_sample(path):
    """Sample table: CSV or Excel (.xlsx, first sheet) with the columns order, doi, file_key."""
    if path.lower().endswith(".xlsx"):
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        head = [str(x).strip().lower() if x is not None else "" for x in next(it)]
        recs = [dict(zip(head, ["" if x is None else str(x) for x in r])) for r in it]
    else:
        with open(path, newline="", encoding="utf-8-sig") as f:
            recs = list(csv.DictReader(f))
    rows = []
    for r in recs:
        if (r.get("order") or "").strip() and (r.get("file_key") or "").strip():
            rows.append((int(float(r["order"])), (r.get("doi") or "").strip(), re.compile(r["file_key"].strip(), re.I)))
    return rows

def core(name):
    """File name without a copy prefix/suffix: used to recognise copies of the same file."""
    stem, ext = os.path.splitext(name)
    return COPY_SUFFIX.sub("", PREFIX.sub("", stem)).lower() + ext.lower()

def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="folder with the downloaded SI files")
    ap.add_argument("dst", nargs="?", help="output folder (default: SRC/SI_renamed)")
    ap.add_argument("--sample", required=True, help="sample table, CSV or Excel (.xlsx)")
    a = ap.parse_args()
    src, sample_path = a.src, a.sample
    dst = a.dst or os.path.join(src, "SI_renamed")
    sample = read_sample(sample_path)
    os.makedirs(dst, exist_ok=True)
    found = {}                                   # order -> core name -> list of (path, name, size)
    for dp, _, fs in os.walk(src):
        if os.path.abspath(dp).startswith(os.path.abspath(dst)):
            continue
        for f in fs:
            if os.path.splitext(f)[1].lower() not in EXT:
                continue
            hits = [o for o, _, key in sample if key.search(f)]
            if len(hits) != 1:
                if len(hits) > 1:
                    print(f"skipped (matches several articles {hits}): {f}")
                continue
            p = os.path.join(dp, f)
            found.setdefault(hits[0], {}).setdefault(core(f), []).append((p, f, os.path.getsize(p)))
    copied = []
    for order, cores in found.items():
        for k, c in enumerate(sorted(cores), 1):
            files = cores[c]
            clean = [x for x in files if not PREFIX.match(x[1])]
            p, f, _ = max(clean or files, key=lambda x: x[2])
            new = f"SI{order:03d}" + (f"_{k}" if len(cores) > 1 else "") + os.path.splitext(f)[1].lower()
            shutil.copy2(p, os.path.join(dst, new))
            note = "" if clean else "  (only a 'Pages from' copy)"
            copied.append((order, f, new, note))
    for order, f, new, note in sorted(copied):
        print(f"{f}  ->  {new}{note}")
    orders = [o for o, _, _ in sample]
    missing = sorted(o for o in orders if o not in found)
    print(f"\nCopied {len(copied)} files for {len(found)} of {len(orders)} articles into {dst}")
    print("Missing Orders:", ", ".join(map(str, missing)) if missing else "none")

if __name__ == "__main__":
    main()
