"""THE FULL SESSION — the instrument's two ears sealed to one chain.

WHAT THE SESSION IS
-------------------
One pass of the code-based instrument, end to end:

    1. the air feed (public air-quality report — the keyless Open-Meteo
       source; AirNow/OpenAQ when keys exist, cache + stale fallback
       otherwise),
    2. the feed's element composition -> an XRF spectrum through the
       engine's forward model (Poisson noise, explicit seed) -> the full
       sniffer inversion (classical, LAW 1347-exact),
    3. THE METAL REGISTER: every metal in the registry
       (``engine/metals.py``) read through LAW 2396 at the declared
       coupling — quantified metals carry their classical term; the rest
       sit EXACTLY on the phi-ground floor (0.3819660113 ppm at kappa=1,
       the gold-in-air reading of LAW 2396),
    4. THE CODE COIL sweep (``engine/coil.py``): the deposit is read as a
       sheet across all ten 528 Hz ladder rungs; every metal is
       registered; the coil's dominant classical metal is scored against
       the XRF's dominant (the consistency gate),
    5. THE RADIO EAR WITNESS: the Wi-Fi sniffer's capture file
       (``field_computer/server/field_wifi_sniffer/captures/air_60s.txt``)
       bound by SHA-256 — the mineral ear and the radio ear on one chain,
    6. seal into the receipt chain (model.physics = "classical", the
       exact-classical discipline of the corpus's own verdict; the
       declared phi layer rides inside the signed report body).

HONESTY
-------
REAL    : the unit-exact arithmetic, the registry mechanics, the ladder
          invariant, the receipt chain, the witness hash.
MODEL   : the feed -> composition endmember model, the forward spectrum,
          the coil's declared geometry/drive/null anchor, the noise floors.
NOT     : hardware; every reading is the declared model's output, and the
          receipt says so (input provenance is carried and signed).
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from engine import air as eng_air
from engine import coil as eng_coil
from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import forward as eng_forward
from engine import metals as eng_metals
from engine import phi_laws
from engine import simulate as eng_simulate

from .air import (DEFAULT_DURATION_MIN, DEFAULT_FLOW_LPM,
                  DEFAULT_FILTER_AREA_CM2, AirReading, air_from_feed)
from .spectrum import Spectrum
from .sniffer import ENGINE_VERSION, SNIFFER_VERSION, sniff

try:  # engine version header for the receipt
    import engine as _engine_pkg
    _ENGINE_VERSION = getattr(_engine_pkg, "__version__", ENGINE_VERSION)
except Exception:  # pragma: no cover
    _ENGINE_VERSION = ENGINE_VERSION

#: The Wi-Fi sniffer's capture corpus — the radio ear (same SOUL_SEED root).
WIFI_SNIFFER_CAPTURE = ("phi-field-native-transformer", "field_computer",
                        "server", "field_wifi_sniffer", "captures",
                        "air_60s.txt")

SESSION_SCHEMA = "xrf-sniffer/session-v1"
SESSION_MODEL_NAME = "xrf+code-coil (attached)"
COIL_VERSION = "coil-1.0.0"


def wifi_witness(capture_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Bind the Wi-Fi sniffer's capture file by SHA-256 (the radio ear).

    Returns None, with the reason carried by the caller, when the capture
    file is absent — never a fabricated witness.
    """
    if capture_path is None:
        here = Path(__file__).resolve()
        root = here.parents[2]                      # .../32_PHI_PHYSICS
        path = root.joinpath(*WIFI_SNIFFER_CAPTURE)
    else:
        path = Path(capture_path)
    if not path.exists():
        return None
    data = path.read_bytes()
    lines = data.decode("utf-8", errors="replace").splitlines()
    frames = [ln for ln in lines if ln.startswith("F ")]
    # radio channels: the first token after "F " is the channel number;
    # payload bytes can leak into that column after NUL truncation, so
    # only pure 1-3 digit tokens are channels — anything else is payload
    channels = sorted(
        {t for ln in frames if len(tokens := ln.split()) > 1
         for t in (tokens[1],) if re.fullmatch(r"\d{1,3}", t)})
    return {
        "kind": "wifi_sniffer_capture",
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "frames": len(frames),
        "channels": channels,
        "note": ("the Wi-Fi sniffer's raw capture; the radio ear of the "
                 "instrument, sealed onto the same receipt chain as the "
                 "mineral ear (SOUL_SEED = 1900 trust root)"),
    }


def wifi_witness_expected_path(capture_path: Optional[str] = None) -> str:
    """Where the Wi-Fi sniffer capture is expected (for the absent record)."""
    if capture_path is not None:
        return str(Path(capture_path))
    here = Path(__file__).resolve()
    root = here.parents[2]                      # .../32_PHI_PHYSICS
    return str(root.joinpath(*WIFI_SNIFFER_CAPTURE))


def _feed_to_sample(reading: AirReading) -> Optional[eng_forward.Sample]:
    """Feed element loading (ug/m3) -> filter areal densities (g/cm2)."""
    elements = reading.elements_ug_m3 or {}
    if not elements:
        return None
    volume_m3 = eng_air.sampled_volume_m3(
        DEFAULT_FLOW_LPM, DEFAULT_DURATION_MIN)
    areal: Dict[int, float] = {}
    for symbol, c_ug_m3 in elements.items():
        try:
            z = eng_elements.element(symbol).z
        except (KeyError, ValueError):
            continue
        # exact chain: ug/m3 * m3 = ug on the filter; / area (cm2) = ug/cm2
        areal_ug_cm2 = (float(c_ug_m3) * volume_m3 / DEFAULT_FILTER_AREA_CM2)
        if areal_ug_cm2 > 0:
            areal[z] = areal_ug_cm2 * 1e-6          # g/cm2
    if not areal:
        return None
    return eng_forward.Sample(areal,
                              label="feed composition -> filter deposit")


def full_session(lat: float, lon: float,
                 kappa: float = phi_laws.KAPPA_FULL,
                 seed: int = 2026110100,
                 detector_preset: Optional[str] = None,
                 calibration_id: Optional[str] = None,
                 air_path_cm: float = 0.0,
                 cache_only: bool = False,
                 cache_dir: Optional[str] = None,
                 ttl_s: float = 6 * 3600.0,
                 source: str = "auto",
                 fetcher: Optional[Callable[[float, float, float], Dict[str, Any]]] = None,
                 wifi_capture: Optional[str] = None,
                 timestamp: Optional[str] = None) -> Dict[str, Any]:
    """Run one full session and return its report payload (pre-seal)."""
    reading = air_from_feed(lat, lon, cache_only=cache_only,
                            cache_dir=cache_dir, ttl_s=ttl_s, source=source,
                            fetcher=fetcher)

    sample = _feed_to_sample(reading)
    spectrum_block: Optional[Dict[str, Any]] = None
    report_dict: Optional[Dict[str, Any]] = None
    spectrum_obj: Optional[Spectrum] = None

    if sample is not None:
        det = eng_detector.PRESETS[detector_preset or "CODE_WINDOWLESS"]
        excitation = eng_forward.Excitation.code(
            40.0, "Rh", total_flux=1e10)
        import numpy as _np
        grid = _np.arange(0.0, 25000.0, 10.0)
        engine_spec = eng_forward.forward_spectrum(
            sample, excitation, det, air_path_cm=air_path_cm,
            live_time_s=300.0, energy_grid=grid)
        engine_spec = eng_simulate.poisson(engine_spec, seed=seed)
        spec = Spectrum.from_engine(engine_spec, provenance="instrument")
        spec.flow_lpm = DEFAULT_FLOW_LPM
        spec.duration_min = DEFAULT_DURATION_MIN
        spec.filter_area_cm2 = DEFAULT_FILTER_AREA_CM2
        spec.sample_id = f"feed composition @ {lat:+.4f},{lon:+.4f}"
        spec.source = f"engine.forward <- air feed ({reading.source})"
        spec.metadata.update({
            "air_path_cm": air_path_cm,
            "detector": det.name,
            "excitation_kv": 40.0,
            "excitation_anode": "Rh",
            "excitation_flux": 1e10,
            "noise": "poisson",
            "seed": int(seed),
        })
        # the truth block: what was fed in, in areal ug/cm2 (like cmd_simulate)
        spec.metadata["truth_elements_ug_cm2"] = {
            eng_elements.element(z).symbol: float(v) * 1e6
            for z, v in sample.areal.items() if float(v) > 0
        }
        xrf = sniff(spec, detector_preset=detector_preset,
                    calibration_id=calibration_id, air_path_cm=air_path_cm,
                    provenance="instrument", timestamp=timestamp,
                    excitation=excitation)
        report_dict = xrf.as_dict()
        spectrum_obj = spec
        spectrum_block = {
            "provenance": "instrument",
            "seed": int(seed),
            "channels": int(spec.energy_ev.size),
            "total_counts": float(spec.counts.sum()),
            "source": spec.source,
            "truth_elements_ug_cm2": spec.metadata.get("truth_elements_ug_cm2"),
            "note": "model forward of the feed's composition, Poisson noise, "
                    "the instrument's forward response; seed-logged",
        }

    # --- the metal register ------------------------------------------------
    areal_by_symbol: Dict[str, float] = {}
    if report_dict:
        for row in report_dict["elements"]:
            if row["detection_flag"] == "detected" and row["areal_ug_cm2"] > 0:
                areal_by_symbol[row["symbol"]] = float(row["areal_ug_cm2"])

    register = metals_register(areal_by_symbol, kappa=kappa,
                               quantified_symbols=set(areal_by_symbol))

    # --- the code coil sweep ----------------------------------------------
    coil = eng_coil.sweep_deposit(areal_by_symbol, kappa=kappa)
    tuning = eng_coil.tuning_table()

    xrf_dominant = (max(sorted(areal_by_symbol.items()), key=lambda kv: kv[1])[0]
                    if areal_by_symbol else None)
    coil_dominant = coil.get("dominant_classical_metal")

    # THE COIN-CLASS CHECK: every metal the XRF saw in the deposit is read
    # coil-style at the declared design point (528 Hz, 0.10 m, 25 mm class).
    # Metals below the analyzer window (the drop record, e.g. Na) and
    # nonmetals are SPOKEN as absent from the register — never skipped in
    # silence (Law 171).
    coin_check: List[Dict[str, Any]] = []
    spoken_absent: List[Dict[str, Any]] = []
    for sym in sorted(areal_by_symbol):
        try:
            m = eng_metals.metal(sym)
        except KeyError:
            z = eng_elements.element(sym).z
            spoken_absent.append({
                "z": z,
                "symbol": sym,
                "reason": eng_metals.NONMETAL_EXCLUSIONS.get(
                    z, "not in the metal registry (absence is spoken)"),
            })
            continue
        ip, q = eng_coil.coin_response_ppm(sym, eng_coil.BASE_FREQUENCY)
        total = math.hypot(ip, q)
        coin_check.append({
            "symbol": sym,
            "ferrous": m.z in eng_metals.FERROUS_ZS,
            "f_hz": eng_coil.BASE_FREQUENCY,
            "inphase_ppm": ip,
            "quadrature_ppm": q,
            "total_ppm": total,
            "channel_class": ("magnetization_inphase" if abs(ip) > abs(q)
                              else "eddy_quadrature"),
            "detectable_at_design": total >= eng_coil.MIN_DETECT_PPM,
        })

    consistency = {
        "xrf_dominant": xrf_dominant,
        "coil_dominant": coil_dominant,
        "agree": (xrf_dominant == coil_dominant
                  if (xrf_dominant and coil_dominant) else None),
        "coil_classical_above_floor": coil["n_physics_term"] > 0,
        "coin_class_check": coin_check,
        "spoken_absent": spoken_absent,
        "note": ("the XRF's strongest areal metal vs the coil's dominant "
                 "classical sheet metal of the same deposit; at PM-scale "
                 "areal a coil's sheet eddy response sits far below 3 sigma, "
                 "so the sheet dominant is honestly None — the coin-class "
                 "check is the coil registering each seen metal at the "
                 "declared design geometry, and every detected element that "
                 "is not in the metal register is spoken, never skipped"),
    }
    witness = wifi_witness(wifi_capture)
    witness_absent: Optional[Dict[str, Any]] = None
    if witness is None:
        witness_absent = {
            "reason": "wifi sniffer capture not found; carried as absent "
                      "(Law 171: absence is spoken, never invented)",
            "expected_path": wifi_witness_expected_path(wifi_capture),
        }

    payload = {
        "schema": SESSION_SCHEMA,
        "instrument": "code-based XRF + code coil (attached head)",
        "provenance": reading.provenance,
        "source": reading.source,
        "location": reading.location,
        "timestamp": timestamp or reading.timestamp,
        "kappa": {
            "declared": float(kappa),
            "law": "PHI-2396",
            "ground": phi_laws.PHI_INV,
            "floor_at_kappa": phi_laws.PHI_SQ_INV,
            "degenerate": "lim_{kappa->0} = C_classical (exact)",
            "note": "the gold-in-air reading convention; kappa=1 is full coupling",
        },
        "air": {k: v for k, v in reading.as_dict().items() if k != "report"},
        "spectrum": spectrum_block,
        "xrf_report": report_dict,
        "metals": register,
        "coil": coil,
        "coil_tuning": {
            "n_metals": len(tuning),
            "rows": tuning,
            "note": "per-metal contrast rung (peak-vs-fleet), peak rung, "
                    "declared detection range; the optimized sweep plan",
        },
        "consistency": consistency,
        "witness": witness,
        "witness_absent": witness_absent,
        "model": {
            "name": SESSION_MODEL_NAME,
            "version": f"sniffer-{SNIFFER_VERSION}+engine-{_ENGINE_VERSION}+{COIL_VERSION}",
            "calibration_id": f"feed-endmember-v1/{reading.source}"
                              f"/coil-design-cu-1pct",
            "physics": "classical",
            "label": "[REAL units/arithmetic/registry] + [MODEL feed->composition, "
                     "forward spectrum, coil declared model] + [PHI-2396 reading "
                     "layer at declared kappa]",
            "method": "air feed -> forward XRF spectrum -> classical sniffer "
                      "inversion -> LAW 2396 metal register -> code-coil "
                      "ladder sweep -> witness hash -> receipt chain",
        },
        "honesty": {
            "REAL": "unit chains, registry coverage, ladder invariant, "
                    "receipt chain, witness binding",
            "MODEL": "feed->composition endmember model, forward spectrum, "
                     "coil geometry/drive/null anchor, acquisition noise",
            "NOT_MEASURED": "every number is the declared model's output; "
                            "the receipt carries the input provenance",
        },
    }
    return payload


def metals_register(areal_by_symbol: Dict[str, float], kappa: float,
                    quantified_symbols: Optional[set] = None) -> Dict[str, Any]:
    """Every registered metal, read through LAW 2396 at the declared coupling.

    Three honest modes, one per row:
      quantified         the XRF inversion put mass on the element: the
                         classical term IS the reading (kappa=0 column) and
                         the phi-reading carries it (kappa column)
      field_carried      no mass over the detection floor: the element is
                         part of the field and reads the phi-ground floor
                         (0.3819660113 ppm at kappa=1) with its classical
                         term carried below
      no_coil_signature  coil-only leave-out not applicable here (kept for
                         the coil register); the metal is still on the frame
    """
    quantified_symbols = quantified_symbols or set()
    volume_m3 = eng_air.sampled_volume_m3(DEFAULT_FLOW_LPM,
                                          DEFAULT_DURATION_MIN)
    rows: List[Dict[str, Any]] = []
    for m in eng_metals.registry():
        areal = float(areal_by_symbol.get(m.symbol, 0.0) or 0.0)
        mass_ug = areal * DEFAULT_FILTER_AREA_CM2
        c_ug_m3 = mass_ug / volume_m3
        ppm_k0 = phi_laws.ug_m3_to_ppm(c_ug_m3)
        reading = phi_laws.ppm_of(ppm_k0, kappa)
        ln = eng_metals.primary_line(m.z)
        rows.append({
            "z": m.z,
            "symbol": m.symbol,
            "category": m.category,
            "primary_line": ln.name if ln else None,
            "primary_line_energy_ev": ln.energy if ln else None,
            "areal_ug_cm2": areal,
            "c_ug_m3": c_ug_m3,
            "c_k0_ppm": reading["c_k0_ppm"],
            "phi_ground_ppm": reading["ground_ppm"],
            "c_phi_ppm": reading["c_phi_ppm"],
            "uplift_vs_static": (reading["c_phi_ppm"] / ppm_k0
                                 if ppm_k0 > 0 else None),
            "mode": ("quantified" if m.symbol in quantified_symbols
                     else "field_carried"),
            "material_label": m.material_label,
            "coil_signature": m.has_coil_signature,
        })
    n_quant = sum(1 for r in rows if r["mode"] == "quantified")
    return {
        "law": "PHI-2396 elemental concentration (declared kappa)",
        "canonical_unit": "mass mixing ratio, ppm of air",
        "sampling": {"flow_lpm": DEFAULT_FLOW_LPM,
                     "duration_min": DEFAULT_DURATION_MIN,
                     "filter_area_cm2": DEFAULT_FILTER_AREA_CM2},
        "n_registered": len(rows),
        "n_quantified": n_quant,
        "n_field_carried": len(rows) - n_quant,
        "rows": rows,
        # the spoken drop record: metals registered in the tables but below
        # the analyzer window (best line eV) — absence is carried, not silent
        "drop_record": [{"symbol": sym, "category": cat, "best_line_ev": ev}
                        for sym, cat, ev in eng_metals.dropped_from_registry()],
    }


def self_check() -> List[str]:
    problems: List[str] = []
    reg = metals_register({}, kappa=phi_laws.KAPPA_FULL)
    if reg["n_registered"] <= 0:
        problems.append("empty metal register")
    for r in reg["rows"]:
        if abs(r["c_phi_ppm"] - phi_laws.PHI_SQ_INV) > 1e-12:
            problems.append(f"{r['symbol']}: floor reading is not phi^-2")
        if r["c_k0_ppm"] != 0.0:
            problems.append(f"{r['symbol']}: empty-air classical term is not zero")
    w = wifi_witness()
    if w is not None and w["frames"] <= 0:
        problems.append("wifi capture witness found no frames")
    return problems


if __name__ == "__main__":  # pragma: no cover
    payload = full_session(40.70, -74.00, kappa=phi_laws.KAPPA_FULL)
    print(payload["schema"])
    print("metals registered:", payload["metals"]["n_registered"],
          "quantified:", payload["metals"]["n_quantified"])
    print("coil dominant:", payload["coil"]["dominant_classical_metal"])
    print("consistency:", payload["consistency"])
    print("witness:", None if payload["witness"] is None
          else payload["witness"]["sha256"][:16])
    print("self_check:", self_check() or "clean")
