"""Full session: schema, register modes, coin-class consistency, seal+verify.

The fetcher is injected so every test is offline and deterministic; the
cache is a fresh tmp dir so the fake feed is always used.
"""
from __future__ import annotations

import pytest

from engine import metals as eng_metals
from engine import phi_laws

from sniffer.receipt import seal, verify_receipt
from sniffer.session import (SESSION_SCHEMA, full_session, metals_register,
                             self_check, wifi_witness)


FEED = {
    "pm10_ug_m3": 9.5, "pm2_5_ug_m3": 5.5, "dust_ug_m3": 0.95,
    "time": "2026-11-01T00:00:00Z", "source": "unit-fake",
}


def _fetcher(lat, lon, timeout_s):
    return dict(FEED)


@pytest.fixture(scope="module")
def session_payload(tmp_path_factory):
    cache = tmp_path_factory.mktemp("xrf_cache")
    return full_session(40.70, -74.00, fetcher=_fetcher, cache_dir=str(cache),
                        timestamp="2026-11-01T00:00:00Z", seed=2026110100)


# ---------------------------------------------------------------------------
# schema and blocks
# ---------------------------------------------------------------------------
def test_session_schema_and_blocks(session_payload):
    p = session_payload
    assert p["schema"] == SESSION_SCHEMA
    for block in ("air", "spectrum", "xrf_report", "metals", "coil",
                  "coil_tuning", "consistency", "witness", "witness_absent",
                  "model", "honesty"):
        assert block in p
    assert p["model"]["physics"] == "classical"
    assert p["air"]["pm10_ug_m3"] == 9.5
    assert p["air"]["pm2_5_ug_m3"] == 5.5
    assert p["air"]["dust_ug_m3"] == 0.95
    assert p["timestamp"] == "2026-11-01T00:00:00Z"
    # a present witness speaks no absence
    if p["witness"] is not None:
        assert p["witness_absent"] is None


def test_ladder_invariant_is_in_the_session(session_payload):
    coil = session_payload["coil"]
    assert coil["ladder_invariant_hz"] == pytest.approx(40134.946166, abs=1e-3)
    assert len(coil["channels"]) == 10
    assert coil["phi_ground_ppm"] == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)


# ---------------------------------------------------------------------------
# the metal register (LAW 2396)
# ---------------------------------------------------------------------------
def test_register_covers_the_full_registry(session_payload):
    met = session_payload["metals"]
    assert met["n_registered"] == len(eng_metals.registry())
    assert met["n_quantified"] >= 1
    assert met["n_quantified"] + met["n_field_carried"] == met["n_registered"]


def test_register_floor_rows_carry_phi_ground(session_payload):
    for r in session_payload["metals"]["rows"]:
        if r["mode"] == "quantified":
            assert r["c_phi_ppm"] > r["c_k0_ppm"] >= 0.0
            assert r["uplift_vs_static"] == pytest.approx(
                r["c_phi_ppm"] / r["c_k0_ppm"], rel=1e-12)
        else:
            # no classical term in this feed: the reading IS the phi-ground
            assert r["c_phi_ppm"] == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)
            assert r["uplift_vs_static"] is None


def test_register_row_recomputed_by_hand(session_payload):
    rows = session_payload["metals"]["rows"]
    quantified = [r for r in rows if r["mode"] == "quantified"]
    assert quantified
    row = quantified[0]
    # exact chain: ug/m3 -> ppm of air -> Law-2396 motion at kappa = 1
    ppm_k0 = phi_laws.ug_m3_to_ppm(row["c_ug_m3"])
    expected = ppm_k0 * (1.0 + phi_laws.PHI_INV) + phi_laws.PHI_SQ_INV
    assert row["c_phi_ppm"] == pytest.approx(expected, rel=1e-12)
    assert row["c_k0_ppm"] == pytest.approx(ppm_k0, rel=1e-12)
    assert row["primary_line_energy_ev"] is not None


def test_empty_areal_register_is_all_floor():
    reg = metals_register({}, kappa=phi_laws.KAPPA_FULL)
    assert reg["n_quantified"] == 0
    assert reg["n_registered"] == len(eng_metals.registry())
    for r in reg["rows"]:
        assert r["c_phi_ppm"] == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)
        assert r["c_k0_ppm"] == 0.0


# ---------------------------------------------------------------------------
# the coil consistency gate and the coin-class check
# ---------------------------------------------------------------------------
def test_coin_class_check_channel_discipline(session_payload):
    coin = session_payload["consistency"]["coin_class_check"]
    assert coin                                   # the feed had metal elements
    for cc in coin:
        if cc["ferrous"]:
            assert cc["channel_class"] == "magnetization_inphase"
        else:
            assert cc["channel_class"] == "eddy_quadrature"
        # strong conductors read detectable at the design geometry
    strong = [cc for cc in coin if cc["symbol"] in ("Al", "Ca")]
    assert all(cc["detectable_at_design"] for cc in strong)


def test_sheet_sweep_is_honest_about_floor(session_payload):
    coil = session_payload["coil"]
    cons = session_payload["consistency"]
    assert (coil["n_physics_term"] > 0) == cons["coil_classical_above_floor"]
    # at PM-scale areal the sheet classical term is below 3 sigma:
    # either honestly None or a real classical term — never a fake number
    dom = coil["dominant_classical_metal"]
    if dom is not None:
        rows = {r["symbol"]: r for r in coil["register"]}
        assert rows[dom]["mode"] == "physics_term"
    else:
        assert cons["coil_dominant"] is None


# ---------------------------------------------------------------------------
# the witness and the receipt
# ---------------------------------------------------------------------------
def test_witness_channels_are_digit_tokens(session_payload):
    w = session_payload["witness"]
    if w is None:
        pytest.skip("wifi sniffer capture not present on this machine")
    # radio channels are pure 1-3 digit tokens; payload bytes must not leak
    for ch in w["channels"]:
        assert ch.isdigit() and len(ch) <= 3


def test_spoken_absent_covers_detected_nonmetals(session_payload):
    spoken = session_payload["consistency"]["spoken_absent"]
    checked = {s["symbol"] for s in spoken}
    detected = {r["symbol"] for r in session_payload["xrf_report"]["elements"]
                if r["detection_flag"] == "detected"}
    from engine.metals import registry, NONMETAL_EXCLUSIONS
    unregistered = {sym for sym in detected
                    if all(m.symbol != sym for m in registry())}
    # every detected element outside the metal registry is spoken with a reason
    assert unregistered <= checked
    for s in spoken:
        z = s["z"]
        if z in NONMETAL_EXCLUSIONS:
            assert s["reason"] == NONMETAL_EXCLUSIONS[z], s
        else:
            assert s["reason"], s


def test_witness_absent_is_spoken(tmp_path):
    missing = str(tmp_path / "no_capture.txt")
    cache = tmp_path / "cache"
    payload = full_session(40.70, -74.00, fetcher=_fetcher, cache_dir=str(cache),
                           timestamp="2026-11-01T00:00:00Z",
                           wifi_capture=missing)
    assert payload["witness"] is None
    absent = payload["witness_absent"]
    assert absent and absent["expected_path"] == missing
    assert "absent" in absent["reason"]


def test_witness_shape(session_payload):
    w = session_payload["witness"]
    if w is None:
        pytest.skip("wifi sniffer capture not present on this machine")
    assert w["kind"] == "wifi_sniffer_capture"
    assert len(w["sha256"]) == 64
    assert w["frames"] > 0
    assert w["channels"]


def test_witness_is_deterministic():
    a, b = wifi_witness(), wifi_witness()
    if a is None:
        pytest.skip("wifi sniffer capture not present on this machine")
    assert a == b


def test_seal_and_verify(session_payload):
    receipt = seal(session_payload)
    result = verify_receipt(receipt)
    assert result["ok"], result["errors"]
    assert result["checks"]["model.physics"]["ok"] is True
    assert result["model"]["physics"] == "classical"


def test_seal_refuses_non_classical(session_payload):
    forged = dict(session_payload)
    forged["model"] = dict(session_payload["model"], physics="phi")
    with pytest.raises(ValueError):
        seal(forged)


def test_session_self_check_clean():
    assert self_check() == []
