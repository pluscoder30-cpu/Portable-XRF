"""Code-based XRF sniffer — read an air sample's minerals from an XRF spectrum.

The package has five pieces:

* :mod:`sniffer.spectrum` — the spectrum type, strict validation, I/O.
* :mod:`sniffer.sniffer`  — the decoder: background, peaks, line ID, NNLS,
  detection limits, element -> mineral apportionment.
* :mod:`sniffer.air`      — filter-sample PM loading and public air-quality
  feeds (cache + offline fallback).
* :mod:`sniffer.receipt`  — canonical JSON + model provenance + hash chain +
  ECDSA P-256 from the field trust root (or a labelled SHA-256 fallback).
* :mod:`sniffer.cli`      — ``python -m sniffer ...``.

Honest framing: the **decoder** is real code and real XRF analysis.  The
**X-ray transduction** (source + detector) is a model.  The sniffer does not
generate or detect X-rays; it decodes a spectrum that exists, and every report
says whether that spectrum is measured, instrument-forward, or feed-derived.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Make the sibling ``engine`` package importable when the sniffer is run from
# outside the XRF directory (e.g. ``python -m sniffer`` from a worktree).
_ROOT = _Path(__file__).resolve().parent.parent
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))

from .spectrum import (Spectrum, SpectrumValidationError, ValidationResult,
                       load_spectrum, save_spectrum)
from .sniffer import (Report, SniffError, default_elements, resolve_detector,
                      sniff, sniff_file)
from .air import AirReading, air_from_feed, air_from_spectrum
from .receipt import (GENESIS_HASH, ReceiptChain, Signer, find_trust_keys,
                      seal, trust_root_available, verify_chain, verify_receipt)
from .selfcheck import run_selfcheck

__version__ = "1.1.0"

__all__ = [
    "Spectrum", "SpectrumValidationError", "ValidationResult",
    "load_spectrum", "save_spectrum",
    "Report", "SniffError", "default_elements", "resolve_detector",
    "sniff", "sniff_file",
    "AirReading", "air_from_feed", "air_from_spectrum",
    "GENESIS_HASH", "ReceiptChain", "Signer", "find_trust_keys",
    "seal", "trust_root_available", "verify_chain", "verify_receipt",
    "run_selfcheck", "__version__",
]
