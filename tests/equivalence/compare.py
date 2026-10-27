"""Compare the outputs of two versions made by run_tools.py.
usage: python compare.py BASE_DIR NEW_DIR
For .xlsx: every cell (value or formula, number format, font, fill, alignment, border), row heights,
column widths, freeze panes, auto filter, conditional formatting and data validation.
For .csv and .txt (printed output): byte-identical."""
import os, sys, openpyxl

A, B = sys.argv[1:3]


def sheet_sig(ws):
    cells = []
    for row in ws.iter_rows():
        for c in row:
            f = c.font
            cells.append((c.coordinate, c.value, c.number_format, f.name, f.size, f.bold, f.italic,
                          f.color.rgb if f.color is not None else None,
                          c.fill.fill_type, c.fill.start_color.rgb if c.fill.start_color is not None else None,
                          c.alignment.wrap_text, c.alignment.vertical, c.alignment.horizontal,
                          c.border.top.style, c.border.left.style))
    rows = {k: v.height for k, v in ws.row_dimensions.items() if v.height is not None}
    cols = {k: v.width for k, v in ws.column_dimensions.items()}
    cf = []
    for rng in ws.conditional_formatting:
        for r in rng.rules:
            fill = r.dxf.fill.start_color.rgb if r.dxf is not None and r.dxf.fill is not None else None
            cf.append((str(rng.sqref), r.type, r.operator, tuple(r.formula or ()), r.stopIfTrue, fill))
    dv = [(str(d.sqref), d.type, d.formula1, d.errorStyle, d.error, d.errorTitle, d.allow_blank)
          for d in ws.data_validations.dataValidation]
    return dict(cells=cells, rows=rows, cols=cols, cf=cf, dv=dv, freeze=ws.freeze_panes,
                filt=ws.auto_filter.ref, title=ws.title)


def xlsx_sig(p):
    wb = openpyxl.load_workbook(p)
    return [sheet_sig(ws) for ws in wb.worksheets]


n = {"xlsx": 0, "csv": 0, "txt": 0}
diffs = []
for sub in sorted(os.listdir(A)):
    fa = sorted(os.listdir(os.path.join(A, sub)))
    fb = sorted(os.listdir(os.path.join(B, sub)))
    if fa != fb:
        diffs.append((sub, "file lists differ", set(fa) ^ set(fb)))
    for f in fa:
        pa, pb = os.path.join(A, sub, f), os.path.join(B, sub, f)
        if not os.path.exists(pb):
            continue
        ext = f.rsplit(".", 1)[-1]
        n[ext] = n.get(ext, 0) + 1
        if ext == "xlsx":
            sa, sb = xlsx_sig(pa), xlsx_sig(pb)
            if sa != sb:
                for x, y in zip(sa, sb):
                    for k in x:
                        if x[k] != y[k]:
                            d = [(p, q) for p, q in zip(x[k], y[k]) if p != q][:2] if isinstance(x[k], list) else (x[k], y[k])
                            diffs.append((sub, f, x["title"], k, str(d)[:400]))
        else:
            if open(pa, "rb").read() != open(pb, "rb").read():
                diffs.append((sub, f, "bytes differ"))
print("compared:", n)
print("differences:", len(diffs))
for d in diffs[:30]:
    print(d)
