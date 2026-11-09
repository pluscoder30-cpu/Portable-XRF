"""THE METAL REGISTRY — every metal this instrument can read, and what it is.

HONESTY
-------
Three kinds of number live here and are never mixed.

``METALS`` categories and ``FERROUS_ZS`` / ``PRECIOUS_ZS`` ...
    [REFERENCE] the standard periodic-table classification (metal /
    metalloid / precious / ferrous / rare-earth / actinide / alkali ...).

``CONDUCTIVITY_S_M`` and ``REL_PERMEABILITY``
    [REFERENCE] room-temperature values where engineering handbooks agree
    (the common metals), [EST] where they do not or where the element is
    not traded (rare earths, actinides, At/Po/Ra/Fr).  ``None`` means "not
    tabulated" and the metal then has **no coil signature** — it is read
    by XRF only.  These two tables feed ONLY the code coil's eddy-response
    forward model (``engine/coil.py``); the XRF spectroscopy never uses
    them.

Readability
    The readable set is decided mechanically by the analyzer window: an
    element is XRF-readable iff it has at least one characteristic line
    with intensity >= ``MIN_LINE_INTENSITY`` inside
    [``MIN_WINDOW_EV``, ``MAX_WINDOW_EV``].  The registry therefore
    provably covers every metal the data can carry: to add a metal is to
    add it to the category table — nothing else.

    The window bounds are the tabulated data's own span, not a hardware
    limit: ``MIN_WINDOW_EV = 40 eV`` sits below the lowest tabulated
    characteristic line (Li Ka3, 49.4 eV) so no element is dropped by
    energy default.  Transport (a windowed detector's Be window, air
    absorption) is a separate declared mechanism applied per read —
    see ``detector.py`` and the sniffer's declared per-detector windows —
    never a registry exclusion.

The excluded row ``NONMETAL_EXCLUSIONS`` states, element by element, why a
visible non-metal (S, P, halogens, noble gases) is not a metal: the
sniffer still reads and reports those elements for the mineral split —
they are simply outside the metal registry, which is a metals registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

from . import elements as _elements
from . import lines as _lines

#: The analyzer window: mechanically the tabulated data's own span.
#: ``MIN_WINDOW_EV`` sits below the lowest tabulated characteristic line in
#: the table (Li Ka3 = 49.4 eV) so that EVERY element with tabulated lines
#: registers; nothing is dropped by a baked energy floor.  Line transport
#: (windowed-detector Be window, air absorption) is a declared forward-model
#: mechanism applied per read — see ``detector.py`` and the sniffer's
#: declared per-detector transport windows — never a registry exclusion.
MIN_WINDOW_EV = 40.0
MAX_WINDOW_EV = 25000.0
MIN_LINE_INTENSITY = 0.05


@dataclass(frozen=True)
class Metal:
    z: int
    symbol: str
    category: str
    conductivity_s_m: Optional[float]
    rel_permeability: Optional[float]
    material_label: str

    @property
    def has_coil_signature(self) -> bool:
        return (self.conductivity_s_m is not None
                and self.rel_permeability is not None
                and self.conductivity_s_m >= 1e-2)


#: [REFERENCE] standard composition classification.  One line per element;
#: the coil tables are the two 4th/5th columns (see module HONESTY above).
_METAL_ROWS: tuple[tuple[int, str, Optional[float], Optional[float], str], ...] = (
    # z, category, conductivity (S/m), mu_r, material label
    (3,  "alkali",            1.06e7, 1.0,    "lithium: best line 54 eV, far below the XRF window [REFERENCE]"),
    (4,  "alkaline_earth",    2.50e7, 1.0,    "beryllium: best line 109 eV, far below the XRF window [REFERENCE]"),
    (5,  "metalloid",         1.0e-2, 1.0,    "boron: best line 184 eV, far below the XRF window; poor conductor [EST]"),
    (11, "alkali",            2.10e7, 1.0,    "sodium: best line 1041 eV, below the XRF window; coil-readable by tabulated sigma [REFERENCE]"),
    (12, "alkaline_earth",    2.26e7, 1.0,    "magnesium [REFERENCE]"),
    (13, "post_transition",   3.77e7, 1.0,    "aluminium [REFERENCE]"),
    (14, "metalloid",         1.0e-1, 1.0,    "semiconductor; oxide in aerosols [EST]"),
    (19, "alkali",            1.43e7, 1.0,    "potassium [REFERENCE]"),
    (20, "alkaline_earth",    2.37e7, 1.0,    "calcium [REFERENCE]"),
    (21, "transition",        1.77e7, 1.0,    "scandium [EST]"),
    (22, "transition",        2.38e6, 1.0,    "titanium [REFERENCE]"),
    (23, "transition",        4.99e6, 1.0,    "vanadium [REFERENCE]"),
    (24, "transition",        7.74e6, 1.0,    "antiferromagnet: bulk mu_r ~ 1 [REFERENCE]"),
    (25, "transition",        1.44e6, 1.0,    "manganese [REFERENCE]"),
    (26, "transition",        9.93e6, 5.0e3,  "ferromagnet: canonical low-field mu_r [REFERENCE]"),
    (27, "transition",        1.63e7, 2.5e2,  "ferromagnet [REFERENCE]"),
    (28, "transition",        1.43e7, 6.0e2,  "ferromagnet [REFERENCE]"),
    (29, "transition",        5.96e7, 1.0,    "copper [REFERENCE]"),
    (30, "transition",        1.69e7, 1.0,    "zinc [REFERENCE]"),
    (31, "post_transition",   6.78e6, 1.0,    "gallium [REFERENCE]"),
    (32, "metalloid",         2.17,   1.0,    "semiconductor, intrinsic [REFERENCE]"),
    (33, "metalloid",         1.0e-1, 1.0,    "semimetal [EST]"),
    (37, "alkali",            7.79e6, 1.0,    "rubidium [REFERENCE]"),
    (38, "alkaline_earth",    4.62e6, 1.0,    "strontium [EST]"),
    (39, "transition",        1.66e6, 1.0,    "yttrium [EST]"),
    (40, "transition",        2.35e6, 1.0,    "zirconium [REFERENCE]"),
    (41, "transition",        6.99e6, 1.0,    "niobium [REFERENCE]"),
    (42, "transition",        1.87e7, 1.0,    "molybdenum [REFERENCE]"),
    (43, "transition",        4.00e6, 1.0,    "technetium: radioelement, all isotopes; tabulated estimate [EST]"),
    (44, "precious",          1.40e7, 1.0,    "ruthenium [EST]"),
    (45, "precious",          2.11e7, 1.0,    "rhodium [REFERENCE]"),
    (46, "precious",          9.62e6, 1.0,    "palladium [REFERENCE]"),
    (47, "precious",          6.30e7, 1.0,    "silver [REFERENCE]"),
    (48, "transition",        1.40e7, 1.0,    "cadmium [REFERENCE]"),
    (49, "post_transition",   1.20e7, 1.0,    "indium [REFERENCE]"),
    (50, "post_transition",   8.70e6, 1.0,    "tin [REFERENCE]"),
    (51, "metalloid",         2.40e6, 1.0,    "semimetal [REFERENCE]"),
    (52, "metalloid",         2.0e-6, 1.0,    "semiconductor [EST]"),
    (55, "alkali",            4.79e6, 1.0,    "caesium [REFERENCE]"),
    (56, "alkaline_earth",    2.90e6, 1.0,    "barium [EST]"),
    (57, "rare_earth",        1.63e6, 1.0,    "lanthanum [EST]"),
    (58, "rare_earth",        1.46e6, 1.0,    "cerium [EST]"),
    (59, "rare_earth",        1.33e6, 1.0,    "praseodymium [EST]"),
    (60, "rare_earth",        1.53e6, 1.0,    "neodymium [EST]"),
    (61, "rare_earth",        None,   None,   "promethium: radioelement, no tabulated conductivity"),
    (62, "rare_earth",        1.10e6, 1.0,    "samarium [EST]"),
    (63, "rare_earth",        1.22e6, 1.0,    "europium [EST]"),
    (64, "rare_earth",        7.36e5, 1.0,    "gadolinium; bulk mu_r ~ 1 at room T [EST]"),
    (65, "rare_earth",        8.70e5, 1.0,    "terbium [EST]"),
    (66, "rare_earth",        1.08e6, 1.0,    "dysprosium [EST]"),
    (67, "rare_earth",        1.24e6, 1.0,    "holmium [EST]"),
    (68, "rare_earth",        1.15e6, 1.0,    "erbium [EST]"),
    (69, "rare_earth",        1.60e6, 1.0,    "thulium [EST]"),
    (70, "rare_earth",        2.50e6, 1.0,    "ytterbium [EST]"),
    (71, "rare_earth",        1.51e6, 1.0,    "lutetium [EST]"),
    (72, "transition",        2.75e6, 1.0,    "hafnium [EST]"),
    (73, "transition",        7.74e6, 1.0,    "tantalum [REFERENCE]"),
    (74, "transition",        1.79e7, 1.0,    "tungsten [REFERENCE]"),
    (75, "transition",        1.86e7, 1.0,    "rhenium [REFERENCE]"),
    (76, "precious",          1.20e7, 1.0,    "osmium [EST]"),
    (77, "precious",          2.12e7, 1.0,    "iridium [REFERENCE]"),
    (78, "precious",          9.44e6, 1.0,    "platinum [REFERENCE]"),
    (79, "precious",          4.11e7, 1.0,    "gold [REFERENCE]"),
    (80, "transition",        1.04e6, 1.0,    "mercury, liquid at room T [REFERENCE]"),
    (81, "post_transition",   7.18e6, 1.0,    "thallium [EST]"),
    (82, "post_transition",   4.84e6, 1.0,    "lead [REFERENCE]"),
    (83, "post_transition",   9.30e5, 1.0,    "bismuth [REFERENCE]"),
    (84, "post_transition",   2.20e6, 1.0,    "polonium, radioactive [EST]"),
    (85, "metalloid",         None,   None,   "astatine: no tabulated conductivity"),
    (87, "alkali",            None,   None,   "francium: no tabulated conductivity"),
    (88, "alkaline_earth",    1.00e6, 1.0,    "radium, radioactive [EST]"),
    (89, "actinide",          None,   None,   "actinium: no tabulated conductivity"),
    (90, "actinide",          6.53e6, 1.0,    "thorium [REFERENCE]"),
    (91, "actinide",          None,   None,   "protactinium: no tabulated conductivity"),
    (92, "actinide",          3.55e6, 1.0,    "uranium [REFERENCE]"),
)

FERROUS_ZS = (26, 27, 28)                    # the ferromagnets
PRECIOUS_ZS = (44, 45, 46, 47, 76, 77, 78, 79)  # the precious group

#: Why each visible non-metal is not in the metals registry.  The sniffer
#: still reads and reports every one of them for the mineral split.
NONMETAL_EXCLUSIONS: Dict[int, str] = {
    1:  "hydrogen — nonmetal",
    2:  "helium — noble gas",
    6:  "carbon — nonmetal (Kα 277 eV tabulated and XRF-readable; not a metal)",
    7:  "nitrogen — nonmetal (Kα 392 eV tabulated and XRF-readable; not a metal)",
    8:  "oxygen — nonmetal (Kα 525 eV tabulated and XRF-readable; not a metal)",
    9:  "fluorine — halogen nonmetal (Kα 677 eV tabulated and XRF-readable; not a metal)",
    10: "neon — noble gas",
    15: "phosphorus — nonmetal (readable; not a metal)",
    16: "sulfur — nonmetal (readable; not a metal)",
    17: "chlorine — halogen (readable; not a metal)",
    18: "argon — noble gas",
    34: "selenium — nonmetal",
    35: "bromine — halogen (readable; not a metal)",
    36: "krypton — noble gas",
    53: "iodine — halogen (readable; not a metal)",
    54: "xenon — noble gas",
    86: "radon — noble gas",
}


_METALS: Dict[int, Metal] = {
    z: Metal(z=z, symbol=_elements.BY_Z[z].symbol, category=cat,
             conductivity_s_m=sigma, rel_permeability=mu_r, material_label=label)
    for z, cat, sigma, mu_r, label in _METAL_ROWS
}


def metal(x) -> Metal:
    """Lookup by Z, symbol or any element-like."""
    z = _elements.element(x).z
    try:
        return _METALS[z]
    except KeyError:
        reason = NONMETAL_EXCLUSIONS.get(z)
        raise KeyError(
            f"Z={z} is not in the metal registry "
            f"({reason if reason else 'not registered in metals.py — absence is spoken in the register'})"
        ) from None


@lru_cache(maxsize=1)
def window_lines(z: int) -> tuple:
    """All tabulated lines of a metal inside the analyzer window."""
    return tuple(ln for ln in _lines.lines(z)
                 if MIN_WINDOW_EV <= ln.energy <= MAX_WINDOW_EV
                 and ln.intensity >= MIN_LINE_INTENSITY)


@lru_cache(maxsize=1)
def primary_line(z: int):
    """The strongest in-window line — the metal's identification line."""
    cands = window_lines(z)
    if not cands:
        return None
    return max(cands, key=lambda ln: ln.intensity)


@lru_cache(maxsize=1)
def registry() -> tuple[Metal, ...]:
    """Every registered metal that is XRF-readable in the window.

    A registered metal with no in-window line cannot be read by this
    analyzer at all; it is dropped here (never invented), and the reason is
    carried in ``dropped_from_registry`` for the audit.  Every metal that
    remains provably has its identification line in the window.
    """
    out = []
    for z in sorted(_METALS):
        if window_lines(z):
            out.append(_METALS[z])
    return tuple(out)


@lru_cache(maxsize=1)
def dropped_from_registry() -> tuple[tuple[str, str, float], ...]:
    """Registered metals with no in-window line (the honest drop record)."""
    out = []
    for z in sorted(_METALS):
        if window_lines(z):
            continue
        all_lines = _lines.lines(z)
        best = max((ln.energy for ln in all_lines), default=0.0)
        out.append((_METALS[z].symbol, _METALS[z].category,
                    best if best else 0.0))
    return tuple(out)


def as_rows() -> List[dict]:
    """The registry as report rows (the session's METALS READ table)."""
    rows: List[dict] = []
    for m in registry():
        ln = primary_line(m.z)
        el = _elements.element(m.z)
        rows.append({
            "z": m.z,
            "symbol": m.symbol,
            "category": m.category,
            "primary_line": ln.name,
            "primary_line_energy_ev": ln.energy,
            "n_window_lines": len(window_lines(m.z)),
            "conductivity_s_m": m.conductivity_s_m,
            "rel_permeability": m.rel_permeability,
            "coil_signature": m.has_coil_signature,
            "density_g_cm3": el.density,
            "material_label": m.material_label,
        })
    return rows


def line_only_metals() -> tuple[str, ...]:
    """Registered metals with NO coil signature (conductivity not tabulated)."""
    return tuple(m.symbol for m in registry() if not m.has_coil_signature)


def self_check() -> List[str]:
    problems: List[str] = []
    if not registry():
        problems.append("empty registry")
    for m in registry():
        ln = primary_line(m.z)
        if ln is None:
            problems.append(f"{m.symbol}: in registry without an in-window line")
        elif not (MIN_WINDOW_EV <= ln.energy <= MAX_WINDOW_EV):
            problems.append(f"{m.symbol}: primary line {ln.energy} eV outside window")
    if {m.z for m in registry() if m.rel_permeability and m.rel_permeability > 10} != set(FERROUS_ZS):
        problems.append("ferrous set != high-mu_r set")
    got_precious = {m.z for m in registry() if m.category == "precious"}
    if got_precious != set(PRECIOUS_ZS):
        problems.append("precious set mismatch")
    if len({m.z for m in registry()}) != len(registry()):
        problems.append("duplicate Z in registry")
    for m in registry():
        if m.has_coil_signature:
            if not (m.conductivity_s_m > 0 and m.rel_permeability >= 1.0):
                problems.append(f"{m.symbol}: invalid coil table entries")
    cat_counts = {}
    for m in registry():
        cat_counts[m.category] = cat_counts.get(m.category, 0) + 1
    if len(cat_counts) < 8:
        problems.append(f"category coverage collapsed: {cat_counts}")
    return problems


if __name__ == "__main__":  # pragma: no cover
    rows = as_rows()
    print(f"METAL REGISTRY — {len(rows)} metals, analyzer window "
          f"{MIN_WINDOW_EV/1000:.1f}-{MAX_WINDOW_EV/1000:.0f} keV")
    print(f"coil-signature metals : {len(rows) - len(line_only_metals())}")
    print(f"XRF-only metals       : {', '.join(line_only_metals()) or 'none'}")
    for r in rows:
        sig = "coil" if r["coil_signature"] else "XRF-only"
        print(f"  {r['symbol']:>3} Z={r['z']:<3} {r['category']:<15} "
              f"{r['primary_line']:>4} {r['primary_line_energy_ev']:8.1f} eV  [{sig}]")
    print("self_check:", self_check() or "clean")
