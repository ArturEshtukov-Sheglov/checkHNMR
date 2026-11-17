# Multiplet-width test: calculations

This directory holds the justification of the multiplet-width test of checkHNMR V2.1.5
(`checkHNMR_V2.1.5_width_test.pdf`) and the code that reproduces every computed number in it.

| File | Content |
|---|---|
| `spin.py` | exact spectra of small spin-1/2 systems by full diagonalization of the spin Hamiltonian (no secular approximation) |
| `analytic.py` | closed-form line positions and intensities: AB, X part of ABX, ABX with a fourth weakly coupled spin, X strongly coupled to A |
| `tables.py` | reproduces Tables 2, 3 and 5 of the note and the numbers quoted in its text; writes `results.json` |
| `results.json` | the output of `tables.py` at full precision (verification data) |
| `test_width.py` | checks that `tables.py` gives the numbers printed in the note; writes `test_width_log.txt` |
| `test_width_log.txt` | the log of the last check: every number of the note, the computed value, PASS or FAIL |

## How to run

Python 3.10 or later and numpy. numpy is installed together with RDKit (`requirements.txt` of the repository; `run_all.py` offers to install the packages). If it is missing, `spin.py` stops with the command to install it; the scripts do not install anything themselves.

```
cd docs/development/width_criterion
python tables.py
python test_width.py          (prints every check and writes test_width_log.txt)
python -m pytest test_width.py
```

The run takes less than a second.

## Conventions

All frequencies and couplings are in hertz. ν increases with δ. The Hamiltonian is
H = Σ ν_i I_zi + Σ J_ij **I**_i·**I**_j with signed J_ij. A line is a transition a → b observed with the total
lowering operator F₋; its intensity |⟨b|F₋|a⟩|² is normalized so that every line of a first-order multiplet
has intensity 1 (high-temperature approximation).

## Where each number of the note comes from

| Note | Function in `tables.py` |
|---|---|
| Table 2 (r for AB) | `table2` (closed form, `analytic.ab_ratio`) |
| Table 3 (X strongly coupled to A); agreement to 0.009 Hz | `table3` |
| Table 5 (protected pair of X) | `table5`: closed form (`analytic.py`) matched to exact diagonalization (`spin.py`); positions are given after the common second-order shift |
| "agree to 0.0011 Hz in position and 0.0011 in intensity" (X moved 100 times farther) | `table5`, keys `far_max_*` |
| "common second-order shift (≤ 0.23 Hz)" | `table5`, key `common_shift` |
| AA′XX′: N lines 9.00 Hz at Δν_AX = 200 Hz and 9.13 Hz at 40 Hz | `aaxx` |
| Example (inner lines ±0.83 Hz, "dd, J = 5.3, 3.7 Hz", weak lines at ±8.3 to ±8.5 Hz) | `example` |
| Acrolein (span 7.63 Hz, J_ab between 5.6 and 9.6 Hz) | `acrolein` (peak list of ChemicalBook, 399.65 MHz, CDCl3) |

Intensities in Table 5 are rounded once, from the exact values.

The counts from the development data quoted in Table 4 of the note (for example, 580 signals of benzenoid
protons) come from the development data of the rule and are not reproduced here.
