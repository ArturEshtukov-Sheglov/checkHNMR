"""The output table of check_descriptions.py: sheet 'checked' (one row per description) and sheet
'summary'. The conclusion, item 6, the colours and every summary number are Excel formulas, so a
verdict corrected by hand updates them at once."""

import re
import sys

import openpyxl

from verdicts import W, conclusion_text


# ===== Constants =====

COLS = ["id", "conclusion", "item1", "item2", "item3", "item3_in6", "item4a", "item4b", "item5", "item6", "item6a", "item6b",
        "item7",
        "findings1", "findings3", "findings4a", "findings4b", "findings6a", "findings6b",
        "H_reported", "H_structure", "freq", "n_signals", "note", "info", "smiles", "description",
        "reading", "reading_notes"]                  # v2.1: how completely the description was read (at the end)
WIDTH = dict(id=24, conclusion=44, item1=20, item2=12, item5=12, item7=12, item3=20, item3_in6=16, item4a=13, item4b=16, item6=15, item6a=15, item6b=17,
             findings1=30, findings3=48, findings4a=32, findings4b=48, findings6a=48, findings6b=48, H_reported=10,
             H_structure=10, freq=7, n_signals=8, note=26, info=40, smiles=30, description=90,
             reading=9, reading_notes=40)
DEFAULT_WIDTH = 12
HEAD = dict(conclusion="conclusion\n(human verification required)", item1="item 1\nproton count",
            item2="item 2\nshifts", item5="item 5\nresolution", item7="item 7\napparent\nmultiplicity",
            item3="item 3\npartners", item3_in6="item 3 finding\nonly in signals\nnot first-order (6)",
            item4a="item 4(a)\nnumber of J", item4b="item 4(b)\npartners in\nstructure (v2)", item6="item 6\nfirst order\n(a or b)", item6a="6(a)\nmagn. non-equiv.",
            item6b="6(b)\nstrong coupling", findings1="findings 1", findings3="findings 3",
            findings4a="findings 4(a)", findings4b="findings 4(b)", findings6a="findings 6(a)", findings6b="findings 6(b)",
            H_reported="H\nreported", H_structure="H\nstructure", freq="MHz", n_signals="signals",
            reading="read\n(text)", reading_notes="what was not read")
# verdicts as written to the table (a translated version maps them to other words)
SHOW = {}
HEADS = HEAD
# choices offered in the drop-down list of each verdict column (another value can still be typed)
CHOICES = dict(
    item1=["consistent", "inconsistent", "inconsistent (check)", "inconsistent? (check)", "mixture (check)",
           "subcategory: exchangeable proton not reported", "subcategory: protons on quadrupolar nuclei not reported",
           "cannot be determined", "no structure"],
    item3=["consistent", "inconsistent", "inconsistent (check)", "partner unverifiable? (check)"],
    item4a=["consistent", "inconsistent"],
    item4b=["consistent", "candidate (check)", "inconsistent", "no structure"],
    item6a=["consistent", "inconsistent", "candidate (check)", "no structure"],
    item6b=["consistent", "inconsistent", "borderline (subcategory)", "cannot be determined",
            "no pair (nothing to check)", "not applicable (6(a))"])
# v2.1.3: items of the checklist that the script does not check, shown so that the table lists items 1-7
NOT_CHECKED = dict(item2="not checked", item5="not checked", item7="not checked")
VERDICT_COLUMNS = ("item1", "item3", "item3_in6", "item4a", "item4b", "item6", "item6a", "item6b")

# colours
RED, YELLOW, GREEN, GREY = "F8CBAD", "FFE699", "C6E0B4", "E7E6E6"
HEADER_FILL, BORDER_COLOUR, ALERT = "44546A", "BFBFBF", "FF0000"
# row heights
HEADER_HEIGHT = 46               # points, header row of 'checked'
SUMMARY_HEADER_HEIGHT = 34       # points, header row of 'summary'
LINE_HEIGHT = 15                 # points per text line
MAX_ROW_HEIGHT = 150             # points
CONCLUSION_LINE = 45             # characters per line in the conclusion column
MIN_CHARS_PER_LINE = 10          # findings columns: characters per line at least...
CHARS_PER_WIDTH = 1.1            # ...or 1.1 x the column width
# summary
RED_SI_SHARE = 0.25              # an SI is marked red if this share of descriptions is inconsistent (1-4)
SUMMARY_LABEL_WIDTH = 52
SUMMARY_WIDTH = 15
FONT_NAME, FONT_SIZE = "Arial", 10
HIDE0 = '0;-0;"";@'              # number format that shows 0 as an empty cell


def show(v):
    return SHOW.get(v, v) if isinstance(v, str) else v


# ===== Excel formulas =====

def x_inc(c):
    """Excel: 1 if the verdict in cell c is 'inconsistent' (not 'inconsistent?')."""
    return f'(LEFT({c},{len(W["inc"])})="{W["inc"]}")*ISERROR(FIND("?",{c}))'


def x_check(c):
    """Excel: 1 if the verdict in cell c means 'to check by hand' (as is_check)."""
    return (f'SIGN(ISNUMBER(SEARCH("{W["unver"]}",{c}))+ISNUMBER(SEARCH("{W["cand"]}",{c}))'
            f'+ISNUMBER(FIND("?",{c}))+ISNUMBER(SEARCH("{W["mix"]}",{c}))+({c}="{W["chk"]}"))')


def x_list(flags, labels):
    """Excel: '1, 3' from flags (Excel 0/1 expressions) and labels (no TEXTJOIN: works in Excel 2010+)."""
    return "MID(" + "&".join(f'IF({f},", {l}","")' for f, l in zip(flags, labels)) + ",3,99)"


def x_conclusion(col, r):
    """Excel formula for the conclusion of row r; the same rule as verdicts.conclusion()."""
    c = {k: f"{col[k]}{r}" for k in col}
    s = [x_inc(c["item1"]), x_inc(c["item3"]), x_inc(c["item4a"])]
    k = [x_check(c["item1"]), x_check(c["item3"]), x_check(c["item4b"]), x_check(c["item6a"])]
    n6 = x_inc(c["item6"])
    ns = "(" + "+".join(s) + ")"
    nk = "(" + "+".join(k) + ")"
    subl = x_list(s, ["1", "3", "4(a)"])
    chkl = x_list(k, ["1", "3", "4(b)", "6(a)"])
    pn = lambda n, lst: f'IF({n}>1,"{W["items"]}","{W["item"]}")&{lst}'
    also = pn(nk, chkl) if W["also_pn"] else chkl
    inc = (f'"{W["head_inc"]}"&IF({ns}>0,{pn(ns, subl)}&"{W["subst"]}","")'
           f'&IF(({ns}>0)*({n6}),"; ","")&IF({n6},"{W["notation"]}","")'
           f'&IF({ns}>=2,"{W["several"]}",IF({ns}=1,"{W["one"]}",""))'
           f'&IF({nk}>0,"{W["also"]}"&{also},"")')
    chk = f'"{W["head_chk"]}"&{pn(nk, chkl)}&"{W["tail_chk"]}"'
    return f'=IF({ns}+{n6}>0,{inc},IF({nk}>0,{chk},"{W["nof"]}"))'


def x_item6(col, r):
    """Excel formula for item 6 from 6(a) and 6(b) of row r; the same rule as verdicts.combine_item6()."""
    a, b = f"{col['item6a']}{r}", f"{col['item6b']}{r}"
    only = W["only6b"] + ": "
    return (f'=IF(OR({a}="{W["inc"]}",{b}="{W["inc"]}"),"{W["inc"]}",'
            f'IF(ISNUMBER(SEARCH("{W["chk"]}",{a})),"{W["chk"]}",'
            f'IF(ISNUMBER(SEARCH("{W["border"]}",{b})),"{W["border_full"]}",'
            f'IF(AND({b}="{W["cbd"]}",{a}="{W["cons"]}"),"{W["cbd"]}",'
            f'IF({a}="{W["nostruct"]}",IF({b}="{W["cbd"]}","{only}{W["cbd"]}","{only}{W["cons"]}"),'
            f'"{W["cons"]}")))))')


# ===== Sheet 'checked' =====

def fill(colour):
    from openpyxl.styles import PatternFill
    return PatternFill("solid", start_color=colour, end_color=colour)


def write_checked(ws, rows_out, col):
    """One row per description; returns the number of the last row."""
    from openpyxl.styles import Alignment, Font, Border, Side
    from openpyxl.utils import get_column_letter

    ws.append([HEADS.get(c, c) for c in COLS])
    thin = Side(style="thin", color=BORDER_COLOUR)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = fill(HEADER_FILL)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[1].height = HEADER_HEIGHT

    for res in rows_out:
        ws.append([NOT_CHECKED[c] if c in NOT_CHECKED else show(res.get(c)) if c.startswith("item") else res.get(c)
                   for c in COLS])
        r = ws.max_row
        # the conclusion and item 6 are formulas: a verdict corrected by hand updates them
        ws[f"{col['conclusion']}{r}"] = x_conclusion(col, r)
        ws[f"{col['item6']}{r}"] = x_item6(col, r)

        lines = len(conclusion_text(res)) // CONCLUSION_LINE + 1
        for k, c in enumerate(COLS, 1):
            cell = ws.cell(row=r, column=k)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if c.startswith("item"):
                if c == "item6":
                    cell.font = Font(bold=True)
                if c in NOT_CHECKED:
                    cell.fill = fill(GREY)
                cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="center")
            if c.startswith("findings"):
                txt = str(cell.value or "")
                per_line = max(MIN_CHARS_PER_LINE, int(WIDTH[c] * CHARS_PER_WIDTH))
                est = sum(1 + len(x) // per_line for x in txt.split("\n")) if txt else 1
                lines = max(lines, est)
        ws.row_dimensions[r].height = min(LINE_HEIGHT * lines, MAX_ROW_HEIGHT)

    last = ws.max_row
    for k, c in enumerate(COLS, 1):
        ws.column_dimensions[get_column_letter(k)].width = WIDTH.get(c, DEFAULT_WIDTH)
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    return last


def add_colours_and_lists(ws, col, last):
    """Colours that follow the cell contents (conditional formatting), and drop-down lists of verdicts."""
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.worksheet.datavalidation import DataValidation

    for key in VERDICT_COLUMNS:
        L = col[key]
        area, c = f"{L}2:{L}{last}", f"{L}2"
        rules = [
            (f'OR(LEFT({c},{len(W["nopair"])})="{W["nopair"]}",LEFT({c},{len(W["na"])})="{W["na"]}")', GREY),
            (x_inc(c), RED),
            (f'OR(ISNUMBER(SEARCH("{W["chk"]}",{c})),ISNUMBER(SEARCH("{W["cand"]}",{c})),'
             f'ISNUMBER(SEARCH("{W["border"]}",{c})),ISNUMBER(SEARCH("{W["subcat"]}",{c})),ISNUMBER(FIND("?",{c})))',
             YELLOW),
            (f'LEFT({c},{len(W["cons"])})="{W["cons"]}"', GREEN),
            (f'LEN({c})>0', GREY)]
        if key == "item3_in6":                # no colour except grey
            rules = [(f'LEN({c})>=0', GREY)]
        for formula, colr in rules:
            ws.conditional_formatting.add(area, FormulaRule(formula=[formula], fill=fill(colr), stopIfTrue=True))

    if "reading" in col:                          # v2.1: green / yellow / red as written in the cell
        L = col["reading"]
        area, c = f"{L}2:{L}{last}", f"{L}2"
        for word, colr in (("red", RED), ("yellow", YELLOW), ("green", GREEN)):
            ws.conditional_formatting.add(area, FormulaRule(formula=[f'{c}="{word}"'], fill=fill(colr), stopIfTrue=True))

    L = col["conclusion"]
    area, c = f"{L}2:{L}{last}", f"{L}2"
    for formula, colr in [(f'LEFT({c},{len(W["head_inc"])})="{W["head_inc"]}"', RED),
                          (f'LEFT({c},{len(W["head_chk"])})="{W["head_chk"]}"', YELLOW),
                          (f'LEN({c})>0', GREEN)]:
        ws.conditional_formatting.add(area, FormulaRule(formula=[formula], fill=fill(colr), stopIfTrue=True))

    # drop-down lists of verdicts (another value can still be typed after a warning)
    for key, choices in CHOICES.items():
        items = [show(x) for x in choices]
        dv = DataValidation(type="list", formula1='"' + ",".join(items) + '"', allow_blank=True,
                            showErrorMessage=True, errorStyle="warning",
                            errorTitle="Verdict",
                            error="This value is not in the list. Keep it anyway?")
        ws.add_data_validation(dv)
        dv.add(f"{col[key]}2:{col[key]}{last}")


# ===== Sheet 'summary' =====

def write_summary(sm, col, last, rows_out, sheet1):
    """Every number is an Excel formula over the sheet 'checked', so that a reader can see how it
    is counted, and the summary follows any verdict corrected there by hand."""
    from openpyxl.styles import Alignment, Font, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.formatting.rule import CellIsRule, FormulaRule

    thin = Side(style="thin", color=BORDER_COLOUR)

    def rng(key):                                 # e.g. checked!$D$2:$D$54
        L = col[key]
        return f"{sheet1}!${L}$2:${L}${last}"

    # verdict -> kind, written with COUNTIF patterns ("*" is any text, "~?" a literal question mark)
    cats = [("consistent", GREEN, lambda R: f'=COUNTIF({R},"{W["cons"]}")'),
            ("inconsistent", RED,
             lambda R: f'=COUNTIF({R},"{W["inc"]}*")-COUNTIF({R},"{W["inc"]}~?*")'),
            ("borderline /\nsubcategory", YELLOW,
             lambda R: f'=COUNTIF({R},"{W["border"]}*")+COUNTIF({R},"{W["subcat"]}*")'),
            ("to check\nby hand", YELLOW,
             lambda R: f'=COUNTIF({R},"*({W["chk"]})")-COUNTIF({R},"{W["inc"]} ({W["chk"]})")+COUNTIF({R},"{W["chk"]}")'),
            ("no structure", GREY,
             lambda R: f'=COUNTIF({R},"{W["nostruct"]}*")+COUNTIF({R},"{W["only6b"]}*")'),
            ("nothing to check /\nnot applicable", GREY,
             lambda R: f'=COUNTIF({R},"{W["nopair"]}*")+COUNTIF({R},"{W["na"]}*")+COUNTIF({R},"{W["cbd"]}*")')]
    names = [("item1", "1  proton count"),
             ("item3", "3  coupling partners"),
             ("item4a", "4(a)  number of J"),
             ("item4b", "4(b)  partners in the structure (in part)"),
             ("item6", "6  first-order notation (a or b)"),
             ("item6a", "   6(a)  magnetic non-equivalence"),
             ("item6b", "   6(b)  strong coupling")]
    nc = len(cats)

    # --- verdicts per item
    sm.append(["item"] + [c for c, _, _ in cats] + ["total", "check: not classified"])
    for k, c in enumerate(sm[1], 1):
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        if 2 <= k <= nc + 1:
            c.fill = fill(cats[k - 2][1])
    sm.row_dimensions[1].height = SUMMARY_HEADER_HEIGHT

    first_item_row = sm.max_row + 1
    for key, label in names:
        R = rng(key)
        sm.append([label] + [f(R) for _, _, f in cats] + [f'=COUNTA({R})'])
        r = sm.max_row
        a, b = get_column_letter(2), get_column_letter(nc + 1)
        # a verdict that fits none of the kinds (e.g. typed by hand with a typo) shows up here
        sm.cell(row=r, column=nc + 3).value = f"={get_column_letter(nc + 2)}{r}-SUM({a}{r}:{b}{r})"
        sm.cell(row=r, column=1).font = Font(bold=not label.startswith("   "))
        for k in range(2, nc + 4):
            cell = sm.cell(row=r, column=k)
            cell.alignment = Alignment(horizontal="center")
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            cell.number_format = HIDE0
        sm.cell(row=r, column=nc + 2).font = Font(bold=True)
    last_item_row = sm.max_row

    for k in range(2, nc + 2):                    # colour a kind only where its count is not zero
        L = get_column_letter(k)
        sm.conditional_formatting.add(f"{L}{first_item_row}:{L}{last_item_row}",
                                      CellIsRule(operator="greaterThan", formula=["0"], fill=fill(cats[k - 2][1])))
    L = get_column_letter(nc + 3)
    sm.conditional_formatting.add(f"{L}{first_item_row}:{L}{last_item_row}",
                                  CellIsRule(operator="notEqual", formula=["0"], fill=fill(ALERT)))
    sm.append([])

    # --- conclusions: counted from the first words of the column 'conclusion'
    C = rng("conclusion")
    INC, SUB, PLUR = W["head_inc"].rstrip(": "), W["subst"].strip(" ()"), W["head_inc"] + W["items"].strip()
    CHK, NOF = W["head_chk"].rstrip(": "), " ".join(W["nof"].split(" ")[:2])
    sm.append(["Conclusions (automatic screening, not an assessment)", "descriptions", "%"])
    for c in sm[sm.max_row]:
        c.font = Font(bold=True)
    n_row = sm.max_row + 1
    for label, formula, colr in [
            ("inconsistent under items 1-4 (substantive)",
             f'=COUNTIF({C},"{INC}*{SUB}*")', RED),
            ("inconsistent under item 6 only (notation)",
             f'=COUNTIF({C},"{INC}:*")-COUNTIF({C},"{INC}*{SUB}*")', RED),
            ("to check by hand (no inconsistency found so far)", f'=COUNTIF({C},"{CHK}*")', YELLOW),
            ("no inconsistency found by the automatic checks", f'=COUNTIF({C},"{NOF}*")', GREEN)]:
        r = sm.max_row + 1
        sm.append([label, formula, f"=IF(COUNTA({C})=0,\"\",B{r}/COUNTA({C}))"])
        sm.cell(row=r, column=1).fill = fill(colr)
    r = sm.max_row + 1
    sm.append(["inconsistent under any checked item",
               f"=B{n_row}+B{n_row + 1}", f"=IF(COUNTA({C})=0,\"\",B{r}/COUNTA({C}))"])
    sm.cell(row=r, column=1).font = Font(bold=True)
    for rr in range(n_row, r + 1):
        sm.cell(row=rr, column=2).alignment = Alignment(horizontal="center")
        sm.cell(row=rr, column=3).alignment = Alignment(horizontal="center")
        sm.cell(row=rr, column=3).number_format = "0%"
    sm.append(["These shares are screening figures: the script can miss inconsistencies (items 2, 4(b), 7 are not "
               "checked; item 3 can be missed) and leaves some cases to be decided by hand. Human verification is required."])
    sm.cell(row=sm.max_row, column=1).font = Font(italic=True)

    # --- per SI file (article): many substantive inconsistencies in one SI suggest checking its raw data
    def article(idv):
        return re.sub(r"_[^_]+$", "", str(idv))
    arts = sorted({article(x["id"]) for x in rows_out})
    if arts:
        I = rng("id")
        sm.append([])
        sm.append(["Per SI file", "descriptions", "inconsistent 1-4", "%", "2+ substantive items"])
        for c in sm[sm.max_row]:
            c.font = Font(bold=True)
            c.alignment = Alignment(wrap_text=True, horizontal="center")
        first = sm.max_row + 1
        for art in arts:
            r = sm.max_row + 1
            pat = re.sub(r"([*?~])", r"~\1", art) + "_*"     # ids of this SI: '<SI>_<label>'
            sm.append([art, f'=COUNTIF({I},"{pat}")', f'=COUNTIFS({I},"{pat}",{C},"{INC}*{SUB}*")',
                       f"=IF(B{r}=0,\"\",C{r}/B{r})",
                       f'=COUNTIFS({I},"{pat}",{C},"{PLUR}*{SUB}*")'])
            for cc in range(2, 6):
                sm.cell(row=r, column=cc).alignment = Alignment(horizontal="center")
            sm.cell(row=r, column=4).number_format = "0%"
        lastr = sm.max_row
        sm.conditional_formatting.add(f"A{first}:E{lastr}",
                                      FormulaRule(formula=[f"OR($D{first}>={RED_SI_SHARE},$E{first}>0)"], fill=fill(RED)))
        sm.append(["SI files marked red (a quarter or more of the descriptions inconsistent under items 1-4, or a "
                   "description with two or more such items): a check of the raw data of the article is advisable."])
        sm.cell(row=sm.max_row, column=1).font = Font(italic=True)

    # --- notes
    sm.append([])
    sm.append([f'="{"Item 3: "}"&COUNTIF({rng("item3_in6")},"{W["yes"]}*")&"{" of "}"'
               f'&(COUNTIF({rng("item3")},"{W["inc"]}*")-COUNTIF({rng("item3")},"{W["inc"]}~?*"))&"'
               + " inconsistent descriptions have their item-3 findings only in signals that are not first-order under item 6."
               + '"'])
    sm.append(["Item 6 is one item checked in two ways; 6(a) and 6(b) are shown below it for detail. "
               "Every finding must be checked by hand."])
    sm.append(["All numbers on this sheet are Excel formulas over the sheet 'checked' (click a cell to see it). "
               "To correct a verdict there, choose it from the drop-down list in the cell: item 6, the conclusion, "
               "the colours and this summary are formulas and follow at once."])
    sm.cell(row=sm.max_row, column=1).font = Font(italic=True)
    sm.column_dimensions["A"].width = SUMMARY_LABEL_WIDTH
    for k in range(2, nc + 4):
        sm.column_dimensions[get_column_letter(k)].width = SUMMARY_WIDTH


def write_table(rows_out, stats, out):
    """Write the two sheets to out (.xlsx)."""
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    sheet1, sheet2 = "checked", "summary"
    col = {c: get_column_letter(k) for k, c in enumerate(COLS, 1)}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet1
    last = write_checked(ws, rows_out, col)
    if last >= 2:
        add_colours_and_lists(ws, col, last)
    sm = wb.create_sheet(sheet2)
    write_summary(sm, col, last, rows_out, sheet1)

    # one font for both sheets: Arial 10 (bold, italic and colour are kept)
    for sheet in (ws, sm):
        for row in sheet.iter_rows():
            for cell in row:
                f = cell.font
                cell.font = Font(name=FONT_NAME, size=FONT_SIZE, bold=f.bold, italic=f.italic, color=f.color)
    try:
        wb.save(out)
    except PermissionError:
        sys.exit(f"Close {out} in Excel and run again.")
