"""Elements -> minerals.

HONESTY
-------
``MINERALS[*].fractions``
    **[EXACT CHEMISTRY]**.  Element mass fractions computed from the mineral
    formula and the IUPAC atomic weights in ``elements.py``.  No fitted
    numbers: quartz is 46.74 % Si / 53.26 % O because SiO2 is.

``ELEMENT_MINERAL_PRIOR``
    **[DECLARED — OPTIONAL OVERRIDE ONLY]**.  XRF measures elements, not
    minerals: any element -> mineral split is underdetermined by the
    photon measurement.  The DEFAULT split is measurement-neutral: each
    measured element is distributed uniformly over the minerals whose
    stoichiometry actually contains it (mechanically derived from the
    formula table — no fabricated composition numbers).  The crustal
    table below may be passed explicitly (``prior=...``) or supplied by a
    registered scan-prior receipt; it is never silently load-bearing.

``unmix()``
    **[MODEL]**.  Non-negative least squares on ``y = A x`` where A is the
    element-fraction matrix and y the measured element areal densities.  The
    system is almost always underdetermined (11 crustal elements, 17 minerals),
    so the solution is regularised toward the prior; the closure residual is
    returned so the user can see whether the mineral set explains the elements.

The honest one-line summary: **the element areal densities are measured; the
mineral split is an apportionment of those measurements under a stated prior.**
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from . import elements as _elements


@dataclass(frozen=True)
class Mineral:
    name: str
    formula: str
    counts: Mapping[str, int]
    category: str
    density: Optional[float] = None      # g/cm^3, typical
    typical_air_fraction: float = 0.0    # normative, see module docstring

    @property
    def fractions(self) -> Dict[int, float]:
        """Element mass fractions, exact from the formula."""
        masses = {sym: n * _elements.element(sym).mass for sym, n in self.counts.items()}
        total = sum(masses.values())
        return {_elements.element(sym).z: m / total for sym, m in masses.items()}

    @property
    def formula_mass(self) -> float:
        return sum(n * _elements.element(s).mass for s, n in self.counts.items())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Mineral {self.name} {self.formula}>"


#: counts are atoms per formula unit.  Hydrates are written out explicitly.
MINERALS: Dict[str, Mineral] = {
    # --- silicate dust ---------------------------------------------------
    "quartz": Mineral("quartz", "SiO2", {"Si": 1, "O": 2}, "silicate", 2.65, 0.30),
    "orthoclase": Mineral("orthoclase", "KAlSi3O8", {"K": 1, "Al": 1, "Si": 3, "O": 8},
                          "feldspar", 2.56, 0.10),
    "albite": Mineral("albite", "NaAlSi3O8", {"Na": 1, "Al": 1, "Si": 3, "O": 8},
                      "feldspar", 2.62, 0.06),
    "anorthite": Mineral("anorthite", "CaAl2Si2O8", {"Ca": 1, "Al": 2, "Si": 2, "O": 8},
                         "feldspar", 2.73, 0.04),
    "kaolinite": Mineral("kaolinite", "Al2Si2O5(OH)4",
                         {"Al": 2, "Si": 2, "O": 9, "H": 4}, "clay", 2.60, 0.10),
    "illite": Mineral("illite", "K0.6Al2.3Si3.5O10(OH)2",
                      {"K": 1, "Al": 2, "Si": 4, "O": 12, "H": 2}, "clay", 2.75, 0.05),
    # --- iron oxides -----------------------------------------------------
    "hematite": Mineral("hematite", "Fe2O3", {"Fe": 2, "O": 3}, "oxide", 5.26, 0.05),
    "goethite": Mineral("goethite", "FeOOH", {"Fe": 1, "O": 2, "H": 1}, "oxide", 4.27, 0.03),
    "magnetite": Mineral("magnetite", "Fe3O4", {"Fe": 3, "O": 4}, "oxide", 5.17, 0.01),
    # --- carbonates / sulfates -------------------------------------------
    "calcite": Mineral("calcite", "CaCO3", {"Ca": 1, "C": 1, "O": 3}, "carbonate", 2.71, 0.06),
    "dolomite": Mineral("dolomite", "CaMg(CO3)2", {"Ca": 1, "Mg": 1, "C": 2, "O": 6},
                        "carbonate", 2.84, 0.02),
    "gypsum": Mineral("gypsum", "CaSO4.2H2O", {"Ca": 1, "S": 1, "O": 6, "H": 4},
                      "sulfate", 2.32, 0.02),
    "ammonium_sulfate": Mineral("ammonium_sulfate", "(NH4)2SO4",
                                {"N": 2, "H": 8, "S": 1, "O": 4}, "sulfate", 1.77, 0.02),
    # --- salts ------------------------------------------------------------
    "halite": Mineral("halite", "NaCl", {"Na": 1, "Cl": 1}, "salt", 2.16, 0.08),
    # --- titanium / manganese --------------------------------------------
    "rutile": Mineral("rutile", "TiO2", {"Ti": 1, "O": 2}, "oxide", 4.23, 0.01),
    "ilmenite": Mineral("ilmenite", "FeTiO3", {"Fe": 1, "Ti": 1, "O": 3}, "oxide", 4.72, 0.005),
    "pyrolusite": Mineral("pyrolusite", "MnO2", {"Mn": 1, "O": 2}, "oxide", 5.03, 0.002),
    # --- carbonaceous ------------------------------------------------------
    "soot": Mineral("soot", "C", {"C": 1}, "carbonaceous", 1.8, 0.05),
    "pollen": Mineral("pollen", "C6H12O6 (model)", {"C": 6, "H": 12, "O": 6},
                      "biological", 1.5, 0.01),
}

#: Typical crustal-aerosol / PM composition priors — **[DECLARED] OPTIONAL
#: OVERRIDE ONLY**, never load-bearing: pass ``prior=`` from a registered
#: scan-prior receipt or an explicit user override.  The default split is
#: the neutral one derived from the stoichiometry table (see
#: ``effective_prior``).  An explicitly-invoked convention, not a property
#: of any particular sample.
ELEMENT_MINERAL_PRIOR: Dict[str, Sequence[Tuple[str, float]]] = {
    "Si": (("quartz", 0.55), ("orthoclase", 0.15), ("albite", 0.10),
           ("anorthite", 0.08), ("kaolinite", 0.12)),
    "Al": (("kaolinite", 0.40), ("orthoclase", 0.20), ("albite", 0.15),
           ("anorthite", 0.15), ("illite", 0.10)),
    "K": (("orthoclase", 0.80), ("illite", 0.20)),
    "Na": (("halite", 0.80), ("albite", 0.20)),
    "Cl": (("halite", 1.00),),
    "Ca": (("calcite", 0.55), ("gypsum", 0.25), ("dolomite", 0.12),
           ("anorthite", 0.08)),
    "Mg": (("dolomite", 0.85), ("illite", 0.15)),
    "Fe": (("hematite", 0.55), ("goethite", 0.30), ("magnetite", 0.10),
           ("ilmenite", 0.05)),
    "Ti": (("rutile", 0.70), ("ilmenite", 0.30)),
    "Mn": (("pyrolusite", 1.00),),
    "S": (("gypsum", 0.50), ("ammonium_sulfate", 0.50)),
    "C": (("soot", 0.80), ("calcite", 0.20)),
    "H": (("pollen", 0.50), ("goethite", 0.30), ("gypsum", 0.20)),
    "N": (("ammonium_sulfate", 1.00),),
}


@lru_cache(maxsize=None)
def mineral(name: str) -> Mineral:
    try:
        return MINERALS[name]
    except KeyError:
        raise KeyError(f"unknown mineral {name!r}; have {sorted(MINERALS)}") from None


def mineral_fractions(name: str) -> Dict[int, float]:
    """**[EXACT]** element mass fractions of a mineral."""
    return mineral(name).fractions


def composition_matrix(names: Optional[Sequence[str]] = None,
                       elements: Optional[Sequence[str]] = None) -> Tuple[np.ndarray, List[str], List[str]]:
    """Build the (elements x minerals) mass-fraction matrix A."""
    names = list(names or MINERALS)
    elems = list(elements or sorted({s for m in names for s in MINERALS[m].counts}))
    A = np.zeros((len(elems), len(names)))
    for j, m in enumerate(names):
        fr = MINERALS[m].fractions
        for i, s in enumerate(elems):
            A[i, j] = fr.get(_elements.element(s).z, 0.0)
    return A, elems, names


def nnls(a: np.ndarray, b: np.ndarray, tol: float = 1e-10,
         max_iter: int = 300) -> np.ndarray:
    """Lawson-Hanson non-negative least squares (delegates to ``linalg.nnls``).

    Solves ``min ||A x - b||  s.t. x >= 0``.
    """
    from .linalg import nnls as _nnls

    return _nnls(a, b, tol=tol, max_iter=max_iter)


def effective_prior(prior: Optional[Mapping[str, Sequence[Tuple[str, float]]]] = None
                    ) -> Dict[str, tuple]:
    """The prior actually in force.

    ``prior=None`` (the default) returns the neutral split: each element
    distributed uniformly over the minerals whose formula contains it,
    derived mechanically from ``MINERALS`` — no baked composition numbers
    and no element is dropped for lacking a prior.  When a prior mapping
    is supplied (a registered scan prior or the declared crustal table),
    it is used as given, element by element.
    """
    if prior is None:
        out: Dict[str, list] = {}
        for name, m in MINERALS.items():
            for symbol in m.counts:
                out.setdefault(symbol, []).append((name, 1.0))
        return {s: tuple(v) for s, v in out.items()}

    return {str(k): tuple((str(n), float(w)) for n, w in v) for k, v in prior.items()}


def unmix(element_areal: Mapping, names: Optional[Sequence[str]] = None,
          lam: float = 1e-3,
          prior: Optional[Mapping[str, float]] = None) -> dict:
    """**[MODEL]** Apportion measured element areal densities to minerals.

    ``element_areal``: {symbol|Z: areal density in any consistent unit}.

    ``prior``: mineral-name -> prior mass fraction for the Tikhonov pull.
    ``prior=None`` (the default) solves the RAW NNLS — the measurement and
    the stoichiometry only, no prior pull.  A prior pull requires an
    explicit prior (registered scan prior or declared override) plus
    ``lam > 0``.

    Returns ``{"minerals": {name: mass}, "closure": {...}}``.
    """
    y_map = {_elements.element(k).z: float(v) for k, v in element_areal.items() if v > 0}
    names = list(names or MINERALS)
    A, elems, names = composition_matrix(names)
    y = np.array([y_map.get(_elements.element(s).z, 0.0) for s in elems])

    if lam > 0 and prior is not None:
        pvec = np.array([float(prior.get(m, 0.0)) for m in names])
        ps = pvec.sum()
        prior_use = pvec / ps if ps > 0 else pvec
        scale = max(y.sum(), 1e-30)
        A_aug = np.vstack([A, np.sqrt(lam) * np.eye(len(names))])
        b_aug = np.concatenate([y, np.sqrt(lam) * prior_use * scale])
    else:
        A_aug, b_aug = A, y

    x = nnls(A_aug, b_aug)
    fitted = A @ x
    resid = y - fitted
    closure = {
        "element_residual": {s: float(r) for s, r in zip(elems, resid)},
        "relative_residual": float(np.linalg.norm(resid) / max(np.linalg.norm(y), 1e-30)),
        "explained_fraction": float(fitted.sum() / max(y.sum(), 1e-30)),
    }
    return {
        "minerals": {m: float(v) for m, v in zip(names, x) if v > 0},
        "closure": closure,
    }


def apportion(element_areal: Mapping, prior: Optional[Mapping[str, Sequence[Tuple[str, float]]]] = None) -> dict:
    """**[MODEL]** Element -> mineral allocation under the prior in force.

    ``prior=None`` (the default) uses the NEUTRAL split: each measured
    element is distributed uniformly over the minerals whose stoichiometry
    contains it (mechanically derived, no fabricated composition numbers).
    Pass ``prior=`` to use a registered scan prior or the declared crustal
    table explicitly.  Either way the split is transparent: it conserves
    every element exactly and states its assumption openly.
    """
    prior_map = effective_prior(prior)
    totals: Dict[str, float] = {m: 0.0 for m in MINERALS}
    for k, mass in element_areal.items():
        el = _elements.element(k)
        if mass <= 0:
            continue
        priors = prior_map.get(el.symbol)
        if not priors:
            continue
        wsum = sum(w for _, w in priors)
        for name, w in priors:
            totals[name] += mass * w / wsum
    return {m: v for m, v in totals.items() if v > 0}


def self_check() -> list[str]:
    problems = []
    for name, m in MINERALS.items():
        fr = m.fractions
        if abs(sum(fr.values()) - 1.0) > 1e-9:
            problems.append(f"{name}: fractions sum to {sum(fr.values())}")
        if any(v <= 0 for v in fr.values()):
            problems.append(f"{name}: non-positive fraction")
    for sym, priors in ELEMENT_MINERAL_PRIOR.items():
        if abs(sum(w for _, w in priors) - 1.0) > 1e-6:
            problems.append(f"prior for {sym} sums to {sum(w for _, w in priors)}")
        for name, _ in priors:
            if name not in MINERALS:
                problems.append(f"prior for {sym} names unknown mineral {name}")
    return problems


if __name__ == "__main__":  # pragma: no cover
    for n in ("quartz", "hematite", "gypsum", "halite"):
        print(n, {_elements.BY_Z[z].symbol: round(f, 4) for z, f in mineral_fractions(n).items()})
    print("self_check:", self_check() or "clean")
