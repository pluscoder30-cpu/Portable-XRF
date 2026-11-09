"""CLI wiring: simulate -> sniff -> receipt -> verify, feed offline, selfcheck."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sniffer import cli
from sniffer.receipt import verify_receipt


def test_simulate_sniff_verify(tmp_path):
    composition = {
        "sample_id": "cli test",
        "pm_ug_m3": 30.0,
        "endmembers": {"mineral_dust": 0.75, "iron_oxide": 0.10,
                       "carbonate": 0.10, "soot": 0.05},
        "flow_lpm": 16.7,
        "duration_min": 1440,
        "filter_area_cm2": 11.3,
        "air_path_cm": 2.0,
        "live_time_s": 300.0,
    }
    comp_path = tmp_path / "composition.json"
    comp_path.write_text(json.dumps(composition), encoding="utf-8")
    spec_path = tmp_path / "spectrum.json"
    report_path = tmp_path / "report.json"
    receipt_path = tmp_path / "receipt.json"

    assert cli.main(["simulate", str(comp_path), "--noise",
                     "--out", str(spec_path)]) == 0
    assert spec_path.exists()
    assert cli.main(["sniff", str(spec_path), "--out", str(report_path),
                     "--receipt", str(receipt_path)]) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["provenance"] == "instrument"
    assert report["model"]["physics"] == "classical"
    assert report["model"]["calibration_id"]
    detected = {r["symbol"] for r in report["elements"]
                if r["detection_flag"] == "detected"}
    assert {"Si", "Fe", "Ca"} <= detected

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    verdict = verify_receipt(receipt)
    assert verdict["ok"], verdict
    assert verdict["model"]["version"] == report["model"]["version"]
    assert cli.main(["verify", str(receipt_path)]) == 0


def test_cli_feed_offline(tmp_path):
    out = tmp_path / "feed.json"
    rec = tmp_path / "feed_receipt.json"
    rc = cli.main(["feed", "0", "0", "--cache-only",
                   "--cache-dir", str(tmp_path / "cache"),
                   "--out", str(out), "--receipt", str(rec)])
    assert rc == 0
    reading = json.loads(out.read_text(encoding="utf-8"))
    assert reading["status"] == "offline_no_cache"
    assert reading["pm10_ug_m3"] is None
    receipt = json.loads(rec.read_text(encoding="utf-8"))
    assert verify_receipt(receipt)["ok"]


def test_cli_rejects_bad_spectrum(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "energy_ev": [0.0, 10.0, 5.0],
        "counts": [1.0, 2.0, 3.0],
        "live_time_s": 10.0,
    }), encoding="utf-8")
    assert cli.main(["sniff", str(bad), "--out", str(tmp_path / "r.json")]) == 2


def test_cli_selfcheck():
    assert cli.main(["selfcheck"]) == 0


# ---------------------------------------------------------------------------
# the full session CLI and the metals register CLI
# ---------------------------------------------------------------------------
FAKE_FEED = {
    "pm10_ug_m3": 9.5, "pm2_5_ug_m3": 5.5, "dust_ug_m3": 0.95,
    "time": "2026-11-01T00:00:00Z", "source": "cli-fake",
}


def test_cli_session_seals_a_chained_witnessed_pair(tmp_path):
    from sniffer.air import _cache_path, _write_cache

    cache_dir = tmp_path / "cache"
    cache_path = _cache_path(cache_dir, 40.70, -74.00, "auto")
    _write_cache(cache_path, {
        "fetched_at": 1730419200.0, "fetched_at_iso": "2026-11-01T00:00:00Z",
        "lat": 40.70, "lon": -74.00, "source": "auto", "data": FAKE_FEED,
    })
    chain = tmp_path / "chain.jsonl"
    out = tmp_path / "session.json"

    rc = cli.main(["session", "40.70", "-74.00", "--runs", "2",
                   "--cache-only", "--cache-dir", str(cache_dir),
                   "--out", str(out), "--chain", str(chain)])
    assert rc == 0
    # run-split artifact names, each sealed
    s1 = tmp_path / "session_run01.json"
    s2 = tmp_path / "session_run02.json"
    assert s1.exists() and s2.exists()
    r1 = tmp_path / "session_run01.receipt.json"
    r2 = tmp_path / "session_run02.receipt.json"
    assert r1.exists() and r2.exists()

    payload = json.loads(s1.read_text(encoding="utf-8"))
    assert payload["schema"] == "xrf-sniffer/session-v1"
    assert payload["metals"]["n_registered"] == 75
    v1 = verify_receipt(json.loads(r1.read_text(encoding="utf-8")))
    v2 = verify_receipt(json.loads(r2.read_text(encoding="utf-8")))
    assert v1["ok"] and v2["ok"]
    # the chain binds both to one genesis-rooted JSONL
    lines = chain.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    chain_hashes = [json.loads(ln)["hash"] for ln in lines]
    assert chain_hashes == [v1["hash"], v2["hash"]]
    assert cli.main(["verify", str(r2), "--chain", str(chain)]) == 0


def test_cli_session_absent_witness_is_spoken(tmp_path):
    from sniffer.air import _cache_path, _write_cache

    cache_dir = tmp_path / "cache"
    cache_path = _cache_path(cache_dir, 40.70, -74.00, "auto")
    _write_cache(cache_path, {
        "fetched_at": 1730419200.0, "fetched_at_iso": "2026-11-01T00:00:00Z",
        "lat": 40.70, "lon": -74.00, "source": "auto", "data": FAKE_FEED,
    })
    capture = tmp_path / "missing_capture.txt"
    out = tmp_path / "session.json"
    rc = cli.main(["session", "40.70", "-74.00", "--runs", "1",
                   "--cache-only", "--cache-dir", str(cache_dir),
                   "--wifi-capture", str(capture), "--out", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["witness"] is None
    assert payload["witness_absent"]["expected_path"] == str(capture)


def test_cli_metals_prints_the_register(capsys):
    from engine import phi_laws as eng_phi_laws

    rc = cli.main(["metals"])
    assert rc == 0
    out_txt = capsys.readouterr().out
    assert "THE METAL REGISTER" in out_txt
    assert "75" in out_txt                      # the readable subset
    assert f"{eng_phi_laws.PHI_SQ_INV:.10f}" in out_txt
    assert "K" in out_txt and "Mg" in out_txt   # the gate's C1 metals are IN
    fe_rows = [ln for ln in out_txt.splitlines() if " Fe " in ln]
    assert fe_rows                              # ferrous row printed
