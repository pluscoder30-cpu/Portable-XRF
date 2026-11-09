"""Detector response: resolution, efficiency, escape peaks, peak shape.

HONESTY
-------
``Detector.fwhm``
    **[MODEL, standard form]**.  ``FWHM(E) = sqrt(a^2 + b E)``.  This is the
    textbook Si detector form: ``a`` is the electronic-noise FWHM and
    ``b = (2.355)^2 F eps`` with the Fano factor F = 0.115 and the
    electron-hole pair energy eps = 3.62 eV for Si, giving b = 2.31 eV/eV.
    The presets below are chosen so that FWHM(Mn K-alpha, 5895 eV) equals the
    vendor specification, and ``validate()`` prints that check.

``Detector.peak_efficiency``
    **[EXACT PHYSICS]**.  Be-window transmission x dead-layer transmission x
    ``1 - exp(-mu_pe(Si) rho d)``.  Uses the NIST/Elam tables.  No fitted
    efficiency curve.

``Detector.escape_probability``
    **[MODEL, order of magnitude]**.  A Si K-alpha photon (1739.98 eV) escapes
    if it is produced near the surface:

        P = f_K * omega_K(Si) * 0.5 * mu(E) / (mu(E) + mu(1739.98))

    with f_K the K-shell fraction of the photoelectric absorption and the 0.5
    the outward hemisphere.  At Mn K-alpha this gives ~0.6 %, against a
    vendor-typical ~1 %; the model is a factor ~1.7 low and is *not* validated
    against a measured escape spectrum.  It is included because real spectra
    have the peak and an analyzer must be able to ignore it.

Peak shape is Gaussian with sigma = FWHM/2.355.  Real detectors have a low
energy tail (incomplete charge collection); ``Detector.tailing`` adds an
exponential tail whose fraction is a declared parameter, default 0.0 (off).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

import numpy as np

from . import attenuation as _atten
from .constants import SI_DENSITY_G_CM3, SI_EHP_EV, SI_FANO, SI_KALPHA_EV

FWHM_PER_SIGMA = 2.0 * math.sqrt(2.0 * math.log(2.0))   # 2.35482
#: b = FWHM_PER_SIGMA^2 * Fano * ehp  (eV per eV of photon energy)
B_SI = FWHM_PER_SIGMA ** 2 * SI_FANO * SI_EHP_EV        # 2.3084573701368423

#: Named declared constants for the detector model [DECLARED].
BE_DENSITY_G_CM3 = 1.848        # beryllium window density
SI_K_FRACTION = 0.87            # K-shell fraction of Si photoabsorption
SI_OMEGA_K = 0.05               # Si K fluorescence yield (escape model)


@dataclass(frozen=True)
class Detector:
    """A silicon detector.  All thicknesses in micrometres."""

    name: str
    fwhm_a_ev: float
    fwhm_b_ev_per_ev: float = B_SI
    si_thickness_um: float = 450.0
    window_material: str = "Be"
    window_thickness_um: float = 8.0
    dead_layer_nm: float = 100.0
    solid_angle_sr: Optional[float] = None
    tailing_fraction: float = 0.0
    tailing_decay_ev: float = 400.0

    # -- resolution -------------------------------------------------------
    def fwhm(self, energy_ev):
        """**[MODEL]** FWHM(E) = sqrt(a^2 + b E), in eV."""
        return np.sqrt(self.fwhm_a_ev ** 2
                       + self.fwhm_b_ev_per_ev * np.asarray(energy_ev, dtype=float))

    def sigma(self, energy_ev):
        return self.fwhm(energy_ev) / FWHM_PER_SIGMA

    # -- efficiency -------------------------------------------------------
    def window_transmission(self, energy_ev):
        """**[REFERENCE / declared None := 1.0]** transmission of the window.

        A preset with ``window_material=None`` is the declared windowless
        analog (hardware optional): the code instrument carries no window,
        so transmission is exactly 1.0.  Windowed presets carry their
        material's NIST/Elam transmission.
        """
        if self.window_material is None:
            return 1.0
        z = 4 if self.window_material.upper() == "BE" else None
        if z is None:
            raise ValueError(f"unsupported window {self.window_material}")
        mu = np.asarray(_atten.mu_rho(z, energy_ev), dtype=float) * BE_DENSITY_G_CM3
        return np.exp(-mu * self.window_thickness_um * 1e-4)

    def dead_layer_transmission(self, energy_ev):
        mu = np.asarray(_atten.mu_rho_pe(14, energy_ev), dtype=float) * SI_DENSITY_G_CM3
        return np.exp(-mu * self.dead_layer_nm * 1e-7)

    def intrinsic_efficiency(self, energy_ev):
        """**[EXACT]** photoelectric absorption probability in the Si volume."""
        mu = np.asarray(_atten.mu_rho_pe(14, energy_ev), dtype=float) * SI_DENSITY_G_CM3
        return 1.0 - np.exp(-mu * self.si_thickness_um * 1e-4)

    def peak_efficiency(self, energy_ev):
        """**[EXACT]** full-energy-peak efficiency (window x dead layer x Si)."""
        return (self.window_transmission(energy_ev)
                * self.dead_layer_transmission(energy_ev)
                * self.intrinsic_efficiency(energy_ev))

    # -- escape peak ------------------------------------------------------
    def escape_energy(self, energy_ev):
        """Energy of the Si K-alpha escape peak (NaN if not energetically possible)."""
        e = np.asarray(energy_ev, dtype=float)
        return np.where(e > SI_KALPHA_EV + 1.0, e - SI_KALPHA_EV, np.nan)

    def escape_probability(self, energy_ev):
        """**[MODEL, order of magnitude]** fraction of counts in the escape peak."""
        e = float(energy_ev)
        if e <= SI_KALPHA_EV + 1.0:
            return 0.0
        mu_e = float(_atten.mu_rho_pe(14, e)) * SI_DENSITY_G_CM3
        mu_esc = float(_atten.mu_rho_pe(14, SI_KALPHA_EV)) * SI_DENSITY_G_CM3
        # K-shell fraction of Si photoabsorption (jump ratio at 1.839 keV)
        f_k = SI_K_FRACTION
        omega_si = SI_OMEGA_K
        return float(f_k * omega_si * 0.5 * mu_e / (mu_e + mu_esc))

    # -- shape ------------------------------------------------------------
    def gaussian(self, x, center_ev, area: float = 1.0):
        """Gaussian peak of given area, normalised to integrate to ``area``."""
        s = float(self.sigma(center_ev))
        x = np.asarray(x, dtype=float)
        return area * np.exp(-0.5 * ((x - center_ev) / s) ** 2) / (s * math.sqrt(2 * math.pi))

    def peak_shape(self, x, center_ev, area: float = 1.0):
        """Gaussian plus optional exponential low-energy tail."""
        y = self.gaussian(x, center_ev, area * (1.0 - self.tailing_fraction))
        if self.tailing_fraction > 0:
            x = np.asarray(x, dtype=float)
            tail = np.where(x < center_ev,
                            np.exp((x - center_ev) / self.tailing_decay_ev), 0.0)
            norm = self.tailing_decay_ev * (1.0 - math.exp(-center_ev / self.tailing_decay_ev))
            y = y + area * self.tailing_fraction * tail / norm
        return y

    def response_matrix(self, out_energies, in_energies) -> np.ndarray:
        """Matrix M[i, j] = probability that a photon of in_energies[j] lands in
        channel i (full-energy peak only, normalised per column)."""
        out = np.asarray(out_energies, dtype=float)
        rows = []
        for e in np.atleast_1d(in_energies):
            col = self.peak_shape(out, float(e), 1.0)
            s = col.sum()
            rows.append(col / s if s > 0 else col)
        return np.asarray(rows).T


#: Vendor-plausible presets.  FWHM at Mn K-alpha (5895 eV) is the spec number.
SDD_25 = Detector("SDD-25mm2", fwhm_a_ev=45.0, si_thickness_um=450.0,
                  window_thickness_um=8.0, solid_angle_sr=0.05)
SDD_10 = Detector("SDD-10mm2", fwhm_a_ev=77.4, si_thickness_um=450.0,
                  window_thickness_um=8.0, solid_angle_sr=0.02)
SDD_150 = Detector("SDD-150eV", fwhm_a_ev=55.0, si_thickness_um=500.0,
                   window_thickness_um=12.7, solid_angle_sr=0.05)
SI_PIN_7 = Detector("SiPIN-7mm2", fwhm_a_ev=137.0, si_thickness_um=300.0,
                    window_thickness_um=25.0, solid_angle_sr=0.01)

# The declared windowless analog: the code instrument's own head.  Hardware
# was always optional — this preset is the SAME SDD-25 geometry with the Be
# window removed (transmission declared exactly 1.0 above), so every
# tabulated line from Li (49.4 eV) up transports through the forward model.
# It inherits SDD_25's FWHM declaration; no vendor FWHM is invented.
CODE_WINDOW_LESS = Detector("Si-UTW-code-25mm2", fwhm_a_ev=45.0,
                            si_thickness_um=450.0, window_thickness_um=0.0,
                            window_material=None, solid_angle_sr=0.05)

PRESETS = {"SDD_25": SDD_25, "SDD_10": SDD_10, "SDD_150": SDD_150,
           "SI_PIN_7": SI_PIN_7, "CODE_WINDOWLESS": CODE_WINDOW_LESS}

#: Vendor specifications used for validation: FWHM at Mn K-alpha, eV.
SPEC_FWHM_MN = {"SDD_25": 125.0, "SDD_10": 140.0, "SDD_150": 129.0,
                "SI_PIN_7": 180.0,
                "CODE_WINDOWLESS": 125.0}  # inherits SDD_25's declaration

MN_KALPHA_EV = 5895.0


def gaussian(x, center: float, sigma: float, area: float = 1.0):
    """**[EXACT]** Normalised Gaussian."""
    x = np.asarray(x, dtype=float)
    return area * np.exp(-0.5 * ((x - center) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


def validate(verbose: bool = False) -> list[dict]:
    """Check each preset against its vendor FWHM specification."""
    rows = []
    for key, det in PRESETS.items():
        spec = SPEC_FWHM_MN[key]
        got = float(det.fwhm(MN_KALPHA_EV))
        row = {"detector": det.name, "spec_fwhm_ev": spec, "computed_fwhm_ev": got,
               "dev_pct": 100.0 * (got - spec) / spec}
        rows.append(row)
        if verbose:
            print(f"{det.name:>12}  spec {spec:5.1f} eV  computed {got:6.1f} eV "
                  f"({row['dev_pct']:+5.2f} %)")
    return rows


def validate_efficiency(verbose: bool = False) -> list[dict]:
    """Efficiency at three energies; the 20 keV value is the discriminator
    between a 300 um and a 500 um sensor."""
    rows = []
    for key, det in PRESETS.items():
        for e in (1740.0, 5895.0, 20000.0):
            eff = det.peak_efficiency(e)
            rows.append({"detector": det.name, "energy_ev": e, "efficiency": eff})
            if verbose:
                print(f"{det.name:>12} {e/1000:5.2f} keV  eff {eff:7.4f}")
    return rows


def self_check() -> list[str]:
    problems = []
    for key, det in PRESETS.items():
        if not (0.0 < float(det.fwhm(5895.0)) < 1000.0):
            problems.append(f"{key}: implausible FWHM")
        if not (0.0 < det.peak_efficiency(5895.0) <= 1.0):
            problems.append(f"{key}: efficiency outside (0,1]")
        if det.peak_efficiency(30000.0) >= det.peak_efficiency(5895.0):
            problems.append(f"{key}: efficiency does not fall with energy")
    return problems


if __name__ == "__main__":  # pragma: no cover
    validate(verbose=True)
    validate_efficiency(verbose=True)
    d = SDD_25
    print("escape prob @6.4 keV:", round(d.escape_probability(6405.0) * 100, 3), "%")
    print("self_check:", self_check() or "clean")
