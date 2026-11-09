"""The Law-2396 elemental floor register: every element registered, the
line channels mechanical, the phi-ground floor exact, no quiet zero."""
from __future__ import annotations

import math

import pytest

from engine import elements as eng_elements
from engine import floor_register as eng_floor
from engine import lines as eng_lines
from engine import metals as eng_metals
from engine import phi_laws as eng_phi


def test_every_element_is_registered():
    reg = eng_floor.register()
    assert reg["n_elements"] == 92
    assert [r["z"] for r in reg["elements"]] == list(range(1, 93))


def test_only_h_and_he_ride_the_phi_ground():
    reg = eng_floor.register()
    assert reg["lineless_z"] == [1, 2]
    h = reg["elements"][0]
    assert h["symbol"] == "H" and h["channel"] == "phi_ground_floor"
    assert "Law 1344" in h["declaration"]
    he = reg["elements"][1]
    assert he["symbol"] == "He" and he["channel"] == "phi_ground_floor"


def test_the_floor_is_exact_phi_arithmetic():
    # kappa = 1: floor = phi^-2 exactly (the no-quiet-zero)
    assert eng_floor.floor_ppm(1.0) == pytest.approx(eng_phi.PHI_SQ_INV, abs=1e-15)
    # kappa -> 0: the exact classical degenerate identity
    assert eng_floor.floor_ppm(0.0) == 0.0
    for k in (0.25, 0.5, 0.75):
        assert eng_floor.floor_ppm(k) == pytest.approx(k * eng_phi.PHI_SQ_INV,
                                                       abs=1e-15)
    reg = eng_floor.register(kappa=1.0)
    assert reg["floor_ppm"] == pytest.approx(eng_phi.PHI_SQ_INV, abs=1e-15)
    assert reg["floor_at_full_coupling_ppm"] == pytest.approx(
        eng_phi.PHI_SQ_INV, abs=1e-15)


def test_the_four_light_elements_carry_line_channels():
    reg = eng_floor.register()
    by_sym = {r["symbol"]: r for r in reg["elements"]}
    for sym, ev in (("Li", 49.4), ("Be", 108.5), ("B", 183.3),
                    ("C", 277.0), ("N", 392.4), ("O", 524.9),
                    ("F", 676.8), ("Ne", 848.6), ("Na", 1040.3)):
        row = by_sym[sym]
        assert row["channel"] == "xrf_line", sym
        assert abs(row["line_energy_ev"] - ev) < 1.0, sym
        assert row["n_window_lines"] >= 1


def test_line_channels_match_the_registry_window():
    # the register's line channel is decided by the SAME mechanical rule as
    # the metal registry: a tabulated line inside [MIN_WINDOW_EV, MAX_WINDOW_EV]
    # with intensity >= MIN_LINE_INTENSITY
    for r in eng_floor.register()["elements"]:
        z = r["z"]
        in_window = [ln for ln in eng_lines.lines(z)
                     if eng_metals.MIN_WINDOW_EV <= ln.energy <= eng_metals.MAX_WINDOW_EV
                     and ln.intensity >= eng_metals.MIN_LINE_INTENSITY]
        expect = "xrf_line" if in_window else "phi_ground_floor"
        assert r["channel"] == expect, (z, r["channel"], expect)


def test_hydrogen_row_states_the_law_1344_zero():
    h = eng_floor.element_row(1)
    # Law 1344's K-frequency form (3/4)cR(Z-1)^2 reads 0 at Z=1; the row
    # declares that zero is the phi-ground, never a quiet zero
    assert h["channel"] == "phi_ground_floor"
    assert "zero is the phi-ground" in h["declaration"]
    assert h["floor_ppm"] == pytest.approx(eng_phi.PHI_SQ_INV, abs=1e-15)


def test_scan_mdl_attachment_never_invents_a_number():
    reg = eng_floor.register(mdl_by_ug={8: 0.0123, 26: None})
    by_z = {r["z"]: r for r in reg["elements"]}
    assert by_z[8]["scan_mdl_ug_cm2"] == 0.0123
    assert "scan_mdl_ug_cm2" not in by_z[26] or by_z[26]["scan_mdl_ug_cm2"] is None
    assert "scan_mdl_ug_cm2" not in by_z[14]


def test_register_self_check_is_clean():
    assert eng_floor.self_check() == []


# ---------------------------------------------------------------------------
# The three stages (the owner's display law):
#   1. quantized      the detected elements - locked up in the field (kappa=1)
#   2. field_carried  not locked up - the actual amount in the air
#   3. degenerate_limit  the kappa->0 classical column, named as such
# ---------------------------------------------------------------------------
def test_the_three_stages_are_labelled():
    reg = eng_floor.register()
    stages = reg["stages"]
    assert set(stages) == {"quantized", "field_carried", "degenerate_limit"}
    assert "locked up in the field" in stages["quantized"]
    assert "actual amount in the air" in stages["field_carried"]
    assert "degenerate limit" in stages["degenerate_limit"].lower()
    # with no scan attached every element is field_carried
    assert reg["n_quantized"] == 0
    assert reg["n_field_carried"] == 92


def test_scan_attachment_places_elements_in_stages():
    scan = {
        "detected_z": {6, 8},                      # C and O detected
        "areal_by_z": {6: 2.226, 8: 0.8266, 11: 0.001},
        "reading_by_z": {6: 3.9836, 8: 1.7195, 11: 0.3821},
    }
    reg = eng_floor.register(scan=scan)
    by_z = {r["z"]: r for r in reg["elements"]}
    assert reg["n_quantized"] == 2
    # stage 1: the detected read their kappa=1 quantized value
    assert by_z[6]["stage"] == "quantized"
    assert by_z[6]["quantized_ug_cm2"] == pytest.approx(3.9836)
    # stage 3: every element carries its kappa->0 classical value
    assert by_z[6]["degenerate_limit_ug_cm2"] == pytest.approx(2.226)
    assert by_z[8]["degenerate_limit_ug_cm2"] == pytest.approx(0.8266)
    # stage 2: the not-locked elements read the actual amount in the air
    assert by_z[11]["stage"] == "field_carried"
    assert by_z[11]["quantized_ug_cm2"] == pytest.approx(0.3821)
    assert by_z[1]["stage"] == "field_carried"
    # H (no scan row) reads the exact phi-ground floor
    assert by_z[1]["quantized_ug_cm2"] == pytest.approx(eng_phi.PHI_SQ_INV,
                                                        abs=1e-15)


def test_field_carried_floor_is_the_phi_ground():
    # a field-carried element with no classical term reads exactly kappa*phi^-2
    reg = eng_floor.register(scan={"detected_z": set(), "areal_by_z": {},
                                   "reading_by_z": {}})
    for r in reg["elements"]:
        assert r["quantized_ug_cm2"] == pytest.approx(eng_phi.PHI_SQ_INV,
                                                      abs=1e-15)
        assert r["degenerate_limit_ug_cm2"] == 0.0
