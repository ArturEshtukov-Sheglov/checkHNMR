"""Closed-form line positions and intensities (no diagonalization), for comparison with spin.py.

Conventions as in spin.py: frequencies in Hz on an axis that increases with delta; H = sum nu_i Iz_i +
sum J_ij I_i.I_j; a line is a transition from the state with the larger total Fz to the one with Fz - 1,
frequency = E_upper - E_lower; intensity |<lower|F-|upper>|^2, so that every first-order line has 1.
All functions return [(frequency, intensity, label)].
"""
import math


def ab(nu_a, nu_b, J):
    """AB system, exact.  dnu = nu_a - nu_b, D = sqrt(dnu^2 + J^2).
    Lines: nu_c +- (D + J)/2 with intensity 1 - J/D (outer), nu_c +- (D - J)/2 with 1 + J/D (inner)."""
    nu_c = (nu_a + nu_b) / 2
    dnu = nu_a - nu_b
    D = math.hypot(dnu, J)
    s = J / D if D > 0 else 1.0
    hi, lo = ("A", "B") if dnu >= 0 else ("B", "A")      # which half lies at the higher frequency
    return [(nu_c + (D + J) / 2, 1 - s, "outer, " + hi), (nu_c + (D - J) / 2, 1 + s, "inner, " + hi),
            (nu_c - (D - J) / 2, 1 + s, "inner, " + lo), (nu_c - (D + J) / 2, 1 - s, "outer, " + lo)]


def ab_ratio(dnu_over_J):
    """Intensity ratio of the outer to the inner line of AB: r = (1 - J/D)/(1 + J/D)."""
    s = 1 / math.hypot(dnu_over_J, 1)
    return (1 - s) / (1 + s)


def abx_x(nu_a, nu_b, nu_x, J_ab, J_ax, J_bx):
    """X part of ABX, X weakly coupled to A and B (secular approximation for X).
    For m_X = +-1/2 the AB block has dnu_+- = (nu_a - nu_b) +- (J_ax - J_bx)/2;
    2D_+- = sqrt(dnu_+-^2 + J_ab^2), tan 2t_+- = J_ab / dnu_+- (2t in (0, pi)).
    Lines: nu_x +- (J_ax + J_bx)/2 (intensity 1, the protected pair); nu_x +- (D_+ - D_-) (cos^2(t_+ - t_-));
    nu_x +- (D_+ + D_-) (sin^2(t_+ - t_-), combination lines)."""
    dnu = nu_a - nu_b
    dp, dm = dnu + (J_ax - J_bx) / 2, dnu - (J_ax - J_bx) / 2
    Dp, Dm = math.hypot(dp, J_ab) / 2, math.hypot(dm, J_ab) / 2
    tp, tm = math.atan2(J_ab, dp) / 2, math.atan2(J_ab, dm) / 2
    c2, s2 = math.cos(tp - tm) ** 2, math.sin(tp - tm) ** 2
    S = (J_ax + J_bx) / 2
    return [(nu_x + S, 1.0, "protected"), (nu_x - S, 1.0, "protected"),
            (nu_x + (Dp - Dm), c2, "mixed"), (nu_x - (Dp - Dm), c2, "mixed"),
            (nu_x + (Dp + Dm), s2, "combination"), (nu_x - (Dp + Dm), s2, "combination")]


def abx_x_plus_weak(nu_a, nu_b, nu_x, J_ab, J_ax, J_bx, J_xc, J_ac=0.0, J_bc=0.0):
    """X part of ABX plus a fourth spin C weakly coupled to A, B and X (a heteronucleus or a remote proton).
    For m_C = +-1/2: ABX with nu_a + m_C J_ac, nu_b + m_C J_bc, nu_x + m_C J_xc."""
    out = []
    for mc in (+0.5, -0.5):
        for f, i, lab in abx_x(nu_a + mc * J_ac, nu_b + mc * J_bc, nu_x + mc * J_xc, J_ab, J_ax, J_bx):
            out.append((f, i, f"m_C={mc:+.1f}, {lab}"))
    return out


def ab_x_half_with_weak_b(nu_x, nu_a, nu_b, J_xa, J_xb, J_ab):
    """X strongly coupled to A, B weakly coupled to both: for m_B = +-1/2 an AB system (A, X) with
    nu_x + m_B J_xb and nu_a + m_B J_ab.  Returns the lines of the X half of both."""
    out = []
    for mb in (+0.5, -0.5):
        for f, i, lab in ab(nu_a + mb * J_ab, nu_x + mb * J_xb, J_xa):     # 'A' = A, 'B' = X (nu_a > nu_x)
            if lab.endswith("B"):
                out.append((f, i, f"m_B={mb:+.1f}, {lab.split(',')[0]}"))
    return out
