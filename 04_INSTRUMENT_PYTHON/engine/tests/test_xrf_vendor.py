"""The external cross-check battery: our tables vs the pulled open-source.

Pulls (hardware-free by construction): xraylib (EPDL-family tabulations)
and PyMca5 (the ESRF element database).  Presence is probed at call time;
an absent package is SPOKEN, never faked.  Validation strength is stated
PER CHECK: X1/X2/X3 are cross-edition checks; X4/X5 are same-source
regression guards (our tables carry the xraydb/Elam lineage, numerically
identical to xraylib's mu table and bitwise PyMca's binding table).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine import xrf_vendor as V


@pytest.fixture(scope="module")
def report():
    return V.run_battery()


def _skip_if_absent(check) -> None:
    if check["ok"] is None:
        pytest.skip(check["status"])


def test_battery_artifact_written(report, tmp_path):
    path = Path(__file__).resolve().parents[2] / "VENDOR" / \
        "external_cross_check.json"
    assert path.exists()
    blob = json.loads(path.read_text(encoding="utf-8"))
    assert blob["schema"] == "xrf-vendor/external-cross-check-v1"


def test_x2_lines_agree_with_xraylib(report):
    c = report["checks"]["X2_lines"]
    _skip_if_absent(c)
    assert c["ok"] is True
    assert c["n_compared"] >= 300
    assert c["max_rel_err"] <= c["tol"]


def test_x1_edges_agree_with_xraylib(report):
    c = report["checks"]["X1_edges"]
    _skip_if_absent(c)
    assert c["ok"] is True
    assert c["n_compared"] >= 250
    assert c["n_excluded_sub_1000_ev"] >= 5      # the spoken scope exists


def test_x4_cross_sections_agree_in_range(report):
    c = report["checks"]["X4_cross_sections"]
    _skip_if_absent(c)
    assert c["ok"] is True
    assert c["max_rel_err"] <= c["tol"]
    for row in c["rows"]:
        assert row["energy_ev"] <= V.DECLARED_MAX_ENERGY_EV


def test_x5_pymca_bindings_agree(report):
    c = report["checks"]["X5_pymca_bindings"]
    _skip_if_absent(c)
    assert c["ok"] is True
    assert c["n_compared"] >= 250
    # strength labeled honestly: a same-source regression guard
    assert c["strength"] == V.STRENGTH_REGRESSION_GUARD


def test_strength_labels_are_stated_per_check(report):
    c4 = report["checks"]["X4_cross_sections"]
    if c4["ok"] is not None:
        assert c4["strength"] == V.STRENGTH_REGRESSION_GUARD
    for k in ("X1_edges", "X2_lines", "X3_yields"):
        c = report["checks"][k]
        if c["ok"] is not None:
            assert c["strength"] == V.STRENGTH_CROSS_EDITION


def test_x3_yields_pass_with_listed_conflicts(report):
    c = report["checks"]["X3_yields"]
    _skip_if_absent(c)
    assert c["ok"] is True
    assert c["n_conflicts"] <= 2
    for conflict in c["conflicts"]:
        # every conflict is LISTED IN FULL with both values
        assert {"z", "shell", "ours", "vendor", "rel_err"} <= set(conflict)


def test_the_known_re_l3_compilation_conflict_is_carried(report):
    c = report["checks"]["X3_yields"]
    _skip_if_absent(c)
    conflicts = c["conflicts"]
    if conflicts:
        assert any(cf["z"] == 75 and cf["shell"] == "L3" for cf in conflicts)


def test_absence_is_spoken_not_failed(tmp_path, monkeypatch):
    # force the probes to report absent and confirm nothing fakes a pass
    # (check-level only: run_battery() writes artifacts, and the artifact
    # must always describe the PRESENT machine)
    monkeypatch.setattr(V, "_probe_xraylib", lambda: None)
    monkeypatch.setattr(V, "_probe_pymca", lambda: None)
    rep = V.check_edges(zs=None)
    assert rep["ok"] is None and "ABSENT" in rep["status"]
    rep2 = V.check_lines(zs=None)
    assert rep2["ok"] is None and "ABSENT" in rep2["status"]
    rep3 = V.check_yields(zs=None)
    assert rep3["ok"] is None and "ABSENT" in rep3["status"]


def test_vendor_self_check():
    # with the packages present, self_check is clean
    if V._probe_xraylib() is None and V._probe_pymca() is None:
        assert V.self_check()
    else:
        assert V.self_check() == []
