"""Air sampling chain and the end-to-end recovery benchmark."""
import pytest

from engine import air, forward, simulate


def test_sampling_arithmetic():
    s = air.AerosolSample(concentration_ug_m3=35.0, flow_lpm=16.7,
                          duration_min=1440.0, filter_area_cm2=11.3)
    print(f"volume {s.volume_m3:.3f} m3, mass {s.collected_mass_ug:.1f} ug, "
          f"areal {s.areal_ug_cm2:.2f} ug/cm2")
    assert s.volume_m3 == pytest.approx(24.048, rel=1e-6)
    assert s.collected_mass_ug == pytest.approx(841.68, rel=1e-5)
    assert s.areal_ug_cm2 == pytest.approx(74.485, rel=1e-4)
    assert s.areal_g_cm2 == pytest.approx(s.areal_ug_cm2 * 1e-6)


def test_sampling_inverse():
    areal = air.areal_density_ug_cm2(20.0, 16.7, 1440.0, 11.3)
    back = air.pm_mass_from_areal(areal, 16.7, 1440.0, 11.3)
    print(f"20 ug/m3 -> {areal:.2f} ug/cm2 -> {back:.4f} ug/m3")
    assert back == pytest.approx(20.0, rel=1e-12)


def test_humidity_lowers_density():
    dry = air.air_density(20.0, 101.325, 0.0)
    wet = air.air_density(20.0, 101.325, 0.8)
    print(f"dry {dry:.4f} kg/m3, 80 % RH {wet:.4f} kg/m3")
    assert wet < dry


def test_attenuation_length():
    for e in (2000.0, 6405.0, 20000.0):
        length = air.attenuation_length_cm(e)
        print(f"{e/1000:5.2f} keV: 1/e length in air {length/100:.2f} m")
        assert length > 0
    assert air.attenuation_length_cm(20000.0) > air.attenuation_length_cm(6405.0)


def test_aerosol_sample_build():
    s = simulate.crustal_dust_sample(30.0)
    print(f"crustal dust 30 ug/m3 -> {s.total_areal*1e6:.2f} ug/cm2, "
          f"{len(s.areal)} elements")
    assert 40 < s.total_areal * 1e6 < 80
    assert 14 in s.areal and 26 in s.areal


def test_recovery_benchmark():
    results = simulate.benchmark(verbose=False)
    stats = simulate.summary_statistics(results)
    print("recovery statistics:", stats)
    rows = [row for r in results.values() for row in r["rows"]]
    for row in rows:
        print(f"{row['element']:>3} true {row['true_ug_cm2']:8.2f} "
              f"recovered {row['recovered_ug_cm2']:8.2f} "
              f"({100*row['rel_error']:+6.1f} %) "
              f"MDL {row['mdl_ug_cm2']:.2f}")
    # The instrument's own chain (code antenna + code head, near-field):
    # the declared recovery budgets — heavy band (Z>=12) <= 20 %, light
    # band (C/O/Na, 277-1040 eV) <= 35 % (the low-E blend + SNIP residual).
    assert stats["median_abs_rel_error"] < 0.05
    assert stats["p90_abs_rel_error"] < 0.60
    for row in rows:
        z = row["z"]
        limit = 0.35 if z in (6, 8, 11) else 0.20
        assert abs(row["rel_error"]) <= limit, (
            f"{row['element']} rel_error {row['rel_error']:+.3f} exceeds "
            f"the declared {limit:.0%} band"
        )


def test_poisson_is_deterministic():
    s = forward.Sample({"Fe": 1e-5})
    exc = forward.Excitation.monoenergetic(10000.0, 1e10)
    spec = forward.forward_spectrum(s, exc, live_time_s=100.0)
    a = simulate.poisson(spec, seed=42)
    b = simulate.poisson(spec, seed=42)
    c = simulate.poisson(spec, seed=43)
    print(f"same seed identical: {bool((a.counts == b.counts).all())}; "
          f"different seed differs: {bool((a.counts != c.counts).any())}")
    assert (a.counts == b.counts).all()
    assert (a.counts != c.counts).any()
