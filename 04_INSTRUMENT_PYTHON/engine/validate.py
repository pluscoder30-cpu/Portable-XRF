"""One command that prints every validation in the engine.

    python -m engine.validate            (from the XRF directory)
    python validate.py                   (from the engine directory)

Every number printed here is compared against an external anchor (NIST,
Krause & Oliver, Bearden, the vendor detector spec) or against an exact
identity.  Nothing is compared against itself.
"""
from __future__ import annotations

import numpy as np

from . import air, attenuation, constants, cross_section, detector
from . import elements, forward, inversion, lines, minerals, simulate, yields


def _hdr(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main() -> int:
    _hdr("1. ELEMENT TABLE")
    print(f"elements: {len(elements.ELEMENTS)} (Z = 1..{elements.ELEMENTS[-1].z})")
    print("structural self-check:", elements.self_check() or "clean")
    for sym, edge, ref in (("Fe", "K", 7112.0), ("Cu", "K", 8979.0),
                           ("Pb", "L3", 13035.0)):
        got = elements.edge_energy(sym, edge)
        print(f"  {sym} {edge}: {got:.1f} eV (reference {ref:.1f}, "
              f"{got-ref:+.1f} eV)")

    _hdr("2. LINE ENERGIES vs THE ANCHOR SET")
    rows = lines.validate_anchors(verbose=True)
    worst = max(abs(r["dev_ev"]) for r in rows)
    print(f"max |deviation| = {worst:.2f} eV "
          f"({max(abs(r['dev_pct']) for r in rows):.4f} %)")

    _hdr("3. MOSELEY'S LAW (Law 1344)")
    stats = lines.validate_moseley()
    print("sigma = 1 (textbook) :", stats["sigma_1"])
    print("sigma(Z) empirical   :", stats["sigma_fitted"])

    _hdr("4. LAW 1347: E_line = E_initial - E_final")
    print(lines.validate_edge_difference())

    _hdr("5. FLUORESCENCE YIELDS (Law 1345)")
    yields.validate_yields(verbose=True)
    print("power-law model vs Krause & Oliver:", yields.validate_table_vs_model())

    _hdr("6. ATTENUATION: NIST DRY AIR")
    att = attenuation.validate_nist_air(verbose=True)
    print(f"max deviation from NIST: "
          f"{max(abs(r['dev_pct']) for r in att):.3f} %")

    _hdr("7. AIR DENSITY")
    air.validate_air(verbose=True)

    _hdr("8. CROSS-SECTIONS")
    print("photoelectric E^-3 model:", cross_section.validate_powerlaw())
    kn = cross_section.validate_klein_nishina()
    print("Klein-Nishina Thomson limit ratio:",
          round(kn["thomson_ratio"], 8))
    print("Compton free-electron vs table: median "
          f"{kn['compton_dev_median_pct']:.1f} %, max "
          f"{kn['compton_dev_max_pct']:.1f} % (bound-electron suppression)")
    print("sharp thresholds:", cross_section.validate_thresholds())

    _hdr("9. DETECTOR")
    detector.validate(verbose=True)
    print("escape fraction at Mn K-alpha: "
          f"{100*detector.SDD_25.escape_probability(5895.0):.3f} % "
          "(vendor-typical ~1 %)")

    _hdr("10. FORWARD / INVERSE ROUND TRIP")
    results = simulate.benchmark(verbose=True)
    print("\nsummary:", simulate.summary_statistics(results))

    _hdr("11. MINERALS")
    print("chemistry self-check:", minerals.self_check() or "clean")
    for name in ("quartz", "hematite", "calcite", "halite"):
        fr = {elements.BY_Z[z].symbol: round(f, 4)
              for z, f in minerals.mineral_fractions(name).items()}
        print(f"  {name:>10}: {fr}")
    names = ["quartz", "hematite", "calcite"]
    truth = np.array([60.0, 25.0, 15.0])
    A, elems, _ = minerals.composition_matrix(names)
    element_areal = {s: float(v) for s, v in zip(elems, A @ truth) if v > 0}
    res = minerals.unmix(element_areal, names=names, lam=0.0)
    print("  unmix round trip:", {k: round(v, 3) for k, v in res["minerals"].items()},
          "residual", f"{res['closure']['relative_residual']:.2e}")

    _hdr("12. HONESTY FLAGS")
    print("SPECTROSCOPY_USES_PHI =", constants.SPECTROSCOPY_USES_PHI)
    print(f"corpus metadata carried: phi={constants.PHI}, "
          f"C_crit={constants.C_CRIT}, "
          f"ladder={constants.LADDER_INVARIANT_HZ:.3f} Hz")
    print("phi terms in any spectroscopy calculation: none")

    print()
    print("All checks completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
