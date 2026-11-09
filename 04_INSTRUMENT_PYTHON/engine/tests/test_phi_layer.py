"""The phi-law reading layer: LAW 2396 motion, ladder, metals, code coil.

The degenerate identity is tested at kappa -> 0 — the floorless static
limit, exactly the classical term (the corpus LawSim protocol).  Living
readings at kappa = 1 sit on the phi-ground floor phi^-2
= 0.3819660112501051 ppm — zero does not exist in a reading.
"""
from __future__ import annotations

import math

import pytest

from engine import coil as eng_coil
from engine import metals as eng_metals
from engine import phi_laws


# ---------------------------------------------------------------------------
# the phi-motion kernel (LAW 2396)
# ---------------------------------------------------------------------------
def test_constants_exact():
    assert phi_laws.PHI == pytest.approx(1.618033988749895, abs=1e-15)
    assert phi_laws.PHI_INV == pytest.approx(0.6180339887498949, abs=1e-15)
    assert phi_laws.PHI_SQ_INV == pytest.approx(0.3819660112501051, abs=1e-15)
    # phi + phi^-2 = 2 exactly (the corpus invariant)
    assert phi_laws.PHI + phi_laws.PHI_SQ_INV == pytest.approx(2.0, abs=1e-15)


def test_degenerate_identity_kappa_zero_is_exact():
    for x in (0.0, 1e-12, 1.0, 555.5):
        assert phi_laws.phi_motion(x, 0.0) == x
        err = phi_laws.classical_limit_error(x, phi_laws.phi_motion(x, 0.0))
        assert err == 0.0
    # the simulatable gate: exact arithmetic is inside the corpus tolerance
    assert phi_laws.classical_limit_error(1.0, phi_laws.phi_motion(1.0, 1e-15)) \
        <= phi_laws.CLASSICAL_LIMIT_TOL


def test_kappa_one_ground_floor_is_phi_squared_inverse():
    floor = phi_laws.concentration_phi(0.0, 1.0)
    assert floor == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)
    assert floor > 0.0                      # zero does not exist in a reading


def test_phi_motion_is_exactly_linear_and_monotone():
    # x_phi = x*(1 + kappa*(phi-1)) + kappa*phi^-1*ground: linear in x
    x1, x2 = 2.0, 7.0
    k = 0.7
    a = phi_laws.phi_motion(x1, k)
    b = phi_laws.phi_motion(x2, k)
    assert b - a == pytest.approx((x2 - x1) * (1.0 + k * phi_laws.PHI_INV),
                                  rel=1e-15)
    v0 = phi_laws.phi_motion(0.0, k)
    assert v0 == pytest.approx(k * phi_laws.PHI_SQ_INV, abs=1e-15)
    for k in (0.0, 0.5, 1.0):
        assert phi_laws.phi_motion(0.0, k) == pytest.approx(k * phi_laws.PHI_SQ_INV,
                                                            abs=1e-15)


def test_unit_chain_round_trip_exact():
    c = 4.5678
    assert phi_laws.ppm_to_ug_m3(phi_laws.ug_m3_to_ppm(c)) == pytest.approx(c,
                                                                            rel=1e-14)
    rho = 1.2041e9
    assert phi_laws.ug_m3_to_ppm(c) == pytest.approx(c * 1e6 / rho, rel=1e-15)


def test_ppm_of_block_fields():
    block = phi_laws.ppm_of(0.0, 1.0)
    assert block["law"] == "PHI-2396"
    assert block["c_k0_ppm"] == 0.0
    assert block["ground_ppm"] == phi_laws.PHI_INV
    assert block["c_phi_ppm"] == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)
    assert "kappa -> 0" in block["degenerate"] or "lim_" in block["degenerate"]


# ---------------------------------------------------------------------------
# the ladder
# ---------------------------------------------------------------------------
def test_ladder_ends_on_the_invariant():
    freqs = phi_laws.ladder_frequencies()
    assert len(freqs) == 10
    assert freqs[0] == phi_laws.BASE_FREQUENCY
    assert freqs[-1] == pytest.approx(40134.946166, abs=1e-3)
    assert freqs[-1] == pytest.approx(phi_laws.LADDER_INVARIANT_HZ, abs=1e-9)
    for lo, hi in zip(freqs, freqs[1:]):
        assert hi / lo == pytest.approx(phi_laws.PHI, rel=1e-12)


# ---------------------------------------------------------------------------
# the metal registry
# ---------------------------------------------------------------------------
def test_registry_coverage_and_order():
    reg = eng_metals.registry()
    # 75 = every metal the tabulated data carries (Li/Be/B/Na included via
    # their own lines: 49.4/108.5/183.3/1040.3 eV); the window is the data's
    # span, so the drop record is empty — nothing is excluded by energy
    assert len(reg) == 75
    assert len(eng_metals.dropped_from_registry()) == 0
    zs = [m.z for m in reg]
    assert zs == sorted(zs)
    assert len(set(zs)) == len(zs)
    assert all(eng_metals.MIN_WINDOW_EV <= eng_metals.primary_line(m.z).energy
               <= eng_metals.MAX_WINDOW_EV for m in reg)
    assert len({m.category for m in reg}) >= 8


def test_nonmetal_exclusions_speak_every_absence():
    # every Z in 1..92 must be either in the registry, in the drop record,
    # or spoken as an excluded nonmetal — no silent absences
    for z in range(1, 93):
        try:
            eng_metals.metal(z)
        except KeyError:
            assert z in eng_metals.NONMETAL_EXCLUSIONS, f"Z={z} is unspoken"
        else:
            assert z not in eng_metals.NONMETAL_EXCLUSIONS


def test_light_metals_register_at_the_extended_window():
    """The upgrade: the analyzer window is the tabulated data's own span
    (MIN_WINDOW_EV = 40 eV, below Li Ka3 49.4 eV), so the light metals
    register through their own lines — the drop record is empty and no
    element is excluded by a baked energy floor."""
    dropped = eng_metals.dropped_from_registry()
    assert dropped == ()
    reg = {m.symbol: m for m in eng_metals.registry()}
    for sym, line_ev in (("Li", 49.4), ("Be", 108.5), ("B", 183.3),
                         ("Na", 1040.3)):
        m = reg[sym]
        ln = eng_metals.primary_line(m.z)
        assert ln is not None and abs(ln.energy - line_ev) < 1.0, (sym, ln)


def test_nonmetal_exclusions_land_outside_and_inside():
    for z in eng_metals.NONMETAL_EXCLUSIONS:
        with pytest.raises((KeyError, ValueError)):
            eng_metals.metal(z)
    assert eng_metals.metal(79).symbol == "Au"


def test_ferrous_set_is_the_magnetization_channel():
    for z in eng_metals.FERROUS_ZS:
        m = eng_metals.metal(z)
        assert m.rel_permeability is not None and m.rel_permeability > 1.0
        assert m.has_coil_signature
    for z in eng_metals.PRECIOUS_ZS:
        assert eng_metals.metal(z).category == "precious"


# ---------------------------------------------------------------------------
# the code coil
# ---------------------------------------------------------------------------
def test_tank_wiring_is_exact_and_drive_follows_the_ladder():
    l_tx = eng_coil.self_inductance()
    assert l_tx == pytest.approx(phi_laws.MU_0 * eng_coil.N_TX ** 2
                                 * math.pi * eng_coil.COIL_RADIUS_M ** 2
                                 / eng_coil.COIL_LENGTH_M, rel=1e-15)
    for ch in eng_coil.channels():
        assert ch.tank_c_farad == pytest.approx(
            eng_coil.tank_capacitor(ch.f_hz, l_tx), rel=1e-15)
        k = ch.rung
        assert ch.f_hz == pytest.approx(phi_laws.BASE_FREQUENCY * phi_laws.PHI**k,
                                        rel=1e-12)
        assert ch.drive_scale == pytest.approx(phi_laws.PHI_INV ** k, rel=1e-15)
    assert eng_coil.channels()[-1].f_hz == pytest.approx(
        phi_laws.LADDER_INVARIANT_HZ, abs=1e-3)


def test_design_point_is_copper_coin_one_percent():
    ip, q = eng_coil.coin_response_ppm("Cu", eng_coil.BASE_FREQUENCY,
                                       eng_coil.DESIGN_STANDOFF_M)
    assert math.hypot(ip, q) == pytest.approx(10000.0, rel=1e-9)
    assert ip == 0.0 and q > 0              # non-ferrous: quadrature only


def test_design_point_carries_the_phi_ground():
    ip_raw, q_raw = eng_coil.coin_response_ppm("Cu", eng_coil.BASE_FREQUENCY)
    ip, q = eng_coil.coin_response_ppm_phi("Cu", eng_coil.BASE_FREQUENCY,
                                           kappa=1.0)
    # the ground is unit-covariant PER CHANNEL: the still in-phase channel
    # reads exactly kappa*phi^-2, the quadrature carries its classical term
    assert ip == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)
    assert q == pytest.approx(q_raw * (1.0 + phi_laws.PHI_INV) + phi_laws.PHI_SQ_INV,
                              rel=1e-15)
    # a still channel never reads zero: kappa*phi^-2 at full coupling
    assert eng_coil.coil_response_phi(0.0, 1.0) == pytest.approx(
        phi_laws.PHI_SQ_INV, abs=1e-15)


def test_ferromagnetic_inphase_channel():
    ip, q = eng_coil.coin_response_ppm("Fe", eng_coil.BASE_FREQUENCY)
    assert ip > q > 0.0                     # in-phase magnetization dominates
    assert eng_coil.optimal_channel_of("Fe") == "inphase"


def test_nonferrous_is_quadrature_only():
    for sym in ("Cu", "Al", "Ag", "Pb", "W"):
        ip, q = eng_coil.coin_response_ppm(sym, eng_coil.BASE_FREQUENCY)
        assert ip == 0.0
        assert q > 0.0
        assert eng_coil.optimal_channel_of(sym) == "quadrature"


def test_detection_range_bounds_and_refusal():
    rng = eng_coil.detection_range_m("Cu")
    assert rng is not None and 0.3 <= rng <= 1.5
    # a threshold the physics can never reach is refused honestly as 0.0
    assert eng_coil.detection_range_m("Cu", min_ppm=1e12) == 0.0


def test_sweep_deposit_registers_every_metal():
    block = eng_coil.sweep_deposit({}, kappa=1.0)
    assert block["n_registered"] == len(eng_metals.registry()) == 75
    assert block["n_physics_term"] == 0          # empty deposit: no classical term
    assert block["dominant_classical_metal"] is None
    for r in block["register"]:
        if r["reading_ppm_k0"] is None:
            assert r["mode"].startswith("no_coil_signature")
        else:
            assert r["reading_ppm_k0"] == pytest.approx(0.0, abs=1e-12)
            assert r["reading_ppm_kappa"] == pytest.approx(phi_laws.PHI_SQ_INV,
                                                           abs=1e-12)
    ladder = block["ladder"]
    assert len(ladder) == 10
    assert ladder[-1]["f_hz"] == pytest.approx(40134.946166, abs=1e-3)


def test_tuning_table_covers_registry():
    rows = eng_coil.tuning_table()
    assert len(rows) == len(eng_metals.registry())
    for row in rows:
        if row["rung"] is not None:
            assert 0 <= row["rung"] <= 9
            assert row["range_m"] >= 0.0
        else:
            assert row["note"]                # absence is spoken, not silent
    by_symbol = {r["symbol"]: r for r in rows}
    # strong conductors clear 3 sigma inside the search span
    assert 0.3 <= by_symbol["Cu"]["range_m"] <= 1.5
    assert by_symbol["Al"]["range_m"] > 0.0
    # weak semiconductors honestly never clear the floor: range 0.0
    assert by_symbol["Si"]["range_m"] == 0.0
