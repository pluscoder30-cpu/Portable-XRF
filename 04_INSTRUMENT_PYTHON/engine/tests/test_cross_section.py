"""Cross-sections: the E^-3 model, Klein-Nishina, Compton shift, thresholds."""
import math

import pytest

from engine import cross_section as cs
from engine.constants import CLASSICAL_ELECTRON_RADIUS_CM


def test_powerlaw_error():
    res = cs.validate_powerlaw(verbose=False)
    print("photoelectric E^-3 model:", res)
    assert res["n"] > 20
    assert res["median_abs_pct"] < 25.0


def test_klein_nishina_thomson_limit():
    res = cs.validate_klein_nishina()
    print(f"Thomson {res['thomson_limit_cm2']:.6e} cm2, "
          f"KN(1 eV) {res['kn_at_1ev_cm2']:.6e} cm2, ratio {res['thomson_ratio']:.8f}")
    assert res["thomson_ratio"] == pytest.approx(1.0, abs=1e-5)
    assert cs.thomson_total() == pytest.approx(
        8 * math.pi / 3 * CLASSICAL_ELECTRON_RADIUS_CM ** 2, rel=1e-12)


def test_klein_nishina_known_value():
    """At 511 keV, sigma_KN / sigma_T = 0.4307 (textbook)."""
    ratio = cs.klein_nishina_total(510998.95) / cs.thomson_total()
    print(f"sigma_KN(511 keV)/sigma_T = {ratio:.4f} (textbook 0.4307)")
    assert ratio == pytest.approx(0.4307, abs=5e-4)


def test_compton_shift():
    # h/(m_e c) = 0.0242631 Angstrom
    d90 = cs.compton_wavelength_shift(100000.0, math.pi / 2)
    d180 = cs.compton_wavelength_shift(100000.0, math.pi)
    print(f"Delta-lambda(90 deg) = {d90:.7f} A, (180 deg) = {d180:.7f} A")
    assert d90 == pytest.approx(0.0242631, abs=1e-6)
    assert d180 == pytest.approx(2 * d90, rel=1e-9)


def test_compton_scattered_energy():
    e = cs.compton_scattered_energy(100000.0, math.pi / 2)
    print(f"100 keV at 90 deg -> {e/1000:.3f} keV (textbook 83.6 keV)")
    assert e / 1000 == pytest.approx(83.6, abs=0.1)


def test_sharp_thresholds():
    res = cs.validate_thresholds()
    print("threshold check:", res)
    assert res["violations"] == []
    assert cs.k_shell_fraction(26, 7112.0 * 0.999) == 0.0
    assert cs.k_shell_fraction(26, 7112.0 * 1.001) > 0.5


def test_self_check():
    assert cs.self_check() == []
