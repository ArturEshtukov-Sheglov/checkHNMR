"""Checks that tables.py reproduces the numbers printed in the note checkHNMR_V2.1.5_width_test.pdf.

Run:  python test_width.py          prints every check and writes test_width_log.txt
      python -m pytest test_width.py
Each line gives the value printed in the note, the computed value at higher precision, and the rule of comparison
(equal after the rounding used in the note, or not above the bound quoted in the note)."""
import datetime
import os
import platform
import sys

import tables as T

M = "−"
TABLE2 = ["0.06", "0.17", "0.29", "0.38", "0.52", "0.67"]
TABLE3 = [("9.041", "0.73"), ("9.169", "0.51"), ("9.353", "0.37"), ("10.000", "0.16")]
TABLE5 = [  # predicted W_p, computed pair, width of the pair, as printed in Table 5
    ("9.00", f"{M}4.501 (0.96); 4.501 (1.04)", "9.002"),
    ("9.00", f"{M}4.501 (0.96); 4.501 (1.05)", "9.002"),
    ("9.00", f"{M}4.498 (0.96); 4.504 (1.05)", "9.002"),
    ("7.00", f"{M}3.502 (0.96); 3.502 (1.04)", "7.004"),
    ("7.00", f"{M}3.502 (0.96); 3.502 (1.03)", "7.004"),
    ("7.00", f"{M}3.491 (0.96); 3.514 (1.03)", "7.004"),
    ("14.70", f"{M}7.354 (0.95); 7.354 (1.05)", "14.708"),
    ("14.70", f"{M}7.326 (0.95); 7.382 (1.05)", "14.708"),
    ("16.60", f"{M}8.298 (0.99); 8.299 (1.01)", "16.597"),
    ("16.60", f"{M}8.293 (0.99); 8.303 (1.01)", "16.596"),
    ("16.60", f"{M}8.298 (0.99); 8.298 (1.01)", "16.596"),
    ("12.00", f"{M}5.997 (0.96); 6.003 (1.05)", "12.001"),
    ("12.00", f"{M}5.997 (0.96); 6.003 (1.05)", "12.001"),
    ("10.50", f"{M}5.247 (0.97); 5.254 (1.04)", "10.501"),
]


def checks():
    """List of (label, value in the note, computed value, rule, passed)."""
    out = []
    eq = "equal after rounding"

    for (x, r), note in zip(T.table2(), TABLE2):
        out.append((f"Table 2: r at dnu/J = {x:g}", note, f"{r:.4f}", eq, f"{r:.2f}" == note))

    t3 = T.table3()
    for r, (w, q) in zip(t3, TABLE3):
        x = f"{r['dnu_over_J']:g}"
        out.append((f"Table 3: width at dnu/J = {x}, Hz", w, f"{r['width']:.4f}", eq, f"{r['width']:.3f}" == w))
        out.append((f"Table 3: outer/inner at dnu/J = {x}", q, f"{r['outer_over_inner']:.4f}", eq,
                    f"{r['outer_over_inner']:.2f}" == q))
    d = max(r["max_dpos_vs_exact"] for r in t3)
    out.append(("Table 3: closed form vs exact diagonalization, Hz", "0.009", f"{d:.4f}", "not above", d <= 0.009))

    rows = T.table5()
    for (lab, r), s, note in zip(rows, T.table5_strings(rows), TABLE5):
        (p1, i1), (p2, i2) = r["pair"]
        out.append((f"Table 5: {lab}: predicted W_p, Hz", note[0], f"{r['W_pred']:.4f}", eq, s[1] == note[0]))
        out.append((f"Table 5: {lab}: computed pair", note[1],
                    f"{p1:.4f} ({i1:.4f}); {p2:.4f} ({i2:.4f})", eq, s[2] == note[1]))
        out.append((f"Table 5: {lab}: width of the pair, Hz", note[2], f"{r['W_pair']:.4f}", eq, s[3] == note[2]))
    far = [r for _, r in rows if "far_max_dpos_after_shift" in r]
    fp = max(r["far_max_dpos_after_shift"] for r in far)
    fi = max(r["far_max_dint"] for r in far)
    sh = max(abs(r["common_shift"]) for _, r in rows)
    out.append(("X 100 times farther: max difference in position, Hz", "0.0011", f"{fp:.5f}", "not above",
                round(fp, 4) <= 0.0011))
    out.append(("X 100 times farther: max difference in intensity", "0.0011", f"{fi:.5f}", "not above",
                round(fi, 4) <= 0.0011))
    out.append(("common second-order shift, Hz", "0.23", f"{sh:.4f}", "not above", sh <= 0.23))

    aa = T.aaxx()
    for dax, note in ((200.0, "9.00"), (40.0, "9.13")):
        out.append((f"AA'XX': distance of the N lines at dnu_AX = {dax:g} Hz, Hz", note, f"{aa[dax]:.4f}", eq,
                    f"{aa[dax]:.2f}" == note))

    ex = T.example()
    out.append(("Example: inner lines at dnu(5,6) = 100 Hz, +- Hz", "3.5", f"{ex[100.0]['inner']:.4f}", eq,
                f"{ex[100.0]['inner']:.1f}" == "3.5"))
    out.append(("Example: inner lines at dnu(5,6) = 2 Hz, +- Hz", "0.83", f"{ex[2.0]['inner']:.4f}", eq,
                f"{ex[2.0]['inner']:.2f}" == "0.83"))
    dd = ex[2.0]["dd"]
    out.append(("Example: reading at dnu(5,6) = 2 Hz, dd J, Hz", "5.3, 3.7", f"{dd[0]:.4f}, {dd[1]:.4f}", eq,
                (f"{dd[0]:.1f}", f"{dd[1]:.1f}") == ("5.3", "3.7")))
    t = ex[0.0]["dd"]
    out.append(("Example: reading at dnu(5,6) = 0 Hz, t J, Hz", "4.5", f"{t[0]:.4f}, {t[1]:.4f}", eq,
                (f"{t[0]:.1f}", f"{t[1]:.1f}") == ("4.5", "4.5")))
    comb = [ex[k]["combination"] for k in (2.0, 0.0)]
    out.append(("Example: weak lines, +- Hz", "8.3 to 8.5", ", ".join(f"{f:.4f}" for f, _ in comb), "within",
                all(8.25 <= f < 8.55 for f, _ in comb)))
    out.append(("Example: weak lines, intensity", "0.16-0.18", ", ".join(f"{i:.4f}" for _, i in comb), "within",
                all(0.155 <= i < 0.185 for _, i in comb)))

    ac = T.acrolein()
    out.append(("Acrolein: span of the CHO lines, Hz", "7.63", f"{ac['span']:.4f}", eq, f"{ac['span']:.2f}" == "7.63"))
    out.append(("Acrolein: J_ab between, Hz", "5.6 and 9.6", f"{ac['J_ab_min']:.4f} and {ac['J_ab_max']:.4f}", eq,
                (f"{ac['J_ab_min']:.1f}", f"{ac['J_ab_max']:.1f}") == ("5.6", "9.6")))
    return out


def test_numbers_of_the_note():
    failed = [c[0] for c in checks() if not c[4]]
    assert not failed, failed


def report():
    import numpy
    res = checks()
    here = os.path.dirname(os.path.abspath(__file__))
    vfile = os.path.join(here, "..", "..", "..", "VERSION")
    version = open(vfile, encoding="utf-8").readline().strip() if os.path.exists(vfile) else "unknown"
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    w = max(len(c[0]) for c in res)
    lines = [f"checkHNMR {version} - multiplet-width test: numbers of the note checkHNMR_V2.1.5_width_test.pdf",
             f"Command: python test_width.py   (run {now}, {platform.system()} {platform.release()}, "
             f"Python {platform.python_version()}, numpy {numpy.__version__})",
             "Columns: check; value in the note; computed value; rule of comparison.",
             "=" * 110]
    for label, note, comp, rule, ok in res:
        lines.append(f"  {'PASS' if ok else 'FAIL'}  {label:<{w}}   note {note}   computed {comp}   ({rule})")
    nfail = sum(not c[4] for c in res)
    lines += ["=" * 110, f"ALL PASSED ({len(res)} checks)" if nfail == 0 else f"{nfail} OF {len(res)} CHECKS FAILED"]
    text = "\n".join(lines) + "\n"
    try:
        sys.stdout.reconfigure(encoding="utf-8")        # Windows consoles and Git Bash: print minus signs
    except (AttributeError, ValueError):
        pass
    print(text, end="")
    with open(os.path.join(here, "test_width_log.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return nfail


if __name__ == "__main__":
    sys.exit(1 if report() else 0)
