"""The forward operator: composition -> expected counts per channel.

HONESTY
-------
What is exact
    * photoelectric absorption probability ``(mu/rho) * m`` (Bragg additivity),
    * the sharp edge thresholds (Law 1346),
    * the fluorescence/Auger competition ``omega`` (Law 1345),
    * the branching ratios (Law 1347),
    * Beer-Lambert transport through air, window and matrix (Law 141),
    * detector efficiency (photoelectric absorption in Si).

What is a model
    * ``Excitation.tube`` -- Kramers continuum + characteristic anode lines.
      The *shape* is the standard Kramers law; the absolute flux is a declared
      parameter, not a measurement of any particular tube.
    * the subshell partition of L/M vacancies (by degeneracy, 2:2:4),
    * ``Background`` -- a two-parameter continuum (exponential + flat),
    * the self-absorption geometry factor (uniform source, mean path).

The thin-sample approximation
    The excitation beam is assumed not to be attenuated *within* the sample.
    For an aerosol filter (10-100 ug/cm^2) the correction is < 1 %; for a
    pressed pellet it is not, and the caller should use a thicker model.
    ``forward_spectrum`` reports the sample's total areal density so the user
    can see when the assumption is being stretched.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import air as _air
from . import attenuation as _atten
from . import detector as _detector
from . import elements as _elements
from . import lines as _lines
from . import yields as _yields
from .constants import SI_KALPHA_EV

# ---------------------------------------------------------------------------
# Excitation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Excitation:
    """A photon flux at the sample plane.

    ``energy_ev`` are bin centres and ``photons_cm2_s`` is the *integrated*
    flux in each bin (photons cm^-2 s^-1), not a density per keV.
    """

    energy_ev: np.ndarray
    photons_cm2_s: np.ndarray
    label: str = ""

    def __post_init__(self):
        e = np.asarray(self.energy_ev, dtype=float)
        f = np.asarray(self.photons_cm2_s, dtype=float)
        if e.shape != f.shape:
            raise ValueError("energy and flux arrays must have the same shape")
        if np.any(f < 0):
            raise ValueError("negative flux")
        object.__setattr__(self, "energy_ev", e)
        object.__setattr__(self, "photons_cm2_s", f)

    @property
    def total_flux(self) -> float:
        return float(self.photons_cm2_s.sum())

    @property
    def max_energy(self) -> float:
        return float(self.energy_ev.max())

    def filtered(self, composition: Mapping, density_g_cm3: float,
                 thickness_cm: float) -> "Excitation":
        """Attenuate the beam through a filter (Be window, air, etc.)."""
        t = _atten.transmission(
            _atten.mu_linear(composition, density_g_cm3, self.energy_ev),
            thickness_cm,
        )
        return Excitation(self.energy_ev, self.photons_cm2_s * t,
                          f"{self.label} | filtered")

    def through_air(self, path_cm: float, t_c: float = 20.0) -> "Excitation":
        t = _air.air_transmission(self.energy_ev, path_cm, t_c)
        return Excitation(self.energy_ev, self.photons_cm2_s * t,
                          f"{self.label} | {path_cm:.1f} cm air")

    # -- constructors -----------------------------------------------------
    @classmethod
    def monoenergetic(cls, energy_ev: float, flux_cm2_s: float = 1e10) -> "Excitation":
        """A single energy bin (synchrotron / monochromator)."""
        return cls(np.array([float(energy_ev)]), np.array([float(flux_cm2_s)]),
                   f"mono {energy_ev/1000:.3f} keV")

    @classmethod
    def tube(cls, kv: float = 40.0, anode: str = "Rh", total_flux: float = 1e10,
             n_bins: int = 240, e_min_ev: float = 1000.0,
             characteristic_fraction: float = 0.25) -> "Excitation":
        """**[MODEL]** Kramers continuum + anode K lines (the declared
        tube analog; its low-energy floor is the analog's declared window).

        Photon flux per unit energy from Kramers' law:
        ``N(E) ~ Z (E0 - E) / E^2`` for 0 < E < E0``.  The absolute scale is
        set by ``total_flux``; the characteristic-line fraction is a declared
        parameter (0.25 of the total when the tube voltage is above the anode
        K edge, else 0).
        """
        el = _elements.element(anode)
        e0 = float(kv) * 1000.0
        e = np.linspace(max(e_min_ev, 200.0), e0, int(n_bins))
        shape = el.z * np.maximum(e0 - e, 0.0) / e ** 2
        shape /= shape.sum()

        frac = 0.0
        char_e = np.array([])
        char_w = np.array([])
        if e0 > el.edge("K") * 1.05 and characteristic_fraction > 0:
            frac = float(characteristic_fraction)
            ka = _lines.line(el.z, "Ka1")
            kb = _lines.line(el.z, "Kb1")
            char_e = np.array([ka.energy, kb.energy])
            char_w = np.array([ka.intensity, kb.intensity])
            char_w = char_w / char_w.sum()

        flux = (1.0 - frac) * total_flux * shape
        if frac > 0:
            # put the characteristic flux into the nearest continuum bins
            for ce, cw in zip(char_e, char_w):
                i = int(np.argmin(np.abs(e - ce)))
                flux[i] += frac * total_flux * cw
        return cls(e, flux, f"{kv:.0f} kV {el.symbol} tube")

    @classmethod
    def code(cls, kv: float = 40.0, anode: str = "Rh", total_flux: float = 1e10,
             n_bins: int = 2400, e_min_ev: float = 40.0,
             characteristic_fraction: float = 0.25) -> "Excitation":
        """**[DECLARED MODEL]** The code antenna's excitation.

        A declared FLAT continuum (equal flux per eV) over the tabulated
        data's own floor (default 40 eV — below the lowest characteristic
        line, Li Ka3 49.4 eV) up to the drive voltage, plus the anode
        characteristic lines when the drive exceeds the K edge.  No Kramers
        ``1/E^2`` divergence and no baked low-energy cutoff: the code-based
        antenna emits across the whole registered range — hardware was
        always optional, and the tube (``Excitation.tube``) remains the
        declared analog with its own transport for the classical-reference
        comparisons.
        """
        el = _elements.element(anode)
        e0 = float(kv) * 1000.0
        e = np.linspace(max(float(e_min_ev), 1.0), e0, int(n_bins))
        shape = np.ones_like(e)
        shape /= shape.sum()

        frac = 0.0
        char_e = np.array([])
        char_w = np.array([])
        if e0 > el.edge("K") * 1.05 and characteristic_fraction > 0:
            frac = float(characteristic_fraction)
            ka = _lines.line(el.z, "Ka1")
            kb = _lines.line(el.z, "Kb1")
            char_e = np.array([ka.energy, kb.energy])
            char_w = np.array([ka.intensity, kb.intensity])
            char_w = char_w / char_w.sum()

        flux = (1.0 - frac) * total_flux * shape
        if frac > 0:
            for ce, cw in zip(char_e, char_w):
                i = int(np.argmin(np.abs(e - ce)))
                flux[i] += frac * total_flux * cw
        return cls(e, flux, f"{kv:.0f} kV {el.symbol} code antenna")


# ---------------------------------------------------------------------------
# Sample / geometry
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Sample:
    """A thin sample: element areal densities in g/cm^2."""

    areal: Mapping[int, float]
    incidence_deg: float = 90.0
    takeoff_deg: float = 45.0
    label: str = ""

    def __post_init__(self):
        clean = {_elements.element(z).z: float(v)
                 for z, v in self.areal.items() if float(v) > 0}
        object.__setattr__(self, "areal", clean)

    @property
    def total_areal(self) -> float:
        return float(sum(self.areal.values()))

    @property
    def mass_fractions(self) -> Dict[int, float]:
        return _elements.areal_to_mass_fraction(self.areal)

    @classmethod
    def from_composition(cls, composition: Mapping, areal_g_cm2: float,
                         **kw) -> "Sample":
        return cls(_elements.mass_fraction_to_areal(composition, areal_g_cm2), **kw)

    @classmethod
    def from_thickness(cls, composition: Mapping, density_g_cm3: float,
                       thickness_cm: float, **kw) -> "Sample":
        return cls.from_composition(composition, density_g_cm3 * thickness_cm, **kw)

    def scaled(self, factor: float) -> "Sample":
        return Sample({z: v * factor for z, v in self.areal.items()},
                      self.incidence_deg, self.takeoff_deg, self.label)


@dataclass(frozen=True)
class Geometry:
    """Detection geometry.  ``solid_angle_fraction`` is Omega / 4pi."""

    solid_angle_fraction: float = 0.01

    def __post_init__(self):
        if not (0 < self.solid_angle_fraction <= 1):
            raise ValueError("solid_angle_fraction must be in (0, 1]")


@dataclass(frozen=True)
class Background:
    """**[MODEL]** Two-parameter Compton shelf + flat noise floor.

    ``continuum_fraction``  fraction of the Compton-scattered photons that land
                            in the shelf (default 1.0: all of them)
    ``continuum_decay_ev``  exponential decay of the shelf
    ``noise_per_kev``       flat electronic/noise floor, counts per keV

    The shelf is normalised so that its integral over energy equals
    ``continuum_fraction * scattered_flux * Omega/4pi``, i.e. it conserves the
    scattered photons instead of inventing a scale.
    """

    continuum_fraction: float = 1.0
    continuum_decay_ev: float = 6000.0
    noise_per_kev: float = 0.0

    def counts(self, energy_ev, live_time_s: float, scattered_flux: float,
               efficiency, solid_angle_fraction: float = 1.0) -> np.ndarray:
        e = np.asarray(energy_ev, dtype=float)
        decay = float(self.continuum_decay_ev)
        shelf_per_ev = (self.continuum_fraction * scattered_flux
                        * solid_angle_fraction * np.exp(-e / decay) / decay)
        return live_time_s * np.asarray(efficiency, dtype=float) * (
            shelf_per_ev + self.noise_per_kev / 1000.0)


# ---------------------------------------------------------------------------
# Spectrum container
# ---------------------------------------------------------------------------
@dataclass
class Spectrum:
    energy_ev: np.ndarray
    counts: np.ndarray
    live_time_s: float = 1.0
    label: str = ""
    meta: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        self.energy_ev = np.asarray(self.energy_ev, dtype=float)
        self.counts = np.asarray(self.counts, dtype=float)
        if self.energy_ev.shape != self.counts.shape:
            raise ValueError("energy and counts must have the same shape")

    def __len__(self) -> int:
        return int(self.energy_ev.size)

    @property
    def total_counts(self) -> float:
        return float(self.counts.sum())

    def rebin(self, n_channels: int, e_max: Optional[float] = None) -> "Spectrum":
        """Rebin onto a uniform grid of ``n_channels`` from 0 to ``e_max``."""
        e_max = float(e_max if e_max is not None else self.energy_ev.max())
        edges = np.linspace(0.0, e_max, int(n_channels) + 1)
        idx = np.clip(np.digitize(self.energy_ev, edges) - 1, 0, int(n_channels) - 1)
        out = np.bincount(idx, weights=self.counts, minlength=int(n_channels))
        centres = 0.5 * (edges[1:] + edges[:-1])
        return Spectrum(centres, out, self.live_time_s, self.label, dict(self.meta))

    def channel_edges(self) -> np.ndarray:
        if len(self) < 2:
            return np.array([0.0, 2 * self.energy_ev[0]])
        d = np.diff(self.energy_ev)
        mid = self.energy_ev[:-1] + d / 2
        return np.concatenate([[self.energy_ev[0] - d[0] / 2], mid,
                               [self.energy_ev[-1] + d[-1] / 2]])


# ---------------------------------------------------------------------------
# Vacancy fractions
# ---------------------------------------------------------------------------
#: Degeneracy of each L/M subshell (2j+1).
_SUBSHELL_DEGENERACY = {"1": 2, "2": 2, "3": 4, "4": 4, "5": 6}
_LM_SUBSHELLS = ("L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5")


def _level_parts(initial: str) -> list[str]:
    """Split a level label, e.g. ``"M4,5"`` -> ``["M4", "M5"]``.

    The reference database groups the spin-orbit pair M4/M5 for some lines.
    Splitting it is the only way to resolve the edge energy; the old code
    raised ``KeyError: 'M4,5'`` for 63 tabulated lines (e.g. Zn M-zeta).
    """
    return [p.strip().upper() for p in str(initial).replace(" ", "").split(",")
            if p.strip()]


def _level_edges(el: _elements.Element, initial: str) -> list[float]:
    """Positive binding energies of the components of a level label."""
    out: list[float] = []
    for part in _level_parts(initial):
        try:
            e = el.edge(part)
        except KeyError:
            continue
        if e > 0:
            out.append(float(e))
    return out


def subshell_vacancy_fraction(z: int, initial: str, energy_ev) -> np.ndarray:
    """**[MODEL]** Fraction of photoabsorptions that create a vacancy in ``initial``.

    K: exact jump-ratio result ``(J_K - 1)/J_K`` above E_K, zero below.
    L/M: the shell total is ``1 - 1/prod(J)`` and the subshells share it by
    degeneracy (L1:L2:L3 = 2:2:4).  Combined labels such as ``M4,5`` are
    split and their degeneracies summed.  This ignores the Coster-Kronig
    cascade, which moves vacancies between L subshells; that is a declared
    property of the convention, spoken here and nowhere hidden.
    """
    el = _elements.element(z)
    e = np.asarray(energy_ev, dtype=float)
    initial = str(initial).upper()

    if initial == "K":
        ek = el.edge("K")
        j = el.jump("K")
        frac = (j - 1.0) / j if j > 1.0 else 0.0
        return np.where(e >= ek, frac, 0.0) if ek > 0 else np.zeros_like(e)

    parts = [p for p in _level_parts(initial) if p in _LM_SUBSHELLS]
    if not parts:
        return np.zeros_like(e)
    shell = parts[0][0]
    names = [n for n in _LM_SUBSHELLS if n[0] == shell]
    weights = {n: _SUBSHELL_DEGENERACY[n[1]] for n in names}
    total_w = sum(weights.values())
    vacancy_weight = sum(_SUBSHELL_DEGENERACY[p[1]] for p in parts)
    # total shell jump = product of the subshell jumps
    prod_j = 1.0
    for n in names:
        prod_j *= max(el.jump(n), 1.0)
    shell_frac = 1.0 - 1.0 / prod_j if prod_j > 1.0 else 0.0
    edges = _level_edges(el, initial)
    e_shell = min(edges) if edges else 0.0
    out = np.where(e >= e_shell, shell_frac * vacancy_weight / total_w, 0.0)
    return out


def _self_absorption(sample: Sample, energy_ev: float) -> float:
    """**[MODEL]** Geometry factor for a uniform thin source.

    ``chi = mu (1/sin(incidence) + 1/sin(takeoff))`` and
    ``G = (1 - exp(-chi m)) / (chi m)``, the standard mean-path expression.
    """
    m = sample.total_areal
    if m <= 0:
        return 1.0
    mu = float(_atten.mu_rho_mixture(sample.mass_fractions, energy_ev))
    s_in = max(math.sin(math.radians(sample.incidence_deg)), 0.15)
    s_out = max(math.sin(math.radians(sample.takeoff_deg)), 0.15)
    chi = mu * (1.0 / s_in + 1.0 / s_out)
    x = chi * m
    return 1.0 if x < 1e-8 else float((1.0 - math.exp(-x)) / x)


# ---------------------------------------------------------------------------
# Forward model
# ---------------------------------------------------------------------------
def emission_lines(sample: Sample, excitation: Excitation) -> List[dict]:
    """Emitted line intensities (photons/s into 4pi) before geometry/detector.

    Returns a list of dicts with ``z``, ``line``, ``energy_ev``, ``rate``.
    """
    out: List[dict] = []
    e = excitation.energy_ev
    flux = excitation.photons_cm2_s
    for z, areal in sample.areal.items():
        el = _elements.element(z)
        mu_pe = np.asarray(_atten.mu_rho_pe(z, e), dtype=float)
        for ln in _lines.lines(z):
            edges = _level_edges(el, ln.initial)
            if not edges:
                continue
            e_init = min(edges)
            frac = subshell_vacancy_fraction(z, ln.initial, e)
            if not np.any(frac > 0):
                continue
            vacancies = float(np.sum(flux * mu_pe * areal * frac))
            if vacancies <= 0:
                continue
            omega = el.omega(ln.initial)
            if omega <= 0:
                continue
            rate = vacancies * omega * ln.intensity
            out.append({
                "z": z,
                "line": ln.name,
                "energy_ev": ln.energy,
                "rate": rate,
                "shell": ln.shell,
            })
    out.sort(key=lambda r: r["energy_ev"])
    return out


def forward_spectrum(sample: Sample, excitation: Excitation,
                     detector: _detector.Detector = _detector.SDD_25,
                     geometry: Geometry = Geometry(),
                     air_path_cm: float = 10.0,
                     live_time_s: float = 100.0,
                     background: Optional[Background] = Background(),
                     include_escape: bool = True,
                     energy_grid: Optional[np.ndarray] = None,
                     air_t_c: float = 20.0) -> Spectrum:
    """The instrument's forward operator.

    Returns a :class:`Spectrum` of *expected* counts (float, not Poisson).
    """
    emitted = emission_lines(sample, excitation)

    if energy_grid is None:
        e_max = max(25_000.0, excitation.max_energy * 1.05)
        energy_grid = np.arange(0.0, e_max, 10.0)
    energy_grid = np.asarray(energy_grid, dtype=float)

    counts = np.zeros_like(energy_grid)
    f_omega = geometry.solid_angle_fraction

    for row in emitted:
        e_line = row["energy_ev"]
        if e_line >= energy_grid[-1]:
            continue
        t_air = float(_air.air_transmission(e_line, air_path_cm, air_t_c))
        eff = float(detector.peak_efficiency(e_line))
        g = _self_absorption(sample, e_line)
        rate = row["rate"] * f_omega * eff * t_air * g
        counts += detector.peak_shape(energy_grid, e_line, rate * live_time_s)
        if include_escape:
            p = detector.escape_probability(e_line)
            if p > 0:
                e_esc = e_line - SI_KALPHA_EV
                if e_esc > 0:
                    counts += detector.peak_shape(energy_grid, e_esc,
                                                  rate * live_time_s * p)

    if background is not None:
        # scattered flux estimate: incident flux x incoherent optical depth
        mu_inc = float(_atten.mu_rho_incoherent(13, 10_000.0))
        scattered = excitation.total_flux * min(1.0, mu_inc * sample.total_areal)
        counts += background.counts(
            energy_grid, live_time_s, scattered,
            detector.peak_efficiency(np.clip(energy_grid, 100.0, None)),
            f_omega)

    # peak_shape/background return a density per eV; convert to counts per channel
    counts = counts * np.gradient(energy_grid)

    meta = {
        "model": "forward-v1",
        "sample_total_areal_g_cm2": sample.total_areal,
        "excitation": excitation.label,
        "detector": detector.name,
        "air_path_cm": air_path_cm,
        "solid_angle_fraction": f_omega,
        "n_lines": len(emitted),
        "thin_sample": sample.total_areal < 0.01,
    }
    return Spectrum(energy_grid, counts, live_time_s,
                    f"forward: {sample.label or 'sample'}", meta)


def design_matrix(elements_list: Sequence, excitation: Excitation,
                  detector: _detector.Detector = _detector.SDD_25,
                  geometry: Geometry = Geometry(),
                  air_path_cm: float = 10.0,
                  live_time_s: float = 100.0,
                  energy_grid: Optional[np.ndarray] = None,
                  include_escape: bool = False,
                  unit_areal: float = 1e-6) -> Tuple[np.ndarray, np.ndarray]:
    """Columns = expected spectrum for ``unit_areal`` g/cm^2 of each element.

    The column is built at a *small* loading (default 1 ug/cm^2) so that the
    response is in its linear regime; building it at 1 g/cm^2 would bake
    self-absorption into the sensitivity and make every trace element look
    1000x weaker.  Used by the fundamental-parameters inversion.
    """
    cols = []
    grid = None
    for z in elements_list:
        unit = Sample({_elements.element(z).z: float(unit_areal)})
        s = forward_spectrum(unit, excitation, detector, geometry, air_path_cm,
                             live_time_s, background=None,
                             include_escape=include_escape, energy_grid=energy_grid)
        grid = s.energy_ev
        cols.append(s.counts)
    return np.asarray(cols).T, np.asarray(grid)


def expected_rate_summary(sample: Sample, excitation: Excitation) -> List[dict]:
    """Human-readable per-line count rates (for reports and tests)."""
    rows = emission_lines(sample, excitation)
    for r in rows:
        r["element"] = _elements.BY_Z[r["z"]].symbol
    return rows


def self_check() -> list[str]:
    problems = []
    s = Sample.from_composition({"Fe": 1.0}, 1e-4)
    exc = Excitation.monoenergetic(10_000.0, 1e10)
    spec = forward_spectrum(s, exc, background=None, include_escape=False)
    if spec.total_counts <= 0:
        problems.append("forward model produced no counts")
    lines_out = emission_lines(s, exc)
    if not lines_out:
        problems.append("no emission lines for Fe at 10 keV")
    for r in lines_out:
        if r["energy_ev"] <= 0:
            problems.append("non-positive line energy")
    return problems


if __name__ == "__main__":  # pragma: no cover
    s = Sample.from_composition({"Fe": 0.7, "Si": 0.2, "Ca": 0.1}, 1e-4)
    exc = Excitation.tube(40.0, "Rh", total_flux=1e10)
    spec = forward_spectrum(s, exc, live_time_s=100.0)
    print(f"total counts in 100 s: {spec.total_counts:.1f}")
    for r in expected_rate_summary(s, exc)[:6]:
        print(f"  {r['element']:>2} {r['line']:<4} {r['energy_ev']:8.1f} eV  "
              f"{r['rate']:.3e} /s into 4pi")
    print("self_check:", self_check() or "clean")
