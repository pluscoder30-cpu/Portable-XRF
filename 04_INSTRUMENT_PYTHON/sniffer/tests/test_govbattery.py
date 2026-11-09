"""Tests for the GOV battery (the government-grade register).

Light by design: the machinery's formulas, the declared standard structure,
and the sealed report's verdict — the full battery run is its own CLI receipt
(`python -m sniffer.govbattery`, chain seq 19 = the ALL GREEN run).
"""
import json
import os

from sniffer.govbattery import (LADDER_UG_CM2, STD_AREAL_UG_CM2, STD_METALS,
                                crm_accepts, rsz_ssz, u_score, z_score)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_the_micromatter_mass_classes_order():
    classes = list(LADDER_UG_CM2.values())
    assert classes == sorted(classes) and len(classes) == 5
    assert 0.5 <= classes[0] and classes[-1] <= 120.0   # the SL..H range


def test_the_declared_standard_is_the_L_class():
    for sym in STD_METALS:
        assert STD_AREAL_UG_CM2[sym] == LADDER_UG_CM2["L"]


def test_the_score_functions_behave_per_formula():
    assert abs(z_score(10.0, 10.1, 1.0)) <= 2.0            # |z| <= 2: acceptable
    assert 2.0 < abs(z_score(12.5, 10.0, 1.0)) < 3.0       # questionable band
    assert abs(z_score(14.0, 10.0, 1.0)) >= 3.0            # unsatisfactory band
    assert abs(u_score(10.02, 0.10, 10.0, 0.01)) <= 2.58   # the 99% band
    assert abs(u_score(10.5, 0.05, 10.0, 0.01)) > 2.58
    rsz, ssz = rsz_ssz([0.0, 0.0, 0.0])
    assert rsz == 0.0 and ssz == 0.0                       # the zero-bias centroid


def test_the_iso_guide_33_crm_gate():
    assert crm_accepts(10.02, 0.10, 10.0, 0.10)
    assert not crm_accepts(11.0, 0.10, 10.0, 0.10)


def test_the_sealed_report_is_all_green():
    with open(os.path.join(ROOT, "QCBATTERY", "gov_report.json"),
              encoding="utf-8") as fh:
        report = json.load(fh)
    verdict = report["payload"]["verdict"]
    assert "ALL GREEN" in verdict
    real = [it for it in report["payload"]["items"]
            if it["class"] == "REAL"]
    assert all(it["ok"] for it in real) and len(real) == 10
    # the federal verification ran off the LIVE certificate (no purchase)
    lg9 = [it for it in real if it["id"] == "LG9_srm2783"][0]
    assert lg9["fixture"]["deposit_area_cm2"] == 9.96
    assert lg9["fixture"]["cert_ng"]["Pb"] == [317, 54]   # JSON lists, not tuples
    assert "archives/2783.pdf" in lg9["fixture"]["source"]
    # the escape/sum/dead-time layer is physics, not a spoken absence
    lg10 = [it for it in real if it["id"] == "LG10_escape_sum_deadtime"][0]
    assert lg10["ok"]
