"""Reproduces every computed number of the note "checkHNMR V2.1.5: Justification of the multiplet-width test".

Run:  python tables.py          (prints Tables 2, 3, 5 and the numbers quoted in the text; writes results.json)
Needs Python 3.10+ and numpy.  Closed-form expressions are in analytic.py, exact diagonalization in spin.py.

Positions are in Hz relative to nu_X.  For each case the closed-form lines of X are matched to the exact lines;
"common shift" is the mean difference (the second-order shift, the same for all lines of X), and the agreement
is reported after removing it.  The same system with X moved 100 times farther from its partners shows that the
remaining differences are the second-order terms omitted in the secular approximation.
"""
import json
import sys
import analytic as A
from spin import lines, merge

MINUS = "−"


def fmt(x, nd):
    """Fixed-point format with a typographic minus sign."""
    s = f"{x:.{nd}f}"
    return s.replace("-", MINUS) if s.startswith("-") and float(s) != 0 else s.lstrip("-")


def num_region(nu, J, lo, hi, eps=0.05, min_int=0.005):
    return [(f, i) for f, i in merge(lines(nu, J), eps=eps) if lo < f < hi and i >= min_int]


def ana_merge(ls, eps=0.05, min_int=0.005):
    return [(f, i) for f, i in merge([(f, i) for f, i, _ in ls], eps=eps) if i >= min_int]


def match(ana, num):
    """Pair every closed-form line with the nearest unused exact line."""
    rows, used = [], set()
    for f, i in ana:
        k = min((k for k in range(len(num)) if k not in used), key=lambda k: abs(num[k][0] - f))
        used.add(k)
        rows.append((f, i, num[k][0], num[k][1]))
    return rows


def protected_case(nu, J, ana_lines, lo, hi, pred, far=None):
    ana = ana_merge(ana_lines, eps=0.4)          # lines closer than 0.4 Hz are compared as one group
    num = num_region(nu, J, lo, hi, eps=0.4)
    m = match(ana, num)
    shift = sum(n - a for a, _, n, _ in m) / len(m)
    lo_l = min(num, key=lambda t: abs(t[0] - shift + pred / 2))      # exact lines nearest to +-pred/2
    hi_l = min(num, key=lambda t: abs(t[0] - shift - pred / 2))
    out = {"W_pred": pred,
           "pair": [[lo_l[0] - shift, lo_l[1]], [hi_l[0] - shift, hi_l[1]]],
           "W_pair": hi_l[0] - lo_l[0],
           "common_shift": shift,
           "max_dpos_after_shift": max(abs(n - a - shift) for a, _, n, _ in m),
           "max_dint": max(abs(inn - ia) for _, ia, _, inn in m)}
    if far is not None:                          # X moved 100 times farther: the truncation error vanishes
        nu_f, ana_f = far
        af, nf = ana_merge(ana_f), num_region(nu_f, J, lo, hi)
        mf = match(af, nf)
        sh = sum(n - a for a, _, n, _ in mf) / len(mf)
        out["far_max_dpos_after_shift"] = max(abs(n - a - sh) for a, _, n, _ in mf)
        out["far_max_dint"] = max(abs(inn - ia) for _, ia, _, inn in mf)
    return out


def table5():
    rows = []
    for jbx, labels in ((1.0, ("ABX: JAX 8.0, JBX 1.0, JAB 7.5; ΔνAB 100", "ABX: … ΔνAB 2",
                                "ABX: … ΔνAB 0")),
                        (-1.0, ("ABX: JBX −1.0; ΔνAB 100", "ABX: JBX −1.0; ΔνAB 2",
                                 "ABX: JBX −1.0; ΔνAB 0"))):
        for dab, lab in zip((100.0, 2.0, 0.0), labels):
            nu = [0.0, 200.0, 200.0 + dab]
            J = {(0, 1): 8.0, (0, 2): jbx, (1, 2): 7.5}
            far = ([0.0, 20000.0, 20000.0 + dab], A.abx_x(20000, 20000 + dab, 0, 7.5, 8.0, jbx))
            rows.append((lab, protected_case(nu, J, A.abx_x(200, 200 + dab, 0, 7.5, 8.0, jbx), -50, 100,
                                             abs(8.0 + jbx), far)))
    for dab, lab in ((100.0, "diene: JAX 15.5, JBX −0.8, JAB 10.5; ΔνAB 100"),
                     (0.0, "diene; ΔνAB 0")):
        nu = [0.0, 300.0, 300.0 + dab]
        J = {(0, 1): 15.5, (0, 2): -0.8, (1, 2): 10.5}
        far = ([0.0, 30000.0, 30000.0 + dab], A.abx_x(30000, 30000 + dab, 0, 10.5, 15.5, -0.8))
        rows.append((lab, protected_case(nu, J, A.abx_x(300, 300 + dab, 0, 10.5, 15.5, -0.8), -50, 150,
                                         abs(15.5 - 0.8), far)))
    J4 = {(0, 1): 7.8, (0, 2): 1.2, (0, 3): 7.6, (1, 2): 8.0, (1, 3): 1.5, (2, 3): 0.7}   # X, A, B, C
    for dab, lab in ((100.0, "two ortho couplings (7.8, 7.6) + meta 1.2; ΔνAB 100"),
                     (2.0, "same; ΔνAB 2"), (0.0, "same; ΔνAB 0")):
        nu = [0.0, 150.0, 150.0 + dab, -150.0]
        ana = A.abx_x_plus_weak(150, 150 + dab, 0, 8.0, 7.8, 1.2, 7.6, 1.5, 0.7)
        far = ([0.0, 15000.0, 15000.0 + dab, -15000.0],
               A.abx_x_plus_weak(15000, 15000 + dab, 0, 8.0, 7.8, 1.2, 7.6, 1.5, 0.7))
        rows.append((lab, protected_case(nu, J4, ana, -60, 60, 7.8 + 1.2 + 7.6, far)))
    # fourth spin weakly coupled to all: 19F (modelled as a spin 1 MHz away) or a remote proton
    for lab, nu4, jx4 in (("ABX (ΔνAB 0) + 19F, JXF −3", 1.0e6, -3.0),
                          ("same, JXF +3", 1.0e6, 3.0),
                          ("ABX (ΔνAB 0) + remote 1H, JXC −1.5", -150.0, -1.5)):
        nu = [0.0, 200.0, 200.0, nu4]
        J = {(0, 1): 8.0, (0, 2): 1.0, (1, 2): 7.5, (0, 3): jx4}
        rows.append((lab, protected_case(nu, J, A.abx_x_plus_weak(200, 200, 0, 7.5, 8.0, 1.0, jx4), -50, 100,
                                         9.0 + abs(jx4))))
    return rows


def table5_strings(rows):
    out = []
    for lab, r in rows:
        (p1, i1), (p2, i2) = r["pair"]
        out.append((lab, fmt(r["W_pred"], 2), f"{fmt(p1, 3)} ({fmt(i1, 2)}); {fmt(p2, 3)} ({fmt(i2, 2)})",
                    fmt(r["W_pair"], 3)))
    return out


def table2():
    return [(x, A.ab_ratio(x)) for x in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)]


def table3():
    """X strongly coupled to A (J_XA 8.0), B far (J_XB 1.0, J_AB 7.5, B 300 Hz from A)."""
    rows = []
    for dax in (50.0, 24.0, 16.0, 8.0):
        nu = [0.0, dax, dax + 300.0]
        J = {(0, 1): 8.0, (0, 2): 1.0, (1, 2): 7.5}
        an = sorted((f, i) for f, i, _ in A.ab_x_half_with_weak_b(0.0, dax, dax + 300.0, 8.0, 1.0, 7.5))
        num = [(f, i) for f, i in merge(lines(nu, J), eps=0.05) if f < dax / 2 and i >= 0.005]
        m = match(an, num)
        outer, inner = an[0][1] + an[1][1], an[2][1] + an[3][1]
        rows.append({"dnu_over_J": dax / 8.0, "width": an[-1][0] - an[0][0], "outer_over_inner": outer / inner,
                     "max_dpos_vs_exact": max(abs(n - a) for a, _, n, _ in m)})
    return rows


def aaxx():
    """AA'XX' of a para-substituted ring: distance of the two N lines (J_AX 8.5, J_AX' 0.5, J_AA' 2.5, J_XX' 2.0)."""
    J5 = {(0, 1): 2.5, (0, 2): 8.5, (0, 3): 0.5, (1, 2): 0.5, (1, 3): 8.5, (2, 3): 2.0}
    out = {}
    for dax in (200.0, 40.0):
        num = [(f, i) for f, i in merge(lines([0.0, 0.0, dax, dax], J5), eps=0.05) if f < dax / 2 and i >= 0.005]
        strong = [f for f, i in num if i >= 1.0]
        out[dax] = max(strong) - min(strong)
    return out


def example():
    """1,2,3-trisubstituted benzene, H-4 (X) 200 Hz from H-5 (A) and H-6 (B): J_45 8.0, J_46 1.0, J_56 7.5."""
    out = {}
    for dab in (100.0, 2.0, 0.0):
        ls = A.abx_x(200.0, 200.0 + dab, 0.0, 7.5, 8.0, 1.0)
        S = 4.5
        inner = abs(ls[2][0])                     # +-(D+ - D-): inner lines picked as a first-order dd
        comb = [(abs(f), i) for f, i, lab in ls if lab == "combination"]
        out[dab] = {"inner": inner, "dd": (S + inner, S - inner), "combination": comb[0]}
    return out


def acrolein():
    """CHO lines of acrolein (ChemicalBook peak list, 399.65 MHz, CDCl3), Hz; span and the range of J_ab."""
    obs = [3835.14, 3833.47, 3832.24, 3830.41, 3828.74, 3827.51]
    span = max(obs) - min(obs)
    return {"span": span, "J_ab_min": span - 2 * 1.0, "J_ab_max": span + 2 * 1.0}   # |4J_ac|, |4J_ad| < 1 Hz


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")        # Windows consoles and Git Bash: print minus signs
    except (AttributeError, ValueError):
        pass
    t5 = table5()
    t2, t3, aa, ex, ac = table2(), table3(), aaxx(), example(), acrolein()
    far_pos = max(r["far_max_dpos_after_shift"] for _, r in t5 if "far_max_dpos_after_shift" in r)
    far_int = max(r["far_max_dint"] for _, r in t5 if "far_max_dint" in r)
    shift = max(abs(r["common_shift"]) for _, r in t5)

    print("Table 2. Intensity ratio of the outer to the inner line in AB")
    print("  dnu/J: " + "  ".join(f"{x:g}" for x, _ in t2))
    print("  r:     " + "  ".join(f"{r:.2f}" for _, r in t2))
    print("Table 3. X strongly coupled to A (B far): width (predicted 9.0) and outer/inner")
    for r in t3:
        print(f"  dnu/J {r['dnu_over_J']:g}: width {r['width']:.3f} Hz, outer/inner {r['outer_over_inner']:.2f}")
    print(f"  closed form vs exact diagonalization: max |d position| = {max(r['max_dpos_vs_exact'] for r in t3):.4f} Hz")
    print("Table 5. Protected pair of X: predicted and computed")
    for row in table5_strings(t5):
        print("  " + " | ".join(row))
    print(f"X 100 times farther: max |d position| = {far_pos:.5f} Hz, max |d intensity| = {far_int:.5f}")
    print(f"common second-order shift: max |shift| = {shift:.4f} Hz")
    print(f"AA'XX' N lines: {aa[200.0]:.2f} Hz at dnu_AX = 200 Hz, {aa[40.0]:.2f} Hz at 40 Hz")
    for dab, e in ex.items():
        print(f"Example, H-5/H-6 {dab:g} Hz apart: inner lines +-{e['inner']:.2f} Hz, read as dd {e['dd'][0]:.1f}, "
              f"{e['dd'][1]:.1f} Hz; combination lines +-{e['combination'][0]:.2f} Hz ({e['combination'][1]:.3f})")
    print(f"Acrolein CHO: span {ac['span']:.2f} Hz; J_ab between {ac['J_ab_min']:.1f} and {ac['J_ab_max']:.1f} Hz")

    res = {"table2": t2, "table3": t3, "table5": [{"case": lab, **r} for lab, r in t5],
           "far_max_dpos": far_pos, "far_max_dint": far_int, "max_common_shift": shift,
           "aaxx_N_distance": {str(k): v for k, v in aa.items()},
           "example": {str(k): v for k, v in ex.items()}, "acrolein": ac}
    with open("results.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
