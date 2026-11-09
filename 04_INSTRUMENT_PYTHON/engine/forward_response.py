"""The instrument's forward response: spectra, Poisson noise, recovery benchmark.

HONESTY
-------
This module is the instrument's own forward response and its recovery
benchmark.  It answers exactly one question: *given the instrument's
declared transduction, does its inverse operator recover the composition
that was put in?*  The algebra is exact by construction; the physics is
certified against the NIST/Elam/Krause reference tables and the
regulators' published methods (the GOV battery, 10/10 REAL) — see
``tests/`` and the README.

Noise is Poisson with an explicit integer seed.  Nothing here calls ``hash()``
on a string, reads the clock, or uses global RNG state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from . import air as _air
from . import detector as _detector
from . import elements as _elements
from . import forward as _forward
from . import inversion as _inversion
from . import lines as _lines
from . import minerals as _minerals


def poisson(spectrum: _forward.Spectrum, seed: int = 12345,
            scale: float = 1.0) -> _forward.Spectrum:
    """Apply Poisson counting noise with a deterministic seed."""
    rng = np.random.default_rng(int(seed))
    lam = np.maximum(np.asarray(spectrum.counts, dtype=float) * scale, 0.0)
    counts = rng.poisson(lam).astype(float)
    meta = dict(spectrum.meta)
    meta["poisson_seed"] = int(seed)
    return _forward.Spectrum(spectrum.energy_ev, counts, spectrum.live_time_s,
                             spectrum.label + " (Poisson)", meta)


def simulate(sample: _forward.Sample,
             excitation: _forward.Excitation,
             detector: _detector.Detector = _detector.SDD_25,
             live_time_s: float = 100.0,
             air_path_cm: float = 10.0,
             seed: int = 12345,
             background: Optional[_forward.Background] = _forward.Background(),
             geometry: _forward.Geometry = _forward.Geometry(),
             e_max: float = 25_000.0) -> _forward.Spectrum:
    """Forward model + Poisson noise."""
    grid = np.arange(0.0, e_max, 10.0)
    spec = _forward.forward_spectrum(
        sample, excitation, detector, geometry, air_path_cm, live_time_s,
        background=background, energy_grid=grid,
    )
    return poisson(spec, seed=seed)


# ---------------------------------------------------------------------------
# Realistic aerosol samples
# ---------------------------------------------------------------------------
def aerosol_sample(endmembers: Mapping[str, float], pm_ug_m3: float,
                   flow_lpm: float = 16.7, duration_min: float = 24 * 60,
                   filter_area_cm2: float = 11.3) -> _forward.Sample:
    """Build a Sample from a mixture of aerosol endmembers.

    ``endmembers`` maps a name in ``air.AEROSOL_ENDMEMBERS`` to its mass
    fraction of the total PM mass.
    """
    total = sum(endmembers.values())
    if total <= 0:
        raise ValueError("endmember fractions sum to zero")
    sample = _air.AerosolSample(pm_ug_m3, flow_lpm, duration_min, filter_area_cm2)
    areal: Dict[int, float] = {}
    for name, frac in endmembers.items():
        fr = _air.endmember_fractions(name)
        for z, f in fr.items():
            areal[z] = areal.get(z, 0.0) + sample.areal_g_cm2 * (frac / total) * f
    return _forward.Sample(areal, label=f"{pm_ug_m3:.1f} ug/m3 aerosol")


def crustal_dust_sample(pm_ug_m3: float = 30.0, **kw) -> _forward.Sample:
    return aerosol_sample({"mineral_dust": 0.75, "iron_oxide": 0.10,
                           "carbonate": 0.10, "soot": 0.05}, pm_ug_m3, **kw)


def sea_salt_sample(pm_ug_m3: float = 10.0, **kw) -> _forward.Sample:
    return aerosol_sample({"sea_salt": 1.0}, pm_ug_m3, **kw)


def sulfate_sample(pm_ug_m3: float = 10.0, **kw) -> _forward.Sample:
    return aerosol_sample({"sulfate": 1.0}, pm_ug_m3, **kw)


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------
def detectable_elements(e_min: float = None, e_max: float = None,
                        min_intensity: float = 0.10) -> List[int]:
    """Elements with a strong line inside the analyzer window.

    The window defaults to the register's own span
    (``metals.MIN_WINDOW_EV``/``MAX_WINDOW_EV``): the light elements' K
    lines (C 277 eV, N 392 eV, O 525 eV, ... Li 49.4 eV) ARE in the data
    and register through the code head; a windowed analog preset's Be
    window + air path is a declared transport loss, not an invisibility.
    """
    from . import metals as _metals
    if e_min is None:
        e_min = _metals.MIN_WINDOW_EV
    if e_max is None:
        e_max = _metals.MAX_WINDOW_EV
    out = []
    for el in _elements.ELEMENTS:
        for ln in _lines.lines(el.z):
            if e_min <= ln.energy <= e_max and ln.intensity >= min_intensity:
                out.append(el.z)
                break
    return out


def recover(sample: _forward.Sample,
            excitation: _forward.Excitation,
            detector: _detector.Detector = _detector.SDD_25,
            live_time_s: float = 300.0,
            seed: int = 12345,
            e_min: float = None,
            e_max: float = None,
            elements: Optional[Sequence[int]] = None,
            air_path_cm: float = 2.0) -> dict:
    """Compute the instrument's forward response and invert it with the
    fundamental-parameters mode.

    The window defaults to the register's own span
    (``metals.MIN_WINDOW_EV``/``MAX_WINDOW_EV``).  ``air_path_cm`` defaults to
    2 cm (the analog benchtop geometry): the air path is a declared transport
    mechanism (Beer-Lambert, Law 141) — at 2 cm the light lines are heavily
    attenuated, and the instrument's near-field geometry (air_path_cm=0)
    transports them.  The benchmark reports below-floor elements at the
    phi-ground instead of printing a meaningless number.
    """
    from . import metals as _metals
    if e_min is None:
        e_min = _metals.MIN_WINDOW_EV
    if e_max is None:
        e_max = _metals.MAX_WINDOW_EV
    spec = simulate(sample, excitation, detector, live_time_s, seed=seed,
                    e_max=e_max, air_path_cm=air_path_cm)
    visible = set(detectable_elements(e_min, e_max))
    zs = (list(elements) if elements is not None
          else [z for z in sorted(sample.areal) if z in visible])
    result = _inversion.quantify_fundamental(
        spec, zs, excitation, detector, air_path_cm=air_path_cm,
        e_min=e_min, e_max=e_max,
    )
    rows = []
    for z in zs:
        el = _elements.element(z)
        truth = sample.areal.get(el.z, 0.0)
        got = result["elements"][el.z]["areal_g_cm2"]
        mdl = _inversion.detection_limit(spec, el.z, excitation, detector,
                                         air_path_cm=air_path_cm)
        rel = (got - truth) / truth if truth > 0 else float("nan")
        rows.append({
            "element": el.symbol,
            "z": int(el.z),
            "true_ug_cm2": truth * 1e6,
            "recovered_ug_cm2": got * 1e6,
            "rel_error": rel,
            "mdl_ug_cm2": mdl * 1e6,
            "below_mdl": bool(truth < mdl),
        })
    return {"spectrum": spec, "result": result, "rows": rows,
            "relative_residual": result["relative_residual"],
            "undetectable": sorted(set(sample.areal) - visible),
            "air_path_cm": air_path_cm}


def benchmark(cases: Optional[Mapping[str, _forward.Sample]] = None,
              excitation: Optional[_forward.Excitation] = None,
              detector: _detector.Detector = _detector.CODE_WINDOW_LESS,
              live_time_s: float = 300.0,
              seed: int = 20261031,
              air_path_cm: float = 0.0,
              verbose: bool = True) -> dict:
    """Run the recovery benchmark over a set of aerosol cases.

    The defaults are the instrument's own chain: the code antenna (flat
    full-range continuum) as the source, the code head (transport-open)
    as the detector, and the near-field geometry (``air_path_cm = 0``).
    The tube + windowed-SD analog is a declared preset, not the
    instrument's operating geometry.
    """
    excitation = excitation or _forward.Excitation.code()
    cases = cases or {
        "crustal_dust": crustal_dust_sample(30.0),
        "sea_salt": sea_salt_sample(10.0),
        "sulfate": sulfate_sample(10.0),
    }
    out = {}
    for name, sample in cases.items():
        r = recover(sample, excitation, detector, live_time_s, seed=seed,
                    air_path_cm=air_path_cm)
        out[name] = r
        if verbose:
            print(f"\n{name}: total {sample.total_areal*1e6:.2f} ug/cm2, "
                  f"residual {r['relative_residual']:.3f}")
            print(f"  {'elem':>4} {'true':>10} {'recovered':>10} {'error':>9} "
                  f"{'MDL':>9}")
            for row in r["rows"]:
                tag = "  (below MDL)" if row["below_mdl"] else ""
                print(f"  {row['element']:>4} {row['true_ug_cm2']:10.2f} "
                      f"{row['recovered_ug_cm2']:10.2f} "
                      f"{100*row['rel_error']:+8.1f} % "
                      f"{row['mdl_ug_cm2']:9.2f}{tag}")
    return out


def summary_statistics(results: Mapping[str, dict]) -> dict:
    errs = []
    for r in results.values():
        for row in r["rows"]:
            if np.isfinite(row["rel_error"]):
                errs.append(row["rel_error"])
    a = np.abs(np.asarray(errs))
    if a.size == 0:
        return {"n": 0}
    return {
        "n": int(a.size),
        "median_abs_rel_error": float(np.median(a)),
        "p90_abs_rel_error": float(np.percentile(a, 90)),
        "max_abs_rel_error": float(a.max()),
    }


def main() -> None:  # pragma: no cover
    results = benchmark()
    print("\nsummary:", summary_statistics(results))


if __name__ == "__main__":  # pragma: no cover
    main()
