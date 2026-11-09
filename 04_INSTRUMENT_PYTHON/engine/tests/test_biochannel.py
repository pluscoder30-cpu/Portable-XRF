"""Tests for engine/biochannel.py — THE TISSUE CHANNEL (Law 2398)."""
import math

import pytest

from engine.biochannel import (PHI, PHI_SQ_INV, KAPPA_BIO, TissueFeedRow,
                               phi_motion, read_tissue_channel)

CRUST = 0.004


def _feed(**overrides):
    rows = [
        TissueFeedRow(tissue='newborn liver', element='Au',
                      classical_ppm=0.12,
                      source='Alexiou 1977, NAA, n=6', n=6),
        TissueFeedRow(tissue='placenta', element='Au',
                      classical_ppm=0.31,
                      source='Alexiou 1977, NAA, n=18', n=18),
    ]
    for r in rows:
        for k, v in overrides.items():
            setattr(r, k, v)
    return rows


# ---- the reading law ------------------------------------------------------

def test_kappa_zero_recovers_classical_exactly():
    for c in (0.12, 0.31, 0.0528, 0.0005, 0.0):
        assert phi_motion(c, 0.0) == c


def test_kappa_one_is_phi_motion_with_phi2_ground():
    c = 0.12
    expected = c * (1.0 + (PHI - 1.0)) + PHI_SQ_INV
    assert phi_motion(c, 1.0) == pytest.approx(expected)
    assert expected == pytest.approx(0.5761300899000926, rel=1e-12)


def test_zero_classical_input_still_carries_the_floor():
    # a channel at zero-classical still reads the ground — never zero (171)
    assert phi_motion(0.0, 1.0) == pytest.approx(PHI_SQ_INV)


# ---- the channel gates ----------------------------------------------------

def test_channel_reads_and_gates_pass_on_real_feed():
    rep = read_tissue_channel(_feed(), crust_ppm=CRUST)
    assert rep.law == 2398
    assert rep.gates['G1_never_zero'] is True
    assert rep.gates['G2_retention_above_crust'] is True
    liver = next(r for r in rep.rows if r['tissue'] == 'newborn liver')
    assert liver['kappa1_reading_ppm'] == pytest.approx(0.5761300899000926)
    assert liver['enrichment_over_crust'] == pytest.approx(30.0)
    assert liver['nearest_integer_rung'] == 7


def test_staircase_falsifier_fires_on_bad_rung():
    # an enrichment 20% above the nearest integer rung must FAIL G3
    rows = [TissueFeedRow(tissue='spleen', element='Ta',
                          classical_ppm=CRUST * PHI ** 7 * 1.20,
                          source='[SPEC] constructed to break G3')]
    rep = read_tissue_channel(rows, crust_ppm=CRUST)
    assert rep.gates['G3_staircase']['verdict'].startswith('FAILED')


def test_staircase_passes_within_tolerance_with_clean_rows():
    rep = read_tissue_channel(_feed(), crust_ppm=CRUST)
    assert rep.gates['G3_staircase']['verdict'].startswith('SUGGESTIVE')


def test_channel_refuses_unowned_numbers():
    rows = [TissueFeedRow(tissue='x', element='Au',
                          classical_ppm=0.5, source='')]
    with pytest.raises(ValueError):
        read_tissue_channel(rows)


def test_channel_refuses_negative_concentration():
    rows = [TissueFeedRow(tissue='x', element='Au',
                          classical_ppm=-0.5, source='y')]
    with pytest.raises(ValueError):
        read_tissue_channel(rows)


def test_accent_rows_do_not_drive_the_staircase():
    rows = _feed()
    rows.append(TissueFeedRow(tissue='sludge ash', element='Au',
                              classical_ppm=1.89,
                              source='Suwa 2009 (mixed sources)',
                              clean=False))
    rep = read_tissue_channel(rows, crust_ppm=CRUST)
    assert 'sludge ash' not in rep.gates['G3_staircase']['off_by_percent']


def test_kappa_bio_declares_full_coupling():
    assert KAPPA_BIO == 1.0
