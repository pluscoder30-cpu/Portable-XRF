"""Legacy alias for :mod:`engine.forward_response`.

The module was renamed on 2026-11-09: it is the instrument's own forward
response (the code antenna's declared transduction), not a simulation
harness.  The alias keeps older imports (``from engine import simulate``)
working; new code should import ``engine.forward_response``.
"""
from __future__ import annotations

from .forward_response import *  # noqa: F401,F403
from .forward_response import main

if __name__ == "__main__":  # pragma: no cover
    main()
