"""Signed receipts: model provenance, tamper detection, chain, fallback."""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest

import sniffer.receipt as receipt_mod
from sniffer.receipt import (GENESIS_HASH, Signer, seal, verify_chain,
                             verify_receipt)
from sniffer.spectrum import Spectrum


def minimal_report(provenance: str = "instrument"):
    return {
        "schema": "xrf-sniffer/report-v1",
        "provenance": provenance,
        "model": {
            "name": "counts_to_concentration",
            "version": "test-1.0.0",
            "calibration_id": "CAL-TEST-001",
            "physics": "classical",
            "label": "[MODEL]",
            "method": "test",
        },
        "elements": [{"symbol": "Fe", "areal_ug_cm2": 1.234}],
        "minerals": {"rows": []},
    }


def small_spectrum():
    e = np.arange(0.0, 1000.0, 10.0)
    return Spectrum(e, 100.0 * np.exp(-e / 500.0), live_time_s=10.0,
                    provenance="instrument", sample_id="receipt-test")


def test_sign_verify_round_trip():
    spec = small_spectrum()
    receipt = seal(minimal_report(), spectrum=spec, timestamp=1_700_000_000.0)
    verdict = verify_receipt(receipt)
    assert verdict["ok"], verdict
    assert verdict["alg"] in ("ES256", "SHA256-CHAIN")
    assert verdict["model"]["version"] == "test-1.0.0"
    assert verdict["model"]["calibration_id"] == "CAL-TEST-001"
    assert verdict["model"]["physics"] == "classical"
    assert receipt["input"]["spectrum_sha256"] == spec.sha256()
    assert receipt["prev_hash"] == GENESIS_HASH
    assert receipt["seq"] == 1


def test_report_without_provenance_is_consistent_with_the_seal_default():
    """A report that does not declare a provenance seals with the receipt's
    provenance defaulted to 'unknown'; the verify's consistency check uses the
    same default, so the receipt verifies (the seal and the check agree)."""
    report = minimal_report()
    report.pop("provenance")
    receipt = seal(report, timestamp=1_700_000_000.0)
    assert receipt["provenance"] == "unknown"
    verdict = verify_receipt(receipt)
    assert verdict["ok"], verdict
    assert verdict["checks"]["provenance"]["ok"]


def test_model_version_is_required():
    report = minimal_report()
    report["model"].pop("version")
    with pytest.raises(ValueError, match="version"):
        seal(report)


def test_calibration_id_is_required():
    report = minimal_report()
    report["model"].pop("calibration_id")
    with pytest.raises(ValueError, match="calibration_id"):
        seal(report)


def test_physics_must_be_classical():
    report = minimal_report()
    report["model"]["physics"] = "phi"
    with pytest.raises(ValueError, match="classical"):
        seal(report)


def test_tampered_report_is_detected():
    receipt = seal(minimal_report(), timestamp=1_700_000_000.0)
    bad = copy.deepcopy(receipt)
    bad["report"]["elements"][0]["areal_ug_cm2"] += 1.0
    verdict = verify_receipt(bad)
    assert not verdict["ok"]
    assert "hash" in verdict["errors"]


def test_tampered_signature_is_detected():
    receipt = seal(minimal_report(), timestamp=1_700_000_000.0)
    bad = copy.deepcopy(receipt)
    bad["signature"] = "00" * len(bad["signature"])
    verdict = verify_receipt(bad)
    assert not verdict["ok"]
    assert "signature" in verdict["errors"]


def test_tampered_model_is_detected():
    receipt = seal(minimal_report(), timestamp=1_700_000_000.0)
    bad = copy.deepcopy(receipt)
    bad["model"]["calibration_id"] = "OTHER-CAL"
    verdict = verify_receipt(bad)
    assert not verdict["ok"]
    assert "hash" in verdict["errors"]


def test_chain_links_and_detects_tamper(tmp_path):
    chain = tmp_path / "chain.jsonl"
    first = seal(minimal_report(), chain_file=chain, timestamp=1_700_000_001.0)
    second = seal(minimal_report(), chain_file=chain, timestamp=1_700_000_002.0)
    assert second["seq"] == 2
    assert second["prev_hash"] == first["hash"]
    verdict = verify_chain(chain)
    assert verdict["ok"], verdict
    assert verdict["n"] == 2
    assert verdict["genesis_ok"]

    lines = chain.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[1])
    obj["report"]["elements"][0]["areal_ug_cm2"] += 5.0
    lines[1] = json.dumps(obj)
    chain.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bad = verify_chain(chain)
    assert not bad["ok"]
    assert any("receipt[1]" in e for e in bad["errors"])


def test_wrong_previous_receipt_is_detected():
    first = seal(minimal_report(), timestamp=1_700_000_001.0)
    second = seal(minimal_report(), prev_receipt=first, timestamp=1_700_000_002.0)
    fake_prev = copy.deepcopy(first)
    fake_prev["hash"] = "00" * 64
    verdict = verify_receipt(second, prev_receipt=fake_prev)
    assert not verdict["ok"]
    assert "prev_hash" in verdict["errors"]


def test_sha256_fallback_mode(monkeypatch):
    monkeypatch.setattr(receipt_mod, "load_trust_module", lambda: None)
    signer = Signer()
    assert signer.alg == "SHA256-CHAIN"
    receipt = seal(minimal_report(), timestamp=1_700_000_000.0, signer=signer)
    verdict = verify_receipt(receipt)
    assert verdict["ok"], verdict
    assert verdict["alg"] == "SHA256-CHAIN"
    assert verdict["signer"] == "self-sha256"


def test_provenance_is_carried_into_the_receipt():
    receipt = seal(minimal_report("instrument"), timestamp=1_700_000_000.0)
    assert receipt["provenance"] == "instrument"
    assert receipt["report"]["provenance"] == "instrument"
    assert verify_receipt(receipt)["ok"]


def test_receipt_is_canonical_json_serialisable():
    receipt = seal(minimal_report(), timestamp=1_700_000_000.0)
    text = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    again = json.loads(text)
    assert verify_receipt(again)["ok"]
