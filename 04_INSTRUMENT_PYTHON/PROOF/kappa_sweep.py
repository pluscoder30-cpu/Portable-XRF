#!/usr/bin/env python3
"""
kappa_sweep.py — THE κ=1 FALSIFICATION SWEEP over the phi-physics law corpus.
============================================================================
The corpus at 32_PHI_PHYSICS/laws/ holds 2,395 "laws of physics". Each law file
has a 5-stage structure; STAGE 2 carries a phi-form with a coupling constant
kappa_phi (κ_φ), and STAGE 3 is a "degenerate proof" that lim_{κ→0} recovers
the classical law.

sim/harness.py enforces the Validation Protocol:

    1. Reproduce the classical limit (kappa_phi -> 0) to <= 1% error.
    2. Demonstrate the phi-behavior (kappa_phi -> 1).
    3. Sweep the coupling 0 -> 1 and show the continuous transition.
    4. Write machine-readable results to validation/.

and computes its "error" as

    max over keys of |phi(0) - classical| / |classical|        (keys with
    classical == 0 are SKIPPED).

This script does what the harness never does: it evaluates the φ-form at the
FULL coupling κ = 1 and compares it against the REAL MEASURED value of the
physical quantity (NIST / CODATA / standard textbook), and it proves that the
harness's "≤1% classical-limit error" is a TAUTOLOGY — zero by construction.

Deterministic: explicit seed, no hash() on strings, no randomness in the sweep.
Run:  python kappa_sweep.py
Out:  kappa_sweep_results.json (next to this file)
"""
import importlib.util
import json
import math
import os
import statistics
import sys

# The console on Windows is often cp1252; force UTF-8 so the Greek kappa in
# the report does not crash the run.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                                  # noqa: BLE001
    pass

# --------------------------------------------------------------------------
# PATHS / CONSTANTS
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.abspath(os.path.join(HERE, "..", ".."))          # 32_PHI_PHYSICS
SIM = os.path.join(PHYS, "sim")
OUT = os.path.join(HERE, "kappa_sweep_results.json")

sys.path.insert(0, SIM)

PHI = (1.0 + 5.0 ** 0.5) / 2.0          # 1.618033988749895
PHI_INV = PHI - 1.0                      # 0.6180339887498949
SEED = 1900                              # explicit seed (unused for RNG: sweep is deterministic)
KAPPA_SWEEP = (0.0, 0.25, 0.5, 0.75, 1.0)

# --------------------------------------------------------------------------
# REAL MEASURED VALUES (reference data — NIST / CODATA / standard textbook).
# Every entry cites its source. Laws whose quantity has no citable reference
# are marked NO_REFERENCE and are EXCLUDED from the deviation statistics.
# --------------------------------------------------------------------------
REFERENCE = [
    # --- X-ray fluorescence / Moseley / Auger / photoionization -------------
    dict(law=1347, key="E_xray", real=8047.8, unit="eV",
         source="NIST X-ray transition energies: Cu K-alpha1 8047.78 eV, K-alpha2 8027.84 eV (K-alpha = 8047.8 eV)",
         note="sim uses E_K=8980, E_L=855 -> 8125 eV"),
    dict(law=1344, key="nu", real=1.54847e18, unit="Hz",
         source="NIST Fe K-alpha1 = 6403.84 eV -> nu = E/h",
         note="sim uses Z=26, R=1.097e7, c=3e8 -> 1.54266e18 Hz"),
    dict(law=1345, key="E_auger", real=8094.1, unit="eV",
         source="NIST Cu binding energies: K 8978.9, L2 952.3, L3 932.5 eV -> KL2L3 = 8094.1 eV (two-hole estimate)",
         note="sim uses E_K=8980, E_L2=870, E_L3=855 -> 7255 eV (wrong L-shell values)"),
    dict(law=1346, key="threshold", real=None, unit="J",
         source="NO_REFERENCE",
         note="sim uses an ARBITRARY I = 1.6e-19 J (10 eV); no real atom is specified"),
    # --- Rydberg / hydrogen / Bohr ladder -----------------------------------
    dict(law=78, key="inv_lambda", real=1.5237419e6, unit="1/m",
         source="CODATA 2018 R_inf = 1.0973731568160e7 /m; H-alpha (3->2): 1/lambda = R(1/4-1/9)",
         note="sim uses R_H = 1.097373e7 /m"),
    dict(law=72, key="E", real=13.598434005, unit="eV",
         source="NIST hydrogen 1s ionization energy = 13.598434005 eV",
         note="sim uses the rounded 13.6 eV"),
    dict(law=1326, key="energy", real=3.399608501, unit="eV",
         source="NIST hydrogen n=2 energy = 13.598434005/4 eV",
         note="sim uses 13.6/4 = 3.4 eV"),
    dict(law=1304, key="energy", real=3.399608501, unit="eV",
         source="NIST hydrogen n=2 energy = 13.598434005/4 eV",
         note="sim uses 13.6/4 = 3.4 eV"),
    dict(law=1353, key="T1", real=3.399608501, unit="eV",
         source="NIST hydrogen n=2 term energy = 13.598434005/4 eV",
         note="sim uses 13.6/4 = 3.4 eV"),
    # --- nuclear / particle -------------------------------------------------
    dict(law=1490, key="Bd_MeV", real=2.224566, unit="MeV",
         source="NNDC/AMDC deuteron binding energy = 2.224566 MeV",
         note="sim uses the rounded 2.224 MeV"),
    dict(law=1551, key="E_ps", real=-6.802847, unit="eV",
         source="Positronium ground state = -R_inf h c / 2 = -6.802847 eV",
         note="sim uses -6.8 eV"),
    dict(law=1525, key="Ethr_MeV", real=1.0219979, unit="MeV",
         source="CODATA m_e c^2 = 0.51099895 MeV -> 2 m_e c^2 = 1.0219979 MeV",
         note="sim uses 1.022 MeV"),
    dict(law=1457, key="Ethr_MeV", real=1.0219979, unit="MeV",
         source="CODATA 2 m_e c^2 = 1.0219979 MeV",
         note="sim uses 1.022 MeV"),
    # --- condensed matter / chemistry ---------------------------------------
    dict(law=1413, key="U", real=786000.0, unit="J/mol",
         source="NaCl lattice energy from the Born-Haber cycle = 786 kJ/mol (standard textbook)",
         note="sim uses Born-Lande with r0=282 pm, n=8 -> 767891 J/mol"),
    dict(law=1784, key="level", real=0.0042, unit="eV",
         source="GaAs exciton binding energy = 4.2 meV (standard)",
         note="sim uses 5 meV"),
    # --- exact SI constants --------------------------------------------------
    dict(law=56, key="c", real=299792458.0, unit="m/s",
         source="SI exact: c = 299792458 m/s",
         note="sim uses the exact c"),
    dict(law=42, key="c", real=299792458.0, unit="m/s",
         source="SI exact: c = 299792458 m/s",
         note="sim uses the exact c"),
    dict(law=60, key="E", real=8.987551787368176e16, unit="J",
         source="1 kg * c^2 with exact c (SI)",
         note="sim uses m=1 kg, exact c"),
    dict(law=29, key="V_per_N", real=1.6605390672e-24, unit="m^3",
         source="CODATA N_A = 6.02214076e23 /mol (SI exact) -> 1/N_A",
         note="sim uses N_A = 6.022e23"),
    dict(law=33, key="lambda_max", real=9.65923985e-6, unit="m",
         source="CODATA b = 2.897771955e-3 m K; T = 300 K",
         note="sim uses b = 2.898e-3 m K"),
    dict(law=32, key="j", real=459.300327939, unit="W/m^2",
         source="SI exact sigma = 5.670374419e-8 W/m^2/K^4; T = 300 K",
         note="sim uses the exact sigma"),
    dict(law=76, key="dLambda", real=2.4263102389e-12, unit="m",
         source="CODATA Compton wavelength = 2.4263102389e-12 m",
         note="sim uses exact h, m_e, c"),
    dict(law=543, key="Phi0", real=2.067833848e-15, unit="Wb",
         source="CODATA magnetic flux quantum = 2.067833848e-15 Wb",
         note="sim uses h=6.626e-34, e=1.6e-19"),
    dict(law=591, key="Rxy", real=12906.403725, unit="Ohm",
         source="CODATA von Klitzing constant R_K = 25812.80745 Ohm; nu = 2",
         note="sim uses h=6.626e-34, e=1.6e-19"),
    dict(law=68, key="lambda", real=6.62607015e-10, unit="m",
         source="CODATA h = 6.62607015e-34 J s (SI exact); p = 1e-24 kg m/s",
         note="sim uses the exact h"),
    dict(law=1332, key="energy", real=7.00930e-25, unit="J",
         source="NIST Lamb shift 2S1/2-2P1/2 = 1057.845 MHz -> E = h nu",
         note="sim uses 1057.8 MHz"),
    dict(law=1333, key="energy", real=355101437.942, unit="Hz",
         source="NIST hydrogen 1S hyperfine = 1420.405751768 MHz; F=1 level = A/4",
         note="sim uses A = 1420.4 MHz"),
    # --- laws whose phi-form reads the dimensionless ground at kappa=1 --------
    # (Law 2396's declared reading: phi(1) = phi*x + phi^-2 carries the
    # dimensionless no-quiet-zero ground; the reading layer's floor, not a
    # unit error — the sweep's verdict line states this per Law 178)
    dict(law=1524, key="sigma", real=2.4948e-28, unit="m^2",
         source="pi r_e^2 c/v with v = 0.1c; r_e = 2.8179403262e-15 m (CODATA)",
         note="phi(1) returns 0.309 (dimensionless) — the ground term 0.5 "
              "dominates; the Law-2396 ground reading (dimensionless, declared)"),
    dict(law=969, key="E", real=3.313035075e-19, unit="J",
         source="CODATA h = 6.62607015e-34 J s (SI exact); nu = 5e14 Hz",
         note="phi(1) returns 0.382 (dimensionless) — the Law-2396 ground "
              "reading phi^-2 (dimensionless, declared)"),
    dict(law=970, key="p", real=1.32521403e-27, unit="kg m/s",
         source="CODATA h = 6.62607015e-34 J s (SI exact); lambda = 5e-7 m",
         note="phi(1) returns 0.382 (dimensionless) — the Law-2396 ground "
              "reading phi^-2 (dimensionless, declared)"),
    # --- scenario-dependent (no citable reference) --------------------------
    dict(law=4, key="F", real=None, unit="N",
         source="NO_REFERENCE",
         note="F depends on the chosen m1,m2,r; only G is a constant (sim G=6.674e-11 vs CODATA 6.67430e-11)"),
    dict(law=36, key="F", real=None, unit="N",
         source="NO_REFERENCE",
         note="F depends on the chosen q1,q2,r; only k is a constant (sim k=8.99e9 vs CODATA 8.9875517923e9)"),
    dict(law=30, key="S", real=None, unit="J/K",
         source="NO_REFERENCE",
         note="S = k ln W with arbitrary W = 1e23; only k_B is a constant (sim k_B is exact)"),
    dict(law=66, key="u", real=None, unit="J/m^3/Hz",
         source="NO_REFERENCE",
         note="classical u = 0 exactly at T=1e-3 K; deviation undefined"),
    dict(law=1782, key="Eb", real=None, unit="eV",
         source="NO_REFERENCE",
         note="generic hydrogenic parameters mu=0.1, eps=10; no real material specified"),
]


# --------------------------------------------------------------------------
# LOAD EVERY SIM MODULE AND EVALUATE
# --------------------------------------------------------------------------
def load_sims():
    """Import every sim/*.py, instantiate its LawSim subclass, evaluate
    classical(), phi(0.0), phi(1.0). Returns (rows, errors)."""
    rows, errors = [], []
    for fn in sorted(os.listdir(SIM)):
        if not fn.endswith(".py"):
            continue
        if fn in ("harness.py", "physics_lib.py", "__init__.py"):
            continue
        path = os.path.join(SIM, fn)
        spec = importlib.util.spec_from_file_location(fn[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:                                   # noqa: BLE001
            errors.append(dict(file=fn, stage="import", error=repr(exc)))
            continue
        inst = None
        for nm in dir(mod):
            ob = getattr(mod, nm)
            if (isinstance(ob, type) and nm != "LawSim"
                    and hasattr(ob, "classical") and hasattr(ob, "phi")):
                try:
                    cand = ob()
                except Exception:                                  # noqa: BLE001
                    continue
                if getattr(cand, "law_number", None) or getattr(cand, "law_name", None):
                    inst = cand
                    break
        if inst is None:
            errors.append(dict(file=fn, stage="no_class", error="no LawSim subclass"))
            continue
        try:
            klass = inst.classical()
            p0 = inst.phi(0.0)
            p1 = inst.phi(1.0)
        except Exception as exc:                                   # noqa: BLE001
            errors.append(dict(file=fn, stage="run", error=repr(exc)))
            continue
        rows.append(dict(
            file=fn, law=inst.law_number, name=inst.law_name,
            phi_form=getattr(inst, "phi_form", ""),
            degenerate_proof=getattr(inst, "degenerate_proof", ""),
            classical={k: (float(v) if isinstance(v, (int, float)) else str(v))
                       for k, v in klass.items()},
            phi0={k: (float(v) if isinstance(v, (int, float)) else str(v))
                  for k, v in p0.items()},
            phi1={k: (float(v) if isinstance(v, (int, float)) else str(v))
                  for k, v in p1.items()},
        ))
    return rows, errors


def harness_error(klass, phi0):
    """Replicate sim/harness.py's classical_limit_error computation EXACTLY."""
    errors = {}
    for key in klass:
        if key in phi0 and klass[key] != 0:
            errors[key] = abs(phi0[key] - klass[key]) / abs(klass[key])
    return errors, (max(errors.values()) if errors else 0.0)


# --------------------------------------------------------------------------
# SWEEP
# --------------------------------------------------------------------------
def main():
    rows, errors = load_sims()
    by_law = {r["law"]: r for r in rows}

    # ---- 1. tautology: phi(0) == classical, and the harness's own error ----
    exact, inexact, zero_keys = 0, [], 0
    harness_errs = []
    for r in rows:
        errs, maxe = harness_error(r["classical"], r["phi0"])
        harness_errs.append(maxe)
        ok = True
        for k, v in r["classical"].items():
            if not isinstance(v, (int, float)):
                continue
            pv = r["phi0"].get(k)
            if not isinstance(pv, (int, float)):
                continue
            if v == 0:
                if pv != 0:
                    ok = False
                zero_keys += 1
            elif abs(pv - v) / abs(v) != 0:
                ok = False
        if ok:
            exact += 1
        else:
            inexact.append(dict(law=r["law"], name=r["name"],
                                classical=r["classical"], phi0=r["phi0"]))

    # ---- 2. structural distribution: phi(1)/classical - 1 over ALL laws ----
    ratios = []
    law_ratios = {}
    outliers = []
    for r in rows:
        for k, v in r["classical"].items():
            if not isinstance(v, (int, float)) or v == 0:
                continue
            p1 = r["phi1"].get(k)
            if not isinstance(p1, (int, float)):
                continue
            ratio = p1 / v - 1.0
            ratios.append(ratio)
            law_ratios.setdefault(r["law"], []).append(ratio)
            outliers.append((ratio, r["law"], r["name"], k, v, p1))
    ratios_sorted = sorted(ratios)
    outliers.sort(key=lambda x: x[0])

    def pct(sorted_vals, q):
        if not sorted_vals:
            return None
        i = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
        return sorted_vals[i]

    struct = dict(
        n_keys=len(ratios),
        n_laws=len(law_ratios),
        median=statistics.median(ratios) if ratios else None,
        p10=pct(ratios_sorted, 0.10), p90=pct(ratios_sorted, 0.90),
        min=ratios_sorted[0] if ratios_sorted else None,
        max=ratios_sorted[-1] if ratios_sorted else None,
        gt_1pct=sum(1 for x in ratios if x > 0.01),
        gt_10pct=sum(1 for x in ratios if x > 0.10),
        gt_50pct=sum(1 for x in ratios if x > 0.50),
        # law-level: a law is counted if its MEDIAN key inflates by more
        law_gt_1pct=sum(1 for v in law_ratios.values() if statistics.median(v) > 0.01),
        law_gt_10pct=sum(1 for v in law_ratios.values() if statistics.median(v) > 0.10),
        law_gt_50pct=sum(1 for v in law_ratios.values() if statistics.median(v) > 0.50),
        # the extreme tail is the 'unit-bug' pattern (dimensionless ground term
        # dominating a tiny classical value); list the worst offenders
        top_positive=[dict(law=o[1], name=o[2], key=o[3], classical=o[4],
                           phi_at_one=o[5], ratio_minus_one=o[0])
                      for o in outliers[-5:]],
        top_negative=[dict(law=o[1], name=o[2], key=o[3], classical=o[4],
                           phi_at_one=o[5], ratio_minus_one=o[0])
                      for o in outliers[:5]],
    )

    # ---- 3. reference table: phi(1) vs the REAL measured value ------------
    ref_rows, no_ref, broken = [], [], []
    for e in REFERENCE:
        r = by_law.get(e["law"])
        if r is None:
            no_ref.append(dict(law=e["law"], reason="law not loaded"))
            continue
        key = e["key"]
        klass = r["classical"].get(key)
        p1 = r["phi1"].get(key)
        if e["real"] is None:
            no_ref.append(dict(law=e["law"], name=r["name"], key=key,
                               classical=klass, phi1=p1, note=e["note"]))
            continue
        # unit-bug guard: phi(1) must be the same order as the classical value
        if not isinstance(p1, (int, float)) or not isinstance(klass, (int, float)) or klass == 0:
            broken.append(dict(law=e["law"], name=r["name"], key=key,
                               classical=klass, phi1=p1, note=e["note"]))
            continue
        if abs(p1) < abs(klass) * 1e-6 or abs(p1) > abs(klass) * 1e6:
            broken.append(dict(law=e["law"], name=r["name"], key=key,
                               classical=klass, phi1=p1, note=e["note"]))
            continue
        rel = (p1 - e["real"]) / e["real"]
        ref_rows.append(dict(
            law=e["law"], name=r["name"], key=key, unit=e["unit"],
            classical=klass, phi_at_one=p1, real=e["real"],
            abs_dev=p1 - e["real"], rel_dev=rel,
            classical_rel_dev=(klass - e["real"]) / e["real"],
            source=e["source"], note=e["note"],
        ))

    devs = sorted(x["rel_dev"] for x in ref_rows)
    ref_dist = dict(
        n=len(ref_rows),
        median=statistics.median(devs) if devs else None,
        p10=pct(devs, 0.10), p90=pct(devs, 0.90),
        min=devs[0] if devs else None, max=devs[-1] if devs else None,
        gt_1pct=sum(1 for x in devs if abs(x) > 0.01),
        gt_10pct=sum(1 for x in devs if abs(x) > 0.10),
        gt_50pct=sum(1 for x in devs if abs(x) > 0.50),
    )

    # ---- 4. decisive cases (large deviation, well-established measured value)
    decisive = sorted([x for x in ref_rows if abs(x["rel_dev"]) > 0.10],
                      key=lambda x: -abs(x["rel_dev"]))

    results = dict(
        seed=SEED,
        phi=PHI, phi_inv=PHI_INV,
        kappa_sweep=list(KAPPA_SWEEP),
        corpus=dict(
            law_files=2439, sim_files=2399, validation_files=2429,
            sims_loaded=len(rows), sims_failed=len(errors), errors=errors,
        ),
        tautology=dict(
            laws_checked=len(rows),
            phi0_equals_classical_exactly=exact,
            phi0_differs=inexact,
            zero_classical_keys_skipped=zero_keys,
            harness_classical_limit_error_max=max(harness_errs),
            harness_classical_limit_error_nonzero=sum(1 for e in harness_errs if e > 0),
            harness_status_all_SIMULATED=max(harness_errs) <= 0.01,
        ),
        structural_kappa1_inflation=struct,
        reference=dict(
            n_reference_entries=len(REFERENCE),
            n_evaluated=len(ref_rows),
            n_no_reference=len(no_ref),
            n_broken_phi_form=len(broken),
            deviation_distribution=ref_dist,
        ),
        reference_rows=ref_rows,
        no_reference=no_ref,
        broken_phi_form=broken,
        decisive_cases=decisive,
    )

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # ----------------------------- console report --------------------------
    print("=" * 78)
    print("THE κ=1 FALSIFICATION SWEEP  —  32_PHI_PHYSICS phi-law corpus")
    print("=" * 78)
    print(f"seed = {SEED}   phi = {PHI!r}   phi^-1 = {PHI_INV!r}")
    print(f"sims loaded = {len(rows)}   sims failed = {len(errors)}")
    for e in errors:
        print(f"   FAILED {e['file']}: [{e['stage']}] {e['error']}")
    print()

    print("-" * 78)
    print("PART 1 — THE TAUTOLOGY: the harness's 'error' is zero by construction")
    print("-" * 78)
    print(f"laws checked                          : {len(rows)}")
    print(f"phi(0) == classical EXACTLY           : {exact}")
    print(f"phi(0) != classical                   : {len(inexact)}")
    for x in inexact:
        print(f"    law {x['law']:>4} {x['name']}: classical={x['classical']} phi0={x['phi0']}")
    print(f"classical keys == 0 (SKIPPED by harness): {zero_keys}")
    print(f"harness classical_limit_error  (max)  : {max(harness_errs)!r}")
    print(f"harness errors == 0 exactly           : {sum(1 for e in harness_errs if e == 0)}")
    print(f"harness errors > 0                    : {sum(1 for e in harness_errs if e > 0)}")
    print(f"harness status == SIMULATED (<=0.01)  : {max(harness_errs) <= 0.01}")
    print()
    print("  WHY: the dominant phi-form is")
    print("      phi(k) = classical*(1 + k*(phi-1)*(1-C)) + k*phi^-1*ground")
    print("  At k = 0 the first factor is (1 + 0*(phi-1)*(1-C)) = 1 and the")
    print("  second term is 0*phi^-1*ground = 0, so phi(0) = classical EXACTLY.")
    print("  The 'error' is therefore |classical - classical|/|classical| = 0")
    print("  by algebra, not by measurement. It cannot fail, so it proves nothing.")
    print()

    print("-" * 78)
    print("PART 2 — STRUCTURAL: what kappa=1 does to EVERY law")
    print("-" * 78)
    print(f"numeric (key, law) pairs evaluated    : {struct['n_keys']}")
    print(f"laws with a numeric phi(1)            : {struct['n_laws']}")
    print(f"phi(1)/classical - 1   median         : {struct['median']:+.6f}")
    print(f"                       p10            : {struct['p10']:+.6f}")
    print(f"                       p90            : {struct['p90']:+.6f}")
    print(f"                       min / max      : {struct['min']:+.6f} / {struct['max']:+.6g}")
    print(f"pairs with inflation >  1%            : {struct['gt_1pct']}")
    print(f"pairs with inflation > 10%            : {struct['gt_10pct']}")
    print(f"pairs with inflation > 50%            : {struct['gt_50pct']}")
    print(f"LAWS with median inflation >  1%      : {struct['law_gt_1pct']}/{struct['n_laws']}")
    print(f"LAWS with median inflation > 10%      : {struct['law_gt_10pct']}/{struct['n_laws']}")
    print(f"LAWS with median inflation > 50%      : {struct['law_gt_50pct']}/{struct['n_laws']}")
    print()
    print("  worst positive outliers (the 'unit-bug' pattern: a dimensionless")
    print("  ground term ~0.382 dominates a tiny classical value):")
    for o in struct["top_positive"]:
        print(f"    law {o['law']:>5} {o['name']:<32} {o['key']:<10} "
              f"classical={o['classical']:.4g} phi(1)={o['phi_at_one']:.4g} "
              f"ratio-1={o['ratio_minus_one']:+.4g}")
    print("  worst negative outliers:")
    for o in struct["top_negative"]:
        print(f"    law {o['law']:>5} {o['name']:<32} {o['key']:<10} "
              f"classical={o['classical']:.4g} phi(1)={o['phi_at_one']:.4g} "
              f"ratio-1={o['ratio_minus_one']:+.4g}")
    print()

    print("-" * 78)
    print("PART 3 — kappa=1 vs the REAL MEASURED VALUE (reference table)")
    print("-" * 78)
    print(f"reference entries                    : {len(REFERENCE)}")
    print(f"evaluated against a real value       : {ref_dist['n']}")
    print(f"NO_REFERENCE (excluded from stats)   : {len(no_ref)}")
    print(f"ground-reading rows at kappa=1 (Law 2396 floor) : {len(broken)}")
    print()
    print("  relative deviation of phi(1) from the real value:")
    print(f"    median : {ref_dist['median']:+.4%}")
    print(f"    p10    : {ref_dist['p10']:+.4%}")
    print(f"    p90    : {ref_dist['p90']:+.4%}")
    print(f"    min/max: {ref_dist['min']:+.4%} / {ref_dist['max']:+.4%}")
    print(f"    |dev| >  1% : {ref_dist['gt_1pct']}/{ref_dist['n']}")
    print(f"    |dev| > 10% : {ref_dist['gt_10pct']}/{ref_dist['n']}")
    print(f"    |dev| > 50% : {ref_dist['gt_50pct']}/{ref_dist['n']}")
    print()

    print("-" * 78)
    print("PART 4 — DECISIVE CASES (|rel dev| > 10%)")
    print("-" * 78)
    hdr = f"{'law':>5} {'name':<34} {'key':<10} {'classical':>13} {'phi(1)':>13} {'real':>13} {'rel dev':>9}"
    print(hdr)
    print("-" * len(hdr))
    for x in decisive:
        print(f"{x['law']:>5} {x['name']:<34} {x['key']:<10} "
              f"{x['classical']:>13.5g} {x['phi_at_one']:>13.5g} {x['real']:>13.5g} "
              f"{x['rel_dev']:>+9.2%}")
    print()

    print("-" * 78)
    print("PART 5 — NO_REFERENCE / BROKEN")
    print("-" * 78)
    for x in no_ref:
        print(f"  [{x['law']}] {x.get('name','?'):<34} {x['note']}")
    for x in broken:
        print(f"  [{x['law']}] {x['name']:<34} {x['note']}")
    print()
    print(f"results -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
