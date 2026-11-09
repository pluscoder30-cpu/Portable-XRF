"""Command line for the code-based XRF sniffer.

Run from the XRF directory::

    python -m sniffer sniff spectrum.json
    python -m sniffer air spectrum.json --flow 16.7 --time 1440 --area 11.3
    python -m sniffer feed 40.7128 -74.0060
    python -m sniffer excite composition.json --noise
    python -m sniffer session 40.70 -74.00 --runs 1 --chain chain.jsonl
    python -m sniffer metals --kappa 1.0
    python -m sniffer verify receipt.json
    python -m sniffer selfcheck
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

import engine
from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import forward as eng_forward
from engine import phi_laws as eng_phi_laws
from engine import simulate as eng_simulate

from .air import (DEFAULT_DURATION_MIN, DEFAULT_FILTER_AREA_CM2, DEFAULT_FLOW_LPM,
                  DEFAULT_CACHE_TTL_S, air_from_feed, air_from_spectrum)
from .receipt import seal, verify_chain, verify_receipt
from .selfcheck import run_selfcheck
from .sniffer import (ENGINE_VERSION, SNIFFER_VERSION, SniffError, sniff)
from .spectrum import (Spectrum, SpectrumValidationError, load_spectrum,
                       save_spectrum)


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------
def _fmt(value: Any, digits: int = 3, width: int = 10) -> str:
    if value is None:
        return f"{'-':>{width}}"
    try:
        return f"{float(value):>{width}.{digits}f}"
    except (TypeError, ValueError):
        return f"{str(value):>{width}}"


def _print_report(report) -> None:
    payload = report.as_dict()
    print("=" * 78)
    print(f"XRF SNIFFER REPORT - provenance: {payload['provenance'].upper()}")
    if payload["provenance"] in ("instrument", "simulated"):
        print("  *** THE INSTRUMENT'S OWN FORWARD RESPONSE: the code antenna's")
        print("      declared transduction of the sample (seed-logged) - the")
        print("      computer IS the instrument; this is its reading, computed ***")
    elif payload["provenance"] == "unknown":
        print("  *** PROVENANCE UNKNOWN: the input did not say where the spectrum came from ***")
    print("=" * 78)
    print(f"sample   : {payload['sample_id'] or '-'}")
    print(f"source   : {payload['source'] or '-'}")
    print(f"time     : {payload['timestamp']}")
    print(f"model    : {payload['model']['version']}")
    print(f"calib    : {payload['model']['calibration_id']}")
    print(f"physics  : {payload['model']['physics']}   label: {payload['model']['label']}")
    fit = payload["fit"]
    print(f"fit      : residual {fit['relative_residual']:.4f} ({fit['quality']})   "
          f"peaks {fit['n_peaks']}   quantified {fit['n_elements_quantified']}   "
          f"detected {fit['n_elements_detected']}")
    gate = payload["gate"]
    print(f"gate     : {'valid' if gate['valid'] else 'GATED'} - {gate['reason']}")
    print()
    print("ELEMENTS (areal density, ug/cm2)")
    print(f"  {'elem':>4} {'areal':>11} {'+/-stat':>9} {'+/-syst':>9} {'MDL':>9}  flag")
    not_quantified: List[str] = []
    for row in payload["elements"]:
        if row["detection_flag"] == "not_quantified" and row["areal_ug_cm2"] == 0:
            not_quantified.append(row["symbol"])
            continue
        print(f"  {row['symbol']:>4} {_fmt(row['areal_ug_cm2'], 4, 11)} "
              f"{_fmt(row['sigma_ug_cm2'], 4, 9)} {_fmt(row['systematic_ug_cm2'], 4, 9)} "
              f"{_fmt(row['mdl_ug_cm2'], 4, 9)}  {row['detection_flag']}")
    if not_quantified:
        print(f"  not quantified (no line in window / air path): {', '.join(not_quantified)}")
    print()
    if payload["peaks"]:
        print("PEAKS (matched lines; residual = observed centre - library energy)")
        print(f"  {'centre eV':>10} {'area':>11} {'SNR':>7} {'FWHM eV':>8}  best line")
        for peak in payload["peaks"]:
            best = peak["best_line"]
            label = (f"{best['element']} {best['line']} ({best['energy_ev']:.1f} eV)"
                     if best else "-")
            resid = f"  delta={peak['residual_ev']:+.1f} eV" if peak["residual_ev"] is not None else ""
            quality = peak.get("match_quality", "")
            print(f"  {_fmt(peak['center_ev'], 1, 10)} {_fmt(peak['area'], 1, 11)} "
                  f"{_fmt(peak['snr'], 1, 7)} {_fmt(peak['fwhm_ev'], 1, 8)}  {label}{resid}"
                  + (f"  [{quality}]" if quality and quality != "good" else ""))
        print()
    minerals = payload["minerals"]
    print(f"MINERALS ({minerals['method']}, {minerals['label']})")
    print(f"  {'mineral':>18} {'element mass':>13} {'fraction':>9} {'unmixed':>10}")
    for row in minerals["rows"]:
        print(f"  {row['name']:>18} {_fmt(row['element_mass_ug_cm2'], 4, 13)} "
              f"{_fmt(100.0 * row['mass_fraction'], 1, 8)}% "
              f"{_fmt(row['unmixed_mass_ug_cm2'], 4, 10)}")
    closure = minerals.get("unmix", {}).get("closure", {})
    print(f"  unmix closure residual: {_fmt(closure.get('relative_residual'), 4, 8)}")
    print("  note: 'element mass' is the apportioned element mass; 'fraction' is of")
    print("        apportioned element mass, not total mineral mass. The 'unmixed'")
    print("        column is an underdetermined consistency check (closure above).")
    print()
    if payload["warnings"]:
        print("WARNINGS")
        for warning in payload["warnings"]:
            print(f"  - {warning}")
        print()
    print("HONESTY")
    print("  REAL    : spectrum decode, peak ID, NNLS inversion, mineral arithmetic, receipt")
    print("  MODEL   : the declared transduction convention (code antenna forward")
    print("            response), counts->concentration, mineral split, uncertainty")
    print("  SPOKEN  : absences are named, never silent; the signature attests the")
    print("            bytes and the model, not the world")
    print("=" * 78)


def _print_air(reading) -> None:
    payload = reading.as_dict()
    print("=" * 78)
    print(f"XRF AIR READER - mode: {payload['mode']}   provenance: {payload['provenance']}")
    print(f"status   : {payload['status']}"
          + ("   (cached)" if payload["cached"] else "")
          + ("   (stale)" if payload["stale"] else ""))
    loc = payload.get("location") or {}
    if loc:
        print(f"location : lat {loc.get('latitude')}  lon {loc.get('longitude')}")
    print(f"time     : {payload['timestamp']}")
    print(f"source   : {payload['source']}")
    print(f"PM2.5    : {_fmt(payload.get('pm2_5_ug_m3'), 2, 10)} ug/m3")
    print(f"PM10     : {_fmt(payload.get('pm10_ug_m3'), 2, 10)} ug/m3")
    print(f"dust     : {_fmt(payload.get('dust_ug_m3'), 2, 10)} ug/m3")
    print(f"visible  : {_fmt(payload.get('visible_element_mass_ug_m3'), 2, 10)} ug/m3 "
          "(XRF-visible element mass; lower bound)")
    print(f"total est: {_fmt(payload.get('estimated_total_pm_ug_m3'), 2, 10)} ug/m3 "
          "(stoichiometric mineral estimate; includes O)")
    if payload.get("elements_ug_m3"):
        print("\nELEMENTS (ug/m3)")
        for symbol, value in sorted(payload["elements_ug_m3"].items(), key=lambda kv: -kv[1]):
            print(f"  {symbol:>4} {value:10.4f}")
    if payload.get("minerals_ug_m3"):
        print("\nMINERALS (ug/m3)")
        for name, value in sorted(payload["minerals_ug_m3"].items(), key=lambda kv: -kv[1]):
            fraction = payload["mineral_mass_fractions"].get(name, 0.0)
            print(f"  {name:>18} {value:10.4f}   {100*fraction:5.1f}%")
    if payload.get("assumptions"):
        print("\nASSUMPTIONS")
        for item in payload["assumptions"]:
            print(f"  - {item}")
    if payload.get("notes"):
        print("\nNOTES")
        for item in payload["notes"]:
            print(f"  - {item}")
    print("=" * 78)


def _print_verification(result: Dict[str, Any], title: str = "RECEIPT VERIFICATION") -> None:
    print("=" * 78)
    print(title)
    print(f"ok       : {result.get('ok')}")
    if "alg" in result:
        print(f"alg      : {result.get('alg')} ({result.get('signer')})")
    if result.get("model"):
        model = result["model"]
        print(f"model    : {model.get('version')}")
        print(f"calib    : {model.get('calibration_id')}")
        print(f"physics  : {model.get('physics')}")
    if "n" in result:
        print(f"receipts : {result.get('n')}   genesis_ok: {result.get('genesis_ok')}")
    if result.get("checks"):
        print("checks   :")
        for name, check in result["checks"].items():
            print(f"  [{'ok' if check['ok'] else 'FAIL'}] {name}")
    if result.get("errors"):
        print("errors   :")
        for error in result["errors"]:
            print(f"  - {error}")
    print("=" * 78)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def _parse_elements(text: Optional[str]):
    if text is None or text.strip() == "":
        return None
    if text.strip().lower() == "all":
        return "all"
    out: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if part:
            out.append(eng_elements.element(part).z)
    return out


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
                    encoding="utf-8")
    return path


def cmd_sniff(args: argparse.Namespace) -> int:
    spec = load_spectrum(args.spectrum)
    report = sniff(
        spec,
        detector_preset=args.detector,
        calibration_id=args.calibration,
        air_path_cm=args.air_path,
        elements=_parse_elements(args.elements),
        add_peak_elements=not args.strict_elements,
    )
    _print_report(report)
    out = Path(args.out) if args.out else Path(args.spectrum).with_suffix(".report.json")
    _write_json(out, report.as_dict())
    receipt = seal(report, spectrum=spec, chain_file=args.chain)
    rec_path = Path(args.receipt) if args.receipt else out.with_suffix(".receipt.json")
    _write_json(rec_path, receipt)
    print(f"report  -> {out}")
    print(f"receipt -> {rec_path}   ({receipt['attestation']['alg']})")
    if args.chain:
        print(f"chain   -> {args.chain}")
    return 0


def cmd_air(args: argparse.Namespace) -> int:
    spec = load_spectrum(args.spectrum)
    location = None
    if args.lat is not None and args.lon is not None:
        location = {"latitude": args.lat, "longitude": args.lon}
    reading = air_from_spectrum(
        spec,
        flow_lpm=args.flow,
        duration_min=args.time,
        filter_area_cm2=args.area,
        detector_preset=args.detector,
        calibration_id=args.calibration,
        air_path_cm=args.air_path,
        location=location,
    )
    _print_air(reading)
    out = Path(args.out) if args.out else Path(args.spectrum).with_suffix(".air.json")
    _write_json(out, reading.as_dict())

    payload = dict(reading.report)
    air_only = reading.as_dict()
    air_only.pop("report", None)
    payload["air"] = air_only
    payload["schema"] = "xrf-sniffer/air-report-v1"
    receipt = seal(payload, spectrum=spec, chain_file=args.chain)
    rec_path = Path(args.receipt) if args.receipt else out.with_suffix(".receipt.json")
    _write_json(rec_path, receipt)
    print(f"air     -> {out}")
    print(f"receipt -> {rec_path}   ({receipt['attestation']['alg']})")
    return 0


def cmd_feed(args: argparse.Namespace) -> int:
    reading = air_from_feed(
        args.lat, args.lon,
        cache_only=args.cache_only,
        cache_dir=args.cache_dir,
        ttl_s=args.ttl,
        source=args.source,
    )
    _print_air(reading)
    out = Path(args.out) if args.out else Path(f"feed_{args.lat:+.3f}_{args.lon:+.3f}.json")
    _write_json(out, reading.as_dict())
    payload = {
        "schema": "xrf-sniffer/feed-report-v1",
        "provenance": "feed",
        "model": {
            "name": "endmember_pm_to_minerals",
            "version": f"sniffer-{SNIFFER_VERSION}+engine-{ENGINE_VERSION}",
            "calibration_id": f"endmember-v1/{reading.source}",
            "physics": "classical",
            "label": "[MODEL/NORMATIVE]",
            "method": "endmember_model",
        },
        "air": reading.as_dict(),
    }
    receipt = seal(payload, feed=reading.feed or reading.as_dict(), chain_file=args.chain)
    rec_path = Path(args.receipt) if args.receipt else out.with_suffix(".receipt.json")
    _write_json(rec_path, receipt)
    print(f"feed    -> {out}")
    print(f"receipt -> {rec_path}   ({receipt['attestation']['alg']})")
    return 0


def cmd_excite(args: argparse.Namespace) -> int:
    """Compute the instrument's forward response for a composition."""
    comp = json.loads(Path(args.composition).read_text(encoding="utf-8"))
    if args.detector:
        from .sniffer import resolve_detector
        det = resolve_detector(args.detector)
    else:
        det = eng_detector.PRESETS["CODE_WINDOWLESS"]

    pm = float(comp.get("pm_ug_m3", 30.0))
    flow = float(comp.get("flow_lpm", DEFAULT_FLOW_LPM))
    duration = float(comp.get("duration_min", DEFAULT_DURATION_MIN))
    area = float(comp.get("filter_area_cm2", DEFAULT_FILTER_AREA_CM2))
    air_path = float(comp.get("air_path_cm", 2.0))
    live = float(comp.get("live_time_s", 300.0))
    kv = float(comp.get("excitation_kv", 40.0))
    anode = str(comp.get("excitation_anode", "Rh"))
    flux = float(comp.get("excitation_flux", 1e10))

    if comp.get("elements_ug_cm2"):
        sample = eng_forward.Sample(
            {eng_elements.element(k).z: float(v) * 1e-6
             for k, v in comp["elements_ug_cm2"].items()})
    else:
        endmembers = comp.get("endmembers") or {
            "mineral_dust": 0.75, "iron_oxide": 0.10,
            "carbonate": 0.10, "soot": 0.05,
        }
        sample = eng_simulate.aerosol_sample(endmembers, pm, flow, duration, area)

    excitation = eng_forward.Excitation.tube(kv, anode, total_flux=flux)
    grid = np.arange(0.0, 25000.0, 10.0)
    engine_spec = eng_forward.forward_spectrum(
        sample, excitation, det, air_path_cm=air_path, live_time_s=live,
        energy_grid=grid,
    )
    if args.noise:
        engine_spec = eng_simulate.poisson(engine_spec, seed=args.seed)

    spec = Spectrum.from_engine(engine_spec, provenance="instrument")
    spec.flow_lpm = flow
    spec.duration_min = duration
    spec.filter_area_cm2 = area
    spec.sample_id = str(comp.get("sample_id", "aerosol (instrument forward)"))
    spec.source = f"engine.forward_response (seed={args.seed if args.noise else 'none'})"
    spec.metadata.update({
        "air_path_cm": air_path,
        "detector": det.name,
        "excitation_kv": kv,
        "excitation_anode": anode,
        "excitation_flux": flux,
        "truth_elements_ug_cm2": {
            eng_elements.BY_Z[z].symbol: float(v * 1e6) for z, v in sample.areal.items()
        },
        "truth_endmembers": comp.get("endmembers"),
        "noise": bool(args.noise),
        "seed": int(args.seed),
    })
    out = Path(args.out) if args.out else Path("instrument_forward_spectrum.json")
    save_spectrum(spec, out, "json")

    print("=" * 78)
    print("INSTRUMENT FORWARD RESPONSE (provenance=instrument)")
    print("the code antenna's declared transduction of the sample - seed-logged")
    print(f"sample   : {spec.sample_id}")
    print(f"detector : {det.name}   air path: {air_path} cm   live time: {live} s")
    print(f"noise    : {'Poisson, seed=' + str(args.seed) if args.noise else 'none'}")
    print(f"channels : {spec.energy_ev.size}   total counts: {spec.counts.sum():.1f}")
    print("TRUTH (ug/cm2):")
    for z, areal in sorted(sample.areal.items(), key=lambda kv: -kv[1]):
        print(f"  {eng_elements.BY_Z[z].symbol:>4} {areal * 1e6:10.4f}")
    print(f"spectrum -> {out}")
    print("=" * 78)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    if args.chain:
        result = verify_chain(args.chain)
        _print_verification(result, "RECEIPT CHAIN VERIFICATION")
        # also verify the supplied receipt itself
        single = verify_receipt(receipt)
        _print_verification(single, "SUPPLIED RECEIPT")
        return 0 if (result["ok"] and single["ok"]) else 1
    result = verify_receipt(receipt)
    _print_verification(result)
    return 0 if result["ok"] else 1


def cmd_selfcheck(args: argparse.Namespace) -> int:
    result = run_selfcheck(verbose=True)
    return 0 if result["ok"] else 1


# ---------------------------------------------------------------------------
# Full session (air feed -> XRF -> metal register -> coil sweep -> witness)
# ---------------------------------------------------------------------------
def _print_session(payload: Dict[str, Any]) -> None:
    print("=" * 78)
    print("FULL SESSION - THE COMPUTER IS THE INSTRUMENT")
    print("code XRF + code coil (attached head); the reading is the instrument's own")
    print("=" * 78)
    air = payload["air"]
    loc = air.get("location", {})
    print(f"location : {loc.get('latitude')}, {loc.get('longitude')}")
    print(f"timestamp: {payload['timestamp']}   source: {payload['source']}"
          f"   status: {air.get('status')}")
    print(f"pm10/pm2.5/dust: {_fmt(air.get('pm10_ug_m3'))} / "
          f"{_fmt(air.get('pm2_5_ug_m3'))} / {_fmt(air.get('dust_ug_m3'))} ug/m3")
    spec = payload.get("spectrum") or {}
    if spec:
        print(f"spectrum : {spec.get('channels')} ch, "
              f"{spec.get('total_counts', 0.0):.0f} counts, seed {spec.get('seed')}"
              " (the instrument's forward response, seed-logged)")
    x = payload.get("xrf_report")
    if x:
        print("xrf detected (areal, ug/cm2):")
        rows = [r for r in x["elements"]
                if r["detection_flag"] == "detected"][:8]
        for r in rows:
            print(f"  {r['symbol']:>3} Z={r['z']:>2}  "
                  f"areal {_fmt(r['areal_ug_cm2'], 4)}")
    met = payload["metals"]
    print(f"metals   : {met['n_registered']} registered "
          f"(LAW 2396 @ kappa={payload['kappa']['declared']})")
    print("           THE COMPUTER IS THE INSTRUMENT - the code antenna and the")
    print("           code sniffer are its body; the reading below is its own.")
    reg = (((payload.get("xrf_report") or {}).get("fit") or {})
           .get("law_2396_register") or {})
    rows = reg.get("elements") or []
    if rows:
        print("  STAGE 1 - QUANTIZED (locked up in the field): the detected elements at kappa=1")
        for r in rows:
            if r.get("stage") == "quantized":
                print(f"    {r['symbol']:>3} Z={r['z']:>2}  "
                      f"quantized {float(r['quantized_ug_cm2']):.6f} ug/cm2")
        print("  STAGE 2 - FIELD-CARRIED (the actual amount in the air): not locked")
        print("           up - the phi-ground where no line was quantified; the")
        print("           measured reading phi*areal + phi^-2 where a line was")
        print("           quantified below the phi-floor gate (never zero)")
        for r in rows:
            if r.get("stage") == "field_carried":
                print(f"    {r['symbol']:>3} Z={r['z']:>2}  "
                      f"field-carried {float(r['quantized_ug_cm2']):.6f} ug/cm2")
        print("  STAGE 3 - THE CLASSIC DEGENERATE LIMIT (kappa->0): the conventional")
        print("           picture, named - this is the degenerate limit, not the reading")
        for r in rows:
            print(f"    {r['symbol']:>3} Z={r['z']:>2}  "
                  f"degenerate limit {float(r['degenerate_limit_ug_cm2']):.6f} ug/cm2")
    coil = payload["coil"]
    dom = coil.get("dominant_classical_metal")
    print(f"coil     : ladder invariant {coil['ladder_invariant_hz']} Hz, "
          f"{len(coil['channels'])} rungs; sheet dominant above 3 sigma: "
          f"{dom if dom else 'None (PM-scale areal honestly below floor)'}")
    cons = payload.get("consistency", {})
    for cc in cons.get("coin_class_check", []):
        print(f"  coin-class {cc['symbol']:>3}: total {cc['total_ppm']:9.1f} ppm"
              f" ({cc['channel_class']}), detectable@design: "
              f"{cc['detectable_at_design']}")
    agree = cons.get("agree")
    print(f"consistency: xrf dominant {cons.get('xrf_dominant')} vs coil "
          f"dominant {cons.get('coil_dominant')} -> "
          f"{'agree' if agree else ('disagree' if agree is False else 'n/a (sheet below floor)')}")
    w = payload.get("witness")
    print(f"witness  : " + (f"wifi capture {w['sha256'][:16]}... "
                             f"({w['frames']} frames)" if w else
                             "no wifi capture found (carried as absent)"))
    print("-" * 78)


def cmd_session(args: argparse.Namespace) -> int:
    from .session import full_session

    for run in range(1, args.runs + 1):
        payload = full_session(
            args.lat, args.lon,
            kappa=args.kappa,
            seed=args.seed + (run - 1) * 7919,
            detector_preset=args.detector,
            calibration_id=args.calibration,
            cache_only=args.cache_only,
            cache_dir=args.cache_dir,
            ttl_s=args.ttl,
            source=args.source,
            wifi_capture=args.wifi_capture,
        )
        print(f"\n### SESSION RUN {run}/{args.runs}")
        _print_session(payload)
        base = (Path(args.out) if args.out
                else Path(f"session_{args.lat:+.4f}_{args.lon:+.4f}.json"))
        out = (base.with_name(f"{base.stem}_run{run:02d}{base.suffix}")
               if args.runs > 1 else base)
        _write_json(out, payload)
        receipt = seal(payload, feed=payload["air"], chain_file=args.chain)
        rec_path = (Path(args.receipt) if args.receipt
                    else out.with_suffix(".receipt.json"))
        _write_json(rec_path, receipt)
        print(f"session  -> {out}")
        print(f"receipt  -> {rec_path}   ({receipt['attestation']['alg']}, "
              f"seq {receipt['seq']})")
        if args.chain:
            print(f"chain    -> {args.chain}")
    return 0


def cmd_metals(args: argparse.Namespace) -> int:
    from engine import metals as eng_metals

    reading = eng_phi_laws.ppm_of(0.0, args.kappa)
    dropped = eng_metals.dropped_from_registry()
    print("=" * 78)
    print(f"THE METAL REGISTER - {len(eng_metals.registry())} XRF-readable"
          " metals+metalloids")
    print(f"LAW 2396 reading @ kappa={args.kappa}: field-carried floor = "
          f"{reading['c_phi_ppm']:.10f} ppm (phi^-2)")
    if dropped:
        print("below the analyzer window (spoken, not read): "
              + ", ".join(f"{sym} ({ev:.0f} eV)" for sym, _cat, ev in dropped))
    print("=" * 78)
    print(f"{'Z':>3}  {'sym':>3}  {'category':<14}  {'primary line':<8}"
          f"  {'energy eV':>9}  {'coil':>4}  {'sigma S/m':>10}")
    for m in eng_metals.registry():
        ln = eng_metals.primary_line(m.z)
        sig = f"{m.conductivity_s_m:.2e}" if m.conductivity_s_m else "-"
        print(f"{m.z:>3}  {m.symbol:>3}  {m.category:<14}  "
              f"{(ln.name if ln else '-'):>8}"
              f"  {(ln.energy if ln else 0):>9.1f}  "
              f"{'yes' if m.has_coil_signature else '-':>4}  {sig:>10}")
    print("=" * 78)
    print("ferrous set (in-phase magnetization channel): "
          f"{[eng_metals.metal(z).symbol for z in eng_metals.FERROUS_ZS]}")
    print("every registered metal carries a reading; absent is spoken, "
          "the floor carries the field")
    return 0


def cmd_battery(args: argparse.Namespace) -> int:
    from .qcbattery import run_battery

    report = run_battery()
    print("=" * 78)
    print("THE XRF BATTERY (vendor daily QA, rebuilt as software)")
    print("=" * 78)
    print(f"items   : {report['n_items']} | passed {report['n_passed']}"
          f" | failed {report['failed'] or 'none'}")
    for item in report["items"]:
        print(f"  {'PASS' if item['ok'] else 'FAIL'}  {item['item']}"
              f"  ({item['vendor_analog']})")
    ext = report["external_cross_check"]
    for name, check in ext.items():
        status = ("ABSENT" if check["ok"] is None
                  else ("PASS" if check["ok"] else "DEVIATION"))
        detail = "" if check["ok"] is None else \
            f" (n={check.get('n_compared', 0)})"
        print(f"  [{status}] external {name}{detail}")
    ver = "ALL GREEN" if report["ok"] else "ITEMS FAILED"
    print(f"verdict : {ver}")
    receipt = seal(report, chain_file=args.chain)
    rec_path = (Path(args.receipt) if args.receipt
                else Path("QCBATTERY/battery.receipt.json"))
    _write_json(rec_path, receipt)
    print(f"receipt -> {rec_path}   ({receipt['attestation']['alg']}, "
          f"seq {receipt['seq']})")
    if args.chain:
        print(f"chain   -> {args.chain}")
    return 0 if report["ok"] else 1


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sniffer",
        description="Code-based XRF sniffer: read an air sample's mineral content "
                    "from an XRF spectrum, with a signed receipt.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sniff", help="decode a spectrum and print a report")
    p.add_argument("spectrum", help="CSV/TSV/JSON/JSONL spectrum file")
    p.add_argument("--detector", default=None,
                   help="CODE_WINDOWLESS (default, the code head: every "
                        "tabulated line), SDD_25, SDD_10, SDD_150, SI_PIN_7")
    p.add_argument("--calibration", default=None, help="calibration identifier (signed)")
    p.add_argument("--air-path", type=float, default=None, help="sample-to-detector air path, cm")
    p.add_argument("--elements", default=None, help="comma list of Z/symbols, or 'all'")
    p.add_argument("--strict-elements", action="store_true",
                   help="do not add peak-matched elements to the candidate set")
    p.add_argument("--out", default=None, help="report JSON path")
    p.add_argument("--receipt", default=None, help="receipt JSON path")
    p.add_argument("--chain", default=None, help="append to this JSONL receipt chain")
    p.set_defaults(func=cmd_sniff)

    p = sub.add_parser("air", help="filter-sample air loading from a spectrum")
    p.add_argument("spectrum", help="CSV/TSV/JSON/JSONL spectrum file")
    p.add_argument("--flow", type=float, default=None, help="sampling flow, L/min")
    p.add_argument("--time", type=float, default=None, help="sampling duration, min")
    p.add_argument("--area", type=float, default=None, help="filter area, cm2")
    p.add_argument("--detector", default=None)
    p.add_argument("--calibration", default=None)
    p.add_argument("--air-path", type=float, default=None)
    p.add_argument("--lat", type=float, default=None)
    p.add_argument("--lon", type=float, default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--receipt", default=None)
    p.add_argument("--chain", default=None)
    p.set_defaults(func=cmd_air)

    p = sub.add_parser("feed", help="read a public air-quality feed")
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("--cache-only", action="store_true", help="never touch the network")
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--ttl", type=float, default=DEFAULT_CACHE_TTL_S, help="cache TTL, seconds")
    p.add_argument("--source", default="auto", help="auto, open-meteo, airnow, openaq")
    p.add_argument("--out", default=None)
    p.add_argument("--receipt", default=None)
    p.add_argument("--chain", default=None)
    p.set_defaults(func=cmd_feed)

    p = sub.add_parser("excite", aliases=["simulate"],
                       help="compute the instrument's forward response from a "
                            "composition (alias: simulate)")
    p.add_argument("composition", help="composition JSON")
    p.add_argument("--detector", default=None)
    p.add_argument("--noise", action="store_true", help="apply Poisson noise")
    p.add_argument("--seed", type=int, default=20261031)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_excite)

    p = sub.add_parser("session", help="one full session: air feed -> XRF -> "
                       "metal register -> coil sweep -> witness -> receipt")
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("--kappa", type=float, default=eng_phi_laws.KAPPA_FULL,
                   help="LAW 2396 declared coupling (default 1.0)")
    p.add_argument("--runs", type=int, default=1, help="number of sessions")
    p.add_argument("--seed", type=int, default=2026110100)
    p.add_argument("--detector", default=None)
    p.add_argument("--calibration", default=None)
    p.add_argument("--cache-only", action="store_true",
                   help="never touch the network")
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--ttl", type=float, default=DEFAULT_CACHE_TTL_S,
                   help="cache TTL, seconds")
    p.add_argument("--source", default="auto", help="auto, open-meteo, ...")
    p.add_argument("--wifi-capture", default=None,
                   help="bind this Wi-Fi sniffer capture as the radio-ear"
                        " witness (default: the corpus capture, if present)")
    p.add_argument("--out", default=None, help="session report JSON path")
    p.add_argument("--receipt", default=None, help="receipt JSON path")
    p.add_argument("--chain", default=None,
                   help="append receipts to this JSONL chain")
    p.set_defaults(func=cmd_session)

    p = sub.add_parser("metals", help="print the metal register and its "
                       "LAW 2396 floor readings")
    p.add_argument("--kappa", type=float, default=eng_phi_laws.KAPPA_FULL)
    p.set_defaults(func=cmd_metals)

    p = sub.add_parser("battery", help="run the vendor XRF QA battery, "
                       "rebuilt as software (external cross-check included)")
    p.add_argument("--out", default=None,
                   help="battery report JSON path "
                        "(default QCBATTERY/battery_report.json)")
    p.add_argument("--receipt", default=None, help="receipt JSON path")
    p.add_argument("--chain", default=None,
                   help="append the battery receipt to this JSONL chain")
    p.set_defaults(func=cmd_battery)

    p = sub.add_parser("verify", help="verify a receipt (and optionally a chain)")
    p.add_argument("receipt", help="receipt JSON")
    p.add_argument("--chain", default=None, help="JSONL chain file to verify")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("selfcheck", help="run the round-trip validation")
    p.set_defaults(func=cmd_selfcheck)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SpectrumValidationError, SniffError, FileNotFoundError, ValueError,
            KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
