"""The XRF battery (vendor daily QA, rebuilt as software) as tests.

Module-scoped single battery run; the vendor tolerances pin the pass.
"""
from __future__ import annotations

import math

import pytest

from sniffer import qcbattery as Q


@pytest.fixture(scope="module")
def report():
    return Q.run_battery()


def test_battery_all_green(report):
    assert report["ok"] is True
    assert report["n_items"] == 10
    assert report["n_passed"] == 10
    assert report["failed"] == []
    assert report["model"]["physics"] == "classical"


def test_b1_energy_standardization_within_vendor_tolerance(report):
    b1 = report["items"][0]
    assert b1["ok"] is True
    for row in b1["rows"]:
        assert row["deviation_ev"] <= Q.TOL_ENERGY_EV


def test_b2_gain_drift_detected_and_corrected(report):
    b2 = report["items"][1]
    assert b2["ok"] is True
    # the declared gain is RECOVERED from the drifted axis
    assert abs(b2["recovered_gain"] - b2["declared_gain"]) \
        <= 1e-4 * b2["declared_gain"]
    for row in b2["rows"]:
        assert row["deviation_ev"] <= Q.TOL_GAIN_EV


def test_b3_resolution_at_mn_vendor_limit(report):
    b3 = report["items"][2]
    assert b3["ok"] is True
    assert "Mn" in b3["measured_at"]          # the vendor's convention
    assert b3["measured_ev"] <= Q.VENDOR_FWHM_LIMIT_EV
    spec = b3["declared_spec_ev"]
    assert abs(b3["measured_ev"] - spec) <= Q.FWHM_SPEC_TOL * spec


def test_b4_monitor_accuracy_graded_tolerances(report):
    b4 = report["items"][3]
    assert b4["ok"] is True
    for row in b4["rows"]:
        if row["class"] == "major":
            assert row["rel_err"] <= Q.DETECT_TOL_MAJOR
        else:
            assert row["rel_err"] <= Q.DETECT_TOL_MINOR


def test_b5_repeatability_rsd_vs_poisson(report):
    b5 = report["items"][4]
    assert b5["ok"] is True
    for row in b5["rows"]:
        assert row["rsd"] <= Q.RSD_FACTOR * row["poisson_ideal"]


def test_b6_drift_monitor_coefficient_recovered(report):
    b6 = report["items"][5]
    assert b6["ok"] is True
    for row in b6["rows"]:
        slope = row["fitted_slope_per_session"]
        truth = row["declared_slope_per_session"]
        assert abs(slope - truth) <= 0.6 * abs(truth)
        assert row["max_corrected_residual"] <= 0.02


def test_b7_blank_budget(report):
    b7 = report["items"][6]
    assert b7["ok"] is True
    assert b7["n_false_peaks"] <= Q.BLANK_FP_BUDGET


def test_b8_crm_accuracy(report):
    b8 = report["items"][7]
    assert b8["ok"] is True
    assert b8["median_rel_err"] <= 0.05
    assert b8["n_recovered"] >= 3


def test_b9_b10_spoken_ledger(report):
    for idx in (8, 9):
        assert report["items"][idx]["ok"] is True
    ledger = report["items"][9]["replaced_by_code"]
    for hardware_item in ("X-ray tube", "SDD detector",
                          "silver standardization coin", "monitor sample",
                          "drift monitor sample"):
        assert hardware_item in ledger
    assert report["items"][9]["not_modeled_spoken"]


def test_external_cross_check_embedded_and_green(report):
    ext = report["external_cross_check"]
    ran = {k: v for k, v in ext.items() if v["ok"] is not None}
    failed = [k for k, v in ext.items() if v["ok"] is False]
    assert failed == []
    assert ran, "at least one external check must run when packages exist"


def test_battery_self_check_clean():
    assert Q.self_check() == []
