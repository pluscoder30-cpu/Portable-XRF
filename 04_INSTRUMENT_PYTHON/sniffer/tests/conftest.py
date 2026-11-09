"""Test path bootstrap: make ``engine`` and ``sniffer`` importable."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # .../XRF
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
