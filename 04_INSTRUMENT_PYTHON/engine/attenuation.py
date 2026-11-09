"""Beer-Lambert transport: mass attenuation, linear attenuation, transmission.

HONESTY
-------
``mu_rho()`` and friends
    **[REFERENCE]**.  Mass attenuation coefficients in cm^2/g, tabulated from
    Elam, Ravel & Sieber (2002) -- the parameterisation of the NIST XCOM data --
    on a 1-40 keV grid that is bracketed on both sides of every absorption
    edge of every element (see ``tools/build_reference_data.py``).  Between
    grid points the interpolation is log-log, which is exact for a pure power
    law and accurate to << 0.1 % for the real curves.

``mu_rho_mixture()``
    **[EXACT MIXING RULE]**.  Bragg additivity: ``mu/rho = sum_i w_i (mu/rho)_i``.
    This is exact for a homogeneous mixture at the 0.1 % level; it is the
    standard rule and is what NIST itself uses to build mixture tables.

``transmission()`` / ``beer_lambert()``
    **[EXACT]**.  ``T = exp(-mu x)``.  Law 141, verified classical by the
    corpus ("Absorption measured exactly exponential with no coherence term").

Range of validity
-----------------
0.5 keV <= E <= 40 keV (the Elam range).  Outside that window the code
extrapolates with the local log-log slope and the caller should treat the
result as an extrapolation.  Energies are in eV throughout; lengths in cm;
``mu`` in 1/cm; ``mu/rho`` in cm^2/g.

The one approximation that is *not* exact: below ~2 keV the photoelectric
cross-section depends on chemical state near an edge (XANES/EXAFS), which no
tabular model captures.  The table is the atomic cross-section.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Union

import numpy as np

from . import elements as _elements

_DATA = Path(__file__).with_name("data") / "mu_rho.npz"

Number = Union[float, np.ndarray]
KINDS = ("total", "photo", "coherent", "incoherent")


@lru_cache(maxsize=1)
def _tables() -> dict:
    with np.load(_DATA) as z:
        return {
            "energy": z["energy_ev"].astype(np.float64),
            "total": z["mu_rho"],
            "photo": z["mu_rho_pe"],
            "coherent": z["mu_rho_coh"],
            "incoherent": z["mu_rho_inc"],
        }


def energy_range() -> tuple[float, float]:
    g = _tables()["energy"]
    return float(g[0]), float(g[-1])


def _interp_loglog(e: Number, x: np.ndarray, y: np.ndarray) -> Number:
    """Log-log interpolation with power-law extrapolation at both ends."""
    scalar = np.isscalar(e)
    ev = np.atleast_1d(np.asarray(e, dtype=float))
    if np.any(ev <= 0):
        raise ValueError("energy must be positive")
    lnx, lny = np.log(x), np.log(y)
    lne = np.log(ev)
    out = np.interp(lne, lnx, lny)
    lo = lne < lnx[0]
    hi = lne > lnx[-1]
    if np.any(lo):
        s = (lny[1] - lny[0]) / (lnx[1] - lnx[0])
        out[lo] = lny[0] + s * (lne[lo] - lnx[0])
    if np.any(hi):
        s = (lny[-1] - lny[-2]) / (lnx[-1] - lnx[-2])
        out[hi] = lny[-1] + s * (lne[hi] - lnx[-1])
    res = np.exp(out)
    return float(res[0]) if scalar else res


def mu_rho(z: int, energy_ev: Number, kind: str = "total") -> Number:
    """**[REFERENCE]** Mass attenuation coefficient in cm^2/g.

    ``kind``: ``total`` | ``photo`` | ``coherent`` | ``incoherent``.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    t = _tables()
    zz = _elements.element(z).z
    return _interp_loglog(energy_ev, t["energy"], t[kind][zz].astype(np.float64))


def mu_rho_pe(z: int, energy_ev: Number) -> Number:
    return mu_rho(z, energy_ev, "photo")


def mu_rho_coherent(z: int, energy_ev: Number) -> Number:
    return mu_rho(z, energy_ev, "coherent")


def mu_rho_incoherent(z: int, energy_ev: Number) -> Number:
    return mu_rho(z, energy_ev, "incoherent")


def _normalise(composition: Mapping) -> Dict[int, float]:
    """Accept {symbol|Z: mass fraction} or a sequence of (element, fraction)."""
    items = composition.items() if isinstance(composition, Mapping) else composition
    out: Dict[int, float] = {}
    for k, v in items:
        z = _elements.element(k).z
        out[z] = out.get(z, 0.0) + float(v)
    total = sum(out.values())
    if total <= 0:
        raise ValueError("composition sums to zero")
    return {z: v / total for z, v in out.items()}


def mu_rho_mixture(composition: Mapping, energy_ev: Number, kind: str = "total") -> Number:
    """**[EXACT MIXING RULE]** Bragg additivity over mass fractions."""
    w = _normalise(composition)
    total = None
    for z, frac in w.items():
        term = frac * np.asarray(mu_rho(z, energy_ev, kind), dtype=float)
        total = term if total is None else total + term
    return float(total) if np.isscalar(energy_ev) else total


def mu_linear(composition: Mapping, density_g_cm3: float, energy_ev: Number,
              kind: str = "total") -> Number:
    """Linear attenuation coefficient mu = (mu/rho) * rho, in 1/cm."""
    return mu_rho_mixture(composition, energy_ev, kind) * float(density_g_cm3)


def transmission(mu_linear_per_cm: Number, thickness_cm: float) -> Number:
    """**[EXACT]** T = exp(-mu x).  Law 141."""
    return np.exp(-np.asarray(mu_linear_per_cm, dtype=float) * float(thickness_cm))


def beer_lambert(i0: Number, composition: Mapping, density_g_cm3: float,
                 thickness_cm: float, energy_ev: Number) -> Number:
    """**[EXACT]** I = I0 exp(-(mu/rho) rho x)."""
    mu = mu_linear(composition, density_g_cm3, energy_ev)
    return np.asarray(i0, dtype=float) * transmission(mu, thickness_cm)


def half_value_layer(composition: Mapping, density_g_cm3: float,
                     energy_ev: float) -> float:
    """Thickness (cm) at which the beam is halved: ln2 / mu."""
    mu = mu_linear(composition, density_g_cm3, energy_ev)
    return float(np.log(2.0) / mu)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
#: NIST X-Ray Mass Attenuation Coefficients, dry air near sea level,
#: table 4 (ComTab/air.html).  Independent of the Elam tables used above.
NIST_AIR_MU_RHO = {
    5000.0: 40.27,
    6000.0: 23.41,
    8000.0: 9.921,
    10000.0: 5.120,
    15000.0: 1.614,
    20000.0: 0.7779,
    30000.0: 0.3538,
}


def validate_nist_air(verbose: bool = False) -> list[dict]:
    """Compare the computed dry-air mixture to the NIST table."""
    from .air import AIR_COMPOSITION

    rows = []
    for e, ref in sorted(NIST_AIR_MU_RHO.items()):
        got = mu_rho_mixture(AIR_COMPOSITION, e)
        rows.append({
            "energy_ev": e,
            "nist": ref,
            "computed": got,
            "dev_pct": 100.0 * (got - ref) / ref,
        })
        if verbose:
            print(f"{e/1000:5.1f} keV  NIST {ref:8.4f}  computed {got:8.4f} "
                  f"({rows[-1]['dev_pct']:+6.2f} %)")
    return rows


def validate_beer_lambert(verbose: bool = False) -> dict:
    """Closed-form checks of the exponential law (Law 141)."""
    mu = 0.5  # 1/cm
    x = 2.0   # cm
    t = transmission(mu, x)
    expected = np.exp(-1.0)
    # additivity: two half-thicknesses compose to one full thickness
    t2 = transmission(mu, x / 2) ** 2
    rows = {
        "T(0.5/cm, 2cm)": float(t),
        "exp(-1)": float(expected),
        "abs_err": abs(float(t) - float(expected)),
        "composition_error": abs(float(t) - float(t2)),
        "half_value_layer_cm": half_value_layer({"Fe": 1.0}, 7.874, 6405.0),
    }
    if verbose:
        print(rows)
    return rows


def self_check() -> list[str]:
    problems = []
    t = _tables()
    if np.any(t["energy"][1:] <= t["energy"][:-1]):
        problems.append("attenuation grid is not strictly increasing")
    for kind in KINDS:
        arr = t[kind]
        if np.any(arr[1:] < 0):
            problems.append(f"negative {kind} coefficient")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("range eV:", energy_range())
    validate_nist_air(verbose=True)
    print(validate_beer_lambert(verbose=True))
