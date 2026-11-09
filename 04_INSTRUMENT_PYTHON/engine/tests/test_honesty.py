"""Honesty / determinism guards.

These tests encode the project's two non-negotiable rules:

1. The spectroscopy is classical.  The corpus's own validation (all 2,395
   laws) asserts the classical result and zero laws assert a phi-detection,
   so no physics module may import or apply a phi constant.

2. Determinism.  No ``hash()`` on strings, no clock reads, no unseeded RNG in
   anything that produces a number.
"""
import inspect
import pathlib
import re

import pytest

from engine import constants

PHYSICS_MODULES = [
    "elements", "lines", "yields", "cross_section", "attenuation",
    "air", "detector", "forward", "inversion", "minerals", "simulate",
]


def _source(module_name: str) -> str:
    import importlib
    mod = importlib.import_module(f"engine.{module_name}")
    return inspect.getsource(mod)


def test_no_phi_in_physics():
    """No physics module may reference the corpus's phi constants."""
    offenders = []
    for name in PHYSICS_MODULES:
        src = _source(name)
        # strip docstrings/comments by looking only at code lines
        for line in src.splitlines():
            code = line.split("#", 1)[0]
            if re.search(r"\b(PHI|PHI_INV|C_CRIT|LADDER_INVARIANT)\b", code):
                offenders.append((name, line.strip()))
    print("phi references in physics code:", offenders or "none")
    assert offenders == []
    assert constants.SPECTROSCOPY_USES_PHI is False


def test_constants_are_carried_as_metadata_only():
    assert constants.PHI == pytest.approx(1.618033988749895)
    assert constants.C_CRIT == pytest.approx(0.563263)
    print(f"corpus metadata: phi={constants.PHI}, C_crit={constants.C_CRIT}, "
          f"ladder={constants.LADDER_INVARIANT_HZ:.3f} Hz, "
          f"used_in_spectroscopy={constants.SPECTROSCOPY_USES_PHI}")


def test_no_string_hash():
    """AST-level check: no ``hash(...)`` call anywhere in the engine."""
    import ast
    import importlib
    offenders = []
    for name in PHYSICS_MODULES + ["linalg"]:
        mod = importlib.import_module(f"engine.{name}")
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "hash"):
                offenders.append((name, node.lineno))
    print("hash() calls:", offenders or "none")
    assert offenders == []


def test_no_global_rng():
    offenders = []
    for name in PHYSICS_MODULES:
        src = _source(name)
        for line in src.splitlines():
            if re.search(r"np\.random\.(rand|randn|random|choice)\s*\(", line):
                offenders.append((name, line.strip()))
    print("unseeded RNG calls:", offenders or "none")
    assert offenders == []


def test_engine_has_no_network_imports():
    banned = ("requests", "urllib", "http.client", "socket", "aiohttp")
    offenders = []
    for name in PHYSICS_MODULES + ["linalg", "constants"]:
        src = _source(name)
        for line in src.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for b in banned:
                    if b in line:
                        offenders.append((name, line.strip()))
    print("network imports:", offenders or "none")
    assert offenders == []


def test_no_time_reads():
    offenders = []
    for name in PHYSICS_MODULES:
        src = _source(name)
        for line in src.splitlines():
            if re.search(r"\b(time\.time|datetime\.now|perf_counter)\b", line):
                offenders.append((name, line.strip()))
    print("clock reads:", offenders or "none")
    assert offenders == []


def test_reference_data_files_exist():
    root = pathlib.Path(__file__).resolve().parents[1] / "data"
    for f in ("elements.json", "lines.json", "mu_rho.npz"):
        assert (root / f).exists(), f
        print(f"{f}: {(root / f).stat().st_size:,} bytes")
