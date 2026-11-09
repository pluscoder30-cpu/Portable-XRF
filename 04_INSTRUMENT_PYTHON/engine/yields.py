"""Fluorescence yields: the radiative / Auger competition (Law 1345).

HONESTY
-------
``omega_k(z)`` / ``omega_l(z, subshell)``
    **[REFERENCE]**.  Krause & Oliver, J. Phys. Chem. Ref. Data 8 (1979) 329,
    as tabulated in the Elam/xraydb tables shipped in ``data/elements.json``.
    These are the values the instrument uses.

``omega_k_powerlaw(z)``
    **[MODEL]**.  The standard single-parameter form

        omega_K = Z^4 / (A + Z^4)

    with ``A`` fitted to the four anchor values below (A = 8.55e5).  It is a
    one-number compression of a four-point anchor set, useful for order-of-
    magnitude work and for showing *why* the table is needed: the Z^4 scaling
    is wrong below Z ~ 15.

``auger_yield``
    **[DERIVED, EXACT]**.  Law 1345 / 1347: ``omega + Auger = 1``.  This is an
    identity, not a measurement; it holds to machine precision by construction.

Anchors and their literature spread
-----------------------------------
Cu 0.44, Mo 0.76 and Al 0.035 agree with the table to 0.3 %, 2.3 % and 5.7 %.
Fe is the interesting one: the requested anchor is 0.32, while Krause & Oliver
tabulate 0.351 (+9.7 %).  Published Fe K yields span 0.32-0.35 depending on the
compilation (Bambynek 1972 vs Krause & Oliver 1979).  The engine reports the
deviation instead of tuning the table to the anchor.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import elements as _elements

#: Fitted to the four anchor values (Al, Fe, Cu, Mo) by least squares in log
#: space.  See module docstring; it is a [MODEL], not a measurement.
POWERLAW_A = 8.550667e5


def _table_omega(z: int, subshell: str) -> float:
    el = _elements.element(z)
    return el.omega(subshell)


def omega_k(z: int) -> float:
    """**[REFERENCE]** K-shell fluorescence yield (Krause & Oliver 1979)."""
    return _table_omega(z, "K")


def omega_l(z: int, subshell: str = "L3") -> float:
    """**[REFERENCE]** L-subshell fluorescence yield, ``subshell`` in L1/L2/L3."""
    s = subshell.upper()
    if s not in ("L1", "L2", "L3"):
        raise ValueError("subshell must be L1, L2 or L3")
    return _table_omega(z, s)


def omega_l_mean(z: int) -> float:
    """**[REFERENCE-DERIVED]** L-shell yield averaged over the 2:2:4 occupancy."""
    return (2 * omega_l(z, "L1") + 2 * omega_l(z, "L2") + 4 * omega_l(z, "L3")) / 8.0


def omega_m(z: int) -> float:
    """**[REFERENCE]** M5 fluorescence yield (0 where not tabulated)."""
    return _table_omega(z, "M5")


def auger_yield(z: int, shell: str = "K") -> float:
    """**[DERIVED]** 1 - omega.  Law 1345: the two channels exhaust the vacancies."""
    shell = shell.upper()
    if shell == "K":
        w = omega_k(z)
    elif shell in ("L", "L1", "L2", "L3"):
        w = omega_l_mean(z) if shell == "L" else omega_l(z, shell)
    elif shell.startswith("M"):
        w = omega_m(z)
    else:
        raise ValueError(f"unknown shell {shell}")
    return 1.0 - w


def omega_k_powerlaw(z: int, a: float = POWERLAW_A) -> float:
    """**[MODEL]** omega_K = Z^4 / (A + Z^4), A fitted to the four anchors."""
    z4 = float(z) ** 4
    return z4 / (a + z4)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
ANCHORS: Dict[int, float] = {13: 0.035, 26: 0.32, 29: 0.44, 42: 0.76}
ANCHOR_NOTE = {
    13: "Al, K shell",
    26: "Fe, K shell (literature spread 0.32-0.35)",
    29: "Cu, K shell",
    42: "Mo, K shell",
}


def validate_yields(verbose: bool = False) -> List[dict]:
    """Compare the table and the power-law model against the anchor values."""
    rows = []
    for z, anchor in ANCHORS.items():
        el = _elements.element(z)
        tab = omega_k(z)
        mod = omega_k_powerlaw(z)
        row = {
            "element": el.symbol,
            "anchor": anchor,
            "table": tab,
            "table_dev_pct": 100.0 * (tab - anchor) / anchor,
            "model": mod,
            "model_dev_pct": 100.0 * (mod - anchor) / anchor,
            "note": ANCHOR_NOTE[z],
        }
        rows.append(row)
        if verbose:
            print(
                f"{el.symbol:>2} K  anchor {anchor:5.3f} | table {tab:6.4f} "
                f"({row['table_dev_pct']:+6.2f} %) | model {mod:6.4f} "
                f"({row['model_dev_pct']:+6.2f} %)"
            )
    return rows


def validate_table_vs_model() -> dict:
    """Error of the power-law model against the full Krause & Oliver table."""
    errs = []
    for el in _elements.ELEMENTS:
        w = el.omega("K")
        if w <= 0 or el.z < 6:
            continue
        errs.append(100.0 * (omega_k_powerlaw(el.z) - w) / w)
    errs.sort(key=abs)
    return {
        "n": len(errs),
        "median_abs_pct": abs(errs[len(errs) // 2]),
        "p95_abs_pct": abs(errs[int(0.95 * (len(errs) - 1))]),
        "max_abs_pct": abs(errs[-1]),
    }


def self_check() -> list[str]:
    problems = []
    for el in _elements.ELEMENTS:
        w = el.omega("K")
        if not (0.0 <= w <= 1.0):
            problems.append(f"Z={el.z} omega_K={w} outside [0,1]")
        if el.z >= 30 and w < 0.05:
            problems.append(f"Z={el.z} omega_K unexpectedly small ({w})")
    return problems


if __name__ == "__main__":  # pragma: no cover
    validate_yields(verbose=True)
    print("power law vs table:", validate_table_vs_model())
    print("self_check:", self_check() or "clean")
