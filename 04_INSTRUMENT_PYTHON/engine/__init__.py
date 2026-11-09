"""XRF physics engine — classical spectroscopy, honestly labelled.

The instrument chain implemented here:

    excitation -> photoionisation -> K/L vacancy -> radiative (XRF) or Auger
    -> characteristic line -> Beer-Lambert transport through air/matrix
    -> detector response -> spectrum -> inverse operator -> element areal
    densities -> mineral apportionment

Every module states at the top what is **[REFERENCE]** (measured/tabulated
data) and what is **[MODEL]** (a closed-form approximation with a stated,
measured error).

Where the phi-laws live
-----------------------
The corpus's verdict for the spectroscopy itself is Law 1347 ("X-ray
fluorescence energies equal the single-hole binding-energy differences
exactly for all couplings"): the core modules below carry no phi and are
guarded by ``tests/test_honesty.py``.  The DECLARED phi-law layer — the
instrument's reading convention commissioned for it — lives in three
modules:

    phi_laws  the five-stage reading law (LAW 2396, unit-covariant
              phi-ground; the 528 Hz ladder and its invariant rung).
    metals    the metal registry (everything this instrument can read).
    coil      THE CODE COIL — the metal-detector head attached to the
              instrument, built on the em-feild/phi_coil ladder drive.
    audit     THE PER-ELEMENT LAW AUDITOR — every metal certified, by
              hand-recomputation, against Laws 1344/1345/1347/2396/2397:
              gold parity (floor == 0.3819660113 ppm for EVERY element),
              binding identities, yields, unit covariance, coil plan.
"""
import importlib
from typing import Any

__version__ = "1.2.0"

_MODULES = (
    "air", "audit", "attenuation", "coil", "constants", "cross_section",
    "detector", "detector_artifacts", "elements", "floor_register", "forward",
    "forward_response", "inversion", "linalg", "lines", "metals", "phi_laws",
    "simulate", "validate", "xrf_vendor", "yields",
)

__all__ = list(_MODULES)


def __getattr__(name: str) -> Any:  # lazy so that submodules never cycle
    if name in _MODULES:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals()) + list(_MODULES))
