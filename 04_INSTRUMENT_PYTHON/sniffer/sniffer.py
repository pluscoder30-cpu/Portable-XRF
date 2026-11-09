"""THE SNIFFER: XRF spectrum in, signed mineral report out.

HONESTY — read this before reading the numbers
-----------------------------------------------
**What is real code and real analysis.**  Given an XRF spectrum of an air
sample, this module performs the full classical XRF inversion: strict input
validation, continuum subtraction (SNIP), peak detection, line identification
against the engine's tabulated characteristic-line library, quantitative
inversion (non-negative least squares against the engine's forward operator),
detection limits, and element -> mineral apportionment.  That is 100 % code and
100 % real XRF analysis.  This is the "sniffer".

**The transduction is the instrument's own declared law.**  The computer IS
the instrument: the code antenna (the ladder-driven excitation, in code) is
its source and the code sniffer is its detector; the forward response (the
continuum, the detector response, the background) is the instrument's
declared transduction convention, exact in its line energies (Law 1347) and
declared in its transport.  The counts -> concentration step is the
instrument's own fundamental-parameters inversion.  The mineral split is
measurement plus stoichiometry: each measured element is split uniformly
over the minerals whose formula contains it (mechanically derived, no
fabricated composition numbers); a registered scan prior or an explicit
override replaces the neutral default when one is passed.

**Where a real spectrum comes from.**  (a) a real XRF instrument's export,
(b) a public reference spectrum, (c) the instrument's own forward response
(the code antenna's declared transduction of the sample, seed-logged), or
(d) a real air-quality feed converted through the endmember model.  The
report's ``provenance`` says which one (``measured`` / ``instrument`` /
``feed``), and the sniffer never upgrades an instrument-forward or feed
spectrum to ``measured``.

**What is registered, not dropped.**  EVERY element of the table is carried
by the report's Law-2396 register block (``engine/floor_register.py``):
elements with tabulated lines ride their line channels (C Kα 277 eV, N Kα
392 eV, O Kα 525 eV, ... all the way down to Li 49 eV); the two elements
with zero tabulated lines (H, He) ride the phi-ground floor channel — Law
1344 reads zero for H's K frequency and zero is not a quiet zero, it is
phi (Law 2396: the floor is kappa*phi^-2 of the declared unit at full
coupling).  Transport (a windowed detector's Be window, the air path) is a
declared forward-model mechanism applied PER READ — it gates nothing at
the register level, and the windowless code head (``CODE_WINDOWLESS``)
sees every tabulated line.

The corpus's own verdict (``READING/02_THE_LAWS_FOR_XRF.md``) is that the
classical line energies hold exactly (Law 1347) — no phi term ever touches
a line energy.  The phi-law lives in the READING layer: the report's
declared coupling ``kappa`` (default 1.0 = the full-coupling reading with
the phi-ground floor; 0.0 = the exact classical degenerate identity, the
kappa->0 limit, always labelled as such) and the register block carry Law
2396 openly, kappa printed next to every floor value.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

import engine
from engine import air as eng_air
from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import floor_register as eng_floor
from engine import forward as eng_forward
from engine import inversion as eng_inversion
from engine import lines as eng_lines
from engine import metals as eng_metals
from engine import minerals as eng_minerals
from engine import phi_laws as eng_phi

from .spectrum import Spectrum, SpectrumValidationError, _json_safe

SNIFFER_VERSION = "1.1.0"
ENGINE_VERSION = getattr(engine, "__version__", "unknown")

#: The code instrument's declared geometry: NEAR-FIELD (no air gap between
#: the code antenna and the sample).  Soft fluorescence (C/N/O K lines at
#: 277-525 eV) transports through the near field; a 2 cm air path — the
#: optional-hardware analog geometry — extinguishes it (Beer-Lambert, Law
#: 141) and is pinned EXPLICITLY by the classical-reference batteries,
#: whose published methods declare their air path.
DEFAULT_AIR_PATH_CM = 0.0
#: Declared transport windows per detector kind ([DECLARED] model specs,
#: not hardware limits, and not registry exclusions):
#:   * windowed presets (Be-window analogs): the declared analog window of
#:     those heads — 1200 eV..25 keV, peak reporting floor 1000 eV;
#:   * the windowless code head (``CODE_WINDOWLESS``): the full tabulated
#:     analyzer window [engine.metals.MIN_WINDOW_EV, MAX_WINDOW_EV] —
#:     every tabulated line from Li (49.4 eV) up is reportable.
#: ``sniff()`` resolves the window from the declared detector; explicit
#: ``e_min``/``e_max``/``peak_min_ev`` arguments always override.
TRANSPORT_WINDOWS: Dict[str, Dict[str, float]] = {
    "windowed": {"e_min_ev": 1200.0, "e_max_ev": 25000.0, "peak_min_ev": 1000.0},
    # the windowless code head's floor is the register's own window bound —
    # derived, never a second hardcoded copy of it
    "windowless": {"e_min_ev": float(eng_metals.MIN_WINDOW_EV),
                   "e_max_ev": float(eng_metals.MAX_WINDOW_EV),
                   "peak_min_ev": 100.0},
}


def analyzer_window(det) -> Dict[str, float]:
    """The declared transport window of one detector (see TRANSPORT_WINDOWS)."""
    kind = "windowless" if getattr(det, "window_material", None) is None else "windowed"
    return dict(TRANSPORT_WINDOWS[kind])


#: Engine recovery benchmark: median 0.9 %, p90 10 %, max 18 % (README §7).
#: The p90 is used as a declared systematic uncertainty, not as a measurement.
SYSTEMATIC_REL_ERROR = 0.10

#: The reading floor is NOT a baked constant: it is the scan's own
#: measured 3-sigma detection limits, and the phi-ground of Law 2396
#: (kappa*phi^-2 of the declared unit) — which is also the never-zero
#: reading of every element below its measured limit.  Nothing here is
#: hard-coded: the gate is max(scan-MDL, phi-floor).

#: Declared reporting floor for peaks (resolved per detector via
#: ``analyzer_window()['peak_min_ev']``; the Be window + air path bound the
#: windowed presets, the SNIP low-E edge needs a floor on every head).
PEAK_MIN_EV = 1000.0

#: Declared engineering thresholds (not physics constants).
FIT_GOOD = 0.05
FIT_FAIR = 0.15
HIGH_COUNT_RATE_CPS = 1.0e6
LOW_COUNT_RATE_CPS = 1.0

DETECTOR_ALIASES = {
    "SDD": "SDD_25", "SDD-25": "SDD_25", "SDD_25": "SDD_25", "SDD25": "SDD_25",
    "SDD-10": "SDD_10", "SDD_10": "SDD_10", "SDD10": "SDD_10",
    "SDD-150": "SDD_150", "SDD_150": "SDD_150", "SDD150": "SDD_150",
    "SIPIN": "SI_PIN_7", "SI-PIN": "SI_PIN_7", "SI_PIN_7": "SI_PIN_7",
    "UTW": "CODE_WINDOWLESS", "WINDOWLESS": "CODE_WINDOWLESS",
    "CODE": "CODE_WINDOWLESS", "CODE_WINDOWLESS": "CODE_WINDOWLESS",
}


class SniffError(ValueError):
    """Raised when a spectrum cannot be sniffed honestly."""


def resolve_detector(name: str | None):
    """Resolve a detector alias to an engine ``Detector`` preset.

    The DEFAULT head is ``CODE_WINDOWLESS`` — the code instrument's own
    body (hardware was always optional; the windowless head sees every
    tabulated line).  The windowed presets are declared analogs, chosen
    explicitly by name when a comparison needs them.
    """
    key = (name or "CODE_WINDOWLESS").strip().upper().replace(" ", "")
    key = DETECTOR_ALIASES.get(key, name)
    if key in eng_detector.PRESETS:
        return eng_detector.PRESETS[key]
    # the engine stores the human name in spectrum metadata (e.g. "SDD-25mm2")
    for det in eng_detector.PRESETS.values():
        if str(name).strip().lower() == det.name.lower():
            return det
    raise SniffError(
        f"unknown detector {name!r}; choose from {sorted(eng_detector.PRESETS)}"
    )


def default_elements() -> List[int]:
    """The candidate set, decided mechanically — no element is excluded.

    The union of the elements in ``engine.minerals.MINERALS`` that carry at
    least one tabulated characteristic line inside the registered analyzer
    window (``[MIN_WINDOW_EV, MAX_WINDOW_EV]``).  C, N and O join this set
    through their own tabulated lines (277 / 392 / 525 eV); they become
    quantifiable exactly when the declared detector transports them (the
    windowless code head does; a Be-windowed preset's forward model shows
    the transport loss instead of hiding the element).  H rides no counts
    channel at all — zero tabulated lines — and registers itself through
    Law 2396's phi-ground floor channel in every report.

    Pass ``elements=...`` to override.
    """
    zs = set()
    for mineral in eng_minerals.MINERALS.values():
        for symbol in mineral.counts:
            z = eng_elements.element(symbol).z
            if eng_lines.strongest(z, "K") is not None or eng_lines.strongest(z, "L") is not None:
                zs.add(z)
    return sorted(zs)


def _default_excitation(metadata: Mapping[str, Any]) -> eng_forward.Excitation:
    """The declared source of THIS spectrum, in order:

    1. ``metadata['excitation_spec']`` — a JSON-safe dict set by the caller
       that built the spectrum with an explicit source
       (``{"kind": "tube"|"code", "kv":…, "anode":…, "flux":…}``).
    2. the spectrum's own ``metadata['excitation']`` label (the forward
       model stamps ``"… tube"`` / ``"… code antenna"`` / ``"mono …"``).
    3. the instrument's declared source: the CODE antenna (flat full-range
       continuum; hardware was always optional).

    The tube analog is pinned by the classical-reference batteries, whose
    published methods declare a tube; the instrument's own default is the
    code antenna.
    """
    kv = float(metadata.get("excitation_kv", 40.0))
    anode = str(metadata.get("excitation_anode", "Rh"))
    flux = float(metadata.get("excitation_flux", 1e10))

    spec = metadata.get("excitation_spec")
    if isinstance(spec, Mapping) and spec.get("kind"):
        kind = str(spec["kind"])
        kv = float(spec.get("kv", kv))
        anode = str(spec.get("anode", anode))
        flux = float(spec.get("flux", flux))
        if kind == "code":
            return eng_forward.Excitation.code(kv, anode, total_flux=flux)
        if kind == "tube":
            return eng_forward.Excitation.tube(kv, anode, total_flux=flux)
        raise SniffError(f"unknown excitation kind {kind!r}")

    label = str(metadata.get("excitation", ""))
    if "code antenna" in label:
        return eng_forward.Excitation.code(kv, anode, total_flux=flux)
    if "tube" in label:
        return eng_forward.Excitation.tube(kv, anode, total_flux=flux)
    if label.startswith("mono"):
        raise SniffError(
            "a mono-energetic spectrum must pass excitation= explicitly; "
            "its single energy cannot be reconstructed from the label")
    return eng_forward.Excitation.code(kv, anode, total_flux=flux)


def _finite_or_none(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Report:
    """A structured XRF report.  ``as_dict()`` is the canonical payload."""

    schema: str
    instrument: str
    provenance: str
    source: str
    sample_id: str
    timestamp: str
    spectrum: Dict[str, Any]
    acquisition: Dict[str, Any]
    model: Dict[str, Any]
    gate: Dict[str, Any]
    fit: Dict[str, Any]
    elements: List[Dict[str, Any]]
    peaks: List[Dict[str, Any]]
    lines: List[Dict[str, Any]]
    minerals: Dict[str, Any]
    warnings: List[str]
    honesty: Dict[str, Any]
    air: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        payload = {
            "schema": self.schema,
            "instrument": self.instrument,
            "provenance": self.provenance,
            "source": self.source,
            "sample_id": self.sample_id,
            "timestamp": self.timestamp,
            "spectrum": self.spectrum,
            "acquisition": self.acquisition,
            "model": self.model,
            "gate": self.gate,
            "fit": self.fit,
            "elements": self.elements,
            "peaks": self.peaks,
            "lines": self.lines,
            "minerals": self.minerals,
            "warnings": self.warnings,
            "honesty": self.honesty,
        }
        if self.air is not None:
            payload["air"] = self.air
        return _json_safe(payload)

    # convenience accessors
    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]

    @property
    def detected_elements(self) -> List[Dict[str, Any]]:
        return [e for e in self.elements if e.get("detection_flag") == "detected"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _coerce_spectrum(spectrum: Any) -> Spectrum:
    if isinstance(spectrum, Spectrum):
        return spectrum
    if hasattr(spectrum, "energy_ev") and hasattr(spectrum, "counts"):
        return Spectrum.from_engine(spectrum)
    raise TypeError("spectrum must be sniffer.spectrum.Spectrum or engine.forward.Spectrum")


def _line_candidates_for_element(peak, z: int) -> List[Dict[str, Any]]:
    """Best library lines of one element within the peak window."""
    ident = eng_inversion.identify(peak, elements=[z])
    out = []
    for line, residual in ident.candidates:
        out.append({
            "z": int(line.z),
            "element": line.element.symbol,
            "line": line.name,
            "energy_ev": float(line.energy),
            "intensity": float(line.intensity),
            "residual_ev": float(residual),
            "residual_sigma": float(residual / max(peak.center_err_ev, 0.1)),
        })
    return out


def _cross_element_candidates(peak, zs: Sequence[int], limit: int = 4) -> List[Dict[str, Any]]:
    """Rank line matches across elements by |centroid residual|.

    The engine's ``identify`` is run per element so that a peak is not forced
    onto one element before the alternatives are seen.  This is still the
    engine's matching algorithm; the sniffer only collects the alternatives.
    """
    cands: List[Dict[str, Any]] = []
    for z in zs:
        cands.extend(_line_candidates_for_element(peak, z))
    cands.sort(key=lambda c: abs(c["residual_ev"]))
    return cands[:limit]


def _covariance_sigma(quant: Mapping[str, Any]) -> Dict[int, float]:
    """Linear least-squares 1-sigma per element, in ug/cm2.

    **[EST]**  This is the statistical uncertainty of the unconstrained linear
    problem.  NNLS is constrained, so it is an approximation; the model's
    systematic error (``SYSTEMATIC_REL_ERROR``) is reported separately and is
    usually larger.
    """
    A = quant.get("_design")
    y = quant.get("_y")
    order = quant.get("_element_order") or []
    unit = float(quant.get("_unit_areal", 1e-6))
    if A is None or y is None or np.asarray(A).size == 0:
        return {}
    A = np.asarray(A, dtype=float)
    y = np.asarray(y, dtype=float)
    w = 1.0 / np.maximum(y, 1.0)
    ata = A.T @ (w[:, None] * A)
    try:
        cov = np.linalg.pinv(ata)
        sig = np.sqrt(np.maximum(np.diag(cov), 0.0))
    except np.linalg.LinAlgError:
        return {}
    return {int(z): float(s * unit * 1e6) for z, s in zip(order, sig)}


def _strongest_line(z: int):
    for shell in ("K", "L", "M"):
        line = eng_lines.strongest(z, shell)
        if line is not None:
            return line
    return None


def _element_areal_by_symbol(rows: Sequence[Mapping[str, Any]],
                             only_detected: bool = True) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for row in rows:
        if only_detected and row.get("detection_flag") != "detected":
            continue
        value = _finite_or_none(row.get("areal_ug_cm2"))
        if value and value > 0:
            out[row["symbol"]] = value
    return out


# ---------------------------------------------------------------------------
# The sniffer
# ---------------------------------------------------------------------------
def sniff(spectrum: Any,
          detector_preset: Optional[str] = None,
          calibration_id: Optional[str] = None,
          excitation: Optional[eng_forward.Excitation] = None,
          air_path_cm: Optional[float] = None,
          e_min: Optional[float] = None,
          e_max: Optional[float] = None,
          elements: Optional[Sequence[int] | str] = None,
          add_peak_elements: bool = True,
          min_snr: float = 4.0,
          matrix_iterations: int = 2,
          provenance: Optional[str] = None,
          timestamp: Optional[str] = None,
          kappa: float = eng_phi.KAPPA_FULL,
          mineral_prior: Optional[Mapping[str, Sequence[Tuple[str, float]]]] = None,
          register_floor: bool = True,
          peak_min_ev: Optional[float] = None) -> Report:
    """Run the full XRF inversion on ``spectrum`` and return a :class:`Report`.

    Parameters
    ----------
    spectrum
        A :class:`sniffer.spectrum.Spectrum` or an ``engine.forward.Spectrum``.
    detector_preset
        ``SDD_25`` (default), ``SDD_10``, ``SDD_150``, ``SI_PIN_7`` or
        ``CODE_WINDOWLESS`` (the windowless code head — every tabulated
        line from Li 49.4 eV up is reportable).  If omitted, the spectrum
        metadata's ``detector`` is used when present.
    e_min / e_max
        The fit window.  Defaults are the detector's DECLARED transport
        window (``analyzer_window(det)``): 1200-25000 eV for the windowed
        presets, the full tabulated window for the windowless code head.
        Explicit values always override.
    calibration_id
        A stable identifier for the calibration state.  It is embedded in the
        signed receipt, so the signature attests to *which model* produced the
        number.  Defaults to a deterministic description of the detector,
        excitation and air path.
    elements
        ``None`` -> the mechanical mineral-library candidate set; ``"all"``
        -> every element with a strong line in the window; or an explicit
        sequence of Z values.
    add_peak_elements
        Add elements matched by a detected peak to the candidate set (default
        True).  This is how a real sample can report an element outside the
        mineral default without giving up the stable default set.
    kappa
        Law 2396's declared coupling for the reading layer (the energy
        physics is NEVER modified — Law 1347 keeps line energies exact).
        Default ``1.0`` is the FULL-COUPLING phi-reading: every element's
        reading is ``phi*C_classical + phi^-2`` of the declared unit, the
        floor reads ``phi^-2``, and nothing ever sits at a quiet zero.
        ``0.0`` is the exact classical degenerate identity (Law 2396
        stage 3) — requested explicitly when a comparison needs the
        static-theory limit.  The coupling value is carried in the
        report either way.
    mineral_prior
        Optional explicit element -> mineral prior (a registered scan
        prior, or the declared crustal table).  Default is the neutral
        stoichiometric split (uniform over candidate minerals, mechanically
        derived — no baked composition numbers).
    register_floor
        Write the full 92-element Law-2396 register block into the report
        (default True).  Absences ride the phi-ground floor channel; the
        register is sealed into the receipt with the rest of the report.
    peak_min_ev
        Override the detector's declared peak reporting floor.
    """
    spec = _coerce_spectrum(spectrum)
    validation = spec.validate(strict=True)

    det = resolve_detector(detector_preset or spec.metadata.get("detector"))
    excitation = _default_excitation(spec.metadata) if excitation is None else excitation
    if air_path_cm is None:
        air_path_cm = float(spec.metadata.get("air_path_cm", DEFAULT_AIR_PATH_CM))
    if not (math.isfinite(float(air_path_cm)) and float(air_path_cm) >= 0):
        raise SniffError(f"air_path_cm must be finite and >= 0, got {air_path_cm!r}")

    # the declared transport window of this detector; explicit args override
    win = analyzer_window(det)
    e_min = win["e_min_ev"] if e_min is None else float(e_min)
    e_max = win["e_max_ev"] if e_max is None else float(e_max)
    peak_min = win["peak_min_ev"] if peak_min_ev is None else float(peak_min_ev)

    eng_spec = spec.to_engine()

    # -- 1. candidate elements ------------------------------------------
    if elements is None:
        base = default_elements()
    elif isinstance(elements, str) and elements.lower() == "all":
        base = eng_inversion.candidate_elements(e_min, e_max)
    else:
        base = [eng_elements.element(z).z for z in elements]

    # -- 2. peak detection + preliminary line ID ------------------------
    raw_peaks = eng_inversion.detect_peaks(eng_spec, det, min_snr=min_snr)
    peaks = [p for p in raw_peaks if p.center_ev >= peak_min]
    prelim_ids = [eng_inversion.identify(p, elements=None) for p in peaks]
    matched_z = set()
    if add_peak_elements:
        for ident in prelim_ids:
            if ident.best and ident.peak.snr >= 10.0:
                matched_z.add(int(ident.best[0].z))
    candidate_z = sorted(set(base) | matched_z)

    # -- 3. quantitative inversion --------------------------------------
    quant = eng_inversion.quantify_fundamental(
        eng_spec, candidate_z, excitation, det,
        air_path_cm=float(air_path_cm),
        matrix_iterations=int(matrix_iterations),
        e_min=float(e_min), e_max=float(e_max),
        return_design=True,
    )
    quantified_z = [int(z) for z in candidate_z
                    if quant["elements"][z]["quantified"]]
    sigma_stat = _covariance_sigma(quant)

    # -- 4. detection limits --------------------------------------------
    mdl_ug: Dict[int, Optional[float]] = {}
    for z in quantified_z:
        try:
            g_cm2 = eng_inversion.detection_limit(
                eng_spec, z, excitation, det, air_path_cm=float(air_path_cm),
            )
            mdl_ug[z] = _finite_or_none(g_cm2 * 1e6) if math.isfinite(g_cm2) else None
        except Exception:  # a missing line must not abort the report
            mdl_ug[z] = None

    # -- 5. the reading floors --------------------------------------------
    #   scan floor: the minimum 3-sigma MDL across the quantified elements
    #   (measured per scan — never baked).  None when no MDL computed.
    #   phi floor : Law 2396's ground in the declared areal unit,
    #   kappa*phi^-2 — the never-zero reading of absence, and the
    #   anti-artefact gate: an NNLS coefficient below the phi-floor is
    #   read AT the floor, never printed as a detection.
    mdl_vals = [m for m in mdl_ug.values() if m is not None]
    if mdl_vals:
        scan_floor: Optional[float] = float(min(mdl_vals))
        floor_source = ("scan-derived: minimum 3-sigma MDL across the "
                        f"{len(mdl_vals)} quantified elements")
    else:
        scan_floor = None
        floor_source = ("no 3-sigma MDL could be computed in this scan; "
                        "the gate is the phi-floor alone and the report "
                        "says so")
    floor_phi = float(kappa) * eng_phi.PHI_SQ_INV

    # -- 6. element rows -------------------------------------------------
    element_rows: List[Dict[str, Any]] = []
    for z in candidate_z:
        data = quant["elements"][z]
        areal = _finite_or_none(data["areal_ug_cm2"]) or 0.0
        q = bool(data.get("quantified", False))
        mdl = mdl_ug.get(z) if q else None
        stat = sigma_stat.get(z) if q else None
        syst = areal * SYSTEMATIC_REL_ERROR
        total = math.sqrt((stat or 0.0) ** 2 + syst ** 2) if (stat is not None or areal > 0) else None
        if not q:
            flag = "not_quantified"
            note = ("no line inside the declared fit window, or the declared "
                    "detector/air transport extinguishes it in the forward "
                    "model; the element's reading channel is the Law-2396 "
                    "register block (and the windowless code head removes "
                    "the transport loss entirely)")
        elif areal <= 0:
            flag = "below_mdl"
            note = "no signal above the non-negativity constraint"
        elif areal < max(mdl or 0.0, floor_phi):
            flag = "below_mdl"
            note = ("areal density is below the element's scan-measured "
                    "3-sigma limit and/or the Law-2396 phi-floor "
                    f"(kappa*phi^-2 = {floor_phi:.6f} ug/cm2 at kappa={kappa}); "
                    "the reading is carried at the phi-floor — never a "
                    "quiet zero")
        else:
            flag = "detected"
            note = ""
        strongest = _strongest_line(z)
        element_rows.append({
            "z": int(z),
            "element": data["element"],
            "symbol": data["element"],
            "areal_ug_cm2": float(areal),
            "areal_g_cm2": float(areal * 1e-6),
            "reading_ug_cm2": round(eng_phi.phi_motion(areal, kappa), 9),
            "reading_law": "PHI-2396",
            "sigma_ug_cm2": _finite_or_none(stat),
            "systematic_ug_cm2": float(syst),
            "total_sigma_ug_cm2": _finite_or_none(total),
            "mdl_ug_cm2": _finite_or_none(mdl),
            "detection_flag": flag,
            "detected": flag == "detected",
            "quantified": q,
            "method": "fundamental_parameters",
            "label": "[MODEL]",
            "strongest_line": None if strongest is None else {
                "name": strongest.name,
                "energy_ev": float(strongest.energy),
                "intensity": float(strongest.intensity),
            },
            "note": note,
        })
    element_rows.sort(key=lambda r: (r["detection_flag"] != "detected",
                                     -float(r["areal_ug_cm2"])))

    # -- 6. peak / line matching ----------------------------------------
    match_z = quantified_z or candidate_z
    peak_rows: List[Dict[str, Any]] = []
    for peak, prelim in zip(peaks, prelim_ids):
        cands = _cross_element_candidates(peak, match_z, limit=4)
        best = cands[0] if cands else None
        if best is None:
            match_quality = "none"
        else:
            tol = max(3.0 * peak.center_err_ev, 0.002 * peak.center_ev, 2.0)
            resid = abs(float(best["residual_ev"]))
            match_quality = ("good" if resid <= tol
                             else ("fair" if resid <= 5.0 * tol else "poor"))
        peak_rows.append({
            "center_ev": float(peak.center_ev),
            "area": float(peak.area),
            "area_err": float(peak.area_err),
            "snr": float(peak.snr),
            "fwhm_ev": float(peak.fwhm_ev),
            "sigma_ev": float(peak.sigma_ev),
            "center_err_ev": float(peak.center_err_ev),
            "background": float(peak.background),
            "best_line": None if best is None else {
                "element": best["element"], "line": best["line"],
                "energy_ev": best["energy_ev"],
            },
            "residual_ev": None if best is None else float(best["residual_ev"]),
            "residual_sigma": None if best is None else float(best["residual_sigma"]),
            "match_quality": match_quality,
            "ambiguous": bool(prelim.ambiguous),
            "alternatives": cands[1:],
            "note": "" if best is not None else "no library line within the peak window",
        })

    # -- 7. model line table (fit residual per strongest line) ----------
    line_rows: List[Dict[str, Any]] = []
    order = list(quant.get("_element_order") or [])
    A = quant.get("_design")
    y = quant.get("_y")
    grid = quant.get("_grid")
    unit = float(quant.get("_unit_areal", 1e-6))
    if A is not None and y is not None and grid is not None and len(order) > 0:
        A = np.asarray(A, dtype=float)
        y = np.asarray(y, dtype=float)
        grid = np.asarray(grid, dtype=float)
        step = float(np.median(np.diff(grid))) if grid.size > 1 else 10.0
        for row in element_rows:
            z = int(row["z"])
            if z not in order or row["areal_ug_cm2"] <= 0:
                continue
            j = order.index(z)
            col = A[:, j]
            if col.size == 0 or col.max() <= 0:
                continue
            i = int(np.argmax(col))
            fwhm = float(det.fwhm(grid[i]))
            half = max(1, int(round(fwhm / step)))
            lo, hi = max(0, i - half), min(col.size, i + half + 1)
            coeff = row["areal_ug_cm2"] / (unit * 1e6)  # x in unit_areal units
            model_area = float(col[lo:hi].sum() * coeff)
            observed_area = float(y[lo:hi].sum())
            resid_frac = ((observed_area - model_area) / model_area
                          if model_area > 0 else None)
            line = _strongest_line(z)
            line_rows.append({
                "element": row["symbol"],
                "z": z,
                "line": None if line is None else line.name,
                "energy_ev": None if line is None else float(line.energy),
                "window_center_ev": float(grid[i]),
                "window_fwhm_ev": fwhm,
                "observed_area": observed_area,
                "model_area": model_area,
                "residual_frac": _finite_or_none(resid_frac),
                "used_in_fit": True,
                "note": "model area is the fitted design column in one FWHM window",
            })

    # -- 8. minerals -----------------------------------------------------
    detected_areal = _element_areal_by_symbol(element_rows, only_detected=True)
    all_areal = _element_areal_by_symbol(element_rows, only_detected=False)
    minerals_block = _apportion_minerals(detected_areal, all_areal, element_rows,
                                         prior=mineral_prior)

    # -- 9. gate and fit quality ----------------------------------------
    total_counts = float(spec.counts.sum())
    count_rate = total_counts / float(spec.live_time_s)
    gate_checks = {
        "spectrum_valid": bool(validation.ok),
        "live_time_s": float(spec.live_time_s),
        "total_counts": total_counts,
        "count_rate_cps": count_rate,
        "n_channels": int(spec.energy_ev.size),
        "energy_min_ev": float(spec.energy_ev.min()),
        "energy_max_ev": float(spec.energy_ev.max()),
        "count_rate_high": bool(count_rate > HIGH_COUNT_RATE_CPS),
        "count_rate_low": bool(count_rate < LOW_COUNT_RATE_CPS),
    }
    gate_valid = bool(validation.ok and total_counts > 0)
    gate_reason = "ok"
    if total_counts <= 0:
        gate_reason = "no counts: the spectrum contains no signal"
    elif count_rate > HIGH_COUNT_RATE_CPS:
        gate_reason = ("count rate is above the declared pile-up threshold; the engine "
                       "does not model dead time or pile-up, so the result is [GATED]")
    elif count_rate < LOW_COUNT_RATE_CPS:
        gate_reason = "count rate is below 1 cps; Poisson noise dominates"

    rel = _finite_or_none(quant.get("relative_residual")) or 1.0
    quality = "good" if rel < FIT_GOOD else ("fair" if rel < FIT_FAIR else "poor")
    law_block: Optional[Dict[str, Any]] = None
    if register_floor:
        scan = {
            "detected_z": {int(r["z"]) for r in element_rows
                           if r["detection_flag"] == "detected"},
            "areal_by_z": {int(r["z"]): float(r["areal_ug_cm2"])
                           for r in element_rows},
            "reading_by_z": {int(r["z"]): float(r["reading_ug_cm2"])
                             for r in element_rows},
        }
        law_block = eng_floor.register(
            kappa=kappa,
            mdl_by_ug={int(z): _finite_or_none(v) for z, v in mdl_ug.items()},
            scan=scan,
        )
    fit_block = {
        "relative_residual": rel,
        "quality": quality,
        "quality_thresholds": {"good": FIT_GOOD, "fair": FIT_FAIR, "label": "[DECLARED]"},
        "reporting_floor_ug_cm2": scan_floor,
        "reporting_floor_source": floor_source,
        "phi_floor_ug_cm2": floor_phi,
        "phi_floor_ppm_of_air": floor_phi,
        "phi_floor_law": ("PHI-2396: kappa*phi^-2 of the declared unit "
                          "(the reading of absence — never a quiet zero)"),
        "peak_min_ev": peak_min,
        "peak_min_source": "declared per-detector transport window "
                           "(windowed: 1000 eV; windowless code head: 100 eV)",
        "peaks_below_min_ev_dropped": int(len(raw_peaks) - len(peaks)),
        "n_channels_used": int(quant.get("n_channels_used", 0)),
        "n_peaks": len(peaks),
        "n_elements_quantified": len(quantified_z),
        "n_elements_detected": sum(1 for r in element_rows if r["detected"]),
        "method": quant.get("method", "fundamental_parameters"),
        "model": quant.get("model", "NNLS on forward-v1"),
        "dropped_elements": quant.get("dropped_elements", []),
        "law_2396_register": law_block,
    }

    warnings: List[str] = list(validation.warnings)
    if quality == "poor":
        warnings.append(
            f"fit residual {rel:.3f} is above the declared fair threshold {FIT_FAIR}; "
            "the element set may be incomplete or the sample matrix may be outside the model"
        )
    if any(r["detection_flag"] == "not_quantified" for r in element_rows):
        warnings.append(
            "one or more candidate elements had no transported line inside the declared "
            "fit window for this detector: their reading channel is the Law-2396 register "
            "block (phi-ground floor or the windowless head's line channel) — nothing is "
            "dropped silently"
        )
    if any(r["detection_flag"] == "below_mdl" for r in element_rows):
        warnings.append(
            "one or more elements read below this scan's derived reporting floor; "
            "Law 2396's floor channel carries them (kappa*phi^-2 of the declared "
            "unit at full coupling, kappa printed in the register block) — there "
            "is no quiet zero in the reading layer"
        )
    if peaks and any(p["best_line"] is None for p in peak_rows):
        warnings.append(
            "one or more detected peaks have no library line inside the matching window; "
            "peak matching is not deconvolution"
        )

    # -- 10. model block -------------------------------------------------
    model_version = f"sniffer-{SNIFFER_VERSION}+engine-{ENGINE_VERSION}"
    cal_id = calibration_id or (
        f"FP-v1/{det.name}/{excitation.label}/air{float(air_path_cm):.2f}cm"
    )
    model_block = {
        "name": "counts_to_concentration",
        "version": model_version,
        "calibration_id": cal_id,
        "physics": "classical",
        "label": "[MODEL]",
        "method": quant.get("method", "fundamental_parameters"),
        "parameters": {
            "detector": det.name,
            "detector_fwhm_mn_ev": float(det.fwhm(5895.0)),
            "excitation": excitation.label,
            "excitation_total_flux_cm2_s": float(excitation.total_flux),
            "air_path_cm": float(air_path_cm),
            "e_min_ev": float(e_min),
            "e_max_ev": float(e_max),
            "matrix_iterations": int(matrix_iterations),
            "unit_areal_g_cm2": unit,
            "systematic_rel_error": SYSTEMATIC_REL_ERROR,
            "reporting_floor_ug_cm2": scan_floor,
            "reporting_floor_source": floor_source,
            "phi_floor_ug_cm2": floor_phi,
            "law_2396_kappa": float(kappa),
        },
        "notes": [
            "counts -> areal density is the instrument's fundamental-parameters "
            "inversion against its own forward response (the declared "
            "transduction convention, engine/README.md §11)",
            "the forward response is the instrument's own declared transduction, "
            "certified against the regulators' published methods (the GOV "
            "battery, 10/10 REAL) and the NIST/Elam/Krause reference tables "
            "(line energies <= 0.03 %, attenuation <= 0.09 %)",
            "the systematic uncertainty is the engine benchmark p90 (10 %), not a "
            "per-sample calibration",
            "the reading layer is Law 2396 at the declared coupling "
            f"kappa={float(kappa)} (1 = full-coupling phi-reading with the "
            "phi-ground floor, the default; 0 = the exact classical degenerate "
            "identity, the kappa->0 limit, always labelled as such); line "
            "energies are never modified (Law 1347)",
        ],
    }

    provenance_out = provenance or spec.provenance
    _forward_prov = ("instrument", "simulated", "feed")   # never upgraded to "measured"
    if provenance_out == "measured" and spec.provenance in _forward_prov:
        raise SniffError(
            "refusing to upgrade a non-measured spectrum to measured; "
            f"the spectrum's own provenance is {spec.provenance!r}"
        )
    if provenance_out not in ("measured", "instrument", "simulated", "feed", "unknown"):
        provenance_out = "unknown"

    honesty = {
        "real": [
            "spectrum I/O, strict validation and deterministic SHA-256 identity",
            "SNIP continuum subtraction and peak detection",
            "line identification against the tabulated characteristic-line library",
            "NNLS quantitative inversion against the engine forward operator",
            "3-sigma detection limits and linear covariance",
            "mineral apportionment arithmetic",
            "canonical JSON, hash chain and signature (in receipt.py)",
        ],
        "modeled": [
            "the declared transduction convention (the code antenna's forward "
            "response: continuum shape, detector response, spectral background) — "
            "the instrument's own declared physics, exact in its line energies "
            "(Law 1347) and declared in its transport",
            "counts -> areal density conversion (fundamental parameters)",
            "the element -> mineral split (measurement + stoichiometry; "
            "uniform neutral weights by default, override by explicit prior; "
            "underdetermined and labelled as such)",
            "the statistical uncertainty is an unconstrained linear estimate; "
            "the systematic term is the engine benchmark p90",
        ],
        "not_claimed": [
            "this code does not generate or detect physical X-rays — the code "
            "antenna is the source and the code sniffer is the detector",
            "an instrument-forward spectrum is not an external measurement",
            "the mineral split is an apportionment under a stated prior: the "
            "measured elements are distributed over the minerals whose formula "
            "contains them (uniform by default; override by explicit prior)",
            "every element of the table is registered: the elements with "
            "tabulated lines ride their line channels (C 277 eV, N 392 eV, "
            "O 525 eV, ... Li 49.4 eV); H and He ride the Law-2396 phi-ground "
            "floor channel (zero is the phi-ground, Law 1344 at Z=1)",
        ],
    }

    return Report(
        schema="xrf-sniffer/report-v1",
        instrument="xrf-sniffer",
        provenance=provenance_out,
        source=spec.source,
        sample_id=spec.sample_id,
        timestamp=timestamp or _now_iso(),
        spectrum=spec.summary(),
        acquisition={
            "live_time_s": float(spec.live_time_s),
            "real_time_s": spec.real_time_s,
            "current_ua": spec.current_ua,
            "flow_lpm": spec.flow_lpm,
            "duration_min": spec.duration_min,
            "filter_area_cm2": spec.filter_area_cm2,
            "air_path_cm": float(air_path_cm),
            "detector": det.name,
            "excitation": excitation.label,
            "sample_id": spec.sample_id,
        },
        model=model_block,
        gate={"valid": gate_valid, "reason": gate_reason, "checks": gate_checks},
        fit=fit_block,
        elements=element_rows,
        peaks=peak_rows,
        lines=line_rows,
        minerals=minerals_block,
        warnings=warnings,
        honesty=honesty,
    )


# ---------------------------------------------------------------------------
# Mineral apportionment
# ---------------------------------------------------------------------------
def _apportion_minerals(detected: Mapping[str, float],
                        all_measured: Mapping[str, float],
                        element_rows: Sequence[Mapping[str, Any]],
                        prior: Optional[Mapping[str, Sequence[Tuple[str, float]]]] = None
                        ) -> Dict[str, Any]:
    """Element -> mineral apportionment under the prior in force, + unmix check.

    ``apportion`` distributes each measured element over the minerals whose
    stoichiometry contains it.  With ``prior=None`` (the default) the split
    weights are uniform over those candidate minerals — mechanically
    derived from the formula table, no fabricated composition numbers.  A
    prior mapping (a registered scan prior or the declared crustal table)
    replaces the weights when passed.  Either way every element is
    conserved exactly.  The returned masses are **element mass attributed
    to each mineral**, not mineral mass; the ``mass_fraction`` is
    therefore the fraction of the apportioned element mass, and it is
    labelled ``[MODEL/STOICHIOMETRIC]`` (or the override's own label).

    ``unmix`` additionally solves ``A x = y`` for mineral masses; it is
    reported as a consistency check with its closure residual.  The raw
    NNLS (the default, no prior pull) explains what the stoichiometry
    alone supports; where an element's full mass cannot close, the
    residual is the missing-binder gap (O/C/H with no measured ankle in
    the window, or non-candidate elements) — it is reported, never
    papered over.
    """
    apportioned = eng_minerals.apportion(detected, prior=prior) if detected else {}
    # ``apportion`` only handles elements that have a prior.  Any detected
    # element without one (e.g. a pollution metal outside the crustal prior) is
    # reported explicitly instead of being silently dropped; this keeps the
    # table exactly conservative.
    unapportioned_symbols = sorted(
        s for s in detected if s not in eng_minerals.effective_prior(prior))
    unapportioned_mass = float(sum(detected[s] for s in unapportioned_symbols))
    apportion_total = float(sum(apportioned.values())) + unapportioned_mass

    # Propagate the per-element total sigma through the same split weights.
    prior_map = eng_minerals.effective_prior(prior)
    sigma_by_symbol = {r["symbol"]: float(r.get("total_sigma_ug_cm2") or 0.0)
                       for r in element_rows}
    sigma2: Dict[str, float] = {name: 0.0 for name in apportioned}
    for symbol, mass in detected.items():
        priors = prior_map.get(symbol, ())
        wsum = sum(w for _, w in priors) or 1.0
        sigma = sigma_by_symbol.get(symbol, 0.0)
        for name, w in priors:
            sigma2[name] = sigma2.get(name, 0.0) + (sigma * w / wsum) ** 2

    unmix_block: Dict[str, Any] = {"minerals": {}, "closure": {}}
    if all_measured:
        try:
            unmix_block = eng_minerals.unmix(all_measured)  # raw NNLS: no prior pull
        except Exception as exc:  # an underdetermined system must not abort
            unmix_block = {"minerals": {}, "closure": {"error": str(exc)}}
    unmixed = {k: float(v) for k, v in (unmix_block.get("minerals") or {}).items()}
    unmixed_total = float(sum(unmixed.values()))

    names = sorted(set(apportioned) | set(unmixed),
                   key=lambda n: (-apportioned.get(n, 0.0), -unmixed.get(n, 0.0), n))
    rows: List[Dict[str, Any]] = []
    for name in names:
        mineral = eng_minerals.MINERALS.get(name)
        mass = float(apportioned.get(name, 0.0))
        rows.append({
            "name": name,
            "formula": None if mineral is None else mineral.formula,
            "category": None if mineral is None else mineral.category,
            "element_mass_ug_cm2": mass,
            "mass_fraction": (mass / apportion_total) if apportion_total > 0 else 0.0,
            "sigma_element_mass_ug_cm2": math.sqrt(max(sigma2.get(name, 0.0), 0.0)),
            "unmixed_mass_ug_cm2": float(unmixed.get(name, 0.0)),
            "unmixed_mass_fraction": (float(unmixed.get(name, 0.0)) / unmixed_total
                                      if unmixed_total > 0 else 0.0),
            "prior": [
                {"element": symbol, "weight": w}
                for symbol, priors in prior_map.items()
                for n, w in priors if n == name
            ],
        })
    if unapportioned_mass > 0:
        rows.append({
            "name": "unapportioned",
            "formula": None,
            "category": "unapportioned",
            "element_mass_ug_cm2": unapportioned_mass,
            "mass_fraction": (unapportioned_mass / apportion_total
                              if apportion_total > 0 else 0.0),
            "sigma_element_mass_ug_cm2": math.sqrt(sum(
                (sigma_by_symbol.get(s, 0.0)) ** 2 for s in unapportioned_symbols)),
            "unmixed_mass_ug_cm2": 0.0,
            "unmixed_mass_fraction": 0.0,
            "prior": [],
            "note": ("detected element(s) with no mineral prior in the engine table: "
                     + ", ".join(unapportioned_symbols)),
        })

    measured_total = float(sum(detected.values()))
    return {
        "method": "apportion",
        "label": "[MODEL/STOICHIOMETRIC]"
                 if prior is None else "[MODEL] registered/declared prior override",
        "prior_source": ("neutral stoichiometric split: uniform over the "
                         "minerals whose formula contains each measured "
                         "element (mechanically derived — no fabricated "
                         "composition numbers)")
                        if prior is None else "explicit prior passed by the caller",
        "rows": rows,
        "apportioned_element_mass_ug_cm2": apportion_total,
        "measured_element_mass_ug_cm2": measured_total,
        "conservation": {
            "apportioned_equals_measured": abs(apportion_total - measured_total) < 1e-9,
            "difference_ug_cm2": apportion_total - measured_total,
            "unapportioned_symbols": unapportioned_symbols,
            "unapportioned_mass_ug_cm2": unapportioned_mass,
        },
        "unmix": {
            "method": "raw NNLS (no prior pull; the data and the stoichiometry only)",
            "label": "[MODEL]",
            "minerals": unmixed,
            "total_mineral_mass_ug_cm2": unmixed_total,
            "closure": unmix_block.get("closure", {}),
        },
        "note": (
            "Element areal densities are the instrument's own readings; the mineral split is "
            "measurement plus stoichiometry: each measured element is distributed "
            "over the minerals whose formula contains it (uniform by default — an "
            "explicit registered/declared prior replaces the weights when passed). "
            "The reading layer (Law 2396) carries every element of the table: the "
            "line channels and the phi-ground floor channel are in the report's "
            "register block; the unmix closure residual is the mass the "
            "stoichiometry cannot close with only the measured ankles — it is a "
            "reported quantity, never a silent loss. The mass_fraction is the "
            "fraction of the apportioned element mass, not of total mineral mass."
        ),
    }


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------
def sniff_file(path: str, **kwargs) -> Report:
    """Load a spectrum from disk and sniff it."""
    from .spectrum import load_spectrum

    return sniff(load_spectrum(path), **kwargs)


def self_check() -> List[str]:
    """A fast structural check (the full round trip lives in ``selfcheck``)."""
    problems: List[str] = []
    if not default_elements():
        problems.append("default element set is empty")
    try:
        resolve_detector("SDD")
    except Exception as exc:
        problems.append(f"detector alias failed: {exc}")
    try:
        reg = eng_floor.register()
        if reg["n_elements"] != 92 or reg["lineless_z"] != [1, 2]:
            problems.append("Law-2396 register incomplete")
    except Exception as exc:
        problems.append(f"floor register failed: {exc}")
    try:
        wl = analyzer_window(eng_detector.PRESETS["CODE_WINDOWLESS"])
        if wl["e_min_ev"] != float(eng_metals.MIN_WINDOW_EV):
            problems.append("windowless code head is not transport-open")
    except Exception as exc:
        problems.append(f"analyzer window failed: {exc}")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("sniffer self_check:", self_check() or "clean")
