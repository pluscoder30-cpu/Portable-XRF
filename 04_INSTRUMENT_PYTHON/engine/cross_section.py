"""Photoelectric and scattering cross-sections.

HONESTY
-------
``photoionization(z, E)`` / ``coherent(z, E)`` / ``incoherent(z, E)``
    **[REFERENCE]**.  Mass cross-sections in cm^2/g from the Elam/NIST tables
    (via ``attenuation.py``).  These are what the forward model uses.

``sigma_pe_powerlaw(z, E)``
    **[MODEL]**.  The classical photoelectric law

        sigma_pe = C * Z^4 / A * E^-3 * prod(1/J_edge for edges above E)

    with ``C`` calibrated at ONE point (Fe, 10 keV, from the table) and the
    edge jumps J from the tabulated jump ratios.  It exists to show the E^-3
    and Z^4 scalings and to give a physically-sensible value outside the
    tabulated range.  Its measured error against the table is reported by
    ``validate_powerlaw()`` -- it is tens of percent, which is why the
    instrument uses the table.

``klein_nishina_total(E)``
    **[EXACT]**.  The Klein-Nishina formula for Compton scattering from a free
    electron, evaluated in closed form (with a series expansion below
    E/m_e c^2 = 1e-4 to avoid catastrophic cancellation).
    ``incoherent_kn(z, E)`` = Z * sigma_KN converted to cm^2/g.

    This is exact for a *free* electron.  Real atoms suppress Compton
    scattering at low energy because most electrons are bound: measured
    against the Elam table the free-electron value overestimates by a median
    49 % over 10-30 keV, falling with energy (Pb: +236 % at 10 keV, +73 % at
    30 keV) and converging to the table above ~100 keV.  That is real physics,
    not a bug in the formula -- and it is why the forward model uses the table.

``compton_wavelength_shift(E, theta)``
    **[EXACT]**.  Law 076: Delta-lambda = (h/m_e c)(1 - cos theta).

Law 1346 (sharp threshold) is implemented as a hard step at the edge: the
photoelectric cross-section of a shell is exactly zero below its binding
energy.  The corpus's own verdict: "Photoionization is exactly zero below the
ionization threshold for all couplings."
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Tuple

import numpy as np

from . import attenuation as _atten
from . import elements as _elements
from .constants import (
    AVOGADRO,
    CLASSICAL_ELECTRON_RADIUS_CM,
    ELECTRON_MASS_KG,
    PLANCK_J_S,
    SPEED_OF_LIGHT_CM_S,
)

#: Electron rest energy in eV.
M_E_C2_EV = 510998.95


# ---------------------------------------------------------------------------
# Reference cross-sections
# ---------------------------------------------------------------------------
def photoionization(z: int, energy_ev) -> float:
    """**[REFERENCE]** photoelectric mass cross-section, cm^2/g."""
    return _atten.mu_rho_pe(z, energy_ev)


def coherent(z: int, energy_ev) -> float:
    """**[REFERENCE]** coherent (Rayleigh) mass cross-section, cm^2/g."""
    return _atten.mu_rho_coherent(z, energy_ev)


def incoherent(z: int, energy_ev) -> float:
    """**[REFERENCE]** incoherent (Compton) mass cross-section, cm^2/g."""
    return _atten.mu_rho_incoherent(z, energy_ev)


def total(z: int, energy_ev) -> float:
    """**[REFERENCE]** total mass attenuation coefficient, cm^2/g."""
    return _atten.mu_rho(z, energy_ev, "total")


# ---------------------------------------------------------------------------
# Photoelectric power law  [MODEL]
# ---------------------------------------------------------------------------
#: Edges used for the jump bookkeeping (the ones that carry real oscillator
#: strength).  Deeper subshells are folded into the edge they belong to.
_JUMP_EDGES = ("K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5")


@lru_cache(maxsize=None)
def _jump_edges(z: int) -> Tuple[Tuple[float, float], ...]:
    el = _elements.element(z)
    out = []
    for name in _JUMP_EDGES:
        e = el.edge(name)
        if e > 0:
            j = el.jump(name)
            if j > 1.0:
                out.append((e, j))
    return tuple(out)


def edge_jump_factor(z: int, energy_ev: float) -> float:
    """Product of 1/J over every edge above ``energy_ev`` (sharp thresholds)."""
    f = 1.0
    for e, j in _jump_edges(z):
        if e > energy_ev:
            f /= j
    return f


@lru_cache(maxsize=1)
def _powerlaw_constant() -> float:
    """Calibrate C at one point: Fe (Z=26), 10 keV, above the K edge."""
    el = _elements.element("Fe")
    e_kev = 10.0
    sigma = float(photoionization(el.z, e_kev * 1000.0))
    return sigma * el.mass / (el.z ** 4 * e_kev ** -3.0)


def sigma_pe_powerlaw(z: int, energy_ev: float) -> float:
    """**[MODEL]** sigma_pe = C Z^4/A E^-3 x edge jumps, in cm^2/g."""
    el = _elements.element(z)
    e_kev = energy_ev / 1000.0
    return (_powerlaw_constant() * el.z ** 4 / el.mass
            * e_kev ** -3.0 * edge_jump_factor(el.z, energy_ev))


def k_shell_fraction(z: int, energy_ev: float) -> float:
    """Fraction of photoelectric absorption that ionises the K shell.

    Above E_K this is (J_K - 1)/J_K, the standard jump-ratio result.  Below
    E_K it is exactly 0 (Law 1346: sharp threshold).
    """
    el = _elements.element(z)
    ek = el.edge("K")
    if ek <= 0 or energy_ev < ek:
        return 0.0
    j = el.jump("K")
    return (j - 1.0) / j if j > 1.0 else 0.0


# ---------------------------------------------------------------------------
# Klein-Nishina  [EXACT]
# ---------------------------------------------------------------------------
def klein_nishina_total(energy_ev: float) -> float:
    """**[EXACT]** Total Klein-Nishina cross-section per electron, cm^2.

    sigma = 2 pi r_e^2 { (1+g)/g^2 [ 2(1+g)/(1+2g) - ln(1+2g)/g ]
                         + ln(1+2g)/(2g) - (1+3g)/(1+2g)^2 },  g = E/m_e c^2
    """
    g = energy_ev / M_E_C2_EV
    if g <= 0:
        raise ValueError("energy must be positive")
    if g < 1e-4:
        # Series expansion; the closed form suffers catastrophic cancellation
        # at small g (the 1/g^2 terms cancel to 1 part in 1e12).
        s_t = 8.0 * np.pi / 3.0 * CLASSICAL_ELECTRON_RADIUS_CM ** 2
        return float(s_t * (1.0 - 2.0 * g + 5.2 * g * g))
    ln = np.log(1.0 + 2.0 * g)
    term = ((1.0 + g) / g ** 2) * (2.0 * (1.0 + g) / (1.0 + 2.0 * g) - ln / g)
    term += ln / (2.0 * g) - (1.0 + 3.0 * g) / (1.0 + 2.0 * g) ** 2
    return float(2.0 * np.pi * CLASSICAL_ELECTRON_RADIUS_CM ** 2 * term)


def thomson_total() -> float:
    """**[EXACT]** Thomson cross-section, cm^2 (low-energy limit of KN)."""
    return float(8.0 * np.pi / 3.0 * CLASSICAL_ELECTRON_RADIUS_CM ** 2)


def incoherent_kn(z: int, energy_ev: float) -> float:
    """**[EXACT per free electron]** Z * sigma_KN, converted to cm^2/g."""
    el = _elements.element(z)
    sigma_atom = el.z * klein_nishina_total(energy_ev)
    return sigma_atom * AVOGADRO / el.mass


def coherent_thomson(z: int) -> float:
    """**[EXACT upper bound]** Z^2 * sigma_T in cm^2/g (no form factor)."""
    el = _elements.element(z)
    return el.z ** 2 * thomson_total() * AVOGADRO / el.mass


def compton_wavelength_shift(energy_ev: float, theta_rad: float) -> float:
    """**[EXACT]** Law 076: Delta-lambda in Angstrom for scattering angle theta."""
    c_m_s = SPEED_OF_LIGHT_CM_S / 100.0
    h_over_mc_m = PLANCK_J_S / (ELECTRON_MASS_KG * c_m_s)
    d_lambda_m = h_over_mc_m * (1.0 - np.cos(theta_rad))
    return float(d_lambda_m * 1e10)          # m -> Angstrom


def compton_scattered_energy(energy_ev: float, theta_rad: float) -> float:
    """**[EXACT]** E' = E / (1 + (E/m_e c^2)(1 - cos theta))."""
    return float(energy_ev / (1.0 + energy_ev / M_E_C2_EV * (1.0 - np.cos(theta_rad))))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_powerlaw(verbose: bool = False) -> dict:
    """Error of the E^-3 / Z^4 model against the Elam table."""
    errs = []
    worst = None
    for z in (6, 8, 13, 14, 20, 22, 26, 29, 30, 42, 47, 50, 82):
        for e_kev in (2.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0):
            e = e_kev * 1000.0
            el = _elements.element(z)
            if el.edge("K") == 0 or e < 1.2 * el.edge("K"):
                continue
            ref = float(photoionization(z, e))
            mod = sigma_pe_powerlaw(z, e)
            err = 100.0 * (mod - ref) / ref
            errs.append(err)
            if worst is None or abs(err) > abs(worst[0]):
                worst = (err, el.symbol, e_kev)
            if verbose:
                print(f"{el.symbol:>2} {e_kev:5.1f} keV  table {ref:10.4f}  "
                      f"model {mod:10.4f}  ({err:+7.1f} %)")
    a = sorted(abs(x) for x in errs)
    return {
        "n": len(a),
        "median_abs_pct": a[len(a) // 2],
        "max_abs_pct": a[-1],
        "worst": worst,
        "constant_C": _powerlaw_constant(),
    }


def validate_klein_nishina() -> dict:
    """KN must reproduce the Thomson limit and the tabulated Compton slope."""
    low = klein_nishina_total(1.0)          # 1 eV: deep in the Thomson limit
    rows = []
    for z in (6, 13, 26, 42, 82):
        for e_kev in (10.0, 20.0, 30.0):
            ref = float(incoherent(z, e_kev * 1000.0))
            mod = incoherent_kn(z, e_kev * 1000.0)
            rows.append({"z": z, "e_kev": e_kev, "table": ref, "kn": mod,
                         "dev_pct": 100.0 * (mod - ref) / ref})
    devs = sorted(abs(r["dev_pct"]) for r in rows)
    return {
        "thomson_limit_cm2": thomson_total(),
        "kn_at_1ev_cm2": low,
        "thomson_ratio": low / thomson_total(),
        "compton_dev_median_pct": devs[len(devs) // 2],
        "compton_dev_max_pct": devs[-1],
        "rows": rows,
    }


def validate_thresholds() -> dict:
    """Law 1346: the K-shell channel is exactly zero below E_K and jumps at E_K."""
    bad = []
    tested = 0
    for z in (13, 26, 42, 82):
        el = _elements.element(z)
        for name in ("K", "L1", "L2", "L3"):
            e = el.edge(name)
            if not (500.0 <= e <= 40000.0):
                continue
            tested += 1
            if name == "K":
                below = k_shell_fraction(z, e * 0.999)
                above = k_shell_fraction(z, e * 1.001)
                if below != 0.0 or above <= 0.0:
                    bad.append((el.symbol, name, below, above))
            # the tabulated total must jump upward across every edge in range
            lo = float(photoionization(z, e * 0.999))
            hi = float(photoionization(z, e * 1.001))
            if not hi > lo:
                bad.append((el.symbol, name, lo, hi))
    return {"edges_tested": tested, "violations": bad}


def self_check() -> list[str]:
    problems = []
    for z in (6, 26, 82):
        if klein_nishina_total(1e4) <= 0:
            problems.append(f"KN non-positive at Z={z}")
    if abs(klein_nishina_total(1.0) / thomson_total() - 1.0) > 1e-5:
        problems.append("KN does not reproduce the Thomson limit")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print(validate_powerlaw(verbose=False))
    kn = validate_klein_nishina()
    print({k: v for k, v in kn.items() if k != "rows"})
    print(validate_thresholds())
    print("self_check:", self_check() or "clean")
