"""Tests for the detector_artifacts layer (the elimination of hardware
artifacts into declared physics — the government-grade battery's LG10).
"""
import math

from engine import detector_artifacts as art


def test_dead_time_curve_is_the_corpus_equation():
    # OCR = ICR * exp(-TAU * ICR): monotone saturating; OCR < ICR always
    for icr in (1e3, 1e4, 1e5, 5e5):
        assert art.dead_time(icr) < icr
    # the analytic maximum sits exactly at ICR = 1/tau
    icr_max = 1.0 / art.TAU
    assert abs(art.dead_time(icr_max) - 1.0 / (art.TAU * math.e)) < 1e-9
    assert art.dead_percent(icr_max) == 1.0 - math.exp(-1.0)


def test_sum_peak_ratio_is_linear_and_paired():
    # Int(2)/Int(1) = ICR * TAU2 / 2 — linear in ICR, linear in TAU2
    r1 = art.sum_peak_ratio(1e5)
    assert abs(r1 - 1e5 * art.TAU2 / 2.0) < 1e-9
    assert abs(art.sum_peak_ratio(2e5) - 2 * r1) < 1e-9
    tau_doubled = art.sum_peak_ratio(1e5, tau2=2 * art.TAU2)
    assert abs(tau_doubled - 2 * r1) < 1e-9


def test_escape_peak_carries_the_si_kalpha_exactly():
    # energy conservation: the escape photon at E - Si K alpha — arithmetic
    assert art.escape_energy(5.9) == 5.9 - art.E_SI_KALPHA_KEV
    assert art.escape_energy(12.0) == 12.0 - art.E_SI_KALPHA_KEV


def test_escape_probability_is_bounded_and_small():
    p = art.escape_probability(5.9)
    assert 0.0 < p <= 0.10        # the thin-Si artifact is small, not zero
    assert art.escape_check(5.9)["photon_kev"] > art.E_SI_KALPHA_KEV
