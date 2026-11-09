"""Physical constants and the corpus's trust-layer metadata.

HONESTY
-------
Two disjoint groups of numbers live here.

1. ``PHYSICAL`` constants (CODATA 2018) are exact-by-definition or measured to
   better than 1e-9 relative.  They are used by the spectroscopy.

2. ``CORPUS`` constants (phi, C_crit, the 528 Hz ladder) are carried **only as
   provenance metadata**.  They are NOT used in any spectroscopy calculation.

   The reason is documented in ``READING/02_THE_LAWS_FOR_XRF.md``: of the
   corpus's 2,395 laws, 2,395 assert the classical result and ZERO assert an
   observed phi-detection.  Law 1347's own verdict line is
   "X-ray fluorescence energies equal the single-hole binding-energy
   differences exactly for all couplings."  Law 1344's is
   "K-alpha frequencies equal (3/4) c R (Z - 1)^2 exactly for all couplings."

   Therefore this engine implements the classical physics and records the
   phi-constants as identity metadata, never as a correction term.
   ``SPECTROSCOPY_USES_PHI`` is False and there is no code path that changes a
   line energy, yield, cross-section or attenuation by a phi factor.
"""
from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# 1. PHYSICAL CONSTANTS  [REFERENCE] CODATA 2018
# --------------------------------------------------------------------------
PLANCK_EV_S = 4.135667696e-15          # h, eV*s
PLANCK_J_S = 6.62607015e-34            # h, J*s (exact)
SPEED_OF_LIGHT_CM_S = 2.99792458e10    # c, cm/s (exact)
ELEMENTARY_CHARGE_C = 1.602176634e-19  # e, C (exact)
ELECTRON_MASS_KG = 9.1093837015e-31
CLASSICAL_ELECTRON_RADIUS_CM = 2.8179403262e-13
AVOGADRO = 6.02214076e23               # 1/mol (exact)
RYDBERG_HC_EV = 13.605693122994        # R_inf * h * c, eV
HC_EV_ANGSTROM = 12398.419843320026    # h*c, eV*Angstrom
BOLTZMANN_EV_K = 8.617333262e-5        # k_B, eV/K
AMU_KG = 1.66053906660e-27

# Silicon detector material constants (used by detector.py)
SI_DENSITY_G_CM3 = 2.3290
SI_BANDGAP_EV = 1.12
SI_EHP_EV = 3.62                       # mean electron-hole pair energy, eV
SI_FANO = 0.115                        # Fano factor
SI_KALPHA_EV = 1739.98                 # Si K-alpha1 (escape peak reference)

# --------------------------------------------------------------------------
# 2. CORPUS / TRUST-LAYER METADATA  [PROVENANCE ONLY — NOT USED IN PHYSICS]
# --------------------------------------------------------------------------
PHI = 1.6180339887498949
PHI_INV = 0.6180339887498949
C_CRIT = 0.563263                      # corpus emergence threshold
F_BASE_HZ = 528.0
LADDER_INVARIANT_HZ = 528.0 * PHI**9   # 40134.946166 Hz
CARRIER_DIM = 816

#: Guard flag.  If anybody ever adds a phi-term to the physics, this must be
#: flipped *and* the corpus's own verdict lines must be overturned by
#: measurement.  As of the 2,395-law validation, they are not.
SPECTROSCOPY_USES_PHI = False


@dataclass(frozen=True)
class Provenance:
    """Machine-readable statement of what a number is."""

    kind: str          # "REFERENCE" | "MODEL" | "EST" | "DERIVED"
    source: str
    accuracy: str = ""

    def label(self) -> str:
        return f"[{self.kind}] {self.source}" + (
            f" (accuracy: {self.accuracy})" if self.accuracy else ""
        )


REFERENCE_DATA = Provenance(
    "REFERENCE",
    "Elam, Ravel & Sieber, Rad. Phys. Chem. 63 (2002) 121, via xraydb 4.5.8; "
    "built on the NIST X-ray Transition Energies Database and "
    "Krause & Oliver, J. Phys. Chem. Ref. Data 8 (1979) 329",
    "line energies <= 1.5 eV from the Bearden/NIST anchors (<= 0.03 %)",
)

NIST_AIR = Provenance(
    "REFERENCE",
    "NIST X-Ray Mass Attenuation Coefficients, air, dry (near sea level), "
    "table 4 (ComTab/air.html)",
    "tabulated to 3 significant figures",
)
