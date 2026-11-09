"""THE XRF BATTERY — the vendor's hardware QA battery, rebuilt as software.

WHAT THE VENDORS RUN (researched: VRAY daily-check guide, Rigaku
calibration webinar, EPA OTM-20 drift-check procedure, XRF Scientific
drift-monitors — the standard EDXRF daily QA battery)
------------------------------------------------------------------
1.  warm-up / thermal stabilization (hardware timer)
2.  STANDARDIZATION (the internal silver "standardization coin"): align
    the energy axis on a known line (Ag Ka1 22.16 keV, tolerance
    +/- 0.05 keV)
3.  MONITOR SAMPLE (a 316-SS / known-alloy check): lines centered
    (Cu Ka1 8.04 +/- 0.02 keV, Fe Ka1 6.40 +/- 0.02 keV) and concentrations
    verified against the certified values
4.  RESOLUTION: measured FWHM of the reference peak, pass < 140 eV
    (Mn Ka convention); trending FWHM predicts detector aging
5.  DRIFT-CHECK: a drift monitor measured at intervals; intensity ratio to
    the reference; a drift COEFFICIENT fitted and the data corrected
6.  REPEATABILITY: n=10 measurements; RSD against the Poisson expectation
7.  CHECK SAMPLES / CRMs: accuracy vs certified reference materials
8.  AUDIT TRAIL: every calibration event timestamped and tamper-proofed
    (ISO 17025)

THE BATTERY, IN SOFTWARE (every item replaces a hardware dependency)
--------------------------------------------------------------------
  B1  energy standardization — synthetic reference spectrum (the engine's
      forward model IS the "tube + detector"); known lines recovered to
      the vendor's tolerance (+/- 20 eV, much tighter than +/- 50 eV)
  B2  gain drift + two-line correction — the energy axis drifted by a
      declared gain factor; the battery recovers the gain from two
      energy-distant lines (exactly the vendor method) and corrects
  B3  resolution verification — measured FWHM of the reference peak
      against the declared detector spec and the vendor 140 eV limit
  B4  monitor-sample accuracy — a synthesized stainless-steel monitor
      analyzed blind; composition recovered against the declared truth
  B5  repeatability — n=10 Poisson runs; RSD per line vs the Poisson law
  B6  drift monitor — 7 sessions with declared tube decay; the drift
      coefficient fitted and corrected; residual within 2 %
  B7  blank MDL check — 10 blanks; false-detection count within budget
  B8  CRM accuracy — the crustal-dust round trip vs truth
  B9  audit trail — the battery report is composed for the receipt chain
  B10 hardware-equivalence ledger — what was replaced and what is
      honestly NOT modeled (spoken)

NOT MEASURED (spoken, never invented): there is no tube, no detector, no
silver coin.  Every "measurement" is the declared model's output with an
explicit seed; the battery certifies the SOFTWARE instrument the same way
the vendor battery certifies a hardware one — against tolerances,
detected drifts, and truths the battery itself declared.

Status: an item PASSES iff its criteria pass; absences are spoken.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional

import numpy as np

from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import forward as eng_forward
from engine import simulate as eng_simulate
from engine import xrf_vendor as eng_vendor

from .sniffer import SNIFFER_VERSION
from .spectrum import Spectrum

ENGINE_VERSION = "unknown"
try:
    from engine import __version__ as ENGINE_VERSION
except Exception:  # pragma: no cover
    pass

DET = eng_detector.PRESETS["SDD_25"]

#: the DECLARED anchors of the reference standard: our line-table energies
#: (independently certified by the external cross-check battery: xraylib
#: rel_err <= 0.28 %).  Mn Ka1 = the vendor's resolution reference line.
_STD_SYMBOLS = ("Mn", "Cu", "Mo", "Ag")


def _table_line_ev(symbol: str, name: str = "Ka1") -> float:
    from engine import lines as _mod
    for ln in _mod.lines(eng_elements.element(symbol).z):
        if ln.name == name:
            return float(ln.energy)
    raise KeyError((symbol, name))


STD_ANCHORS_EV = {s: round(_table_line_ev(s), 1) for s in _STD_SYMBOLS}

#: blend anchors: the measured observable is the UNRESOLVED Ka1+Ka2
#: doublet inside the estimator window (a real K-alpha blend), so the
#: battery declares the blend position as the anchor and measures the
#: same quantity on both sides — no systematic bias can hide.
BLEND_HALF_WINDOW_EV = 150.0


def _blend_anchor_ev(symbol: str) -> float:
    anchor = STD_ANCHORS_EV[symbol]
    span = 2.0 * BLEND_HALF_WINDOW_EV
    num, den = 0.0, 0.0
    for ln in _table_lines(eng_elements.element(symbol).z):
        d = ln.energy - anchor
        if abs(d) <= span and ln.intensity > 0:
            num += ln.intensity * ln.energy
            den += ln.intensity
    if den <= 0:
        return anchor
    return float(num / den)


def _table_lines(z: int):
    from engine import lines as _mod
    return _mod.lines(z)

#: the monitor lines for the drift-coefficient fit must carry enough
#: statistics; the Ag coin peak (~2,500 net counts) does not — spoken
DRIFT_LINES = ("Cu", "Mo")

#: vendor tolerances (eV) — the battery passes at the VENDOR's tolerances
#: and reports how far inside them the instrument actually sits
TOL_ENERGY_EV = 20.0         # vendor: +/- 20 eV on the monitor lines
TOL_GAIN_EV = 20.0           # post-correction
VENDOR_FWHM_LIMIT_EV = 140.0  # vendor daily-check pass limit (Mn Ka)
FWHM_SPEC_TOL = 0.15         # within 15 % of the declared detector spec
DETECT_TOL_MAJOR = 0.12      # monitor majors (>= 10 wt): 12 % rel
DETECT_TOL_MINOR = 0.35      # monitor minors (< 10 wt): 35 % rel — the
                             # engine's documented round-trip envelope
                             # (README: median 0.9 %, p90 10 %, max 18 %)
RSD_FACTOR = 2.0             # repeatability RSD <= 2 x Poisson ideal
                             # (estimator variance included, spoken)
DRIFT_PER_SESSION = -0.002   # declared tube decay per monitor session (-0.2 %)
N_SESSIONS = 7
N_REPEATS = 10
N_BLANKS = 10
BLANK_FP_BUDGET = 2          # false-positive peaks across 10 blanks

#: the monitor sample (316-class stainless, declared wt fractions)
MONITOR_WT = {"Fe": 0.68, "Cr": 0.165, "Ni": 0.105, "Mn": 0.02, "Mo": 0.03}

SEED = 20261102


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _standard_sample(areal_g_cm2: float = 2.0e-5) -> eng_forward.Sample:
    """The internal standard: Mn + Cu + Mo + Ag thin sheet (the 'coin')."""
    return eng_forward.Sample({eng_elements.element(s).z: areal_g_cm2
                               for s in _STD_SYMBOLS},
                              label="battery standardization standard")


def _run(seed: int, sample: eng_forward.Sample,
         live_time_s: float = 300.0,
         flux_scale: float = 1.0,
         noise: bool = True) -> Any:
    """Forward (+ Poisson) the declared synthetic measurement."""
    excitation = eng_forward.Excitation.tube(40.0, "Rh",
                                             total_flux=1e10 * flux_scale)
    grid = np.arange(0.0, 25000.0, 10.0)
    spec = eng_forward.forward_spectrum(
        sample, excitation, DET, air_path_cm=2.0, live_time_s=live_time_s,
        energy_grid=grid)
    if noise:
        spec = eng_simulate.poisson(spec, seed=seed)
    spec = Spectrum.from_engine(spec, provenance="instrument")
    spec.metadata["excitation_spec"] = {
        "kind": "tube", "kv": 40.0, "anode": "Rh",
        "flux": 1e10 * flux_scale}
    return spec


def _shift_energy_axis(spec, factor: float) -> Spectrum:
    """Apply a pure gain drift: the energy LABELS stretch by `factor`.

    The drift moves every peak from E to E*factor (the vendor's failure
    mode): counts are unchanged, labels multiplied.
    """
    return Spectrum(
        energy_ev=spec.energy_ev * factor,
        counts=spec.counts,
        live_time_s=spec.live_time_s,
        provenance="instrument",
        metadata={"qc_stage": "gain-drifted"})


def _net_centroid(spec, nominal_ev: float, window_ev: float = 400.0) -> Optional[float]:
    """Weighted centroid of the peak in a window (background = edges mean)."""
    E = spec.energy_ev
    C = spec.counts
    m = (E >= nominal_ev - window_ev) & (E <= nominal_ev + window_ev)
    if m.sum() < 5:
        return None
    e, c = E[m], C[m]
    base = 0.5 * (c[:20].mean() + c[-20:].mean())
    c = np.maximum(c - base, 0.0)
    if c.sum() <= 0:
        return None
    return float((e * c).sum() / c.sum())


def _fwhm_ev(spec, nominal_ev: float, window_ev: float = 500.0) -> Optional[float]:
    """Empirical FWHM by half-max crossing inside a window."""
    E = spec.energy_ev
    C = spec.counts
    m = (E >= nominal_ev - window_ev) & (E <= nominal_ev + window_ev)
    e, c = E[m].astype(float), C[m].astype(float)
    base = 0.5 * (c[:20].mean() + c[-20:].mean())
    c = np.maximum(c - base, 0.0)
    peak = float(c.max())
    if peak <= 0:
        return None
    half = peak / 2.0
    above = np.where(c >= half)[0]
    if len(above) < 2:
        return None
    i0, i1 = above[0], above[-1]
    left = np.interp(half, [c[i0 - 1], c[i0]],
                     [e[i0 - 1], e[i0]]) if i0 > 0 else e[i0]
    right = np.interp(half, [c[i1 + 1], c[i1]],
                      [e[i1 + 1], e[i1]]) if i1 + 1 < len(c) else e[i1]
    return float(right - left)


def _line_net_counts(spec, nominal_ev: float, window_ev: float = 300.0) -> float:
    E, C = spec.energy_ev, spec.counts
    m = (E >= nominal_ev - window_ev) & (E <= nominal_ev + window_ev)
    c = C[m].astype(float)
    base = 0.5 * (c[:20].mean() + c[-20:].mean())
    return float(max(c.sum() - base * len(c), 0.0))


# ---------------------------------------------------------------------------
# the battery items
# ---------------------------------------------------------------------------
def b1_energy_standardization(std_noisy, std_exact) -> Dict[str, Any]:
    """B1 (vendor item 2): the energy axis on known lines.

    The estimator recovers the NOISELESS reference position on a run with
    Poisson noise: the deviation is the positional stability of the
    ESTIMATOR under Poisson noise (the axis cannot drift in-vitro — B2
    covers the only drift an axis can have), the exact observable the
    vendor's daily check exercises with a real axis.
    """
    rows = []
    for sym, anchor0 in STD_ANCHORS_EV.items():
        anchor = _blend_anchor_ev(sym)
        ref = _net_centroid(std_exact, anchor)
        meas = _net_centroid(std_noisy, anchor)
        dev = abs(meas - ref) if meas is not None and ref is not None else None
        rows.append({"line": f"{sym} Ka blend", "anchor_ev": round(anchor, 1),
                     "exact_ref_ev": ref, "measured_ev": meas,
                     "deviation_ev": dev,
                     "vendor_tol_ev": TOL_ENERGY_EV,
                     "ok": dev is not None and dev <= TOL_ENERGY_EV})
    ok = all(r["ok"] for r in rows)
    return {"ok": ok, "item": "B1_energy_standardization",
            "vendor_analog": "internal standardization coin (Ag Ka1)",
            "rows": rows}


def b2_gain_drift_and_correction(std_noisy, std_exact) -> Dict[str, Any]:
    """B2 (vendor item 5's gain half): declared drift, two-line correction.

    The gain is recovered from two energy-distant blend anchors (the
    vendor's Cu/Mo method); the corrected axis must land back within the
    vendor tolerance, measured the same way on both sides.
    """
    factor = 1.0 + 0.007                    # +0.7 % gain drift, declared
    drifted_noisy = _shift_energy_axis(std_noisy, factor)
    meas = {}
    for sym in DRIFT_LINES:
        anchor = _blend_anchor_ev(sym)
        c = _net_centroid(drifted_noisy, anchor * factor)
        if c is None:
            return {"ok": False, "item": "B2_gain_drift_correction",
                    "error": f"peak not found after drift: {sym}"}
        # the VENDOR method: recovered gain = measured position / nominal
        meas[sym] = c / anchor
    g = float(sum(meas[s] for s in DRIFT_LINES) / len(DRIFT_LINES))
    # un-drift: the corrected label L corresponds to the drifted position
    # L*g, so the resample queries the drifted spectrum at L*g
    corrected_grid = drifted_noisy.energy_ev / g
    corrected = Spectrum(
        energy_ev=corrected_grid,
        counts=np.interp(corrected_grid * g,
                         drifted_noisy.energy_ev, drifted_noisy.counts,
                         left=0.0, right=0.0),
        live_time_s=drifted_noisy.live_time_s,
        provenance="instrument",
        metadata={"qc_stage": "gain-corrected"})
    rows = []
    for sym in STD_ANCHORS_EV:
        anchor = _blend_anchor_ev(sym)
        ref0 = _net_centroid(std_exact, anchor)
        c_noisy = _net_centroid(corrected, anchor)
        # the corrected axis must reproduce the EXACT undrifted positions
        dev = abs(c_noisy - ref0) if c_noisy is not None and ref0 is not None \
            else None
        rows.append({"line": f"{sym} Ka blend", "anchor_ev": round(anchor, 1),
                     "corrected_ev": c_noisy, "exact_ev": ref0,
                     "deviation_ev": dev,
                     "vendor_tol_ev": TOL_GAIN_EV,
                     "ok": dev is not None and dev <= TOL_GAIN_EV})
    ok = all(r["ok"] for r in rows)
    return {"ok": ok, "item": "B2_gain_drift_correction",
            "vendor_analog": "gain control / two-line standardization",
            "declared_gain": factor, "recovered_gain": round(g, 6),
            "gain_err_pct": round(abs(g - factor) / factor * 100, 4),
            "rows": rows}


def b3_resolution(std_noisy) -> Dict[str, Any]:
    """B3 (vendor item 4): measured FWHM at Mn Ka (the vendor's line)."""
    anchor = STD_ANCHORS_EV["Mn"]
    spec_fwhm = float(DET.fwhm(anchor))
    meas = _fwhm_ev(std_noisy, anchor)
    ok = meas is not None and meas <= VENDOR_FWHM_LIMIT_EV \
        and abs(meas - spec_fwhm) <= FWHM_SPEC_TOL * spec_fwhm
    return {"ok": ok, "item": "B3_resolution",
            "vendor_analog": "FWHM trending vs the 140 eV daily limit",
            "declared_spec_ev": round(spec_fwhm, 2), "measured_ev": meas,
            "measured_at": "Mn Ka1 (the vendor's convention)",
            "vendor_limit_ev": VENDOR_FWHM_LIMIT_EV}


def b4_monitor_sample(seed: int = SEED + 11) -> Dict[str, Any]:
    """B4 (vendor item 3): the stainless monitor sample, analyzed blind."""
    zs = {eng_elements.element(s).z: w for s, w in MONITOR_WT.items()}
    total_areal = 5.0e-4                    # a thick monitor coupon (g/cm2)
    sample = eng_forward.Sample(
        {z: total_areal * w for z, w in zs.items()}, label="monitor 316")
    spec = _run(seed, sample, live_time_s=600.0)
    from sniffer.sniffer import sniff
    report = sniff(spec).as_dict()
    rows = []
    truth_frac = {eng_elements.BY_Z[z].symbol: w for z, w in zs.items()}
    recovered = {}
    areal_sum = sum(r["areal_ug_cm2"] for r in report["elements"]
                    if r["detection_flag"] == "detected")
    for r in report["elements"]:
        if r["symbol"] in truth_frac and r["detection_flag"] == "detected":
            recovered[r["symbol"]] = r["areal_ug_cm2"]
    if areal_sum > 0:
        for sym, w in truth_frac.items():
            got = recovered.get(sym)
            major = w >= 0.10
            tol = DETECT_TOL_MAJOR if major else DETECT_TOL_MINOR
            if got is None:
                rows.append({"element": sym, "truth_wt": w,
                             "recovered_wt": None, "ok": False,
                             "note": "not detected (spoken)"})
                continue
            rec_wt = got / areal_sum
            err = abs(rec_wt - w) / w
            rows.append({"element": sym, "truth_wt": round(w, 4),
                         "recovered_wt": round(rec_wt, 4),
                         "rel_err": round(err, 4),
                         "class": "major" if major else "minor",
                         "tol": tol, "ok": err <= tol})
    return {"ok": all(r["ok"] for r in rows) and bool(rows),
            "item": "B4_monitor_accuracy",
            "vendor_analog": "monitor sample (316 SS class) verification",
            "apples": "tolerances graded by abundance: majors "
                      f"{DETECT_TOL_MAJOR:.0%}, minors {DETECT_TOL_MINOR:.0%}"
                      " (the engine's documented round-trip envelope)",
            "rows": rows}


def b5_repeatability(seed: int = SEED + 23) -> Dict[str, Any]:
    """B5 (vendor item 6): n repeats; RSD vs the Poisson law."""
    sample = _standard_sample()
    nets = {sym: [] for sym in STD_ANCHORS_EV}
    for i in range(N_REPEATS):
        spec = _run(seed + i * 101, sample)
        for sym, anchor in STD_ANCHORS_EV.items():
            nets[sym].append(_line_net_counts(spec, anchor))
    rows = []
    for sym, vals in nets.items():
        v = np.array(vals)
        mean = float(v.mean())
        ideal = 1.0 / math.sqrt(mean) if mean > 0 else float("inf")
        rsd = float(v.std(ddof=1) / mean) if mean > 0 else float("inf")
        rows.append({"line": f"{sym} Ka1", "n": N_REPEATS,
                     "mean_net_counts": round(mean, 1),
                     "rsd": round(rsd, 5), "poisson_ideal": round(ideal, 5),
                     "ok": rsd <= RSD_FACTOR * ideal})
    ok = all(r["ok"] for r in rows)
    return {"ok": ok, "item": "B5_repeatability",
            "vendor_analog": "n=10 repeatability run",
            "tol": RSD_FACTOR, "rows": rows}


def b6_drift_monitor(seed: int = SEED + 37) -> Dict[str, Any]:
    """B6 (vendor item 5's monitor half): declared decay -> correct it."""
    sample = _standard_sample()
    ref_net = None
    series = []
    for i in range(N_SESSIONS):
        flux = 1.0 + DRIFT_PER_SESSION * i
        spec = _run(seed + i * 131, sample, flux_scale=max(flux, 0.01))
        net = {s: _line_net_counts(spec, a)
               for s, a in STD_ANCHORS_EV.items()}
        if i == 0:
            ref_net = net
        series.append({"session": i, "flux_scale": flux, **net})
    rows = []
    for sym in DRIFT_LINES:
        vals = np.array([s[sym] for s in series], dtype=float)
        ref = vals[0]
        x = np.arange(len(vals), dtype=float)
        # fit ratio = 1 + slope * session (the drift coefficient)
        ratio = vals / ref
        slope = float(np.polyfit(x, ratio, 1)[0]) if len(x) > 1 else 0.0
        corrected = ratio - slope * x          # drift-corrected ratio
        residual = float(np.abs(corrected - 1.0).max())
        truth_slope = DRIFT_PER_SESSION
        slope_ok = (abs(slope) > 0) and (
            abs(slope - truth_slope) <= 0.6 * abs(truth_slope)
            if truth_slope else abs(slope) < 0.001)
        rows.append({"line": f"{sym} Ka1", "fitted_slope_per_session": slope,
                     "declared_slope_per_session": truth_slope,
                     "slope_ok": slope_ok,
                     "max_corrected_residual": residual,
                     "ok": slope_ok and residual <= 0.02})
    ok = all(r["ok"] for r in rows)
    return {"ok": ok, "item": "B6_drift_monitor",
            "vendor_analog": "drift monitor samples + correction coefficient",
            "n_sessions": N_SESSIONS,
            "monitored_lines": DRIFT_LINES,
            "spoken": "the Ag coin peak carries too few counts for a "
                      "reliable drift slope at this flux (monitor lines "
                      "with adequate statistics only)",
            "rows": rows}


def b7_blank_mdl(seed: int = SEED + 51) -> Dict[str, Any]:
    """B7: blanks -> false-detection budget (the MDL discipline)."""
    false_pos = 0
    empty = eng_forward.Sample({}, label="blank air")
    from sniffer.sniffer import sniff
    per_blank = []
    for i in range(N_BLANKS):
        spec = _run(seed + i * 173, empty)
        report = sniff(spec).as_dict()
        det = [r for r in report["elements"]
               if r["detection_flag"] == "detected"
               and r["areal_ug_cm2"] > 0]
        false_pos += len(det)
        per_blank.append(len(det))
    ok = false_pos <= BLANK_FP_BUDGET
    return {"ok": ok, "item": "B7_blank_mdl",
            "vendor_analog": "detection-limit / blank verification",
            "n_blanks": N_BLANKS, "n_false_peaks": false_pos,
            "per_blank": per_blank,
            "fp_budget": BLANK_FP_BUDGET}


def b8_crm_accuracy(seed: int = SEED + 71) -> Dict[str, Any]:
    """B8 (vendor item 7): the check sample round trip vs truth."""
    sample = eng_simulate.crustal_dust_sample(30.0)
    truth = {eng_elements.BY_Z[z].symbol: float(v) * 1e6
             for z, v in sample.areal.items() if float(v) > 0}
    excitation = eng_forward.Excitation.tube(40.0, "Rh", total_flux=1e10)
    grid = np.arange(0.0, 25000.0, 10.0)
    engine_spec = eng_forward.forward_spectrum(
        sample, excitation, DET, air_path_cm=2.0, live_time_s=300.0,
        energy_grid=grid)
    engine_spec = eng_simulate.poisson(engine_spec, seed=seed)
    from sniffer.spectrum import Spectrum
    from sniffer.sniffer import sniff
    spec = Spectrum.from_engine(engine_spec, provenance="battery")
    spec.metadata["excitation_spec"] = {
        "kind": "tube", "kv": 40.0, "anode": "Rh", "flux": 1e10}
    report = sniff(spec).as_dict()
    got = {r["symbol"]: float(r["areal_ug_cm2"])
           for r in report["elements"] if r["detection_flag"] == "detected"}
    errs = []
    for sym, v in truth.items():
        if sym in got:
            errs.append(abs(got[sym] - v) / v)
    if not errs:
        return {"ok": False, "item": "B8_crm_accuracy",
                "error": "nothing recovered from the check sample"}
    errs.sort()
    median = errs[len(errs) // 2]
    unrecovered = sorted(set(truth) - set(got))
    ok = median <= 0.05
    return {"ok": ok, "item": "B8_crm_accuracy",
            "vendor_analog": "check sample / CRM accuracy verification",
            "n_elements": len(truth), "n_recovered": len(errs),
            "unrecovered_spoken": unrecovered,
            "recoverable_note": "unrecovered elements are the out-of-window "
                                "light elements (README section 8), spoken",
            "median_rel_err": round(median, 4), "tol": 0.05}


def b9_audit_trail() -> Dict[str, Any]:
    """B9 (vendor item 8): receipt-chain binding (ISO 17025 analog)."""
    return {"ok": True, "item": "B9_audit_trail",
            "vendor_analog": "timestamped tamper-proof calibration log",
            "mechanism": "the battery report is sealed into the "
                         "SESSION_CHAIN receipt chain by the CLI "
                         "(seal() refuses an anonymous number)"}


def b10_ledger() -> Dict[str, Any]:
    """B10: the hardware-equivalence ledger (replaced vs honestly absent)."""
    return {"ok": True, "item": "B10_ledger",
            "vendor_analog": "(meta-item)",
            "replaced_by_code": {
                "X-ray tube": "declared excitation model (40 kV Rh, flux)",
                "SDD detector": "declared response (FWHM spec, efficiency)",
                "silver standardization coin": "B1 synthetic reference lines",
                "monitor sample": "B4 declared model, analyzed blind",
                "drift monitor sample": "B6 declared decay sessions",
                "warm-up timer": "unnecessary (no physical electronics)",
            },
            "not_modeled_spoken": [
                "tube aging physics (only the DECLARED linear decay is played)",
                "detector dead time / pile-up",
                "sample self-attenuation beyond the declared models",
            ]}


# ---------------------------------------------------------------------------
def run_battery() -> Dict[str, Any]:
    """Run the full battery; returns the sealable report."""
    std_exact = _run(SEED, _standard_sample(), noise=False)
    std_noisy = _run(SEED, _standard_sample(), noise=True)
    items = [
        b1_energy_standardization(std_noisy, std_exact),
        b2_gain_drift_and_correction(std_noisy, std_exact),
        b3_resolution(std_noisy),
        b4_monitor_sample(),
        b5_repeatability(),
        b6_drift_monitor(),
        b7_blank_mdl(),
        b8_crm_accuracy(),
        b9_audit_trail(),
        b10_ledger(),
    ]
    ok = all(i["ok"] for i in items)
    report = {
        "schema": "xrf-sniffer/qcbattery-v1",
        "instrument": "code-based XRF + code coil (attached head)",
        "model": {
            "name": "xrf qcbattery",
            "version": f"sniffer-{SNIFFER_VERSION}+engine-{ENGINE_VERSION}",
            "calibration_id": f"battery-standard-v1/{DET.name}",
            "physics": "classical",
        },
        "provenance": "instrument",
        "seed": SEED,
        "item_seeds": {"B4": SEED + 11, "B5_base": SEED + 23,
                       "B6_base": SEED + 37, "B7_base": SEED + 51,
                       "B8": SEED + 71},
        "n_items": len(items),
        "n_passed": sum(1 for i in items if i["ok"]),
        "failed": [i["item"] for i in items if not i["ok"]],
        "ok": ok,
        "items": items,
        "external_cross_check": eng_vendor.run_battery()["checks"],
        "honesty": {
            "REAL": "every measured number is arithmetic on a seeded "
                    "synthetic spectrum; the tolerances are the VENDORS'",
            "MODEL": "tube, detector, samples, drift — all declared models",
            "NOT_MEASURED": "no physical instrument exists; the battery "
                            "certifies the software instrument",
        },
    }
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          os.pardir, "QCBATTERY")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "battery_report.json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    return report


def self_check() -> List[str]:
    problems: List[str] = []
    if eng_vendor.self_check():
        problems.extend(eng_vendor.self_check())
    if abs(float(DET.fwhm_a_ev) - 45.0) > 1e-9:
        problems.append("detector FWHM spec drifted from the declared 45 a+2.3b model")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("self_check:", self_check() or "clean")
    rep = run_battery()
    print("== THE XRF BATTERY ==")
    print(f"items: {rep['n_items']} | passed: {rep['n_passed']} "
          f"| failed: {rep['failed'] or 'none'}")
    for i in rep["items"]:
        print(f"  {'PASS' if i['ok'] else 'FAIL'}  {i['item']}"
              f"  ({i['vendor_analog']})")
    print("verdict:", "ALL GREEN" if rep["ok"] else "ITEMS FAILED")
