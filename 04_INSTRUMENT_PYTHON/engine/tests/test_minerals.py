"""Minerals: exact formula chemistry, apportionment, unmixing."""
import numpy as np
import pytest

from engine import air, minerals


def test_formula_chemistry():
    expected = {
        "quartz": {"Si": 0.46743, "O": 0.53257},
        "hematite": {"Fe": 0.69944, "O": 0.30056},
        "halite": {"Na": 0.39340, "Cl": 0.60660},
        "calcite": {"Ca": 0.40043, "C": 0.12000, "O": 0.47957},
    }
    for name, want in expected.items():
        got = {minerals._elements.BY_Z[z].symbol: f
               for z, f in minerals.mineral_fractions(name).items()}
        for sym, w in want.items():
            print(f"{name:>8} {sym}: computed {got[sym]:.5f}, reference {w:.5f}, "
                  f"dev {got[sym]-w:+.5f}")
            assert got[sym] == pytest.approx(w, abs=2e-4)


def test_all_minerals_close():
    assert minerals.self_check() == []


def test_prior_weights_sum():
    for sym, priors in minerals.ELEMENT_MINERAL_PRIOR.items():
        assert sum(w for _, w in priors) == pytest.approx(1.0, abs=1e-9)


def test_apportion_conserves_elements():
    element_areal = {"Si": 10.0, "Al": 3.0, "Fe": 2.0, "Ca": 1.0, "K": 0.5}
    out = minerals.apportion(element_areal)
    print("apportioned minerals:", {k: round(v, 3) for k, v in out.items()})
    assert all(v > 0 for v in out.values())
    assert sum(out.values()) == pytest.approx(sum(element_areal.values()), rel=1e-9)


def test_unmix_recovers_a_known_mixture():
    names = ["quartz", "hematite", "calcite"]
    truth = {"quartz": 60.0, "hematite": 25.0, "calcite": 15.0}
    A, elems, _ = minerals.composition_matrix(names)
    x_true = np.array([truth[n] for n in names])
    y = A @ x_true
    element_areal = {s: float(v) for s, v in zip(elems, y) if v > 0}
    print("synthetic element masses:", {k: round(v, 3) for k, v in element_areal.items()})
    res = minerals.unmix(element_areal, names=names, lam=0.0)
    print("unmixed:", {k: round(v, 3) for k, v in res["minerals"].items()},
          "residual", round(res["closure"]["relative_residual"], 6))
    for n in names:
        assert res["minerals"][n] == pytest.approx(truth[n], rel=1e-6)
    assert res["closure"]["relative_residual"] < 1e-8


def test_unmix_with_noise_stays_positive():
    names = ["quartz", "orthoclase"]
    A, elems, _ = minerals.composition_matrix(names)
    y = A @ np.array([50.0, 20.0])
    noisy = {s: float(max(v * 1.05, 0)) for s, v in zip(elems, y)}
    res = minerals.unmix(noisy, names=names, lam=0.0)
    assert all(v >= 0 for v in res["minerals"].values())


def test_endmember_composition():
    dust = air.endmember_symbol_fractions("mineral_dust")
    print("mineral dust:", {k: round(v, 4) for k, v in sorted(dust.items())})
    assert dust["O"] > dust["Si"] > dust["Al"] > dust["K"]
    iron = air.endmember_symbol_fractions("iron_oxide")
    print("iron oxide:", {k: round(v, 4) for k, v in sorted(iron.items())})
    assert iron["Fe"] > 0.6
    salt = air.endmember_symbol_fractions("sea_salt")
    assert salt["Na"] == pytest.approx(0.3934, abs=1e-4)
    assert salt["Cl"] == pytest.approx(0.6066, abs=1e-4)


def test_crustal_elements_present():
    for sym in air.CRUSTAL_ELEMENTS:
        assert minerals._elements.element(sym).z > 0
