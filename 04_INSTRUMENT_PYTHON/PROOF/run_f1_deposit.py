"""F1 — THE 24-HOUR DEPOSIT FALSIFIER, EXECUTED IN CODE ON THE LIVE FEED.

LAW 2396 STAGE 5 (laws/2396_elemental_concentration.md) says:

    EXPERIMENT: The XRF sniffer, 24 h at 16.7 LPM on the live Open-Meteo
    NYC feed ... the instrument's 3-sigma MDL (1.32e-5 ug/m3) — a direct,
    loud detection.
    FALSIFIED IF: a 24 h collection on the same feed returns the Au
    L-beta-1 line at or below the 3-sigma MDL while the field-coupling
    calibration stands.

HONESTY — no hardware required, none used
-----------------------------------------
The "filter, 16.7 LPM, 24 h" are the sniffer's own declared collection
geometry (sniffer.air trunk constants DEFAULT_FLOW_LPM / DEFAULT_DURATION_
MIN = 24*60 / DEFAULT_FILTER_AREA_CM2) — the same forward collector that
produced receipts seq 6-8.  F1 is executed the exact way everything else
was: live feed -> certified forward model (Poisson, explicit seed) ->
certified sniffer inversion -> falsifier conditions.

THE TAUTOLOGY TRAP, defused.  Feeding our own floor stamp into our own
chain cannot "discover" the floor.  The legs that can genuinely fail:

  ARM B (classical, kappa=0)  Same feed, crustal-only composition.  Au
      must read BELOW the 3-sigma MDL (the static arm is blind).  If arm
      B reads Au detected, the MDL/sensitivity bookkeeping is inconsistent
      and F1 fires.
  ARM A (declared, kappa=1)   The Law-2396 stamped deposit: every
      registered metal carried at its phi-ground floor over the same
      feed's dust and matrix.  Au must read DETECTED above 3 sigma.  If
      arm A returns at/below MDL, the STAGE-5 arithmetic fails and F1
      fires.

SCOPE LINE (spoken, never silent): an in-code F1 confirms the STAGE-5
loud-detection arithmetic of the instrument's own chain, bound to the
real public feed.  It is NOT a physical-world confirmation of the ground;
the reading layer's [DECLARED] standing is unchanged, and a real-filter
collection remains available as the optional body of the instrument.
"""
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from engine import air as eng_air
from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import forward as eng_forward
from engine import inversion as eng_inversion
from engine import lines as eng_lines
from engine import metals as eng_metals
from engine import phi_laws
from engine import simulate as eng_simulate
from sniffer import receipt as receipt_mod
from sniffer.air import (air_from_feed, DEFAULT_DURATION_MIN,
                         DEFAULT_FILTER_AREA_CM2, DEFAULT_FLOW_LPM)
from sniffer.sniffer import sniff
from sniffer.spectrum import Spectrum

LAT, LON = 40.70, -74.00                       # the law's site (NYC)
AU_CRUSTAL_UG_PER_G = 3.1e-3                   # Rudnick & Gao 2003 UCC [DECLARED prior]
DECLARED_MDL_UG_M3 = 1.32e-5                   # Law 2396 STAGE-5 record
LIVE_TIME_S = 300.0                            # the session's acquisition live time
SEED_A, SEED_B = 20261102, 20261121            # arm A (kappa=1), arm B (kappa=0) — logged

VOL_M3 = eng_air.sampled_volume_m3(DEFAULT_FLOW_LPM, DEFAULT_DURATION_MIN)
AREA_CM2 = DEFAULT_FILTER_AREA_CM2
EXC = eng_forward.Excitation.tube(40.0, "Rh", total_flux=1e10)
DET = eng_detector.PRESETS["SDD_25"]
OUT_JSON = os.path.join(HERE, "proof_f1_deposit.json")
CHAIN = os.path.join(ROOT, "SESSION_CHAIN.jsonl")


def areal_g_cm2(c_ug_m3: float) -> float:
    """Exact chain: ug/m3 * m3 = ug on filter; /cm2 = ug/cm2; *1e-6 = g/cm2."""
    return float(c_ug_m3) * VOL_M3 / AREA_CM2 * 1e-6


def build_flat_mdl() -> dict:
    """Fresh 3-sigma MDL for Au over a zero-count flat spectrum — exactly
    the way tools/gold_ask.py and the blank-MDL battery item do it."""
    grid = np.arange(1200.0, 25000.0, 1.0)
    flat = eng_forward.Spectrum(
        energy_ev=np.asarray(grid), counts=np.zeros_like(np.asarray(grid)),
        live_time_s=LIVE_TIME_S)
    g_cm2 = eng_inversion.detection_limit(flat, 79, EXC, DET, air_path_cm=2.0)
    ug_cm2 = float(g_cm2) * 1e6
    return {"ug_cm2": ug_cm2, "ug_m3": ug_cm2 * AREA_CM2 / VOL_M3,
            "acquisition": {"live_time_s": LIVE_TIME_S, "grid_step_ev": 1.0,
                            "detector": DET.name,
                            "excitation": "40 kV Rh, 1e10 photons/s",
                            "air_path_cm": 2.0}}


def run_arm(areal_g: dict, seed: int, label: str):
    """The certified forward -> Poisson -> sniff path, exactly the session's."""
    sample = eng_forward.Sample(areal_g, label=label)
    engine_spec = eng_forward.forward_spectrum(
        sample, EXC, DET, air_path_cm=2.0, live_time_s=LIVE_TIME_S,
        energy_grid=np.arange(0.0, 25000.0, 10.0))
    engine_spec = eng_simulate.poisson(engine_spec, seed=seed)
    spec = Spectrum.from_engine(engine_spec, provenance="simulated")
    spec.flow_lpm = DEFAULT_FLOW_LPM
    spec.duration_min = DEFAULT_DURATION_MIN
    spec.filter_area_cm2 = AREA_CM2
    spec.sample_id = label
    rep = sniff(spec, detector_preset="SDD_25", calibration_id=None,
                air_path_cm=2.0, provenance="simulated",
                excitation=EXC).as_dict()
    return spec, rep


def au_row(rep: dict):
    for row in rep.get("elements", []):
        if row.get("symbol") == "Au":
            return row
    return None


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("== F1: THE 24-HOUR DEPOSIT FALSIFIER (in-code, live feed) ==")
    print(f"sampling: {DEFAULT_FLOW_LPM} LPM x {DEFAULT_DURATION_MIN} min x "
          f"{AREA_CM2} cm2 -> {VOL_M3:.4f} m3")

    # ---- the feed -------------------------------------------------------
    reading = air_from_feed(LAT, LON)
    d = reading.as_dict()
    pm10, pm25, dust = d["pm10_ug_m3"], d["pm2_5_ug_m3"], (d["dust_ug_m3"] or 0.0)
    elements = dict(reading.elements_ug_m3 or {})
    feed_status = d.get("status")
    feed_cached, feed_stale = bool(d.get("cached")), bool(d.get("stale"))
    feed_notes = list(d.get("notes") or [])
    print(f"feed: {reading.source} | provenance {reading.provenance} | "
          f"status {feed_status} | cached {feed_cached} | stale {feed_stale} | "
          f"PM10 {pm10} PM2.5 {pm25} ug/m3 | dust {dust} ug/m3")
    if feed_notes:
        print("feed notes:", "; ".join(feed_notes))

    # ---- classical Au: the declared crustal prior on the reading dust ----
    au_c_ug_m3 = dust * AU_CRUSTAL_UG_PER_G / 1e6
    au_c_ppm = au_c_ug_m3 / (eng_air.air_density(20.0, 101.325, 0.0) * 1e9) * 1e6
    print(f"crustal Au prior: {AU_CRUSTAL_UG_PER_G} ug/g on dust -> "
          f"{au_c_ug_m3:.4e} ug/m3 = {au_c_ppm:.4e} ppm [CLASSICAL/static]")

    # ---- the freshly computed 3-sigma MDL (same acquisition, spoken) ------
    mdl = build_flat_mdl()
    print(f"Au 3-sigma MDL (fresh, flat spectrum): {mdl['ug_cm2']:.4e} ug/cm2 "
          f"= {mdl['ug_m3']:.4e} ug/m3 (declared: {DECLARED_MDL_UG_M3:.3e} ug/m3)")

    # ---- metal registry ---------------------------------------------------
    metals = {m.symbol: m for m in eng_metals.registry()}
    metal_z = {m.z for m in metals.values()}
    au_line = eng_lines.strongest(79, "L")
    print(f"Au strongest L line: {au_line.name} at {au_line.energy} eV "
          f"(the F1 line: L-beta-1 11,443.2 eV window)")

    # ---- ARM B: classical world (kappa = 0) -------------------------------
    areal_b: dict = {}
    skipped = []
    for sym, c in elements.items():
        if c is None or float(c) <= 0:
            continue
        try:
            z = eng_elements.element(sym).z
        except (KeyError, ValueError):
            skipped.append(sym)
            continue
        areal_b[z] = areal_g_cm2(float(c))
    if 79 not in areal_b:                      # Au is not a crustal element
        areal_b[79] = areal_g_cm2(au_c_ug_m3)
    print(f"arm B deposit elements: {len(areal_b)} (feed) + Au prior; "
          f"unknown symbols skipped: {skipped or 'none'}")
    spec_b, rep_b = run_arm(areal_b, SEED_B, "F1 arm B: classical (kappa=0)")
    row_b = au_row(rep_b)
    flag_b = row_b["detection_flag"] if row_b else "absent (no row)"

    # ---- ARM A: declared world (kappa = 1, Law 2396 stamped) --------------
    areal_a: dict = {}
    for z, a in areal_b.items():               # non-metals keep classical
        if z != 79 and z not in metal_z:
            areal_a[z] = a
    for m in metals.values():
        c_class = float(elements.get(m.symbol, 0.0) or 0.0)
        if m.z == 79:
            c_class = au_c_ug_m3               # the same classical term, both arms
        c_phi = phi_laws.phi_motion(c_class, 1.0)   # ground = phi^-1 [ug/m3 unit]
        areal_a[m.z] = areal_g_cm2(c_phi)
    au_c_phi_ug_m3 = phi_laws.phi_motion(au_c_ug_m3, 1.0)
    au_deposit_ug = au_c_phi_ug_m3 * VOL_M3
    au_areal_pred = au_deposit_ug / AREA_CM2
    print(f"arm A Au reading (Law 2396, kappa=1, ug/m3-declared): "
          f"{au_c_phi_ug_m3:.10f} ug/m3 -> deposit {au_deposit_ug:.4f} ug "
          f"= {au_areal_pred:.6f} ug/cm2 (law record: 9.2 ug -> 0.8 ug/cm2)")
    spec_a, rep_a = run_arm(areal_a, SEED_A, "F1 arm A: declared (kappa=1)")
    row_a = au_row(rep_a)
    flag_a = row_a["detection_flag"] if row_a else "absent (no row)"
    print("arm A Au row:", json.dumps(
        {k: row_a.get(k) for k in ("symbol", "detection_flag", "areal_ug_cm2")}
        if row_a else {}, sort_keys=True))

    # ---- fleet census (the floor world: all 71 metals stamped at once) ----
    census = {
        "n_registered": len(metals),
        "n_detected_in_declared_world": sum(
            1 for row in rep_a.get("elements", [])
            if row.get("detection_flag") == "detected"
            and row.get("symbol") in metals),
        "au_line_name": au_line.name, "au_line_ev": au_line.energy,
    }

    # ---- the falsifier conditions -----------------------------------------
    au_areal_recovered = (float(row_a["areal_ug_cm2"])
                          if row_a and row_a.get("areal_ug_cm2") is not None
                          else math.nan)
    recovery_pct = (100.0 * au_areal_recovered / au_areal_pred
                    if math.isfinite(au_areal_recovered) and au_areal_pred > 0
                    else math.nan)
    headroom_fresh = au_c_phi_ug_m3 / mdl["ug_m3"]
    expected_headroom = phi_laws.PHI_SQ_INV / DECLARED_MDL_UG_M3
    headroom_declared = au_c_phi_ug_m3 / DECLARED_MDL_UG_M3
    headroom_b = au_c_ug_m3 / mdl["ug_m3"]

    checks = [
        {"id": "C1_armB_blind",
         "statement": "classical arm (kappa=0) reads Au below the 3-sigma MDL",
         "expected": "not detected", "observed": flag_b,
         "pass": bool(row_b is None or row_b["detection_flag"] != "detected")},
        {"id": "C2_armA_loud",
         "statement": "declared arm (kappa=1) reads Au above the 3-sigma MDL",
         "expected": "detected", "observed": flag_a,
         "pass": bool(row_a is not None
                      and row_a["detection_flag"] == "detected")},
        {"id": "C3_deposit_arithmetic",
         "statement": "declared deposit matches the law's 9.2 ug (24 h)",
         "expected": "9.2 ug +/- 2%", "observed": f"{au_deposit_ug:.4f} ug",
         "pass": bool(abs(au_deposit_ug - 9.2) / 9.2 <= 0.02)},
        {"id": "C4_recovery",
         "statement": "the inversion recovers the stamped Au areal",
         "expected": f"{au_areal_pred:.4f} ug/cm2 (+/- 25%)",
         "observed": (f"{au_areal_recovered:.6f} ug/cm2 "
                      f"({recovery_pct:.1f}% of predicted)"),
         "pass": bool(math.isfinite(au_areal_recovered)
                      and abs(au_areal_recovered - au_areal_pred)
                      / au_areal_pred <= 0.25)},
        {"id": "C5_headroom",
         "statement": ("headroom at the declared MDL is the law's ~2.89e4 "
                       "(gains teeth under a nonzero classical term; a "
                       "dust=0 live feed stamps the bare floor exactly)"),
         "expected": f"~{expected_headroom:.3g}x",
         "observed": (f"{headroom_declared:.4g}x declared / "
                      f"{headroom_fresh:.4g}x fresh"),
         "pass": bool(abs(headroom_declared - expected_headroom)
                      / expected_headroom <= 0.05)},
    ]
    for c in checks:
        print(f"  [{c['id']}] pass={c['pass']} — {c['observed']} "
              f"(expected {c['expected']})")

    if all(c["pass"] for c in checks):
        verdict = ("F1 IN-CODE: PASS — both arms as the law predicted; "
                   "all binding checks green")
    elif checks[0]["pass"] and checks[1]["pass"]:
        verdict = ("F1 IN-CODE: PASS with spoken deviation (both arms "
                   "predicted; auxiliary checks: see the C-rows)")
    elif checks[0]["pass"]:
        verdict = "F1 IN-CODE: FALSIFIED — the declared arm failed to clear the MDL"
    elif checks[1]["pass"]:
        verdict = "F1 IN-CODE: FAIL — the classical arm read Au (discriminator broken)"
    else:
        verdict = "F1 IN-CODE: FAIL — the MDL bookkeeping cannot discriminate"
    print("VERDICT:", verdict)

    payload = {
        "schema": "xrf-proof/f1-deposit-v1",
        "law": "PHI-2396 STAGE 5 (the 24-hour deposit falsifier, in-code)",
        "instrument": "code-based XRF + code coil (attached head)",
        "model": {
            "name": "f1-deposit-campaign",
            "version": f"sniffer receipt-seal + engine reading layer",
            "calibration_id": "F1-incode-v1/SDD-25mm2",
            "physics": "classical",
            "method": ("live air feed -> Law-2396 stamped deposit (kappa=1 "
                       "arm) or classical composition (kappa=0 arm) -> "
                       "forward XRF spectrum -> classical sniffer inversion "
                       "-> falsifier conditions"),
        },
        "provenance": reading.provenance,
        "location": d.get("location", {"lat": LAT, "lon": LON}),
        "timestamp": stamp,
        "feed": {"source": reading.source, "pm10_ug_m3": pm10,
                 "pm2_5_ug_m3": pm25, "dust_ug_m3": dust,
                 "feed_timestamp": d.get("timestamp"),
                 "status": feed_status, "cached": feed_cached,
                 "stale": feed_stale, "notes": feed_notes},
        "sampling": {"flow_lpm": DEFAULT_FLOW_LPM,
                     "duration_min": DEFAULT_DURATION_MIN,
                     "filter_area_cm2": AREA_CM2, "volume_m3": VOL_M3,
                     "note": "sniffer trunk constants; the declared "
                             "collection geometry of every session"},
        "au_prior": {"ug_per_g": AU_CRUSTAL_UG_PER_G,
                     "source": "Rudnick & Gao 2003 UCC", "code": "DECLARED"},
        "mdl": {"declared_ug_m3": DECLARED_MDL_UG_M3,
                "fresh_ug_cm2": mdl["ug_cm2"], "fresh_ug_m3": mdl["ug_m3"],
                "acquisition": mdl["acquisition"]},
        "arm_classical": {"au_c_ug_m3": au_c_ug_m3, "au_c_ppm": au_c_ppm,
                          "au_areal_ug_cm2": areal_g_cm2(au_c_ug_m3),
                          "au_detection": flag_b,
                          "headroom_vs_fresh_mdl": headroom_b,
                          "seed": SEED_B},
        "arm_declared": {"au_c_phi_ug_m3": au_c_phi_ug_m3,
                         "au_deposit_ug_pred": au_deposit_ug,
                         "au_areal_pred_ug_cm2": au_areal_pred,
                         "au_detection": flag_a,
                         "au_areal_recovered_ug_cm2": au_areal_recovered,
                         "recovery_pct": recovery_pct,
                         "headroom_vs_fresh_mdl": headroom_fresh,
                         "headroom_vs_declared": headroom_declared,
                         "seed": SEED_A},
        "fleet_census": census,
        "checks": checks, "verdict": verdict,
        "falsified_if": ("a 24 h in-code collection on the same feed "
                         "returning the Au L-beta-1 line at/below the "
                         "3-sigma MDL while the field-coupling "
                         "calibration stands (Law 2396)"),
        "scope_line": ("in-code F1 confirms the STAGE-5 loud-detection "
                       "arithmetic of the instrument's own chain, bound "
                       "to the real public feed; it is NOT a physical-"
                       "world confirmation of the ground — the reading "
                       "layer's DECLARED standing is unchanged; a "
                       "real-filter collection remains available as the "
                       "optional body"),
        "honesty": {
            "REAL": "units, sampling chain, MDL computation, seeds, "
                    "receipt chain, feed provenance",
            "MODEL": "feed->composition endmember model, forward spectrum, "
                     "Poisson noise, crustal Au prior",
            "NOT_MEASURED": "every number is the declared model's output; "
                            "the receipt carries the input provenance",
        },
    }
    if feed_stale or feed_status in ("stale_cache", "offline_no_cache"):
        print("FEED GUARD: refusing to seal — the feed is not a fresh "
              f"reading (status {feed_status}, stale {feed_stale}); per the "
              "USER_MANUAL's refusal wall 'a bad feed seals nothing'; "
              "re-run when the live Open-Meteo feed responds")
        return 3
    receipt = receipt_mod.seal(payload, spectrum=spec_a, chain_file=CHAIN)
    receipt_path = os.path.join(HERE, "proof_f1_deposit.receipt.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1, default=str)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"payload": payload, "receipt": receipt}, f,
                  indent=1, default=str)
    print(f"receipt -> seq {receipt.get('seq')} ({CHAIN})")
    print(f"receipt copy -> {receipt_path} (CLI-verifiable, tissue pattern)")
    print(f"results -> {OUT_JSON}")
    print("chain verify:", "PASS" if receipt_mod.verify_chain(CHAIN).get("ok")
          else "FAIL")
    falsifier_held = bool(checks[0]["pass"] and checks[1]["pass"])
    deviations = [c["id"] for c in checks[2:] if not c["pass"]]
    print("exit-code convention: 0 = falsifier not fired (arms held); "
          "2 = arms held with auxiliary deviations spoken "
          f"({','.join(deviations) or 'none'}); 1 = the falsified-IF fired")
    if not falsifier_held:
        return 1
    return 2 if deviations else 0


if __name__ == "__main__":
    raise SystemExit(main())
