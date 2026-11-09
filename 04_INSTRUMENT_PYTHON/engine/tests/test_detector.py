"""Detector response: resolution specs, efficiency, escape peaks, shape."""
import numpy as np
import pytest

from engine import detector


def test_resolution_specs():
    rows = detector.validate(verbose=True)
    for r in rows:
        print(f"{r['detector']:>12}  spec {r['spec_fwhm_ev']:5.1f} eV  "
              f"computed {r['computed_fwhm_ev']:6.1f} eV  "
              f"({r['dev_pct']:+5.2f} %)")
        assert abs(r["dev_pct"]) < 0.5, r


def test_fwhm_scaling():
    d = detector.SDD_25
    f1, f4 = float(d.fwhm(1000.0)), float(d.fwhm(4000.0))
    print(f"FWHM(1 keV) {f1:.1f} eV, FWHM(4 keV) {f4:.1f} eV")
    # sqrt(a^2 + bE) grows sub-linearly and monotonically
    assert f4 > f1
    assert f4 < 4 * f1
    assert float(d.fwhm(0.0)) == pytest.approx(d.fwhm_a_ev)


def test_efficiency_shape():
    d = detector.SDD_25
    eff = [float(d.peak_efficiency(e)) for e in (1740, 5895, 12000, 20000, 30000)]
    print("efficiency:", [round(x, 4) for x in eff])
    assert all(0 < x <= 1 for x in eff)
    assert eff[1] > eff[0]          # Be window dominates at 1.7 keV
    assert eff[2] > eff[3] > eff[4]  # silicon transparency above ~10 keV


def test_escape_peak():
    d = detector.SDD_25
    p = d.escape_probability(6405.0)
    print(f"escape fraction at 6.4 keV: {100*p:.3f} % (vendor-typical ~1 %)")
    assert 0 < p < 0.02
    assert d.escape_probability(1500.0) == 0.0
    assert float(d.escape_energy(6405.0)) == pytest.approx(6405.0 - 1739.98, abs=1e-6)


def test_gaussian_normalisation():
    x = np.arange(0.0, 20000.0, 1.0)
    y = detector.gaussian(x, 6000.0, 50.0, area=1234.0)
    print(f"Gaussian area: {y.sum():.3f} (requested 1234)")
    assert y.sum() == pytest.approx(1234.0, rel=1e-3)
    assert y.argmax() == 6000


def test_peak_shape_no_tail():
    x = np.arange(0.0, 20000.0, 1.0)
    a = detector.SDD_25.gaussian(x, 6000.0, 100.0)
    b = detector.SDD_25.peak_shape(x, 6000.0, 100.0)
    assert np.allclose(a, b)


def test_self_check():
    assert detector.self_check() == []
