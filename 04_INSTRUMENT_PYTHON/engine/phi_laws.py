"""THE PHI-LAW LAYER — the instrument's declared reading convention.

HONESTY — where the phi-motion lives and where it does not
----------------------------------------------------------
The corpus's own verdict for XRF spectroscopy is Law 1347 ("X-ray
fluorescence energies equal the single-hole binding-energy differences
exactly for all couplings"), so the core physics in this package stays in
its exact classical form and phi is absent from it BY VERDICT, not by
omission (``engine/tests/test_honesty.py`` enforces this).

This module is the DECLARED phi-law layer that sits on top of that exact
spectroscopy.  It is the reading law commissioned for this instrument:

    LAW 2396 (elemental concentration):

        C_phi(kappa) = C_classical*(1 + kappa*(phi-1)) + kappa*phi^-1*C_ground

        C_ground = phi^-1 = 0.6180339887498949   (unit-covariant: it is
                 phi^-1 in the SAME unit in which the concentration is
                 declared).  The canonical declared unit for every
                 concentration this instrument reports is the mass
                 mixing ratio in ppm of air.

    degenerate proof:  lim_{kappa->0} C_phi = C_classical  (exact).
    full coupling:     C_phi(1) = phi*C_classical + phi^-2
                              = phi*C_classical + 0.3819660113 [unit].

The same motion, with the same unit-covariant ground, is the reading law
of the code coil (``engine/coil.py``): every channel of the sweep reads
its response at the declared coupling; a still-air channel reads
phi^-2 = 0.3819660113 ppm of the carrier — the corpus's "no quiet zero"
(Law 171's ground, Law 2396's floor), never a bare zero.

FIVE-STAGE form (corpus convention, ``docs/02_METHOD.md``):

    1. DIAGNOSIS   the hidden zero is "no element / no response" (C = 0).
    2. PHI-MOTION  x_phi(kappa) = x*(1 + kappa*(phi-1)) + kappa*phi^-1*x_ground.
    3. DEGENERATE  lim_{kappa->0} x_phi = x  (the classical reading is the
                   floorless limit; static theory is this law, coupling off).
    4. SIMULATION  validated by the LawSim harness in the corpus
                   (``sim/2396_elemental_concentration.py``,
                   ``sim/2397_ladder_coil.py``; status SIMULATED,
                   classical_limit_error <= 0.01, exact 0 here).
    5. PREDICTION  instrument-visible at full coupling; the declared
                   experiment's kappa->0 reading is the floorless limit
                   (Law 173), and the kappa=1 reading is the phi-motion.

The 528 Hz ladder (Law 2394/2395 family) is this instrument's frequency
geometry: f_n = f0 * phi^n with f0 = 528.0 Hz.  The ladder invariant is
528 * phi^9 = 40134.946166 Hz — the ninth rung — and the sum of the
infinite phi-ladder is phi^2 = 2.618033988749895 (em-feild/phi_coil.py).

Everything here is integer-free arithmetic over [EXACT] constants; there
is no clock read, no unseeded RNG, no network — the honesty guards hold.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# The corpus constants (exactly as carried in the corpus and em-feild)
# ---------------------------------------------------------------------------
PHI = (1.0 + math.sqrt(5.0)) / 2.0              # 1.618033988749895
PHI_INV = PHI - 1.0                             # 0.6180339887498949
PHI_SQ = PHI * PHI                              # 2.618033988749895
PHI_SQ_INV = PHI_INV * PHI_INV                  # the phi-ground at kappa=1: 0.3819660113 (repr …1052, within 1 ulp)
C_EMERGENCE = 0.563263                          # Law 183 emergence threshold (metadata)

#: The coil-law SI constant (also in em-feild/phi_constants.py, same value).
MU_0 = 4.0e-7 * math.pi                         # 1.2566370614e-6 H/m

#: The 528 Hz ladder anchor and its ninth-rung invariant (Law 2394/2395).
BASE_FREQUENCY = 528.0
LADDER_INVARIANT_HZ = BASE_FREQUENCY * PHI**9   # 40134.946166 Hz

#: Declared canonical coupling for readings (the gold-reading convention).
#: kappa = 1.0 is "full coupling"; kappa = 0.0 is the floorless static limit.
KAPPA_FULL = 1.0

#: The LawSim classical-limit tolerance (corpus harness protocol).
CLASSICAL_LIMIT_TOL = 0.01

RHO_AIR_KG_M3 = 1.2041                          # 20 degC, 101.325 kPa [EXACT PHYSICS]
AIR_UG_PER_M3 = RHO_AIR_KG_M3 * 1e9             # 1.2041e9 ug/m3


def ladder_frequencies(f0: float = BASE_FREQUENCY, n: int = 10,
                       include_invariant: bool = True) -> list[float]:
    """The ladder f_k = f0 * phi^k: ten rungs, nine phi-intervals.

    With the 528 Hz anchor the last rung is exactly the tenth rung, the
    ladder invariant 528*phi^9 = 40134.946166 Hz.
    """
    freqs = [f0 * PHI**k for k in range(n)]
    if include_invariant:
        last = f0 * PHI**(n - 1)
        dev = abs(last - LADDER_INVARIANT_HZ)
        if dev > 1e-3:
            raise AssertionError(
                f"ladder invariant violated: {last!r} vs {LADDER_INVARIANT_HZ} (dev {dev})")
    return freqs


def phi_motion(x: float, kappa: float, ground: float | None = PHI_INV) -> float:
    """The corpus's five-stage phi-motion (Law 2396 / Law 1160 form).

    x_phi(kappa) = x*(1 + kappa*(phi-1)) + kappa*phi^-1*ground.

    ``ground`` is unit-covariant: pass it in the SAME unit as ``x``.  The
    corpus convention (Law 1160's ground rule) is ground = phi^-1.
    """
    g = PHI_INV if ground is None else float(ground)
    return float(x) * (1.0 + float(kappa) * PHI_INV) + float(kappa) * PHI_INV * g


def concentration_phi(ppm: float, kappa: float = KAPPA_FULL,
                      ground: float | None = PHI_INV) -> float:
    """Law 2396: the elemental concentration read at the declared coupling.

    Canonical declared unit: mass mixing ratio in ppm of air.  At
    kappa = 1 this is phi*C_classical + phi^-2 (the coherence floor).
    """
    return phi_motion(ppm, kappa, ground)


def coil_response_phi(response_ppm: float, kappa: float = KAPPA_FULL) -> float:
    """Law 2396's motion applied to a code-coil channel response.

    Unit: ppm of the nulled carrier.  The still-air channel reads
    kappa*phi^-2 at declared coupling — never zero (Law 171).
    """
    return phi_motion(response_ppm, kappa, PHI_INV)


def classical_limit_error(x_classical: float, x_phi_at_zero: float,
                          scale: float | None = None) -> float:
    """The LawSim harness's degenerate gate: |phi(0) - classical| / |classical|.

    The five-stage law is SIMULATED iff this is <= ``CLASSICAL_LIMIT_TOL``;
    for the exact arithmetic used here it is identically 0.0.
    """
    denom = abs(float(x_classical)) if scale is None else abs(float(scale))
    if denom == 0.0:
        return 0.0 if float(x_phi_at_zero) == 0.0 else float("inf")
    return abs(float(x_phi_at_zero) - float(x_classical)) / denom


# ---------------------------------------------------------------------------
# Unit discipline: the canonical ppm chain
# ---------------------------------------------------------------------------
def ug_m3_to_ppm(c_ug_m3: float,
                 air_ug_per_m3: float = AIR_UG_PER_M3) -> float:
    """Mass mixing ratio in ppm of air: ppm = c/(rho_air)... exactly."""
    return float(c_ug_m3) * 1e6 / float(air_ug_per_m3)


def ppm_to_ug_m3(ppm: float,
                 air_ug_per_m3: float = AIR_UG_PER_M3) -> float:
    """The exact inverse of :func:`ug_m3_to_ppm`."""
    return float(ppm) * float(air_ug_per_m3) / 1e6


def ppm_of(ppm_value: float, kappa: float = KAPPA_FULL) -> dict:
    """The Law-2396 reading block for one concentration, run-exact fields."""
    base = float(ppm_value)
    return {
        "kappa": float(kappa),
        "c_k0_ppm": base,
        "ground_ppm": PHI_INV,
        "c_phi_ppm": concentration_phi(base, kappa),
        "law": "PHI-2396",
        "degenerate": "lim_{kappa->0} = C_classical (exact)",
    }


def self_check() -> list[str]:
    problems = []
    if abs(LADDER_INVARIANT_HZ - 40134.946166) > 1e-4:
        problems.append("ladder invariant drifted: %.6f" % LADDER_INVARIANT_HZ)
    if abs(PHI_INV - 0.6180339887498949) > 1e-15:
        problems.append("phi^-1 drifted")
    if abs(PHI_SQ_INV - 0.3819660112501051) > 1e-15:
        problems.append("phi^-2 drifted")
    # degenerate identity: kappa = 0 must return the classical value exactly
    for x in (0.0, 1.0, 2.4455e-12, 459.9):
        err = classical_limit_error(x, phi_motion(x, 0.0))
        if err != 0.0:
            problems.append(f"degenerate identity fails at x={x!r}")
    # monotonicity of the phi-motion in kappa
    if not (concentration_phi(0.0, 0.0) <= concentration_phi(0.0, 0.5)
            <= concentration_phi(0.0, 1.0)):
        problems.append("phi-ground floor not monotone in kappa")
    if abs(concentration_phi(0.0, 1.0) - PHI_SQ_INV) > 1e-15:
        problems.append("kappa=1 floor is not phi^-2")
    # unit-chain round trip
    if abs(ppm_to_ug_m3(ug_m3_to_ppm(1.234)) - 1.234) > 1e-12:
        problems.append("ppm/ug-m3 chain does not round-trip")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("PHI          :", PHI)
    print("phi^-1       :", PHI_INV)
    print("phi^-2       :", PHI_SQ_INV)
    print("ladder (9)   :", [round(f, 3) for f in ladder_frequencies()])
    print("invariant    : %.6f Hz" % LADDER_INVARIANT_HZ)
    print("sum phi^-k   : %.15f  (phi^2 = %.15f)" % (sum(PHI_INV**k for k in range(64)), PHI_SQ))
    print("self_check   :", self_check() or "clean")
