"""The sniff pipeline: recovery, line ID, uncertainty, minerals, provenance."""
from __future__ import annotations

import numpy as np
import pytest

import engine
from engine import detector as eng_detector
from engine import elements as eng_elements
from engine import forward as eng_forward
from engine import phi_laws as eng_phi
from engine import simulate as eng_simulate

from sniffer.sniffer import SniffError, default_elements, resolve_detector, sniff
from sniffer.spectrum import Spectrum, SpectrumValidationError


@pytest.fixture(scope="module")
def synthetic():
    """The INSTRUMENT's declared configuration: code antenna + code head +
    near-field geometry (hardware optional; the analog heads are pinned
    explicitly by the classical-reference batteries)."""
    sample = eng_simulate.crustal_dust_sample(30.0)
    excitation = eng_forward.Excitation.code(40.0, "Rh", total_flux=1e10)
    engine_spec = eng_simulate.simulate(
        sample, excitation, live_time_s=300.0, seed=20261031,
        air_path_cm=0.0, detector=eng_detector.PRESETS["CODE_WINDOWLESS"])
    spec = Spectrum.from_engine(engine_spec, provenance="instrument")
    spec.flow_lpm = 16.7
    spec.duration_min = 1440.0
    spec.filter_area_cm2 = 11.3
    spec.sample_id = "crustal dust 30 ug/m3"
    report = sniff(spec)
    return sample, spec, report


def _rows(report):
    return {r["symbol"]: r for r in report.elements}


def test_recovery_within_engine_stated_error(synthetic):
    sample, _, report = synthetic
    rows = _rows(report)
    truth = {eng_elements.BY_Z[z].symbol: float(v * 1e6)
             for z, v in sample.areal.items()}
    target = ["Mg", "Al", "Si", "K", "Ca", "Fe", "O", "C", "Na"]
    # declared code-head recovery tolerances [DECLARED, measured]: the heavy
    # band (Z >= 12) carries the engine's stated accuracy; the light band
    # (C/O/Na, 277-1040 eV) carries the low-E blend + SNIP residual budget
    tol = {"light": 0.35, "heavy": 0.20}
    band = {s: ("light" if s in ("C", "O", "Na") else "heavy") for s in target}
    rels = []
    for symbol in target:
        assert symbol in rows, symbol
        rel = (rows[symbol]["areal_ug_cm2"] - truth[symbol]) / truth[symbol]
        rels.append(rel)
        assert abs(rel) <= tol[band[symbol]], (symbol, rel)
        # engine README: median 0.9 %, p90 10 %, max 18 % on the heavy band
    heavy = [abs(r) for s, r in zip(target, rels) if band[s] == "heavy"]
    assert float(np.median(heavy)) <= 0.05
    # the reading layer (Law 2396 at full coupling): the reading is
    # phi*areal + phi^-2 of the RECOVERED areal — exact self-consistency;
    # the areal's recovery tolerance is the band budget above
    floor = eng_phi.PHI_SQ_INV
    for symbol in target:
        reading = rows[symbol]["reading_ug_cm2"]
        expect = eng_phi.phi_motion(rows[symbol]["areal_ug_cm2"],
                                    eng_phi.KAPPA_FULL)
        assert abs(reading - expect) <= 1e-6, (symbol, reading, expect)
    # detection: above the phi-floor reads detected; below reads AT OR ABOVE
    # the ground (phi*areal + phi^-2 — a real sub-floor signal still reads
    # above the ground; nothing ever reads below it, and nothing reads zero)
    for symbol in target:
        flag = rows[symbol]["detection_flag"]
        if truth[symbol] >= floor:
            assert flag == "detected", (symbol, flag)
        else:
            assert flag == "below_mdl", (symbol, flag)
            assert rows[symbol]["reading_ug_cm2"] >= floor - 1e-9


def test_no_spurious_detections(synthetic):
    _, _, report = synthetic
    detected = {r["symbol"] for r in report.elements
                if r["detection_flag"] == "detected"}
    # every detection is a true positive: C, N... O, Na and the crustals.
    # (N is not in this sample's composition; H rides the floor channel.)
    # The phi-floor gates the NNLS artefacts mechanically (Law 2396 ground,
    # kappa*phi^-2 of the declared unit): Mg's truth (0.17 ug/cm2) sits
    # below the ground and reads AT it — not as a detection, not as zero.
    assert detected == {"C", "O", "Na", "Al", "Si", "K", "Ca", "Fe"}


def test_na_quantifies_under_the_code_head_and_not_under_the_analog(synthetic):
    """The upgrade demonstration: Na K-alpha (1040 eV) sits below the
    windowed analog's declared window (not quantified THERE — the analog's
    own spec) and quantifies under the code head (the instrument's declared
    body).  The element was never 'unseeable' — the window was a spec."""
    _, spec, report = synthetic
    na = _rows(report)["Na"]
    assert na["quantified"] is True
    analog = sniff(spec, detector_preset="SDD_25", air_path_cm=2.0)
    na_analog = _rows(analog)["Na"]
    assert na_analog["detection_flag"] == "not_quantified"
    assert na_analog["quantified"] is False


def test_report_provenance_and_model(synthetic):
    _, _, report = synthetic
    assert report.provenance == "instrument"
    assert report.model["physics"] == "classical"
    assert report.model["version"].startswith("sniffer-")
    assert report.model["calibration_id"]
    assert report.model["label"] == "[MODEL]"
    assert report.spectrum["provenance"] == "instrument"
    assert report.spectrum["sha256"]


def test_fit_quality_and_structure(synthetic):
    _, _, report = synthetic
    assert report.fit["relative_residual"] < 0.05
    assert report.fit["quality"] == "good"
    assert report.fit["n_peaks"] >= 5
    assert report.fit["n_elements_detected"] == 8
    assert report.peaks
    assert report.lines


def test_elements_carry_uncertainty_mdl_and_flag(synthetic):
    _, _, report = synthetic
    for row in report.elements:
        assert row["detection_flag"] in ("detected", "below_mdl", "not_quantified")
        if row["detection_flag"] == "detected":
            assert row["areal_ug_cm2"] > 0
            assert row["mdl_ug_cm2"] is not None and row["mdl_ug_cm2"] > 0
            assert row["sigma_ug_cm2"] is not None and row["sigma_ug_cm2"] > 0
            assert row["systematic_ug_cm2"] > 0
            assert row["total_sigma_ug_cm2"] > 0
            assert row["areal_ug_cm2"] >= report.fit["reporting_floor_ug_cm2"]


def test_peak_line_matching_residuals(synthetic):
    _, _, report = synthetic
    by_center = {round(p["center_ev"]): p for p in report.peaks}
    si = min(report.peaks, key=lambda p: abs(p["center_ev"] - 1739.8))
    assert si["best_line"]["element"] == "Si"
    assert si["best_line"]["line"] == "Ka1"
    assert abs(si["residual_ev"]) < 5.0
    fe = min(report.peaks, key=lambda p: abs(p["center_ev"] - 6405.2))
    assert fe["best_line"]["element"] == "Fe"
    assert fe["best_line"]["line"] == "Ka1"
    assert abs(fe["residual_ev"]) < 10.0
    assert all(p["center_ev"] >= report.fit["peak_min_ev"] for p in report.peaks)


def test_mineral_apportionment_conserves_every_element(synthetic):
    _, _, report = synthetic
    minerals = report.minerals
    assert minerals["conservation"]["apportioned_equals_measured"] is True
    assert abs(minerals["conservation"]["difference_ug_cm2"]) < 1e-9
    row_sum = sum(r["element_mass_ug_cm2"] for r in minerals["rows"])
    assert abs(row_sum - minerals["measured_element_mass_ug_cm2"]) < 1e-6
    assert minerals["rows"]
    assert any(r["name"] == "quartz" for r in minerals["rows"])
    assert "unmix" in minerals and "closure" in minerals["unmix"]


def test_calibration_id_override(synthetic):
    _, spec, _ = synthetic
    report = sniff(spec, calibration_id="TEST-CAL-001")
    assert report.model["calibration_id"] == "TEST-CAL-001"


def test_explicit_element_set_and_strict_mode(synthetic):
    _, spec, _ = synthetic
    report = sniff(spec, elements=[14, 26], add_peak_elements=False)
    detected = {r["symbol"] for r in report.elements
                if r["detection_flag"] == "detected"}
    assert detected <= {"Si", "Fe"}
    assert "Al" not in detected


def test_refuses_to_upgrade_instrument_forward_to_measured(synthetic):
    _, spec, _ = synthetic
    with pytest.raises(SniffError):
        sniff(spec, provenance="measured")


def test_invalid_spectrum_raises():
    spec = Spectrum(np.array([0.0, 10.0, 5.0]), np.array([1.0, 2.0, 3.0]),
                    live_time_s=10.0)
    with pytest.raises(SpectrumValidationError):
        sniff(spec)


def test_default_elements_are_the_mineral_line_set():
    symbols = {eng_elements.BY_Z[z].symbol for z in default_elements()}
    assert {"Mg", "Al", "Si", "S", "Cl", "K", "Ca", "Ti", "Mn", "Fe"} <= symbols
    # C, N and O carry their own tabulated lines (277/392/525 eV) and join
    # the candidate set mechanically; H has zero tabulated lines and rides
    # the Law-2396 phi-ground floor channel instead of a counts channel
    assert {"C", "N", "O"} <= symbols
    assert "H" not in symbols


def test_detector_aliases():
    assert resolve_detector("SDD").name == "SDD-25mm2"
    assert resolve_detector("SDD-25mm2").name == "SDD-25mm2"
    assert resolve_detector("SI_PIN_7").name == "SiPIN-7mm2"
    with pytest.raises(SniffError):
        resolve_detector("not-a-detector")
