"""Inverse operator: background, peaks, matching, NNLS, detection limits."""
import numpy as np
import pytest

from engine import detector, forward, inversion, lines


def make_spectrum(energies, areas, sigma=55.0, bg=50.0, seed=7, live=100.0):
    e = np.arange(0.0, 15000.0, 10.0)
    y = bg * np.exp(-e / 6000.0)
    for c, a in zip(energies, areas):
        y = y + a * np.exp(-0.5 * ((e - c) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
    rng = np.random.default_rng(seed)
    return forward.Spectrum(e, rng.poisson(np.maximum(y, 0)).astype(float), live)


def test_snip_preserves_peaks():
    e = np.arange(0.0, 15000.0, 10.0)
    y = 200.0 * np.exp(-e / 5000.0)
    peak = 200000.0 * np.exp(-0.5 * ((e - 6405.0) / 53.0) ** 2) / (53.0 * np.sqrt(2 * np.pi))
    bg = inversion.snip_background(y + peak, iterations=15)
    i = int(np.argmin(np.abs(e - 6405.0)))
    print(f"background under the peak: {bg[i]:.2f} (true {200*np.exp(-6405/5000):.2f}); "
          f"peak height {(y+peak)[i]:.0f}")
    assert bg[i] < 0.1 * (y[i] + peak[i])
    assert abs(bg[i] - 200 * np.exp(-6405 / 5000)) < 20


def test_peak_detection_and_fit():
    spec = make_spectrum([6405.0, 7059.0], [40000.0, 6000.0])
    peaks = inversion.detect_peaks(spec, detector.SDD_25, min_snr=4.0)
    print("peaks:", peaks)
    assert len(peaks) >= 2
    centres = sorted(p.center_ev for p in peaks)
    assert centres[0] == pytest.approx(6405.0, abs=15.0)
    assert centres[1] == pytest.approx(7059.0, abs=15.0)


def test_identification():
    spec = make_spectrum([6405.0], [40000.0])
    peaks = inversion.detect_peaks(spec)
    ident = inversion.identify(peaks[0], elements=[26])
    print("identification:", [(c[0].label, round(c[1], 2)) for c in ident.candidates])
    assert ident.best is not None
    assert ident.best[0].name == "Ka1"
    assert abs(ident.best[1]) < 10.0


def test_identification_rejects_far_peak():
    spec = make_spectrum([5000.0], [40000.0])
    peaks = inversion.detect_peaks(spec)
    ident = inversion.identify(peaks[0], elements=[26], tol_sigma=1.0)
    print("candidates for a 5 keV peak against Fe:", ident.candidates)
    assert ident.candidates == ()


def test_nnls_recovers_two_elements():
    exc = forward.Excitation.monoenergetic(12000.0, 1e10)
    sample = forward.Sample({"Fe": 3e-6, "Cu": 5e-6})
    spec = forward.forward_spectrum(sample, exc, background=None, live_time_s=1000.0)
    rng = np.random.default_rng(11)
    spec = forward.Spectrum(spec.energy_ev, rng.poisson(np.maximum(spec.counts, 0)),
                            spec.live_time_s)
    res = inversion.quantify_fundamental(spec, [26, 29], exc,
                                         subtract_background=False, e_min=5000.0)
    print("recovered:", {k: round(v["areal_ug_cm2"], 3) for k, v in res["elements"].items()},
          "residual", round(res["relative_residual"], 4))
    assert res["elements"][26]["areal_g_cm2"] == pytest.approx(3e-6, rel=0.15)
    assert res["elements"][29]["areal_g_cm2"] == pytest.approx(5e-6, rel=0.15)


def test_detection_limit_is_infinite_below_path_cutoff():
    exc = forward.Excitation.monoenergetic(12000.0, 1e10)
    spec = forward.forward_spectrum(forward.Sample({"Fe": 1e-5}), exc,
                                    background=None, live_time_s=100.0)
    mdl_ok = inversion.detection_limit(spec, 26, exc, air_path_cm=2.0)
    mdl_bad = inversion.detection_limit(spec, 12, exc, air_path_cm=100.0)
    print(f"MDL Fe (2 cm air): {mdl_ok*1e6:.3f} ug/cm2; "
          f"MDL Mg (100 cm air): {mdl_bad:.3e} g/cm2")
    assert np.isfinite(mdl_ok) and mdl_ok > 0
    assert mdl_bad == float("inf") or mdl_bad > 1.0


def test_calibration_round_trip():
    exc = forward.Excitation.monoenergetic(12000.0, 1e10)
    standard = forward.Sample({"Fe": 1e-5})
    spec = forward.forward_spectrum(standard, exc, background=None, live_time_s=500.0)
    calib = inversion.Calibration.from_standard(spec, standard)
    print("sensitivity:", calib.sensitivities)
    unknown = forward.forward_spectrum(forward.Sample({"Fe": 2e-5}), exc,
                                       background=None, live_time_s=500.0)
    res = inversion.quantify_calibration(unknown, calib)
    print("calibration result:", res["elements"])
    assert res["elements"][26]["areal_g_cm2"] == pytest.approx(2e-5, rel=0.02)


def test_analyze_pipeline():
    """Full peak -> element pipeline on a clean two-element spectrum."""
    exc = forward.Excitation.monoenergetic(15000.0, 1e10)
    sample = forward.Sample({"Fe": 2e-5, "Cu": 3e-5})
    spec = forward.forward_spectrum(sample, exc, background=None, live_time_s=1000.0)
    rng = np.random.default_rng(3)
    spec = forward.Spectrum(spec.energy_ev, rng.poisson(np.maximum(spec.counts, 0)),
                            spec.live_time_s)
    out = inversion.analyze(spec)
    found = {v["element"] for v in out["elements"].values()}
    print("peaks:", [(round(p.center_ev, 1), round(p.snr, 1)) for p in out["peaks"]])
    print("elements found:", found)
    assert {"Fe", "Cu"} <= found


def test_self_check():
    assert inversion.self_check() == []
