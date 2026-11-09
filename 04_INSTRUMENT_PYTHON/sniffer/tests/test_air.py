"""Air reader: filter unit math, feed cache, offline fallback, composition."""
from __future__ import annotations

import math

import numpy as np
import pytest

from engine import forward as eng_forward
from engine import simulate as eng_simulate

from sniffer.air import (DEFAULT_FILTER_AREA_CM2, DEFAULT_FLOW_LPM,
                         air_from_feed, air_from_spectrum)
from sniffer.spectrum import Spectrum


@pytest.fixture(scope="module")
def synthetic():
    sample = eng_simulate.crustal_dust_sample(30.0)
    excitation = eng_forward.Excitation.tube(40.0, "Rh", total_flux=1e10)
    engine_spec = eng_simulate.simulate(
        sample, excitation, live_time_s=300.0, seed=20261031, air_path_cm=2.0)
    spec = Spectrum.from_engine(engine_spec, provenance="instrument")
    spec.flow_lpm = 16.7
    spec.duration_min = 1440.0
    spec.filter_area_cm2 = 11.3
    spec.sample_id = "air-unit-test"
    return sample, spec


def test_filter_unit_math(synthetic):
    _, spec = synthetic
    reading = air_from_spectrum(
        spec, flow_lpm=16.7, duration_min=1440.0, filter_area_cm2=11.3,
        location={"latitude": 40.0, "longitude": -74.0},
    )
    # visible element mass is the exact areal -> concentration conversion;
    # the sum of the per-element concentrations is the same number
    expected_visible = sum(reading.elements_ug_m3.values())
    assert reading.visible_element_mass_ug_m3 == pytest.approx(expected_visible, rel=1e-12)
    assert reading.estimated_total_pm_ug_m3 is not None
    assert reading.estimated_total_pm_ug_m3 >= reading.visible_element_mass_ug_m3
    assert reading.elements_ug_m3
    assert reading.minerals_ug_m3
    assert reading.location == {"latitude": 40.0, "longitude": -74.0}
    assert reading.timestamp
    assert reading.provenance == "instrument"
    assert reading.report is not None


def test_filter_exact_conversion_from_areal(synthetic):
    _, spec = synthetic
    reading = air_from_spectrum(spec, flow_lpm=DEFAULT_FLOW_LPM,
                                duration_min=1440.0,
                                filter_area_cm2=DEFAULT_FILTER_AREA_CM2)
    report = reading.report
    detected_areal = sum(r["areal_ug_cm2"] for r in report["elements"]
                         if r["detection_flag"] == "detected")
    volume_m3 = DEFAULT_FLOW_LPM * 1440.0 / 1000.0
    expected = detected_areal * DEFAULT_FILTER_AREA_CM2 / volume_m3
    assert reading.visible_element_mass_ug_m3 == pytest.approx(expected, rel=1e-12)
    # every element conversion uses the same exact factor
    factor = DEFAULT_FILTER_AREA_CM2 / volume_m3
    for row in report["elements"]:
        if row["detection_flag"] == "detected":
            assert reading.elements_ug_m3[row["symbol"]] == pytest.approx(
                row["areal_ug_cm2"] * factor, rel=1e-12)


def test_filter_requires_a_sampled_volume():
    spec = Spectrum(np.arange(0.0, 1000.0, 10.0), np.ones(100),
                    live_time_s=10.0, provenance="instrument")
    with pytest.raises(ValueError, match="flow_lpm|duration_min|filter_area_cm2"):
        air_from_spectrum(spec)


def test_feed_offline_no_cache(tmp_path):
    reading = air_from_feed(0.0, 0.0, cache_only=True, cache_dir=tmp_path)
    assert reading.status == "offline_no_cache"
    assert reading.pm10_ug_m3 is None
    assert reading.pm2_5_ug_m3 is None
    assert reading.minerals_ug_m3 == {}
    assert reading.cached is False
    assert any("offline" in a.lower() for a in reading.assumptions)


def test_feed_cache_ttl_and_stale(tmp_path):
    calls = {"n": 0}

    def fake(lat, lon, timeout):
        calls["n"] += 1
        return {
            "source": "test-feed",
            "time": "2026-01-01T00:00:00Z",
            "pm10_ug_m3": 20.0,
            "pm2_5_ug_m3": 12.0,
            "dust_ug_m3": 5.0,
        }

    def boom(lat, lon, timeout):
        raise RuntimeError("network down")

    live = air_from_feed(1.0, 2.0, cache_dir=tmp_path, fetcher=fake)
    assert live.status == "ok"
    assert live.pm10_ug_m3 == 20.0
    assert live.minerals_ug_m3
    assert live.cached is False

    cached = air_from_feed(1.0, 2.0, cache_only=True, cache_dir=tmp_path)
    assert cached.status == "cached"
    assert cached.cached is True
    assert cached.pm10_ug_m3 == 20.0

    stale = air_from_feed(1.0, 2.0, cache_dir=tmp_path, fetcher=boom, ttl_s=0.0)
    assert stale.status == "stale_cache"
    assert stale.stale is True
    assert stale.pm10_ug_m3 == 20.0
    assert any("stale" in n.lower() for n in stale.notes)

    # cache_only never calls the network
    before = calls["n"]
    air_from_feed(1.0, 2.0, cache_only=True, cache_dir=tmp_path,
                  fetcher=boom)
    assert calls["n"] == before


def test_feed_ttl_zero_forces_a_refetch(tmp_path):
    calls = {"n": 0}

    def fake(lat, lon, timeout):
        calls["n"] += 1
        return {"source": "test-feed", "pm10_ug_m3": 10.0, "pm2_5_ug_m3": 8.0,
                "dust_ug_m3": 0.0, "time": "2026-01-01T00:00:00Z"}

    air_from_feed(1.0, 2.0, cache_dir=tmp_path, fetcher=fake, ttl_s=0.0)
    air_from_feed(1.0, 2.0, cache_dir=tmp_path, fetcher=fake, ttl_s=0.0)
    assert calls["n"] == 2


def test_feed_invalid_coordinates():
    with pytest.raises(ValueError):
        air_from_feed(100.0, 0.0, cache_only=True)


def test_feed_with_measured_composition(tmp_path):
    def fake(lat, lon, timeout):
        return {"source": "test-feed", "pm10_ug_m3": 20.0, "pm2_5_ug_m3": 15.0,
                "dust_ug_m3": 4.0, "time": "2026-01-01T00:00:00Z"}

    reading = air_from_feed(1.0, 2.0, cache_dir=tmp_path, fetcher=fake,
                            composition={"Si": 10.0, "Fe": 2.0})
    assert reading.elements_ug_m3 == {"Si": 10.0, "Fe": 2.0}
    assert reading.estimated_total_pm_ug_m3 == 20.0
    assert any("composition" in a for a in reading.assumptions)


def test_feed_minerals_are_normalised(tmp_path):
    def fake(lat, lon, timeout):
        return {"source": "test-feed", "pm10_ug_m3": 20.0, "pm2_5_ug_m3": 12.0,
                "dust_ug_m3": 5.0, "time": "2026-01-01T00:00:00Z"}

    reading = air_from_feed(1.0, 2.0, cache_dir=tmp_path, fetcher=fake)
    total = sum(reading.minerals_ug_m3.values())
    assert total > 0
    assert math.isclose(sum(reading.mineral_mass_fractions.values()), 1.0, rel_tol=1e-9)
    assert reading.minerals_ug_m3["quartz"] > 0
