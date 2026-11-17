"""Exact 1H spectra of small spin-1/2 systems by full diagonalization (no secular approximation).

Part of the justification of the multiplet-width test, checkHNMR V2.1.5 (docs/development/width_criterion/).

Conventions (all in Hz):
  H = sum_i nu_i Iz_i + sum_{i<j} J_ij (Ix_i Ix_j + Iy_i Iy_j + Iz_i Iz_j)   -- full scalar coupling
  nu_i  -- frequency of spin i on an axis that increases with delta (larger nu = downfield)
  J_ij  -- signed coupling constant
  line  -- transition a -> b with frequency E_a - E_b, where F- = sum_i I-_i lowers the total Fz by 1;
           intensity |<b|F-|a>|^2 (high-temperature approximation: all states equally populated).
           With this normalization every line of a first-order multiplet has intensity 1.
"""
import itertools
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("numpy is needed. It is installed together with the packages of checkHNMR\n"
             "(run_all.py offers to install them), or install it by hand:\n"
             f"    {sys.executable} -m pip install numpy")

SX = np.array([[0, .5], [.5, 0]], dtype=complex)
SY = np.array([[0, -.5j], [.5j, 0]], dtype=complex)
SZ = np.array([[.5, 0], [0, -.5]], dtype=complex)
SM = np.array([[0, 0], [1, 0]], dtype=complex)          # I- : |alpha> -> |beta>


def op(o, k, n):
    """Single-spin operator o acting on spin k of an n-spin system."""
    m = np.array([[1.0 + 0j]])
    for i in range(n):
        m = np.kron(m, o if i == k else np.eye(2))
    return m


def hamiltonian(nu, J):
    """nu: list of frequencies; J: {(i, j): J_ij}."""
    n = len(nu)
    H = sum(nu[i] * op(SZ, i, n) for i in range(n))
    for (i, j), v in J.items():
        H = H + v * sum(op(s, i, n) @ op(s, j, n) for s in (SX, SY, SZ))
    return H


def merge(ls, eps=1e-4):
    """Merge transitions closer than eps Hz (intensities add), e.g. the centre line of a first-order triplet."""
    out = []
    for f, i in sorted(ls):
        if out and abs(out[-1][0] - f) < eps:
            out[-1] = (out[-1][0], out[-1][1] + i)
        else:
            out.append((f, i))
    return out


def lines(nu, J, tol=1e-6):
    """All transitions of the full spectrum (observed with the total F-): list of (frequency, intensity)."""
    n = len(nu)
    E, V = np.linalg.eigh(hamiltonian(nu, J))
    Fm = sum(op(SM, i, n) for i in range(n))
    M = V.conj().T @ Fm @ V
    out = []
    for a, b in itertools.product(range(2 ** n), repeat=2):
        inten = abs(M[b, a]) ** 2
        if inten > tol:
            out.append((float(E[a] - E[b]), float(inten)))
    return merge(out)
