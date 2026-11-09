"""The element table, Z = 1..92.

HONESTY
-------
Everything in this module is **[REFERENCE] measured/tabulated data**, not a
model.  Source: ``xraydb`` 4.5.8, which packages

  * Elam, Ravel & Sieber, Rad. Phys. Chem. 63 (2002) 121  (edge energies),
  * the NIST X-ray Transition Energies Database,
  * Krause & Oliver, J. Phys. Chem. Ref. Data 8 (1979) 329  (fluorescence
    yields and edge jump ratios).

The numbers were copied verbatim by ``tools/build_reference_data.py``; nothing
here is re-fitted.  The engine reads ``data/elements.json`` and has no runtime
dependency on xraydb.

Fields
------
``mass``      atomic weight in u (standard atomic weight, IUPAC).
``density``   g/cm^3.  For gases this is the STP (0 degC, 101.325 kPa) value,
              NOT the density at lab temperature; use ``air.air_density`` for
              that.
``edges``     binding energy in eV for K, L1, L2, L3, M5.  ``0.0`` means the
              shell does not exist for that Z (e.g. H has no L shell).
``edge_jump`` mu_above/mu_below at the edge (dimensionless).  NOTE: the jump
              ratio column and the Elam mu table disagree by a few percent at
              some edges; the jump ratio is used only for the K-shell fraction
              of photoabsorption, where a few percent is inside the model error.
``fyield``    fluorescence yield of that subshell (Krause & Oliver 1979).

Caveat on ``M5``: for the 3d metals (Z = 22..29) the tabulated M4/M5 values
collapse to ~2-5 eV (the 3d band edge) and are placeholders, not usable
binding energies.  M-line XRF is only meaningful for Z > ~40, where the values
are real.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Mapping, Union

_DATA = Path(__file__).with_name("data") / "elements.json"

EDGE_NAMES = (
    "K", "L1", "L2", "L3",
    "M1", "M2", "M3", "M4", "M5",
    "N1", "N2", "N3", "N4", "N5", "N6", "N7",
    "O1", "O2", "O3", "O4", "O5",
    "P1", "P2", "P3",
)
#: Binding energies decrease along this sequence (K > L1 > ... > N7).
EDGE_SEQUENCE = EDGE_NAMES

ElementLike = Union[int, str, "Element"]


@dataclass(frozen=True)
class Element:
    z: int
    symbol: str
    name: str
    mass: float
    density: float
    edges: Mapping[str, float]
    edge_jump: Mapping[str, float]
    fyield: Mapping[str, float]

    # -- convenience ------------------------------------------------------
    def edge(self, name: str = "K") -> float:
        """Binding energy of ``name`` in eV.  0.0 if the shell does not exist."""
        try:
            return float(self.edges[name.upper()])
        except KeyError as exc:
            raise KeyError(
                f"{self.symbol} has no {name} edge; known: {sorted(self.edges)}"
            ) from exc

    def has_edge(self, name: str) -> bool:
        return self.edge(name) > 0.0

    def jump(self, name: str = "K") -> float:
        """Edge jump ratio mu_above/mu_below (1.0 if unknown)."""
        return float(self.edge_jump.get(name.upper(), 1.0)) or 1.0

    def omega(self, name: str = "K") -> float:
        """Fluorescence yield of the subshell (0.0 if unknown)."""
        return float(self.fyield.get(name.upper(), 0.0))

    @property
    def E_K(self) -> float:
        return self.edge("K")

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Element {self.z} {self.symbol} {self.name}>"


def _load() -> tuple[tuple[Element, ...], Dict[str, Element], Dict[str, object]]:
    with open(_DATA, "r", encoding="utf-8") as fh:
        blob = json.load(fh)
    elems = []
    for row in blob["elements"]:
        elems.append(
            Element(
                z=int(row["z"]),
                symbol=row["symbol"],
                name=row["name"],
                mass=float(row["mass"]),
                density=float(row["density"]),
                edges={k: float(v) for k, v in row["edges"].items()},
                edge_jump={k: float(v) for k, v in row["edge_jump"].items()},
                fyield={k: float(v) for k, v in row["fyield"].items()},
            )
        )
    elems.sort(key=lambda e: e.z)
    by_symbol = {e.symbol.upper(): e for e in elems}
    by_symbol.update({e.name.upper(): e for e in elems})
    return tuple(elems), by_symbol, blob["provenance"]


ELEMENTS, _BY_NAME, PROVENANCE = _load()
BY_Z: Dict[int, Element] = {e.z: e for e in ELEMENTS}


@lru_cache(maxsize=None)
def element(x: ElementLike) -> Element:
    """Resolve an element from Z, symbol or name (case-insensitive)."""
    if isinstance(x, Element):
        return x
    if isinstance(x, int):
        try:
            return BY_Z[x]
        except KeyError:
            raise KeyError(f"Z={x} outside 1..{len(ELEMENTS)}") from None
    key = str(x).strip().upper()
    if key.isdigit():
        return element(int(key))
    try:
        return _BY_NAME[key]
    except KeyError:
        raise KeyError(f"unknown element {x!r}") from None


def edge_energy(x: ElementLike, edge: str = "K") -> float:
    return element(x).edge(edge)


def mass_fraction_to_areal(
    composition: Mapping[ElementLike, float], total_areal_density_g_cm2: float
) -> Dict[int, float]:
    """Convert normalised mass fractions to per-element areal densities (g/cm^2).

    ``composition`` need not sum to 1; it is normalised here.
    """
    norm = {element(k).z: float(v) for k, v in composition.items()}
    total = sum(norm.values())
    if total <= 0:
        raise ValueError("composition sums to zero")
    return {z: w / total * total_areal_density_g_cm2 for z, w in norm.items()}


def areal_to_mass_fraction(areal: Mapping[ElementLike, float]) -> Dict[int, float]:
    """Per-element areal densities (g/cm^2) -> normalised mass fractions."""
    vals = {element(k).z: float(v) for k, v in areal.items() if v > 0}
    total = sum(vals.values())
    if total <= 0:
        raise ValueError("areal densities sum to zero")
    return {z: v / total for z, v in vals.items()}


def symbols(zs: Iterable[int]) -> str:
    return "".join(BY_Z[z].symbol for z in zs)


def self_check() -> list[str]:
    """Structural sanity checks on the table.  Returns a list of problems."""
    problems = []
    if len(ELEMENTS) != 92:
        problems.append(f"expected 92 elements, found {len(ELEMENTS)}")
    for e in ELEMENTS:
        if not (0 < e.mass < 300):
            problems.append(f"Z={e.z} bad mass {e.mass}")
        if e.density <= 0:
            problems.append(f"Z={e.z} bad density {e.density}")
        prev = float("inf")
        for name in ("K", "L1", "L2", "L3", "M5"):
            en = e.edges.get(name, 0.0)
            if en <= 0:
                continue
            if en > prev + 0.5:   # Na L2/L3 differ by 0.1 eV in the source table
                problems.append(f"Z={e.z} {name} edge not decreasing ({en} > {prev})")
            prev = en
    return problems
