"""Forward operator: linearity, thresholds, air attenuation, absolute sanity."""
import numpy as np
import pytest

from engine import air, detector, forward, lines


def test_linearity_in_areal_density():
    exc = forward.Excitation.monoenergetic(10000.0, 1e10)
    grid = np.arange(0.0, 12000.0, 10.0)
    a = forward.forward_spectrum(forward.Sample({"Fe": 1e-6}), exc,
                                 background=None, energy_grid=grid)
    b = forward.forward_spectrum(forward.Sample({"Fe": 4e-6}), exc,
                                 background=None, energy_grid=grid)
    ratio = b.total_counts / a.total_counts
    print(f"4x areal density -> {ratio:.4f}x counts")
    assert ratio == pytest.approx(4.0, rel=0.02)


def test_no_fluorescence_below_edge():
    exc = forward.Excitation.monoenergetic(6000.0, 1e10)   # below Fe K 7112
    grid = np.arange(0.0, 12000.0, 10.0)
    s = forward.forward_spectrum(forward.Sample({"Fe": 1e-4}), exc,
                                 background=None, energy_grid=grid)
    print(f"counts below the Fe K edge: {s.total_counts:.6f}")
    assert s.total_counts == pytest.approx(0.0, abs=1e-9)


def test_above_edge_emits_kalpha():
    exc = forward.Excitation.monoenergetic(8000.0, 1e10)
    grid = np.arange(0.0, 12000.0, 10.0)
    s = forward.forward_spectrum(forward.Sample({"Fe": 1e-4}), exc,
                                 background=None, energy_grid=grid)
    i = int(np.argmin(np.abs(grid - 6405.2)))
    print(f"Fe K-alpha peak height: {s.counts[i-5:i+5].max():.1f} counts")
    assert s.counts[i - 5:i + 5].max() > 1.0


def test_air_attenuates():
    exc = forward.Excitation.monoenergetic(10000.0, 1e10)
    grid = np.arange(0.0, 12000.0, 10.0)
    s = forward.Sample({"Fe": 1e-4})
    near = forward.forward_spectrum(s, exc, background=None, energy_grid=grid,
                                    air_path_cm=0.0)
    far = forward.forward_spectrum(s, exc, background=None, energy_grid=grid,
                                   air_path_cm=100.0)
    i = int(np.argmin(np.abs(grid - 6405.2)))
    ratio = far.counts[i - 5:i + 5].max() / near.counts[i - 5:i + 5].max()
    expected = float(air.air_transmission(6405.0, 100.0))
    print(f"100 cm air transmission at 6.4 keV: {ratio:.5f} "
          f"(Beer-Lambert {expected:.5f})")
    assert ratio == pytest.approx(expected, rel=1e-2)


def test_absolute_count_sanity():
    """Hand calculation for 100 ug/cm2 Fe at 10 keV, K lines only.

    vacancies = flux * mu_pe * m * f_K
    counts    = vacancies * omega_K * branch * Omega/4pi * eff * live
    """
    from engine import attenuation, cross_section, yields
    flux, m, live = 1e10, 1e-4, 100.0
    exc = forward.Excitation.monoenergetic(10000.0, flux)
    spec = forward.forward_spectrum(forward.Sample({"Fe": m}), exc,
                                    background=None, live_time_s=live,
                                    include_escape=False, air_path_cm=0.0)
    mu = float(attenuation.mu_rho_pe(26, 10000.0))
    fk = cross_section.k_shell_fraction(26, 10000.0)
    omega = yields.omega_k(26)
    eff = float(detector.SDD_25.peak_efficiency(6405.2))
    branch = sum(l.intensity for l in lines.lines(26, "K"))
    expected = flux * mu * m * fk * omega * branch * 0.01 * eff * live
    # K lines only: everything above 6 keV
    got = float(spec.counts[spec.energy_ev > 6000.0].sum())
    print(f"hand calculation {expected:.1f} counts, engine {got:.1f} counts "
          f"({100*(got/expected-1):+.2f} %)")
    assert got == pytest.approx(expected, rel=0.03)


def test_design_matrix_units():
    exc = forward.Excitation.monoenergetic(10000.0, 1e10)
    grid = np.arange(0, 12000.0, 10.0)
    A, _ = forward.design_matrix([26], exc, live_time_s=100.0,
                                 energy_grid=grid, include_escape=False)
    unit = forward.forward_spectrum(forward.Sample({"Fe": 1e-6}), exc,
                                    background=None, live_time_s=100.0,
                                    energy_grid=grid, include_escape=False)
    print(f"design column sum {A[:,0].sum():.3f}, direct {unit.total_counts:.3f}")
    assert A[:, 0].sum() == pytest.approx(unit.total_counts, rel=1e-9)


def test_self_check():
    assert forward.self_check() == []
