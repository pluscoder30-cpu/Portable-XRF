"""Beer-Lambert: NIST air anchors, exact exponential identities, edge jumps."""
import math

import numpy as np
import pytest

from engine import air, attenuation


def test_nist_air():
    rows = attenuation.validate_nist_air(verbose=True)
    assert len(rows) == 7
    for r in rows:
        print(f"{r['energy_ev']/1000:5.1f} keV  NIST {r['nist']:8.4f}  "
              f"computed {r['computed']:8.4f} cm2/g  ({r['dev_pct']:+6.2f} %)")
        assert abs(r["dev_pct"]) < 1.0, r


def test_air_density():
    res = air.validate_air(verbose=False)
    for r in res["density"]:
        print(f"{r['t_c']:5.1f} degC  ref {r['reference']:.4f}  "
              f"computed {r['computed']:.4f} kg/m3  ({r['dev_pct']:+6.3f} %)")
        assert abs(r["dev_pct"]) < 0.1
    assert res["max_nist_dev_pct"] < 1.0


def test_beer_lambert_exact():
    res = attenuation.validate_beer_lambert()
    print(res)
    assert res["abs_err"] < 1e-15
    assert res["composition_error"] < 1e-15
    # a 2 cm half-value layer halves the beam
    assert attenuation.transmission(0.5, 2.0) == pytest.approx(math.exp(-1.0))


def test_transmission_is_multiplicative():
    mu = 3.7
    assert (attenuation.transmission(mu, 1.0) * attenuation.transmission(mu, 2.0)
            == pytest.approx(attenuation.transmission(mu, 3.0)))


def test_edge_jump_present():
    """mu/rho must jump upward at the Fe K edge (Law 1346)."""
    e = 7112.0
    below = float(attenuation.mu_rho(26, e * 0.999))
    above = float(attenuation.mu_rho(26, e * 1.001))
    print(f"Fe K edge: below {below:.2f}, above {above:.2f} cm2/g, "
          f"jump {above/below:.2f}")
    assert above / below > 5.0


def test_mixture_additivity():
    comp = {"Fe": 0.7, "Si": 0.3}
    e = 10000.0
    expected = 0.7 * float(attenuation.mu_rho(26, e)) + 0.3 * float(attenuation.mu_rho(14, e))
    assert attenuation.mu_rho_mixture(comp, e) == pytest.approx(expected)


def test_half_value_layer():
    hvl = attenuation.half_value_layer({"Fe": 1.0}, 7.874, 6405.0)
    print(f"Fe half-value layer at 6.405 keV: {hvl*1e4:.1f} um")
    assert 0 < hvl < 0.01


def test_energy_range():
    lo, hi = attenuation.energy_range()
    print(f"tabulated range: {lo:.0f} - {hi:.0f} eV")
    assert lo <= 500.0 and hi >= 40000.0


def test_vectorised_matches_scalar():
    e = np.array([5000.0, 10000.0, 20000.0])
    arr = attenuation.mu_rho(26, e)
    for i, ei in enumerate(e):
        assert arr[i] == pytest.approx(float(attenuation.mu_rho(26, float(ei))))
