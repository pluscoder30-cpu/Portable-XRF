"""THE CODE COIL — the metal-detector coil, in code, attached to the XRF.

ATTACHED INSTRUMENT, NOT A NEW ONE
----------------------------------
This is the metal-detector head of the code-based XRF — the same pattern
as the code antenna and the code radio in this codebase: the instrument
is the code, hardware is an optional body.

BUILT FROM THE COILS WE ALREADY MADE
------------------------------------
* ``em-feild/phi_coil.py`` supplies the phi-ladder drive conventions:
  I_k = I0*phi^-k, f_k = f0*phi^k on the 528 Hz ladder, the summed
  ladder field = phi^2 x single-segment, and the mutually-coupled
  resonant chain A_{k+1} = phi*A_k.  Its constants (PHI, MU_0, 528 Hz
  anchor) are re-declared in ``engine/phi_laws.py`` with identical values.
* ``phi-field-native-transformer/field_computer/server/field_wifi_sniffer``
  is the radio ear of this codebase; the session that runs this coil
  carries that sniffer's capture file as a signed witness (same SOUL_SEED
  trust root), sealing the mineral ear and the radio ear to one chain.

PHYSICS STACK — which law does what
-----------------------------------
[EXACT]     the ladder (528*phi^9 = 40134.946166 Hz, asserted), the tank
            capacitor wiring C = 1/(omega^2 L) per channel (Law 675/676
            resonance algebra), Ohm/Kirchhoff around the loop.
[LAW 638]   self-inductance: the coils are solenoid-form,
            L = mu0 * N^2 * A / length (the corpus's own classical form).
[LAW 637]   mutual inductance: coaxial coil pairs,
            M = mu0 * N1 * N2 * pi * a1^2 * a2^2 / (2*(a1^2+d^2)^1.5)
            (near-field dipole form [MODEL] for a2 <= a1).
[LAW 039/048] Faraday/Lenz: the target's induced currents oppose flux
            change; the eddy re-radiation enters the receiver in
            QUADRATURE (the -90 deg eddy phase).
[LAW 801]   eddy currents: targets carry eddy currents whose skin depth
            is delta = sqrt(2*rho/(omega*mu0*mu_r)) — the penetration
            bookkeeping of every conductive target.
[MAGNETIZ.] a ferromagnetic target (mu_r > 10: Fe/Co/Ni, engine/metals.py)
            also re-magnetizes: the magnetization dipole re-radiates IN
            PHASE (flux-adding), with declared saturation M_sat.  That
            in-phase vs quadrature split is the classic ferrous/non-ferrous
            discriminator, and this code implements it.
[LAW 2396]  the reading layer: every channel reading carries the
            unit-covariant phi-ground (Law 171's no-quiet-zero); at
            declared coupling kappa = 1 a perfectly still channel reads
            phi^-2 = 0.3819660113 ppm of the nulled carrier.
[MODEL/     the coil geometry, drive current, null design point and
 DECLARED]  acquisition noise floor are declared parameters, exactly
            like the tube flux and background model of the XRF forward
            model.  The one calibration anchor is declared: a coin-class
            copper target (25 mm) at the design standoff reads exactly
            10,000 ppm at the base channel; every other metal, distance
            and ladder frequency scales from it by the physics above.

The sweep registers EVERY registered metal (engine/metals.py): coin-class
targets read their physics response; deposit-sheet traces (the air's
metallic aerosol, from the XRF reading) read at the field-carried floor.
Nothing is dropped, nothing is invented: the reading states which column
carried it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

from . import metals as _metals
from .phi_laws import (BASE_FREQUENCY, KAPPA_FULL, LADDER_INVARIANT_HZ, MU_0,
                       PHI, PHI_INV, PHI_SQ, PHI_SQ_INV, coil_response_phi,
                       classical_limit_error, ladder_frequencies, phi_motion)

# ---------------------------------------------------------------------------
# Declared coil geometry and acquisition (the [MODEL/DECLARED] layer)
# ---------------------------------------------------------------------------
N_TX = 200                      # turns, transmit coil [MODEL/DECLARED]
N_RX = 200                      # turns, receive coil
COIL_RADIUS_M = 0.04            # 40 mm winding radius, both coils
COIL_LENGTH_M = 0.01            # 10 mm solenoid length
TX_WIRE_R_OHM = 2.0             # transmit + lead resistance [MODEL]
RX_WIRE_R_OHM = 2.0
PAIR_SEPARATION_M = 0.30        # coaxial Tx-Rx spacing
DRIVE_CURRENT_A = 0.1           # resonant drive current [MODEL]
NOISE_FLOOR_V = 5.7e-9          # 3-sigma acquisition noise @10 Hz BW [MODEL]
MIN_DETECT_PPM = 30.0           # declared operating floor (~2.2x the base-rung 3-sigma noise-equivalent reading)

#: coin-class target ("metal detector" sense): 25 mm disc, 2 mm thick
COIN_RADIUS_M = 0.0125
COIN_THICKNESS_M = 0.002
DESIGN_STANDOFF_M = 0.10        # coin at 10 cm from the coil face
DESIGN_RESPONSE_PPM = 10000.0   # copper coin reads exactly 1 % of the nulled carrier [DECLARED]
DESIGN_CHANNEL = 0              # the base rung (528 Hz) is the design channel

#: deposit-sheet mode: the filter deposit read as a thin conducting layer
SHEET_AREA_CM2 = 11.3           # matches sniffer.air.DEFAULT_FILTER_AREA_CM2
SHEET_BAND_W_M = 0.004          # effective eddy band width [MODEL]

#: ferromagnetic saturation magnetization [EST for Co/Ni; REFERENCE soft iron]
M_SAT_FERRO = 1.7e6             # A/m, soft-audio saturation of the coin class
MU_R_FERRO_THRESHOLD = 10.0

SHEET_WIRE_EQUIV_M = 1.0e-3     # deposit sheet's wire-equivalent radius [MODEL]


def self_inductance(n_turns: int = N_TX, radius_m: float = COIL_RADIUS_M,
                    length_m: float = COIL_LENGTH_M) -> float:
    """LAW 638 (classical form): L = mu0 * N^2 * A / length (solenoid)."""
    area = math.pi * radius_m ** 2
    return MU_0 * float(n_turns) ** 2 * area / float(length_m)


def mutual_coaxial(d_m: float, a_primary_m: float, a_secondary_m: float,
                   n_primary: int, n_secondary: int) -> float:
    """LAW 637 (near-field dipole form, [MODEL] for a_secondary <= a_primary):
    M = mu0 * N1 * N2 * pi * a1^2 * a2^2 / (2*(a1^2 + d^2)^1.5)."""
    a1, a2, d = float(a_primary_m), float(a_secondary_m), abs(float(d_m))
    return MU_0 * float(n_primary) * float(n_secondary) * math.pi * (
        a1 * a1 * a2 * a2) / (2.0 * (a1 * a1 + d * d) ** 1.5)


def tank_capacitor(f_hz: float, l_h: float) -> float:
    """LAW 675/676 (exact wiring algebra): C = 1/(omega^2 L)."""
    omega = 2.0 * math.pi * float(f_hz)
    return 1.0 / (omega * omega * float(l_h))


def skin_depth_m(sigma_s_m: float, omega: float, mu_r: float = 1.0) -> float:
    """LAW 801 bookkeeping: delta = sqrt(2 rho/(omega mu0 mu_r))."""
    return math.sqrt(2.0 / (float(sigma_s_m) * MU_0 * float(mu_r) * float(omega)))


def _tx_field_H(d_m: float) -> float:
    """The transmit field H at the target plane (A/m), from LAW 637's field:
    B = mu0 * N I a^2/(2(a^2+d^2)^1.5);  H = B/mu0."""
    b = MU_0 * N_TX * DRIVE_CURRENT_A * COIL_RADIUS_M ** 2 / (
        2.0 * (COIL_RADIUS_M ** 2 + d_m * d_m) ** 1.5)
    return b / MU_0


def _target_impedance(omega: float, sigma_s_m: float, mu_r: float,
                      radius_m: float, thickness_m: Optional[float],
                      wire_equiv_m: float = 5e-4) -> complex:
    """The target's equivalent loop impedance Z = R + j*omega*L.

    LAW 638 form for L (wire-equivalent loop), LAW 801 skin-depth for R:
    the eddy band conducts through min(delta, thickness) of the target.
    """
    l_geometric = MU_0 * float(radius_m) * (
        math.log(8.0 * radius_m / wire_equiv_m) - 2.0)
    delta = skin_depth_m(sigma_s_m, omega, mu_r)
    t_active = min(delta, thickness_m) if thickness_m else min(delta, COIN_THICKNESS_M)
    r_eddy = (1.0 / sigma_s_m) * (2.0 * math.pi * radius_m) / (SHEET_BAND_W_M * t_active)
    return complex(r_eddy, omega * l_geometric)


def _magnetization_dipole_A_m2(metal: "_metals.Metal",
                               d_m: float) -> Optional[float]:
    """The in-phase magnetization channel for ferromagnetic targets.

    m = M_eff * V;  M_eff = min(chi * H_target, M_sat) with chi = mu_r - 1
    (SI: mu_r = 1 + chi, M = chi*H).
    Returns None for non-ferromagnetic metals (no in-phase channel).
    """
    mu_r = metal.rel_permeability
    if mu_r is None or mu_r < MU_R_FERRO_THRESHOLD:
        return None
    h = _tx_field_H(d_m)
    chi = mu_r - 1.0                       # relative susceptibility: mu_r = 1 + chi
    m_eff = min(chi * h, M_SAT_FERRO)
    volume = math.pi * COIN_RADIUS_M ** 2 * COIN_THICKNESS_M
    return m_eff * volume


def raw_coin_response(metal: "_metals.Metal", f_hz: float,
                      standoff_m: float) -> Tuple[float, float]:
    """The coin-class target response at the receiver: (in-phase V, quadrature V).

    Quadrature (eddy, LAW 801 Faraday/Lenz):
        V_q = omega^2 * M_tt * M_rt * I0 / |Z_t|   (re-radiated eddy field)
    In-phase (magnetization dipole, Fe/Co/Ni):
        V_ip = omega * B_dip * A_rx  (dipole flux approximation [MODEL];
        the dipole axis is the coil axis; B_dip already carries the
        mu0/(4pi) dipole law, and the receiver's per-turn scale is absorbed
        into the single declared calibration anchor, K_null = design_V*100)
    """
    omega = 2.0 * math.pi * float(f_hz)
    d_tx = float(standoff_m)
    d_rx = max(abs(PAIR_SEPARATION_M - d_tx), 1e-3)
    m_tt = mutual_coaxial(d_tx, COIL_RADIUS_M, COIN_RADIUS_M, N_TX, 1)
    m_rt = mutual_coaxial(d_rx, COIL_RADIUS_M, COIN_RADIUS_M, N_RX, 1)
    sigma, mu_r = metal.conductivity_s_m, metal.rel_permeability or 1.0
    if not sigma:
        return (0.0, 0.0)
    z_t = _target_impedance(omega, sigma, mu_r, COIN_RADIUS_M, None)
    v_eddy = (omega ** 2) * m_tt * m_rt * DRIVE_CURRENT_A / abs(z_t)
    v_magnetic = 0.0
    m_dip = _magnetization_dipole_A_m2(metal, d_tx)
    if m_dip is not None:
        # dipole on-axis field B = mu0/(4pi) * 2m/d_rx^3; flux through Rx:
        # Phi = B * A_rx; emf = omega * Phi  [dipole approx, a_rx << d_rx]
        b_dip = MU_0 / (4.0 * math.pi) * 2.0 * m_dip / (d_rx ** 3)
        area_rx = math.pi * COIL_RADIUS_M ** 2
        v_magnetic = omega * b_dip * area_rx
    return (v_magnetic, v_eddy)


# ---------------------------------------------------------------------------
# The ladder sweep
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Channel:
    rung: int
    f_hz: float
    tank_c_farad: float
    q_resonance: float
    drive_scale: float = 1.0     # phi^-k ladder-drive scale (em-feild convention)

    def as_dict(self) -> dict:
        return {"rung": self.rung, "f_hz": round(self.f_hz, 3),
                "tank_c_farad": self.tank_c_farad,
                "q_resonance": self.q_resonance,
                "drive_scale": self.drive_scale}


def channels() -> Tuple[Channel, ...]:
    """THE LADDER: ten resonant rungs, f_k = 528*phi^k, Law 675 tank each.

    The invariant rung 528*phi^9 = 40134.946166 Hz is asserted inside
    ``ladder_frequencies``; each rung's tank capacitor is exact wiring
    (Law 675/676), and the drive follows the em-feild phi-ladder scale
    I_k = I0*phi^-k, whose infinite sum is phi^2 = 2.618 x single-segment.
    """
    freqs = ladder_frequencies(n=10)
    l_tx = self_inductance()
    out = []
    for k, f in enumerate(freqs):
        c = tank_capacitor(f, l_tx)
        q = 2.0 * math.pi * f * l_tx / TX_WIRE_R_OHM
        out.append(Channel(rung=k, f_hz=f, tank_c_farad=c,
                           q_resonance=q, drive_scale=PHI_INV ** k))
    return tuple(out)


# ---------------------------------------------------------------------------
# Declared calibration anchor and the reading layer
# ---------------------------------------------------------------------------
def design_response_v() -> float:
    """The design target's raw response scale (V), copper coin at design point."""
    ip, q = raw_coin_response(_metals.metal("Cu"), BASE_FREQUENCY, DESIGN_STANDOFF_M)
    return math.hypot(ip, q)


def _null_v() -> float:
    """K_null: the receiver voltage that reads 1 ppm [DECLARED design anchor].

    The design point (copper coin, base rung 528 Hz, 0.10 m standoff) reads
    exactly 10,000 ppm of the nulled carrier:
        reading_ppm = 1e6 * V / K_null  ->  K_null = design_V * 1e6/1e4
                    = design_V * 100.
    Every other metal, rung and standoff scales from it by the physics.
    """
    return design_response_v() * 100.0


def coin_response_ppm(symbol: str, f_hz: float,
                      standoff_m: float = DESIGN_STANDOFF_M) -> Tuple[float, float]:
    """(in-phase, quadrature) reading in ppm of the nulled carrier, kappa = 0.

    The physics ratio is exact inside the declared model; the single
    absolute anchor is the declared design point (copper coin, 528 Hz,
    10 cm standoff, 10,000 ppm).  Ferrous targets carry the in-phase
    channel; everything else is quadrature-only.

    DRIVE INVARIANCE (declared): the reading is in ppm of the nulled
    carrier — signal and carrier scale together under any drive, so the
    per-rung drive ladder I_k = I0*phi^-k is staged at the drive stage and
    does not change any reading in ppm_of_carrier.  The detection floor is
    carried in the same convention (MIN_DETECT_PPM on the base-rung
    carrier, applied rung-invariantly).
    """
    m = _metals.metal(symbol)
    ip_v, q_v = raw_coin_response(m, f_hz, standoff_m)
    k_null = _null_v()
    return (1e6 * ip_v / k_null, 1e6 * q_v / k_null)


def coin_response_ppm_phi(symbol: str, f_hz: float,
                          standoff_m: float = DESIGN_STANDOFF_M,
                          kappa: float = KAPPA_FULL) -> Tuple[float, float]:
    """Law 2396 readings: every channel carries the phi-ground.

    A still channel (no target term) reads kappa*phi^-2 at full coupling:
    0.3819660113 ppm of the carrier — the corpus's no-quiet-zero floor.
    """
    ip0, q0 = coin_response_ppm(symbol, f_hz, standoff_m)
    return (phi_motion(ip0, kappa), phi_motion(q0, kappa))


def sweep_coin(symbol: str, standoff_m: float = DESIGN_STANDOFF_M,
               kappa: float = KAPPA_FULL) -> List[dict]:
    """The full 10-rung sweep table for one coin-class target."""
    rows = []
    for ch in channels():
        ip, q = coin_response_ppm_phi(symbol, ch.f_hz, standoff_m, kappa)
        rows.append({
            "rung": ch.rung, "f_hz": round(ch.f_hz, 3), "symbol": symbol,
            "inphase_ppm": ip, "quadrature_ppm": q,
            "total_ppm": math.hypot(ip, q),
            "reading_mode": "magnetization_inphase" if abs(ip) > abs(q) else "eddy_quadrature",
            "kappa": kappa,
        })
    return rows


def optimal_channel(symbol: str, standoff_m: float = DESIGN_STANDOFF_M) -> int:
    """The rung where this metal's response best SEPARATES from the fleet.

    Contrast criterion: argmax over rungs of (this metal's total response /
    the registered fleet's mean total response at that rung).  Amplitude
    alone is monotone in frequency for every conductor (the skin-limited
    regime pushes everything up ~ omega^1.5), so the raw peak is always the
    top rung; the discriminative rung is the contrast peak.
    """
    rows = sweep_coin(symbol, standoff_m, kappa=0.0)
    fleet = _fleet_mean_per_rung(standoff_m)
    best_rung, best_contrast = 0, 0.0
    for r in rows:
        mean = fleet[r["rung"]]
        contrast = r["total_ppm"] / mean if mean > 0 else 0.0
        if contrast > best_contrast:
            best_contrast, best_rung = contrast, r["rung"]
    return best_rung


def peak_channel(symbol: str, standoff_m: float = DESIGN_STANDOFF_M) -> int:
    """The raw-amplitude peak rung (monotone up the ladder for conductors)."""
    rows = sweep_coin(symbol, standoff_m, kappa=0.0)
    return max(rows, key=lambda r: r["total_ppm"])["rung"]


@lru_cache(maxsize=32)
def _fleet_mean_per_rung(standoff_m: float) -> Tuple[float, ...]:
    """Per-rung mean total response over all coil-signature registered metals."""
    symbols = [m.symbol for m in _metals.registry() if m.has_coil_signature]
    sums = [0.0] * 10
    for sym in symbols:
        for r in sweep_coin(sym, standoff_m, kappa=0.0):
            sums[r["rung"]] += r["total_ppm"]
    n = len(symbols) or 1
    return tuple(s / n for s in sums)


def detection_range_m(symbol: str, min_ppm: float = MIN_DETECT_PPM,
                      kappa: float = 0.0) -> Optional[float]:
    """The max standoff where the classical response still clears 3 sigma.

    The coin approaches the head from OUTSIDE the Tx face; the response
    falls with the triple mutual-inductance falloff, so the range is a
    real falloff-limited number per metal.  Bisection over t in
    [0.005, 1.5] m.  Returns 0.0 when the threshold is never cleared.
    """
    lo, hi = 0.005, 1.5
    def resp(d: float) -> float:
        best = 0.0
        for ch in channels():
            ip, q = coin_response_ppm(symbol, ch.f_hz, d)
            best = max(best, math.hypot(phi_motion(ip, kappa),
                                        phi_motion(q, kappa)))
        return best
    if resp(lo) < min_ppm:
        return 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if resp(mid) >= min_ppm:
            lo = mid
        else:
            hi = mid
    return lo


def tuning_table() -> List[dict]:
    """THE OPTIMIZED SWEEP PLAN: per metal, the best rung and max range.

    This is the 'optimize the shit out of it' output: the ladder is
    phi-spaced so every conductivity/mu_r class has a clean rung, the
    tanks are exact, and each metal is assigned its maximal-response
    channel and its declared detection range.
    """
    rows = []
    for m in _metals.registry():
        if not m.has_coil_signature:
            rows.append({"symbol": m.symbol, "rung": None,
                         "f_hz": None, "range_m": None,
                         "note": "no coil signature (conductivity not tabulated)"})
            continue
        best_rung = optimal_channel(m.symbol)
        contrast = None
        if best_rung is not None:
            fleet = _fleet_mean_per_rung(DESIGN_STANDOFF_M)
            matched = [r for r in sweep_coin(m.symbol, kappa=0.0)
                       if r["rung"] == best_rung]
            own = matched[0]
            mean = fleet[best_rung]
            contrast = own["total_ppm"] / mean if mean > 0 else 0.0
        rows.append({
            "symbol": m.symbol,
            "rung": best_rung,
            "f_hz": round(channels()[best_rung].f_hz, 3) if best_rung is not None else None,
            "contrast_at_rung": round(contrast, 3) if contrast is not None else None,
            "peak_rung": peak_channel(m.symbol),
            "range_m": detection_range_m(m.symbol),
            "winning_channel": optimal_channel_of(m.symbol),
            "ferrous": m.z in _metals.FERROUS_ZS,
        })
    return rows


def optimal_channel_of(symbol: str) -> str:
    ip_rows, q_rows = [], []
    for ch in channels():
        ip, q = coin_response_ppm(symbol, ch.f_hz)
        ip_rows.append(ip)
        q_rows.append(q)
    return "inphase" if max(ip_rows) > max(q_rows) else "quadrature"


# ---------------------------------------------------------------------------
# Deposit-sheet mode (the air's metallic aerosol, from the XRF reading)
# ---------------------------------------------------------------------------
def sheet_response_ppm(symbol: str, areal_ug_cm2: float,
                       f_hz: float = BASE_FREQUENCY,
                       standoff_m: float = DESIGN_STANDOFF_M,
                       kappa: float = KAPPA_FULL) -> dict:
    """The filter deposit's trace response for one metal.

    Areal mass (ug/cm2) -> sheet thickness t = m/rho (exact); the sheet is
    the coin physics with the deposit radius (sqrt(A/pi) from
    SHEET_AREA_CM2) and the sheet's own R/L.  The classical term is tiny
    at deposit loadings, so the declared Law-2396 reading is dominated by
    the phi-ground floor at full coupling — the FIELD-CARRIED column the
    register reports, explicitly labelled.
    """
    m = _metals.metal(symbol)
    sigma, mu_r = m.conductivity_s_m, m.rel_permeability or 1.0
    if not m.has_coil_signature or areal_ug_cm2 <= 0:
        return {"symbol": symbol, "areal_ug_cm2": areal_ug_cm2,
                "response_ppm_k0": 0.0,
                "reading_ppm_k0": 0.0,
                "reading_ppm_kappa": phi_motion(0.0, kappa),
                "mode": "field_carried_floor",
                "kappa": kappa}
    area_m2 = SHEET_AREA_CM2 * 1e-4
    r_sheet = math.sqrt(area_m2 / math.pi)
    rho = 1.0 / sigma                               # ohm m
    areal_kg_m2 = areal_ug_cm2 * 1e-5               # exact: 1 ug/cm2 = 1e-5 kg/m2
    density_kg_m3 = _elements_density(symbol)
    thickness = areal_kg_m2 / density_kg_m3 if density_kg_m3 > 0 else None
    omega = 2.0 * math.pi * float(f_hz)
    d_rx = max(abs(PAIR_SEPARATION_M - standoff_m), 1e-3)
    m_tt = mutual_coaxial(standoff_m, COIL_RADIUS_M, r_sheet, N_TX, 1)
    m_rt = mutual_coaxial(d_rx, COIL_RADIUS_M, r_sheet, N_RX, 1)
    l_sheet = MU_0 * mu_r * r_sheet * (
        math.log(8.0 * r_sheet / SHEET_WIRE_EQUIV_M) - 2.0)
    if thickness:
        delta = skin_depth_m(sigma, omega, mu_r)
        t_active = min(delta, thickness)
        r_eddy = rho * 2.0 * math.pi * r_sheet / (SHEET_BAND_W_M * t_active)
        z_sheet = complex(r_eddy, omega * l_sheet)
        v_resp = (omega ** 2) * m_tt * m_rt * DRIVE_CURRENT_A / abs(z_sheet)
    else:
        v_resp = 0.0                                # no tabulated density
    nulled = _null_v()
    k0_reading = 1e6 * v_resp / nulled              # ppm of the nulled carrier
    return {"symbol": symbol, "areal_ug_cm2": areal_ug_cm2,
            "response_ppm_k0": k0_reading,
            "reading_ppm_k0": k0_reading,
            "reading_ppm_kappa": phi_motion(k0_reading, kappa),
            "mode": ("physics_term" if k0_reading >= MIN_DETECT_PPM
                     else "field_carried_floor"),
            "kappa": kappa}


def _elements_density(symbol: str) -> float:
    """Sheet density in kg/m3 from the reference element table ([REFERENCE])."""
    from . import elements as _elements
    rho_g_cm3 = _elements.element(symbol).density
    return (rho_g_cm3 or 0.0) * 1000.0


# ---------------------------------------------------------------------------
# THE SWEEP — run the ladder against the ambient target, register everything
# ---------------------------------------------------------------------------
def sweep_deposit(areal_by_symbol: Dict[str, float],
                  kappa: float = KAPPA_FULL) -> Dict:
    """Sweep all ten rungs against the air's metallic aerosol deposit.

    Every registered metal is registered — three honest columns:
      physics_term        the metal's classical sheet response clears 3 sigma
      field_carried_floor the metal reads at the Law-2396 ground (phi^-2 ppm
                          at full coupling), with its classical term carried
                          beneath
      no_coil_signature   conductivity not tabulated: XRF-only metal

    Returns the full block for the session report, including the dominant
    classical metal (the coil's classification of the deposit) and the
    per-rung totals.
    """
    rows = sweep_table(areal_by_symbol, kappa)
    physics = [r for r in rows if r["mode"] == "physics_term"]
    dominant = (max(physics, key=lambda r: r["reading_ppm_k0"])["symbol"]
                if physics else None)
    ladder = []
    for ch in channels():
        rung_total = 0.0
        for r in rows:
            rung_total += _sheet_rung_reading(r["symbol"], ch.f_hz,
                                              areal_by_symbol.get(r["symbol"], 0.0),
                                              kappa)
        ladder.append({"rung": ch.rung, "f_hz": round(ch.f_hz, 3),
                       "deposit_total_ppm": rung_total})
    return {
        "schema": "xrf-coil/sweep-v1",
        "instrument": "code-coil (attached, phi-ladder)",
        "target": "filter deposit (air metallic aerosol), declared sheet model",
        "channels": [ch.as_dict() for ch in channels()],
        "ladder_invariant_hz": round(BASE_FREQUENCY * PHI**9, 6),
        "kappa": kappa,
        "phi_ground_ppm": PHI_SQ_INV,
        "register": rows,
        "n_registered": len(rows),
        "n_physics_term": len(physics),
        "dominant_classical_metal": dominant,
        "ladder": ladder,
        "honesty": {
            "LAW 637/638": "mutual/self inductance (corpus classical forms)",
            "LAW 801": "eddy currents + skin depth bookkeeping",
            "LAW 039/048": "Faraday/Lenz quadrature re-radiation",
            "MAGNETIZATION": "in-phase ferrous dipole channel (Fe/Co/Ni, declared M_sat)",
            "DRIVE": "I_k = I0*phi^-k is staged at the drive stage; readings are "
                     "ppm of the nulled carrier, invariant to that scaling "
                     "(signal and carrier scale together under the null)",
            "LAW 2396": "every reading carries the unit-covariant phi-ground",
            "MODEL": "coil geometry, drive current, null design point, noise floor",
            "DECLARED": "design anchor: Cu coin @ 528 Hz @ 0.10 m = 10,000 ppm",
        },
    }


def sweep_table(areal_by_symbol: Dict[str, float],
                kappa: float = KAPPA_FULL) -> List[dict]:
    """Per-metal register rows for the deposit sweep (all registered metals)."""
    rows = []
    for m in _metals.registry():
        areal = float(areal_by_symbol.get(m.symbol, 0.0) or 0.0)
        if not m.has_coil_signature:
            rows.append({"symbol": m.symbol, "z": m.z, "category": m.category,
                         "areal_ug_cm2": areal, "reading_ppm_k0": None,
                         "reading_ppm_kappa": None,
                         "mode": "no_coil_signature (XRF-only)",
                         "kappa": kappa})
            continue
        r = sheet_response_ppm(m.symbol, areal, kappa=kappa)
        r.update({"z": m.z, "category": m.category})
        rows.append(r)
    return rows


def _sheet_rung_reading(symbol: str, f_hz: float, areal_ug_cm2: float,
                        kappa: float) -> float:
    r = sheet_response_ppm(symbol, areal_ug_cm2, f_hz=f_hz, kappa=kappa)
    return r["reading_ppm_kappa"] or phi_motion(0.0, kappa)


def self_check() -> List[str]:
    problems: List[str] = []
    # ladder invariant asserted inside ladder_frequencies()
    chs = channels()
    if len(chs) != 10:
        problems.append("expected 10 ladder rungs incl. the invariant rung")
    if abs(chs[0].f_hz - BASE_FREQUENCY) > 1e-9:
        problems.append("base rung is not 528 Hz")
    if abs(chs[-1].f_hz - LADDER_INVARIANT_HZ) > 1e-3:
        problems.append("ninth rung is not the ladder invariant")
    l_tx = self_inductance()
    if not 0.01 < l_tx < 0.1:
        problems.append(f"transmit inductance implausible: {l_tx}")
    for ch in chs:
        if not ch.tank_c_farad > 0:
            problems.append(f"rung {ch.rung}: nonpositive tank capacitor")
    # degenerate identity of the reading layer (kappa -> 0 is exact)
    ip, q = coin_response_ppm("Fe", BASE_FREQUENCY)
    ip_phi0 = phi_motion(ip, 0.0)
    err = classical_limit_error(ip, ip_phi0)
    if err > 0.0:
        problems.append(f"reading layer degenerate check failed: {err}")
    ip1, q1 = coin_response_ppm_phi("Fe", BASE_FREQUENCY, kappa=1.0)
    if abs(ip1 - phi_motion(ip, 1.0)) > 1e-12:
        problems.append("phi-reading mismatch at kappa=1")
    # a still channel reads the phi-ground floor at full coupling, never zero
    floor = phi_motion(0.0, 1.0)
    if abs(floor - PHI_SQ_INV) > 1e-15:
        problems.append("still-channel floor is not phi^-2")
    # ferrous discrimination: iron carries the in-phase (magnetization) term
    rows = sweep_coin("Fe", kappa=0.0)
    if abs(rows[0]["inphase_ppm"]) <= 0:
        problems.append("iron shows no magnetization channel")
    cu_rows = sweep_coin("Cu", kappa=0.0)
    if abs(cu_rows[0]["inphase_ppm"]) != 0.0:
        problems.append("copper shows a magnetization channel (must not)")
    if cu_rows[0]["total_ppm"] <= 1.0:
        problems.append("copper design point does not read at the declared ppm")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("self_inductance :", self_inductance(), "H")
    for ch in channels():
        print(f"  rung {ch.rung}: {ch.f_hz:11.3f} Hz   C = {ch.tank_c_farad:.3e} F   "
              f"Q = {ch.q_resonance:.1f}   drive x{ch.drive_scale:.4f}")
    print("Fe sweep @10 cm (kappa=0):")
    for r in sweep_coin("Fe", kappa=0.0):
        print(f"   rung {r['rung']}: ip {r['inphase_ppm']:10.1f} ppm  "
              f"quad {r['quadrature_ppm']:10.1f} ppm  [{r['reading_mode']}]")
    print("Fe optimal rung :", optimal_channel("Fe"))
    print("Cu optimal rung :", optimal_channel("Cu"))
    print("Fe range        :", detection_range_m("Fe"), "m")
    print("Cu range        :", detection_range_m("Cu"), "m")
    print("self_check      :", self_check() or "clean")
