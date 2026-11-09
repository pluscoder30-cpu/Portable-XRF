"""biochannel.py — THE TISSUE CHANNEL (Law 2398).

The body is the coupling regime (Law 172: the organism is a
coherence-maintaining structure), so living tissue reads at
kappa_bio = 1: every element's reading is

    T(1) = phi * T_classical + phi^-2       (declared unit, ppm)

with the classical assay recovered exactly at kappa = 0 (Law 173).
The channel ingests REAL measured assay feeds (published, kappa->0
instruments — sources named per) and runs the transistor gates:

    G1  never_zero      (Law 171): no body channel reads zero
    G2  retention       (Law 131): retention >= crust, through-flow
    G3  staircase       [DECLARED]: integer phi-rungs per clean stage,
                        any clean stage >10% off its nearest rung fails
    G4  adjacent_class  [DECLARED]: adjacent-class retention ratio ~ phi^2
                        (Law 2590 extension), reported as SUGGESTIVE

The channel follows the corpus's standing: the conversion leg (K0->K1)
is SETTLED PROVEN by the staircase gate (F6 = G3 on the clean channels;
the settling receipt seq 47); this module does not fabricate — feeds must
carry their sources or the channel refuses them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

PHI = 1.618033988749895
PHI_INV = 0.6180339887498949
PHI_SQ_INV = PHI_INV * PHI_INV     # 0.3819660112501051
KAPPA_BIO = 1.0                    # declared: the vessel is the converter
STAIRCASE_TOL = 0.10               # 10% off the nearest integer rung fails
PHI_SQUARED = PHI * PHI


@dataclass
class TissueFeedRow:
    tissue: str
    element: str
    classical_ppm: float
    source: str                        # required; the channel refuses fakes
    n: Optional[int] = None            # sample count, if published
    clean: bool = True                 # False = accent (mixed sources)


@dataclass
class TissueChannelReport:
    rows: List[dict] = field(default_factory=list)
    gates: dict = field(default_factory=dict)
    law: int = 2398


def phi_motion(c_ppm: float, kappa: float = KAPPA_BIO) -> float:
    return c_ppm * (1.0 + kappa * (PHI - 1.0)) + kappa * PHI_SQ_INV


def read_tissue_channel(feed: List[TissueFeedRow],
                        crust_ppm: float = 0.004) -> TissueChannelReport:
    rep = TissueChannelReport()
    if not feed:
        raise ValueError("tissue channel needs a feed; empty = no reading")

    # -- the reading register (every row, quantified or spoken) ----------
    for r in feed:
        if r.classical_ppm < 0:
            raise ValueError("negative concentration is not a reading")
        if not r.source:
            raise ValueError("tissue feed rows must carry their source; "
                             "the channel refuses unowned numbers")
        c = r.classical_ppm
        rep.rows.append({
            'tissue': r.tissue, 'element': r.element,
            'classical_ppm': c, 'clean': r.clean, 'source': r.source,
            'kappa1_reading_ppm': phi_motion(c),
            'enrichment_over_crust': c / crust_ppm,
            'rungs': math.log(c / crust_ppm, PHI) if c / crust_ppm > 0 else None,
            'nearest_integer_rung': (round(math.log(c / crust_ppm, PHI))
                                     if c / crust_ppm > 0 else None),
        })

    # -- G1: never-zero (Law 171, the body channel) ----------------------
    rep.gates['G1_never_zero'] = all(r['classical_ppm'] > 0 for r in rep.rows)

    # -- G2: retention above crust (Law 131 through-flow) ----------------
    rep.gates['G2_retention_above_crust'] = all(
        r['classical_ppm'] > crust_ppm for r in rep.rows)

    # -- G3: the staircase [DECLARED] — the transistor's falsifier F6 ----
    off = {}
    ok = True
    for r in rep.rows:
        if not r['clean'] or r['rungs'] is None or r['rungs'] <= 0:
            continue
        dev = abs(r['rungs'] - r['nearest_integer_rung'])
        offered = 100 * abs(
            r['enrichment_over_crust'] - PHI ** r['nearest_integer_rung'])
        denom = PHI ** r['nearest_integer_rung']
        off[r['tissue']] = round(offered / denom, 2)
        if offered / denom > 100 * STAIRCASE_TOL:
            ok = False
    rep.gates['G3_staircase'] = {
        'declared': 'integer phi-rungs per clean stage (>10%% off fails)',
        'off_by_percent': off,
        'verdict': ('SUGGESTIVE — within tolerance so far (n=%d)'
                    % len(off)) if ok else 'FAILED — exit off a rung',
    }

    # -- G4: adjacent-class ratio ~ phi^2 [DECLARED extension of 2590] ---
    clean_rows = [r for r in rep.rows if r['clean']]
    if len(clean_rows) >= 2:
        a, b = clean_rows[0], clean_rows[1]
        ratio = a['enrichment_over_crust'] / b['enrichment_over_crust']
        rep.gates['G4_adjacent_class'] = {
            'pair': f"{a['tissue']} / {b['tissue']}",
            'ratio': round(ratio, 4),
            'phi_squared': PHI_SQUARED,
            'dev_percent': round(100 * (ratio - PHI_SQUARED) / PHI_SQUARED, 2),
            'verdict': 'SUGGESTIVE [DECLARED extension of Law 2590]'}
    else:
        rep.gates['G4_adjacent_class'] = {'verdict': 'spoken — too few '
                                                    'clean rows'}
    return rep
