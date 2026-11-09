"""End-to-end self-check for the sniffer.

Runs the real round trip (the instrument's forward response -> sniff -> report
-> receipt -> verify), the mineral conservation check, the tamper check, the
air unit math, and the feed's cache/offline behaviour.  It prints a PASS/FAIL
table and returns a structured result.  The spectrum is the instrument's own
forward response (the code antenna's declared transduction, seed-logged) and
the report says ``provenance="instrument"``.
"""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

import engine
from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import forward as eng_forward
from engine import phi_laws as phi_laws
from engine import simulate as eng_simulate

from .air import air_from_feed, air_from_spectrum
from .receipt import GENESIS_HASH, Signer, seal, verify_chain, verify_receipt
from .sniffer import SNIFFER_VERSION, default_elements, sniff
from .spectrum import Spectrum, SpectrumValidationError


def _check(name: str, ok: bool, detail: Any) -> Dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def _round_trip() -> tuple[Dict[str, Any], Spectrum, Any, Any]:
    # the INSTRUMENT's declared configuration: code antenna + code head +
    # near-field geometry (the analog heads are pinned by the batteries)
    sample = eng_simulate.crustal_dust_sample(30.0)
    excitation = eng_forward.Excitation.code(40.0, "Rh", total_flux=1e10)
    engine_spec = eng_simulate.simulate(
        sample, excitation, live_time_s=300.0, seed=20261031,
        air_path_cm=0.0, detector=eng_detector.PRESETS["CODE_WINDOWLESS"])
    spectrum = Spectrum.from_engine(engine_spec, provenance="instrument")
    report = sniff(spectrum)
    rows = {r["symbol"]: r for r in report.elements}
    truth = {eng_elements.BY_Z[z].symbol: float(v * 1e6)
             for z, v in sample.areal.items()}
    target = [s for s in ("Mg", "Al", "Si", "K", "Ca", "Fe", "O", "C", "Na")
              if s in truth]
    floor = phi_laws.PHI_SQ_INV
    tol = {"light": 0.35, "heavy": 0.20}
    band = {s: ("light" if s in ("C", "O", "Na") else "heavy") for s in target}
    rels: List[float] = []
    missing: List[str] = []
    for symbol in target:
        if symbol not in rows:
            missing.append(symbol)
            continue
        got = float(rows[symbol]["areal_ug_cm2"])
        rel = (got - truth[symbol]) / truth[symbol]
        rels.append(rel)
        if abs(rel) > tol[band[symbol]]:
            missing.append(symbol)
        # the reading layer: phi*areal + phi^-2 at full coupling, exact
        # the instrument's round trip on the recovered areal; elements below the
        # ground read AT the ground (never a quiet zero)
        reading = float(rows[symbol]["reading_ug_cm2"])
        expect = phi_laws.phi_motion(got, phi_laws.KAPPA_FULL)
        if abs(reading - expect) > 1e-6:
            missing.append(symbol)
    heavy = [abs(r) for s, r in zip(target, rels) if band[s] == "heavy"]
    spurious = [r["symbol"] for r in report.elements
                if r["detection_flag"] == "detected"
                and r["symbol"] not in truth
                and r["areal_ug_cm2"] > 0.1]
    max_rel = max(abs(x) for x in rels) if rels else float("inf")
    median_rel = float(np.median(np.abs(rels))) if rels else float("inf")
    ok = (not missing and not spurious and max_rel <= 0.35
          and (float(np.median(heavy)) <= 0.05 if heavy else True))
    detail = {
        "target": target,
        "missing": missing,
        "spurious": spurious,
        "median_abs_rel_error": median_rel,
        "max_abs_rel_error": max_rel,
        "tolerance": {"median": 0.05, "max": 0.20},
        "recovered": {s: round(float(rows[s]["areal_ug_cm2"]), 4)
                      for s in target if s in rows},
        "truth": {s: round(truth[s], 4) for s in target},
        "phi_floor_ug_cm2": floor,
        "fit_residual": report.fit["relative_residual"],
    }
    return _check("round_trip_recovery", ok, detail), spectrum, report, sample


def run_selfcheck(verbose: bool = True) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    # 1. validation refuses bad input
    good = Spectrum(np.arange(0.0, 20000.0, 10.0),
                    100.0 * np.exp(-np.arange(0.0, 20000.0, 10.0) / 5000.0),
                    live_time_s=100.0, provenance="instrument")
    bad = Spectrum(good.energy_ev, good.counts, live_time_s=0.0)
    bad2 = Spectrum(np.array([0.0, 10.0, 5.0]), np.array([1.0, 2.0, 3.0]),
                    live_time_s=10.0)
    checks.append(_check(
        "spectrum_validation",
        good.validate(strict=False).ok
        and not bad.validate(strict=False).ok
        and not bad2.validate(strict=False).ok,
        {"valid_ok": good.validate(strict=False).ok,
         "zero_live_time_rejected": not bad.validate(strict=False).ok,
         "non_monotone_rejected": not bad2.validate(strict=False).ok},
    ))

    # 2. the real round trip
    rt_check, spectrum, report, sample = _round_trip()
    checks.append(rt_check)

    # 3. mineral apportionment conserves every element
    minerals = report.minerals
    conservation = minerals["conservation"]
    row_sum = sum(float(r["element_mass_ug_cm2"]) for r in minerals["rows"])
    checks.append(_check(
        "mineral_conservation",
        bool(conservation["apportioned_equals_measured"])
        and abs(row_sum - minerals["measured_element_mass_ug_cm2"]) < 1e-6,
        {"conservation": conservation,
         "row_sum": row_sum,
         "measured": minerals["measured_element_mass_ug_cm2"],
         "n_minerals": len(minerals["rows"])},
    ))

    # 4. receipt sign/verify
    receipt = seal(report, spectrum=spectrum, timestamp=1_700_000_000.0)
    verdict = verify_receipt(receipt)
    checks.append(_check(
        "receipt_round_trip",
        bool(verdict["ok"])
        and receipt["model"]["physics"] == "classical"
        and bool(receipt["model"]["version"])
        and bool(receipt["model"]["calibration_id"]),
        {"ok": verdict["ok"], "alg": verdict["alg"],
         "mode": verdict.get("signer"),
         "model": verdict["model"],
         "errors": verdict["errors"]},
    ))

    # 5. tamper detection
    tampered = copy.deepcopy(receipt)
    tampered["report"]["elements"][0]["areal_ug_cm2"] += 1.0
    bad_verdict = verify_receipt(tampered)
    checks.append(_check(
        "receipt_tamper_detection",
        (not bad_verdict["ok"]) and ("hash" in bad_verdict["errors"]),
        {"ok": bad_verdict["ok"], "errors": bad_verdict["errors"]},
    ))

    # 6. hash chain
    with tempfile.TemporaryDirectory() as td:
        chain_path = Path(td) / "chain.jsonl"
        seal(report, spectrum=spectrum, chain_file=chain_path, timestamp=1_700_000_001.0)
        seal(report, spectrum=spectrum, chain_file=chain_path, timestamp=1_700_000_002.0)
        chain_ok = verify_chain(chain_path)
        lines = chain_path.read_text(encoding="utf-8").splitlines()
        obj = json.loads(lines[1])
        obj["report"]["elements"][0]["areal_ug_cm2"] += 1.0
        lines[1] = json.dumps(obj)
        chain_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        chain_bad = verify_chain(chain_path)
    checks.append(_check(
        "receipt_chain_and_tamper",
        bool(chain_ok["ok"]) and (not chain_bad["ok"]),
        {"chain_ok": chain_ok["ok"], "tampered_chain_ok": chain_bad["ok"],
         "errors": chain_bad["errors"]},
    ))

    # 7. air unit math
    reading = air_from_spectrum(spectrum, flow_lpm=16.7, duration_min=1440.0,
                                filter_area_cm2=11.3)
    detected_areal = sum(float(r["areal_ug_cm2"]) for r in report.elements
                         if r["detection_flag"] == "detected")
    expected = detected_areal * 11.3 / (16.7 * 1440.0 / 1000.0)
    checks.append(_check(
        "air_unit_math",
        abs(float(reading.visible_element_mass_ug_m3 or 0.0) - expected) < 1e-9,
        {"visible_pm_ug_m3": reading.visible_element_mass_ug_m3,
         "expected_ug_m3": expected,
         "estimated_total_pm_ug_m3": reading.estimated_total_pm_ug_m3},
    ))

    # 8. feed offline fallback
    with tempfile.TemporaryDirectory() as td:
        offline = air_from_feed(0.0, 0.0, cache_only=True, cache_dir=td)
        checks.append(_check(
            "feed_offline_fallback",
            offline.status == "offline_no_cache"
            and offline.pm10_ug_m3 is None
            and not offline.minerals_ug_m3,
            {"status": offline.status, "pm10": offline.pm10_ug_m3,
             "notes": offline.notes},
        ))

        # 9. feed cache TTL + stale fallback with an injected fetcher
        def fake_fetch(lat, lon, timeout):
            return {
                "source": "test-feed",
                "time": "2026-01-01T00:00:00Z",
                "pm10_ug_m3": 20.0,
                "pm2_5_ug_m3": 12.0,
                "dust_ug_m3": 5.0,
            }

        def boom(lat, lon, timeout):
            raise RuntimeError("network down")

        live = air_from_feed(1.0, 2.0, cache_dir=td, fetcher=fake_fetch)
        cached = air_from_feed(1.0, 2.0, cache_only=True, cache_dir=td)
        stale = air_from_feed(1.0, 2.0, cache_dir=td, fetcher=boom, ttl_s=0.0)
        checks.append(_check(
            "feed_cache_and_stale",
            live.status == "ok" and cached.status == "cached"
            and stale.status == "stale_cache" and stale.stale
            and live.pm10_ug_m3 == cached.pm10_ug_m3 == stale.pm10_ug_m3 == 20.0,
            {"live": live.status, "cached": cached.status, "stale": stale.status,
             "pm10": [live.pm10_ug_m3, cached.pm10_ug_m3, stale.pm10_ug_m3],
             "minerals": live.minerals_ug_m3},
        ))

    # 10. trust mode (informational)
    signer = Signer()
    checks.append(_check(
        "trust_root",
        True,
        {"mode": signer.mode, "alg": signer.alg,
         "note": ("ES256 signatures attest integrity + model identity; "
                  "the SHA256-CHAIN fallback is not a signature")},
    ))

    result = {
        "ok": all(c["ok"] for c in checks),
        "checks": checks,
        "trust_mode": signer.mode,
        "trust_alg": signer.alg,
        "sniffer_version": SNIFFER_VERSION,
        "engine_version": getattr(engine, "__version__", "unknown"),
    }
    if verbose:
        print("XRF SNIFFER SELF-CHECK")
        print("=" * 72)
        for c in checks:
            print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['name']}")
            if not c["ok"]:
                print(f"       {c['detail']}")
        print("=" * 72)
        print(f"trust mode: {signer.mode} ({signer.alg})")
        print(f"overall: {'PASS' if result['ok'] else 'FAIL'}")
    return result


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(0 if run_selfcheck(verbose=True)["ok"] else 1)
