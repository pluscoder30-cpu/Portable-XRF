"""Spectrum type, strict validation, I/O and deterministic identity."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from sniffer.spectrum import (Spectrum, SpectrumValidationError, load_spectrum,
                              save_spectrum)


def make_spec(n: int = 200) -> Spectrum:
    energy = np.arange(n, dtype=float) * 10.0
    counts = 100.0 * np.exp(-energy / 5000.0) + 500.0 * np.exp(
        -0.5 * ((energy - 6400.0) / 60.0) ** 2)
    return Spectrum(
        energy_ev=energy,
        counts=counts,
        live_time_s=300.0,
        real_time_s=310.0,
        current_ua=10.0,
        flow_lpm=16.7,
        duration_min=1440.0,
        filter_area_cm2=11.3,
        sample_id="unit-test",
        source="unit-test",
        provenance="instrument",
        metadata={"detector": "SDD_25", "note": "synthetic"},
    )


def test_valid_spectrum_passes():
    result = make_spec().validate(strict=False)
    assert result.ok
    assert result.n_channels == 200
    assert result.errors == []


def test_non_monotone_rejected():
    spec = Spectrum(np.array([0.0, 10.0, 5.0]), np.array([1.0, 2.0, 3.0]),
                    live_time_s=10.0)
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("increasing" in e for e in result.errors)


def test_negative_counts_rejected():
    spec = Spectrum(np.array([0.0, 10.0, 20.0]), np.array([1.0, -2.0, 3.0]),
                    live_time_s=10.0)
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("negative" in e for e in result.errors)


def test_nan_counts_rejected():
    spec = Spectrum(np.array([0.0, 10.0, 20.0]),
                    np.array([1.0, math.nan, 3.0]), live_time_s=10.0)
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("NaN" in e for e in result.errors)


def test_zero_live_time_rejected():
    spec = make_spec()
    spec.live_time_s = 0.0
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("live_time_s" in e for e in result.errors)


def test_real_time_shorter_than_live_time_rejected():
    spec = make_spec()
    spec.real_time_s = 1.0
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("shorter" in e for e in result.errors)


def test_negative_flow_rejected():
    spec = make_spec()
    spec.flow_lpm = -1.0
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("flow_lpm" in e for e in result.errors)


def test_length_mismatch_rejected():
    spec = make_spec()
    spec.counts = spec.counts[:-1]
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("mismatch" in e for e in result.errors)


def test_too_few_channels_rejected():
    spec = Spectrum(np.array([0.0, 10.0]), np.array([1.0, 2.0]), live_time_s=10.0)
    result = spec.validate(strict=False)
    assert not result.ok
    assert any("at least 3" in e for e in result.errors)


def test_strict_raises():
    spec = make_spec()
    spec.live_time_s = 0.0
    with pytest.raises(SpectrumValidationError):
        spec.validate(strict=True)


def test_engine_bridge_round_trip():
    spec = make_spec()
    engine_spec = spec.to_engine()
    assert engine_spec.energy_ev.shape == spec.energy_ev.shape
    assert engine_spec.live_time_s == spec.live_time_s
    back = Spectrum.from_engine(engine_spec)
    assert np.allclose(back.energy_ev, spec.energy_ev)
    assert np.allclose(back.counts, spec.counts)
    assert back.live_time_s == spec.live_time_s


def test_json_round_trip(tmp_path):
    spec = make_spec()
    path = save_spectrum(spec, tmp_path / "s.json")
    loaded = load_spectrum(path)
    assert np.allclose(loaded.energy_ev, spec.energy_ev)
    assert np.allclose(loaded.counts, spec.counts)
    assert loaded.live_time_s == spec.live_time_s
    assert loaded.provenance == "instrument"
    assert loaded.sample_id == "unit-test"
    assert loaded.metadata["detector"] == "SDD_25"
    assert loaded.sha256() == spec.sha256()


@pytest.mark.parametrize("fmt", ["csv", "tsv", "jsonl"])
def test_delimited_round_trip(tmp_path, fmt):
    spec = make_spec()
    path = save_spectrum(spec, tmp_path / f"s.{fmt}", fmt)
    loaded = load_spectrum(path)
    assert np.allclose(loaded.energy_ev, spec.energy_ev)
    assert np.allclose(loaded.counts, spec.counts, rtol=1e-9)
    assert loaded.live_time_s == pytest.approx(spec.live_time_s)
    assert loaded.provenance == "instrument"


def test_csv_none_metadata_round_trip(tmp_path):
    spec = make_spec()
    spec.real_time_s = None
    spec.current_ua = None
    path = save_spectrum(spec, tmp_path / "s.csv", "csv")
    loaded = load_spectrum(path)
    assert loaded.real_time_s is None
    assert loaded.current_ua is None


def test_json_channels_shape(tmp_path):
    blob = {
        "live_time_s": 10.0,
        "provenance": "measured",
        "channels": [
            {"energy_ev": 0.0, "counts": 1.0},
            {"energy_ev": 10.0, "counts": 2.0},
            {"energy_ev": 20.0, "counts": 3.0},
        ],
    }
    path = tmp_path / "channels.json"
    path.write_text(json.dumps(blob), encoding="utf-8")
    loaded = load_spectrum(path)
    assert loaded.provenance == "measured"
    assert list(loaded.counts) == [1.0, 2.0, 3.0]


def test_hash_is_deterministic_and_sensitive():
    a = make_spec()
    b = make_spec()
    assert a.sha256() == b.sha256()
    b.counts[10] += 1.0
    assert a.sha256() != b.sha256()


def test_zero_counts_warns_but_is_valid():
    spec = make_spec()
    spec.counts = np.zeros_like(spec.counts)
    result = spec.validate(strict=False)
    assert result.ok
    assert any("zero total counts" in w for w in result.warnings)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_spectrum("definitely-not-a-file.json")
