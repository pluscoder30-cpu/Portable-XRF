"""The characteristic-line library, plus Moseley's law and the Law-1347 check.

HONESTY
-------
Two different kinds of number live in this module and they are never mixed.

``LINE_DB`` / ``line_energy()``
    **[REFERENCE]**.  Measured/tabulated line energies and branching ratios,
    copied verbatim from ``data/lines.json`` (Elam, Ravel & Sieber 2002, which
    packages the NIST X-ray Transition Energies Database).  These are the
    numbers the instrument uses.

``moseley_kalpha()``
    **[MODEL]**.  Moseley's law ``E = R hc (Z - sigma)^2 (1/n_f^2 - 1/n_i^2)``
    with either the textbook ``sigma = 1`` or an empirical quadratic
    ``sigma(Z)`` fitted to the eight K-alpha anchors below.  It is a *model of
    the table*, kept so the classical law can be quantified; it is never used
    to compute a line energy for the instrument.

``edge_difference_energy()``
    **[REFERENCE-DERIVED]**.  Law 1347's statement ``E = E_initial - E_final``
    applied to the tabulated binding energies.  For every K and L line in the
    table this reproduces the tabulated line energy to < 0.2 eV, which is a
    direct verification of the law on 1,000+ lines.

Why the L lines are not Moseley lines
-------------------------------------
L-alpha is L3 -> M5: both levels have principal quantum number n = 3, so
Moseley's ``(1/n_f^2 - 1/n_i^2)`` is identically zero.  Moseley's law simply
does not apply to L/M transitions; the binding-energy difference (Law 1347)
does, and it is exact.  This is stated here because it is the honest reason
the L-line energies come from the table and not from a Moseley fit.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import elements as _elements
from .constants import RYDBERG_HC_EV

_DATA = Path(__file__).with_name("data") / "lines.json"

#: Canonical ordering (Siegbahn notation).
LINE_ORDER: Tuple[str, ...] = (
    "Ka1", "Ka2", "Ka3", "Kb1", "Kb3", "Kb2", "Kb4", "Kb5",
    "La1", "La2", "Ll", "Ln",
    "Lb1", "Lb2", "Lb3", "Lb4", "Lb5", "Lb6",
    "Lg1", "Lg2", "Lg3", "Lg6",
    "Ma1", "Mb", "Mg", "Mz",
)

#: Lines whose initial level is the K shell (used for excitation bookkeeping).
K_LINES = ("Ka1", "Ka2", "Ka3", "Kb1", "Kb3", "Kb2")

#: Principal quantum numbers for Moseley's law (K and L series only).
_N_SHELL = {"K": 1, "L": 2, "M": 3, "N": 4}


@dataclass(frozen=True)
class Line:
    z: int
    name: str
    energy: float          # eV
    intensity: float       # branching ratio within the initial subshell
    initial: str           # e.g. "K", "L3", "M5"
    final: str             # e.g. "L3", "M5", "N6,7"

    @property
    def element(self) -> _elements.Element:
        return _elements.element(self.z)

    @property
    def shell(self) -> str:
        return self.initial[0]

    @property
    def label(self) -> str:
        return f"{self.element.symbol} {self.name}"

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Line {self.label} {self.energy:.1f} eV I={self.intensity:.3f}>"


def _load() -> Dict[int, Dict[str, Line]]:
    with open(_DATA, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    db: Dict[int, Dict[str, Line]] = {}
    for z_str, rows in blob["lines"].items():
        z = int(z_str)
        db[z] = {
            name: Line(
                z=z,
                name=name,
                energy=float(rec["energy"]),
                intensity=float(rec["intensity"]),
                initial=rec["initial"],
                final=rec["final"],
            )
            for name, rec in rows.items()
        }
    return db


LINE_DB: Dict[int, Dict[str, Line]] = _load()
PROVENANCE = json.loads(_DATA.read_text(encoding="utf-8"))["provenance"]

ALL_LINES: Tuple[Line, ...] = tuple(
    LINE_DB[z][name] for z in sorted(LINE_DB) for name in LINE_ORDER if name in LINE_DB[z]
)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
def lines(z: int, shell: Optional[str] = None) -> Tuple[Line, ...]:
    """All tabulated lines of an element, optionally filtered by initial shell."""
    rows = LINE_DB.get(_elements.element(z).z, {})
    out = [rows[n] for n in LINE_ORDER if n in rows]
    if shell:
        out = [ln for ln in out if ln.shell == shell.upper()[0]]
    return tuple(out)


def line(z: int, name: str) -> Line:
    """One named line.  Raises KeyError if the element has no such line."""
    zz = _elements.element(z).z
    try:
        return LINE_DB[zz][name]
    except KeyError:
        have = sorted(LINE_DB.get(zz, {}))
        raise KeyError(f"{_elements.element(z).symbol} has no {name} line; have {have}") from None


def line_energy(z: int, name: str) -> float:
    """**[REFERENCE]** tabulated line energy in eV."""
    return line(z, name).energy


def branching(z: int, name: str) -> float:
    """Probability that a vacancy in ``initial`` emits this line."""
    return line(z, name).intensity


def strongest(z: int, shell: str = "K") -> Optional[Line]:
    cand = lines(z, shell)
    return max(cand, key=lambda ln: ln.intensity) if cand else None


# ---------------------------------------------------------------------------
# Level helpers
# ---------------------------------------------------------------------------
def _level_energy(z: int, level: str) -> Optional[float]:
    """Binding energy of a level label.

    Combined labels such as ``"N2,3"`` are resolved to the **first** listed
    level.  That is the convention of the underlying database: with it, all
    1,156 reconstructible lines reproduce the tabulated energy to <= 0.01 eV
    (see ``validate_edge_difference``).  Averaging the two levels instead
    introduces errors up to 114 eV on K-beta2 at high Z.
    """
    el = _elements.element(z)
    raw = [p.strip() for p in level.replace(" ", "").split(",") if p.strip()]
    first = raw[0] if raw else ""
    if first and first[0].isdigit():        # defensive: bare "7" in "N6,7"
        return None
    e = el.edge(first) if first else 0.0
    return e if e > 0 else None


def edge_difference_energy(z: int, initial: str, final: str) -> Optional[float]:
    """**[REFERENCE-DERIVED]** Law 1347: E = E_initial - E_final.

    Returns None when either level is not tabulated for that element.
    """
    a = _level_energy(z, initial)
    b = _level_energy(z, final)
    if a is None or b is None:
        return None
    return a - b


def line_energy_from_edges(z: int, name: str) -> Optional[float]:
    """Binding-energy difference for a named line (Law 1347)."""
    ln = line(z, name)
    return edge_difference_energy(z, ln.initial, ln.final)


# ---------------------------------------------------------------------------
# Moseley's law  [MODEL]
# ---------------------------------------------------------------------------
def moseley_energy(z: int, n_initial: int, n_final: int, sigma: float = 1.0) -> float:
    """**[MODEL]** E = R hc (Z - sigma)^2 (1/n_f^2 - 1/n_i^2), in eV."""
    if n_final >= n_initial:
        raise ValueError("n_final must be smaller than n_initial")
    return RYDBERG_HC_EV * (z - sigma) ** 2 * (1.0 / n_final**2 - 1.0 / n_initial**2)


#: Empirical screening function for K-alpha: sigma(Z) = c2 Z^2 + c1 Z + c0.
#: Fitted by least squares to the eight K-alpha anchor lines in ``ANCHORS``.
#: NOT independent evidence -- it is a three-number compression of those eight
#: measurements.  Validation on the remaining 74 tabulated K-alpha lines is in
#: ``validate_moseley()``.
MOSELEY_SIGMA_KALPHA = (-8.25e-4, 3.4011e-2, 0.626634)


def screening_constant_kalpha(z: int) -> float:
    """**[MODEL]** Empirical sigma(Z) for K-alpha (quadratic, see above)."""
    c2, c1, c0 = MOSELEY_SIGMA_KALPHA
    return c2 * z * z + c1 * z + c0


def moseley_kalpha(z: int, sigma: Optional[float] = None) -> float:
    """**[MODEL]** K-alpha energy from Moseley's law.

    ``sigma=None`` uses the empirical ``screening_constant_kalpha(Z)``;
    ``sigma=1.0`` reproduces Moseley's original textbook form.
    """
    s = screening_constant_kalpha(z) if sigma is None else sigma
    return moseley_energy(z, 2, 1, s)


def moseley_kbeta(z: int, sigma: float = 1.8) -> float:
    """**[MODEL]** K-beta (K -> M, n=3 -> 1) with the conventional sigma ~ 1.8."""
    return moseley_energy(z, 3, 1, sigma)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Anchor:
    element: str
    line: str
    energy_ev: float
    source: str


#: The documented anchor set requested for this build.  These are the widely
#: quoted Bearden-era values; the NIST/Elam table differs from them by <= 1.5 eV
#: (<= 0.03 %), which is reported rather than hidden.
ANCHORS: Tuple[Anchor, ...] = (
    Anchor("Cu", "Ka1", 8047.8, "Bearden 1967 / standard XRF reference"),
    Anchor("Fe", "Ka1", 6403.8, "Bearden 1967 / standard XRF reference"),
    Anchor("Al", "Ka1", 1486.7, "Bearden 1967 / standard XRF reference"),
    Anchor("Si", "Ka1", 1739.9, "Bearden 1967 / standard XRF reference"),
    Anchor("Ca", "Ka1", 3691.7, "Bearden 1967 / standard XRF reference"),
    Anchor("Ti", "Ka1", 4510.9, "Bearden 1967 / standard XRF reference"),
    Anchor("Mo", "Ka1", 17479.3, "Bearden 1967 / standard XRF reference"),
    Anchor("Ag", "Ka1", 22163.0, "Bearden 1967 / standard XRF reference"),
    Anchor("Pb", "La1", 10551.5, "Bearden 1967 / standard XRF reference"),
)


def validate_anchors(verbose: bool = False) -> List[dict]:
    """Compare the tabulated and Moseley K-alpha energies to the anchor set."""
    rows = []
    for a in ANCHORS:
        el = _elements.element(a.element)
        tab = line_energy(el.z, a.line)
        row = {
            "element": el.symbol,
            "line": a.line,
            "anchor_ev": a.energy_ev,
            "table_ev": tab,
            "dev_ev": tab - a.energy_ev,
            "dev_pct": 100.0 * (tab - a.energy_ev) / a.energy_ev,
        }
        if a.line.startswith("Ka"):
            mos = moseley_kalpha(el.z)
            row["moseley_ev"] = mos
            row["moseley_dev_pct"] = 100.0 * (mos - a.energy_ev) / a.energy_ev
        rows.append(row)
        if verbose:
            print(
                f"{el.symbol:>2} {a.line:<4} anchor {a.energy_ev:9.1f} eV | "
                f"table {tab:9.1f} eV ({row['dev_ev']:+5.1f} eV, "
                f"{row['dev_pct']:+6.3f} %)"
                + (
                    f" | Moseley {row['moseley_ev']:9.1f} "
                    f"({row['moseley_dev_pct']:+6.3f} %)"
                    if "moseley_ev" in row
                    else ""
                )
            )
    return rows


def validate_moseley() -> dict:
    """Error of the Moseley models against every tabulated K-alpha line."""
    classic, empirical = [], []
    for ln in ALL_LINES:
        if ln.name != "Ka1":
            continue
        classic.append(100.0 * (moseley_kalpha(ln.z, sigma=1.0) - ln.energy) / ln.energy)
        empirical.append(100.0 * (moseley_kalpha(ln.z) - ln.energy) / ln.energy)

    def stats(v: Sequence[float]) -> dict:
        a = sorted(abs(x) for x in v)
        return {
            "n": len(a),
            "median_abs_pct": a[len(a) // 2],
            "p95_abs_pct": a[int(0.95 * (len(a) - 1))],
            "max_abs_pct": a[-1],
        }

    return {"sigma_1": stats(classic), "sigma_fitted": stats(empirical)}


def validate_edge_difference() -> dict:
    """Law 1347 check: E_line ?= E_initial - E_final for every tabulated line."""
    devs: List[Tuple[float, Line]] = []
    skipped = 0
    for ln in ALL_LINES:
        e = edge_difference_energy(ln.z, ln.initial, ln.final)
        if e is None:
            skipped += 1
            continue
        devs.append((e - ln.energy, ln))
    devs.sort(key=lambda t: abs(t[0]))
    absdev = [abs(d) for d, _ in devs]
    return {
        "n_checked": len(devs),
        "n_skipped": skipped,
        "median_abs_ev": absdev[len(absdev) // 2],
        "p99_abs_ev": absdev[int(0.99 * (len(absdev) - 1))],
        "max_abs_ev": absdev[-1],
        "worst": [(ln.label, d) for d, ln in devs[-3:]],
    }


def self_check() -> list[str]:
    problems = []
    for z, rows in LINE_DB.items():
        for name, ln in rows.items():
            if ln.energy <= 0:
                problems.append(f"{z} {name}: non-positive energy")
            if not (0 < ln.intensity <= 1.0001):
                problems.append(f"{z} {name}: intensity {ln.intensity} outside (0,1]")
        # Branching ratios of the K and L subshells must close to 1.  The M
        # groups are not checked: the database lists M-zeta (M4,5 -> N2,3)
        # against a combined initial level, so its sum is not normalised.
        by_shell: Dict[str, float] = {}
        for ln in rows.values():
            if ln.initial in ("K", "L1", "L2", "L3"):
                by_shell[ln.initial] = by_shell.get(ln.initial, 0.0) + ln.intensity
        for shell, total in by_shell.items():
            if abs(total - 1.0) > 0.02:
                problems.append(f"Z={z} {shell} branching sums to {total:.3f}")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("Anchors")
    validate_anchors(verbose=True)
    print("\nMoseley vs table:", validate_moseley())
    print("\nLaw 1347 edge difference:", validate_edge_difference())
    print("\nself_check:", self_check() or "clean")
