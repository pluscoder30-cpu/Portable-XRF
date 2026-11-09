"""The inverse operator: spectrum -> peaks -> elements -> areal densities.

HONESTY
-------
``snip_background``
    **[STANDARD ALGORITHM]**.  SNIP (Statistics-sensitive Non-linear Iterative
    Peak-clipping), Ryan et al. 1988.  It estimates the continuum under the
    peaks; it does not know any physics and cannot invent a peak.

``detect_peaks`` / ``fit_peak``
    **[ALGORITHM]**.  Local maxima above a Poisson significance threshold, then
    a Gaussian + linear background fit on a small grid of (centre, sigma) with
    linear least squares for the amplitude.  The Gaussian width is constrained
    to the detector's own FWHM curve, so a peak cannot be "fitted" into
    existence by shrinking its width.

``identify``
    **[ALGORITHM]**.  Line matching against the reference table with a
    tolerance of max(3 sigma, 0.2 % of E).  At 6.4 keV and 125 eV FWHM the
    tolerance is ~0.4 keV, which separates K-alpha1 from K-beta for every
    element up to Z ~ 50; above that the K lines crowd and the matcher returns
    multiple candidates rather than guessing.

``quantify_calibration``
    **[EMPIRICAL]**.  counts / (live time x sensitivity).  The sensitivity must
    come from a measured standard; the function cannot check that the standard
    was valid.

``quantify_fundamental``
    **[MODEL]**.  Non-negative least squares against the forward operator.
    This is only as good as ``forward.py`` -- it inherits every model
    approximation listed there.  The returned ``relative_residual`` is the
    honest quality number.

Nothing here applies a phi-correction.  The corpus's own verdict (Law 1347)
is that the line energies are exactly the classical binding-energy
differences; the matcher therefore uses the classical table.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from . import detector as _detector
from . import elements as _elements
from . import forward as _forward
from . import lines as _lines
from . import metals as _metals
from .linalg import nnls

# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------
def background_iterations(spectrum: _forward.Spectrum,
                          detector: _detector.Detector = _detector.SDD_25) -> int:
    """SNIP width in channels: ~1.2 x the detector FWHM at mid-spectrum.

    This is the standard guidance (the clipping window must be comparable to
    the peak width).  Using a fixed 40 iterations on a 10 eV/channel spectrum
    clips a 125 eV peak *and* the smooth continuum underneath it -- measured
    on a synthetic spectrum, 40 iterations removed 79 % of the continuum at
    1.74 keV while 12 removed 6 %.
    """
    e = spectrum.energy_ev
    if e.size < 3:
        return 5
    step = float(np.median(np.diff(e))) or 1.0
    # Reference energy: the low end, where peaks are narrowest.  SNIP has one
    # global window, so it is tuned for the sharpest peak in the spectrum;
    # that under-clips slightly at high energy (safe: it leaves continuum,
    # it does not eat peaks).
    e_ref = min(max(2000.0, 0.1 * float(e.max())), 4000.0)
    fwhm_ch = float(detector.fwhm(e_ref)) / step
    return int(max(6, min(60, round(1.3 * fwhm_ch))))


def snip_background(counts, iterations: int = 40) -> np.ndarray:
    """**[STANDARD ALGORITHM]** SNIP continuum estimate."""
    y = np.asarray(counts, dtype=float)
    if y.size < 5:
        return np.zeros_like(y)
    y = np.maximum(y, 0.0)
    v = np.log(np.log(np.sqrt(y + 1.0) + 1.0) + 1.0)
    n = v.size
    for p in range(1, int(iterations) + 1):
        if 2 * p >= n:
            break
        v[p:n - p] = np.minimum(v[p:n - p], 0.5 * (v[0:n - 2 * p] + v[2 * p:n]))
    out = (np.exp(np.exp(v) - 1.0) - 1.0) ** 2 - 1.0
    return np.maximum(out, 0.0)


# ---------------------------------------------------------------------------
# Peaks
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Peak:
    center_ev: float
    height: float
    sigma_ev: float
    area: float
    area_err: float
    snr: float
    background: float
    center_err_ev: float = 0.0

    @property
    def fwhm_ev(self) -> float:
        return self.sigma_ev * _detector.FWHM_PER_SIGMA

    def __repr__(self) -> str:  # pragma: no cover
        return (f"<Peak {self.center_ev:.1f} eV area {self.area:.1f} "
                f"+-{self.area_err:.1f} snr {self.snr:.1f}>")


@dataclass(frozen=True)
class Identification:
    peak: Peak
    candidates: Tuple[Tuple[_lines.Line, float], ...]   # (line, deviation in eV)

    @property
    def best(self) -> Optional[Tuple[_lines.Line, float]]:
        return self.candidates[0] if self.candidates else None

    @property
    def ambiguous(self) -> bool:
        if len(self.candidates) < 2:
            return False
        return abs(self.candidates[1][1] - self.candidates[0][1]) < 1.0


def _local_maxima(y: np.ndarray) -> np.ndarray:
    if y.size < 3:
        return np.array([], dtype=int)
    left = y[1:-1] > y[:-2]
    right = y[1:-1] >= y[2:]
    return np.where(left & right)[0] + 1


def detect_peaks(spectrum: _forward.Spectrum,
                 detector: _detector.Detector = _detector.SDD_25,
                 min_snr: float = 4.0,
                 min_area: float = 10.0,
                 background: Optional[np.ndarray] = None) -> List[Peak]:
    """Find and fit peaks.  ``min_snr`` is in units of sqrt(background)."""
    e = spectrum.energy_ev
    y = spectrum.counts
    it = background_iterations(spectrum, detector)
    bg = snip_background(y, it) if background is None else np.asarray(background, float)
    net = y - bg
    noise = np.sqrt(np.maximum(bg, 1.0))
    idx = _local_maxima(net)
    if idx.size == 0:
        return []

    # keep maxima that clear the significance threshold
    keep = [i for i in idx if net[i] > min_snr * noise[i] and net[i] > 0]
    if not keep:
        return []

    # merge maxima that fall inside the same FWHM
    merged: List[int] = []
    for i in sorted(keep, key=lambda k: -net[k]):
        fwhm_ch = max(1, int(round(float(detector.fwhm(e[i])) / max(np.median(np.diff(e)), 1e-9))))
        if i < fwhm_ch or i > e.size - fwhm_ch:
            continue        # edge artifact: the fit window would run off the data
        if all(abs(i - j) > fwhm_ch for j in merged):
            merged.append(i)

    peaks: List[Peak] = []
    for i in sorted(merged):
        p = fit_peak(e, y, i, detector, bg)
        if p is None:
            continue
        # A broad Gaussian fitted to a 2-count bump has a large *area* but a
        # tiny *height*.  Requiring the height to clear the noise rejects it.
        if p.height < min_snr * math.sqrt(max(p.background, 1.0)):
            continue
        if p.area >= min_area and p.snr >= min_snr:
            peaks.append(p)
    return peaks


def fit_peak(energy, counts, index: int,
             detector: _detector.Detector = _detector.SDD_25,
             background: Optional[np.ndarray] = None) -> Optional[Peak]:
    """Fit one peak: Gaussian + linear background, width tied to the detector."""
    e = np.asarray(energy, dtype=float)
    y = np.asarray(counts, dtype=float)
    bg = snip_background(y) if background is None else np.asarray(background, float)
    if not (0 <= index < e.size):
        return None
    guess = e[index]
    sigma0 = float(detector.sigma(guess))
    if not np.isfinite(sigma0) or sigma0 <= 0:
        return None
    half = max(3.0 * sigma0, 2.0 * np.median(np.diff(e)))
    m = (e >= guess - half) & (e <= guess + half)
    if m.sum() < 5:
        return None
    x, yy = e[m], y[m]
    base = float(np.median(bg[m]))

    best = None
    for mu in np.linspace(guess - 0.6 * sigma0, guess + 0.6 * sigma0, 13):
        for s in sigma0 * np.linspace(0.75, 1.35, 7):
            g = np.exp(-0.5 * ((x - mu) / s) ** 2) / (s * math.sqrt(2 * math.pi))
            design = np.column_stack([g, np.ones_like(x), x - mu])
            coef, *_ = np.linalg.lstsq(design, yy, rcond=None)
            model = design @ coef
            chi2 = float(np.sum((yy - model) ** 2 / np.maximum(yy, 1.0)))
            if best is None or chi2 < best[0]:
                best = (chi2, mu, s, coef)

    if best is None:
        return None
    _, mu, s, coef = best
    area = float(coef[0])
    if area <= 0:
        return None
    width = max(1.0, half / max(np.median(np.diff(e)), 1e-9))
    area_err = math.sqrt(max(area, 0.0) + 2.0 * max(base, 0.0) * width)
    snr = area / area_err if area_err > 0 else 0.0
    # centroid uncertainty of a fitted Gaussian: sigma / sqrt(N)
    center_err = float(s / math.sqrt(max(area, 1.0)))
    return Peak(center_ev=float(mu), height=float(coef[0] / (s * math.sqrt(2 * math.pi))),
                sigma_ev=float(s), area=area, area_err=float(area_err),
                snr=float(snr), background=base, center_err_ev=center_err)


# ---------------------------------------------------------------------------
# Identification
# ---------------------------------------------------------------------------
def candidate_elements(energy_min: float, energy_max: float,
                       min_intensity: Optional[float] = None) -> List[int]:
    """Elements with at least one strong line inside the window.

    The floor defaults to the register's own declared line-intensity
    threshold (``metals.MIN_LINE_INTENSITY``) — the same constant the
    registry uses, never a second hidden copy.
    """
    if min_intensity is None:
        min_intensity = _metals.MIN_LINE_INTENSITY
    out = []
    for el in _elements.ELEMENTS:
        for ln in _lines.lines(el.z):
            if energy_min <= ln.energy <= energy_max and ln.intensity >= min_intensity:
                out.append(el.z)
                break
    return out


#: Matching floor for line identification [DECLARED]: the weakest relative
#: line intensity the matcher will consider.  Distinct from the register's
#: ``MIN_LINE_INTENSITY`` (which decides which elements are candidates);
#: this one only filters lines during peak matching.
MATCH_MIN_LINE_INTENSITY = 0.02


def identify(peak: Peak, elements: Optional[Sequence[int]] = None,
             tol_sigma: float = 3.0, tol_frac: float = 5e-4,
             min_intensity: float = MATCH_MIN_LINE_INTENSITY,
             prefer_elements: Optional[Sequence[int]] = None) -> Identification:
    """Match a fitted peak to library lines.

    Two tolerances are used, because a merged doublet is not a single line:

    * the **centroid tolerance** is max(3 x centroid uncertainty, 0.05 % of E,
      1 eV).  At 6.4 keV with 40,000 counts it is ~3 eV, which separates
      K-alpha from K-beta for every element.
    * the **search window** is 0.75 x the peak FWHM, because a K-alpha1 /
      K-alpha2 doublet at 125 eV FWHM is one peak whose centroid sits between
      the two lines.

    An element is scored by how well the *intensity-weighted centroid of its
    lines inside the window* matches the fitted centroid.  That is the
    physically correct test for a blended multiplet: Ca K-alpha1+K-alpha2 has
    a centroid 1.7 eV below K-alpha1, and the matcher accepts Ca because its
    doublet centroid lands on the peak.
    """
    tol = max(tol_sigma * max(peak.center_err_ev, 0.0),
              tol_frac * peak.center_ev, 1.0)
    window = max(0.75 * peak.fwhm_ev, tol)
    zs = list(elements) if elements is not None else range(1, 93)

    groups: List[Tuple[float, int, List[_lines.Line]]] = []
    prefer = set(int(z) for z in (prefer_elements or ()))
    for z in zs:
        near = [ln for ln in _lines.lines(int(z))
                if ln.intensity >= min_intensity
                and abs(ln.energy - peak.center_ev) <= window]
        if not near:
            continue
        wsum = sum(ln.intensity for ln in near)
        centroid = sum(ln.energy * ln.intensity for ln in near) / wsum
        score = abs(centroid - peak.center_ev) / tol + 0.3 * (1.0 - max(
            ln.intensity for ln in near))
        if int(z) in prefer:
            # an element already confirmed by a strong line gets a bonus; this
            # is how a real analyzer resolves e.g. S K-beta vs Mo L-beta3
            score -= 0.35
        groups.append((score, z, near))

    if not groups:
        return Identification(peak, ())

    groups.sort(key=lambda g: g[0])
    best = groups[0]
    lines_out = sorted(best[2], key=lambda ln: -ln.intensity)
    cands = tuple((ln, ln.energy - peak.center_ev) for ln in lines_out)
    return Identification(peak, cands)


def identify_all(peaks: Sequence[Peak],
                 elements: Optional[Sequence[int]] = None) -> List[Identification]:
    return [identify(p, elements) for p in peaks]


# ---------------------------------------------------------------------------
# Detection limits
# ---------------------------------------------------------------------------
def detection_limit(spectrum: _forward.Spectrum,
                    z: int,
                    excitation: _forward.Excitation,
                    detector: _detector.Detector = _detector.SDD_25,
                    geometry: _forward.Geometry = _forward.Geometry(),
                    air_path_cm: float = 10.0,
                    unit_areal: float = 1e-6,
                    sigma: float = 3.0) -> float:
    """**[MODEL]** 3-sigma minimum detectable areal density, g/cm^2.

    ``MDL = sigma * sqrt(B) / S`` where B is the background counts under the
    element's strongest peak (one FWHM window) and S the peak counts per unit
    areal density.  Returns ``inf`` when the element has no line that survives
    the path (e.g. Mg K-alpha through 10 cm of air).
    """
    design, grid = _forward.design_matrix(
        [z], excitation, detector, geometry, air_path_cm,
        spectrum.live_time_s, energy_grid=spectrum.energy_ev,
        include_escape=True, unit_areal=unit_areal,
    )
    col = design[:, 0]
    if col.size == 0 or col.max() <= 0:
        return float("inf")
    i = int(np.argmax(col))
    fwhm_ch = max(1.0, float(detector.fwhm(grid[i])) / max(np.median(np.diff(grid)), 1e-9))
    half = int(round(fwhm_ch))
    lo, hi = max(0, i - half), min(col.size, i + half + 1)
    sensitivity = float(col[lo:hi].sum())
    if sensitivity <= 0:
        return float("inf")
    bg = snip_background(spectrum.counts, background_iterations(spectrum, detector))
    background = float(np.sum(bg[lo:hi]))
    # a zero-count background is possible in a noiseless simulation; floor it
    # at one count so the limit stays finite but never claims sub-count power
    return float(sigma * math.sqrt(max(background, 1.0)) / sensitivity * unit_areal)


# ---------------------------------------------------------------------------
# Quantification: calibration curve
# ---------------------------------------------------------------------------
@dataclass
class Calibration:
    """Empirical sensitivity: counts/s per (g/cm^2), per element."""

    sensitivities: Dict[int, float]
    live_time_s: float = 1.0
    note: str = ""

    @classmethod
    def from_standard(cls, spectrum: _forward.Spectrum, sample: _forward.Sample,
                      detector: _detector.Detector = _detector.SDD_25,
                      line_name: Optional[str] = None) -> "Calibration":
        """Derive sensitivities from a measured standard of known loading."""
        peaks = detect_peaks(spectrum, detector)
        ids = identify_all(peaks, list(sample.areal))
        sens: Dict[int, float] = {}
        for ident in ids:
            if not ident.candidates:
                continue
            ln = ident.candidates[0][0]
            if line_name and ln.name != line_name:
                continue
            z = ln.z
            if z in sens or z not in sample.areal:
                continue
            areal = sample.areal[z]
            if areal <= 0:
                continue
            sens[z] = ident.peak.area / (spectrum.live_time_s * areal)
        return cls(sens, spectrum.live_time_s,
                   "sensitivities from a measured standard; validity depends on "
                   "the standard's matrix matching the unknown's matrix")


def quantify_calibration(spectrum: _forward.Spectrum, calib: Calibration,
                         detector: _detector.Detector = _detector.SDD_25,
                         peaks: Optional[Sequence[Peak]] = None) -> dict:
    """**[EMPIRICAL]** areal density = net counts / (live time x sensitivity)."""
    peaks = list(peaks) if peaks is not None else detect_peaks(spectrum, detector)
    ids = identify_all(peaks, list(calib.sensitivities))
    out: Dict[int, dict] = {}
    for ident in ids:
        if not ident.candidates:
            continue
        ln = ident.candidates[0][0]
        s = calib.sensitivities.get(ln.z)
        if not s or s <= 0:
            continue
        areal = ident.peak.area / (spectrum.live_time_s * s)
        prev = out.get(ln.z)
        if prev is None or areal > prev["areal_g_cm2"]:
            out[ln.z] = {
                "element": _elements.BY_Z[ln.z].symbol,
                "line": ln.name,
                "areal_g_cm2": float(areal),
                "areal_ug_cm2": float(areal * 1e6),
                "area": ident.peak.area,
                "area_err": ident.peak.area_err,
                "snr": ident.peak.snr,
            }
    return {
        "elements": out,
        "method": "calibration",
        "model": "counts / (live_time * sensitivity)",
    }


# ---------------------------------------------------------------------------
# Quantification: fundamental parameters
# ---------------------------------------------------------------------------
def quantify_fundamental(spectrum: _forward.Spectrum,
                         elements: Sequence[int],
                         excitation: _forward.Excitation,
                         detector: _detector.Detector = _detector.SDD_25,
                         geometry: _forward.Geometry = _forward.Geometry(),
                         air_path_cm: float = 10.0,
                         unit_areal: float = 1e-6,
                         subtract_background: bool = True,
                         matrix_iterations: int = 2,
                         e_min: float = 1000.0,
                         e_max: Optional[float] = None,
                         detection_floor_ug_cm2: float = 0.05,
                         return_design: bool = False) -> dict:
    """**[MODEL]** NNLS against the forward operator.

    ``unit_areal`` is the areal density (g/cm^2) used to build each design
    column; the solution is scaled back by it.  1e-6 g/cm^2 = 1 ug/cm^2.

    ``matrix_iterations`` re-scales each column by the sample self-absorption
    implied by the current estimate.  The first NNLS assumes a trace sample
    (no matrix); for a 60 ug/cm^2 deposit that under-estimates the 1-2 keV
    lines by 5-10 %, and the iteration removes most of that bias.

    ``return_design=True`` additionally returns the final design matrix, the
    (background-subtracted) data vector, the channel grid and the element
    order under the ``_design``, ``_y``, ``_grid`` and ``_element_order``
    keys.  The sniffer uses these to propagate a linear least-squares
    uncertainty; it is not a change to the physics.

    ``detection_floor_ug_cm2`` is the declared NNLS-artefact guard used for
    the ``detected`` flag (an engineering threshold, not a physics
    constant).  Callers who derive a scan-specific floor — e.g. the sniffer
    derives its reporting floor from the scan's own 3-sigma detection
    limits — pass it explicitly here; the default only exists so the
    function is honest standalone.
    """
    e = spectrum.energy_ev
    e_max = float(e_max if e_max is not None else min(e.max(), 30_000.0))
    m = (e >= e_min) & (e <= e_max)
    grid = e[m]
    y = spectrum.counts[m]
    if subtract_background:
        it = background_iterations(spectrum, detector)
        y = np.maximum(y - snip_background(spectrum.counts, it)[m], 0.0)

    design_full, _ = _forward.design_matrix(
        elements, excitation, detector, geometry, air_path_cm,
        spectrum.live_time_s, energy_grid=grid, include_escape=True,
        unit_areal=unit_areal,
    )
    # A numerically zero column cannot be quantified: the element has no line
    # inside the fit window, or the air path extinguishes it (e.g. Na K-alpha
    # at 1.04 keV when e_min = 1.2 keV).  Leaving such a column in the NNLS
    # makes the active set ill-conditioned and returns 1e12 ug/cm2 artefacts;
    # the element is reported at zero with ``quantified=False`` instead.
    col_norm = np.linalg.norm(design_full, axis=0)
    max_norm = float(col_norm.max()) if col_norm.size else 0.0
    keep = col_norm > max_norm * 1e-9
    solve_elements = [int(z) for z, k in zip(elements, keep) if k]
    dropped_elements = [int(z) for z, k in zip(elements, keep) if not k]
    design = design_full[:, keep] if keep.any() else design_full[:, :0]

    if design.shape[1]:
        design_unit = design.copy()   # the un-attenuated (thin) design
        x = nnls(design, y)
        for _ in range(max(0, int(matrix_iterations))):
            est = {_elements.element(z).z: float(xi * unit_areal)
                   for z, xi in zip(solve_elements, x) if xi > 0}
            if not est:
                break
            sample_est = _forward.Sample(est)
            unit_samples = {z: _forward.Sample({z: unit_areal})
                            for z in solve_elements}
            for j, z in enumerate(solve_elements):
                col_u = design_unit[:, j]
                if col_u.max() <= 0:
                    continue
                e_peak = float(grid[int(np.argmax(col_u))])
                g_est = _forward._self_absorption(sample_est, e_peak)
                g_unit = _forward._self_absorption(unit_samples[z], e_peak)
                if g_est > 0 and g_unit > 0:
                    # rebuild the column from the CURRENT estimate's
                    # self-absorption (a fixed-point iteration, not a
                    # compounding product — the compounded form diverges
                    # for thick, low-E-absorbing deposits)
                    design[:, j] = col_u * (g_est / g_unit)
            x = nnls(design, y)
    else:
        x = np.zeros(0)

    fitted = design @ x
    resid = y - fitted
    rel = float(np.linalg.norm(resid) / max(np.linalg.norm(y), 1e-30))

    solved = {int(z): float(coeff) for z, coeff in zip(solve_elements, x)}
    out = {}
    for z in elements:
        el = _elements.element(z)
        coeff = solved.get(el.z, 0.0)
        areal = float(coeff * unit_areal)
        out[el.z] = {
            "element": el.symbol,
            "areal_g_cm2": areal,
            "areal_ug_cm2": areal * 1e6,
            "detected": bool(coeff > float(detection_floor_ug_cm2)),
            "quantified": el.z in solved,
        }
    result = {
        "elements": out,
        "method": "fundamental_parameters",
        "relative_residual": rel,
        "n_channels_used": int(m.sum()),
        "model": "NNLS on forward-v1",
        "dropped_elements": [_elements.BY_Z[z].symbol for z in dropped_elements],
    }
    if return_design:
        result["_design"] = design
        result["_y"] = y
        result["_grid"] = grid
        result["_element_order"] = solve_elements
        result["_unit_areal"] = float(unit_areal)
    return result


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------
def analyze(spectrum: _forward.Spectrum,
            detector: _detector.Detector = _detector.SDD_25,
            min_snr: float = 4.0,
            elements: Optional[Sequence[int]] = None) -> dict:
    """Peaks -> identification -> element list.  No quantification.

    Si K-alpha escape peaks (parent energy minus 1739.98 eV) are flagged and
    excluded: they are detector artefacts, not elements.
    """
    from .constants import SI_KALPHA_EV

    peaks = detect_peaks(spectrum, detector, min_snr=min_snr)
    escape_flags = [False] * len(peaks)
    for i, p in enumerate(peaks):
        for j, q in enumerate(peaks):
            if i == j:
                continue
            if abs(q.center_ev - (p.center_ev + SI_KALPHA_EV)) < max(
                    3 * q.center_err_ev, 0.002 * q.center_ev, 2.0):
                if q.area > 5 * p.area:
                    escape_flags[i] = True
    ids = identify_all(peaks, elements)

    # second pass: an element confirmed by a strong, high-intensity line gets a
    # bonus when the remaining peaks are matched (multi-line confirmation)
    confirmed = set()
    for ident in ids:
        if ident.candidates and ident.peak.snr > 30:
            ln = ident.candidates[0][0]
            if ln.intensity >= 0.3:
                confirmed.add(ln.z)
    if confirmed:
        ids = [identify(p, elements, prefer_elements=confirmed) for p in peaks]

    found: Dict[int, dict] = {}
    for ident, is_escape in zip(ids, escape_flags):
        if is_escape or not ident.candidates:
            continue
        ln, dev = ident.candidates[0]
        cur = found.get(ln.z)
        if cur is None or ident.peak.area > cur["area"]:
            found[ln.z] = {
                "element": _elements.BY_Z[ln.z].symbol,
                "line": ln.name,
                "energy_ev": ln.energy,
                "dev_ev": dev,
                "area": ident.peak.area,
                "snr": ident.peak.snr,
                "ambiguous": ident.ambiguous,
            }
    return {
        "peaks": peaks,
        "identifications": ids,
        "escape_peaks": [p for p, f in zip(peaks, escape_flags) if f],
        "elements": found,
        "n_peaks": len(peaks),
    }


def self_check() -> list[str]:
    problems = []
    e = np.arange(0.0, 20000.0, 10.0)
    y = 100.0 * np.exp(-e / 5000.0) + 1000.0 * np.exp(-0.5 * ((e - 6400.0) / 53.0) ** 2)
    bg = snip_background(y)
    if bg[640] > 0.5 * y[640]:
        problems.append("SNIP removed the peak")
    peaks = detect_peaks(_forward.Spectrum(e, y), _detector.SDD_25)
    if not peaks:
        problems.append("failed to detect a synthetic peak")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("self_check:", self_check() or "clean")
