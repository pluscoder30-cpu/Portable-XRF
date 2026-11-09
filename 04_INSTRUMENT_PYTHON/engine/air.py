"""The air model: composition, density, and the aerosol sampling chain.

HONESTY
-------
``AIR_VOLUME_FRACTIONS`` / ``AIR_COMPOSITION``
    **[REFERENCE]**.  Standard dry air near sea level (CRC Handbook / US
    Standard Atmosphere): N2 78.084 %, O2 20.946 %, Ar 0.934 %, CO2 0.042 %
    by volume, plus the trace gases listed.  Element mass fractions are
    computed from those volume fractions and the IUPAC atomic weights -- they
    are not fitted.  The resulting N/O/Ar mass split (75.52 / 23.14 / 1.29)
    reproduces the NIST dry-air composition.

``air_density()``
    **[EXACT PHYSICS]**.  Ideal gas, dry-air and water-vapour partial
    pressures, Magnus saturation formula.  Validated against the standard
    densities 1.2923 / 1.2250 / 1.2041 kg/m^3 at 0 / 15 / 20 degC.

``AerosolSample``
    **[EXACT ARITHMETIC]**.  concentration x flow x time / filter area.  This
    is the definition of areal density; there is no model in it.  What *is* a
    model is the inlet/collection efficiency (default 1.0) and the assumption
    that the deposit is uniform over the filter area.

``AEROSOL_ENDMEMBERS``
    **[MODEL / NORMATIVE]**.  The composition of each aerosol class.  Mineral
    dust, sea salt and sulfate compositions come from the mineral formulas
    (exact chemistry); the *mix* within a class is a stated assumption.

The air path matters: at 6.4 keV the 1/e attenuation length in air at 20 degC
is about 2.4 m, so a 10 cm air gap costs ~4 % of the Fe K-alpha line.  The
engine computes that from the NIST table, not from a rule of thumb.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Mapping, Optional, Sequence

import numpy as np

from . import attenuation as _atten
from . import elements as _elements
from . import minerals as _minerals

# ---------------------------------------------------------------------------
# 1. Composition
# ---------------------------------------------------------------------------
#: Dry air by volume (mole) fraction.  CRC Handbook of Chemistry and Physics.
AIR_VOLUME_FRACTIONS: Dict[str, float] = {
    "N2": 0.78084,
    "O2": 0.20946,
    "Ar": 0.00934,
    "CO2": 0.00042,
    "Ne": 0.000018,
    "He": 0.00000524,
    "CH4": 0.0000017,
    "Kr": 0.00000114,
    "H2": 0.00000055,
}

#: Molar masses (g/mol) of the molecular species.
_MOLAR_MASS = {
    "N2": 28.0134, "O2": 31.9988, "Ar": 39.948, "CO2": 44.0095, "Ne": 20.1797,
    "He": 4.002602, "CH4": 16.0425, "Kr": 83.798, "H2": 2.01588, "H2O": 18.01528,
}

#: Molecular -> element atom counts.
_ATOMS = {
    "N2": {"N": 2}, "O2": {"O": 2}, "Ar": {"Ar": 1}, "CO2": {"C": 1, "O": 2},
    "Ne": {"Ne": 1}, "He": {"He": 1}, "CH4": {"C": 1, "H": 4},
    "Kr": {"Kr": 1}, "H2": {"H": 2}, "H2O": {"H": 2, "O": 1},
}


def _element_mass_fractions(volume_fractions: Mapping[str, float]) -> Dict[int, float]:
    grams: Dict[int, float] = {}
    for species, frac in volume_fractions.items():
        n_atoms = _ATOMS[species]
        for sym, count in n_atoms.items():
            z = _elements.element(sym).z
            grams[z] = grams.get(z, 0.0) + frac * count * _elements.BY_Z[z].mass
    total = sum(grams.values())
    return {z: g / total for z, g in grams.items()}


#: **[REFERENCE-DERIVED]** dry-air element mass fractions.
AIR_COMPOSITION: Dict[int, float] = _element_mass_fractions(AIR_VOLUME_FRACTIONS)

#: Mean molar mass of dry air, g/mol.
MOLAR_MASS_DRY_AIR = sum(
    f * _MOLAR_MASS[s] for s, f in AIR_VOLUME_FRACTIONS.items()
) / sum(AIR_VOLUME_FRACTIONS.values())

R_DRY_AIR = 287.058      # J/(kg K)
R_WATER_VAPOUR = 461.495  # J/(kg K)


def saturation_vapour_pressure_hpa(t_c: float) -> float:
    """**[MODEL]** Magnus formula over water (valid -45..60 degC, ~0.3 % error)."""
    return 6.112 * math.exp(17.62 * t_c / (243.12 + t_c))


def air_composition(t_c: float = 20.0, rh: float = 0.0) -> Dict[int, float]:
    """**[REFERENCE + EXACT MIXING]** element mass fractions including H2O."""
    if rh <= 0:
        return dict(AIR_COMPOSITION)
    vf = dict(AIR_VOLUME_FRACTIONS)
    # water vapour volume fraction = rh * p_sat / p_total (approx, ideal gas)
    p_sat = saturation_vapour_pressure_hpa(t_c)
    vf["H2O"] = min(0.99, rh * p_sat / 1013.25)
    return _element_mass_fractions(vf)


def air_density(t_c: float = 20.0, pressure_kpa: float = 101.325,
                rh: float = 0.0) -> float:
    """**[EXACT PHYSICS]** Air density in kg/m^3 (and g/cm^3 via /1000).

    Ideal gas with dry-air and water-vapour partial pressures.
    """
    p_total = pressure_kpa * 1000.0
    p_v = min(rh, 0.99) * saturation_vapour_pressure_hpa(t_c) * 100.0
    p_d = max(p_total - p_v, 0.0)
    t_k = t_c + 273.15
    return p_d / (R_DRY_AIR * t_k) + p_v / (R_WATER_VAPOUR * t_k)


def air_density_g_cm3(t_c: float = 20.0, pressure_kpa: float = 101.325,
                      rh: float = 0.0) -> float:
    return air_density(t_c, pressure_kpa, rh) / 1000.0


def air_mu_rho(energy_ev, t_c: float = 20.0, rh: float = 0.0):
    """**[REFERENCE]** Mass attenuation coefficient of air, cm^2/g."""
    return _atten.mu_rho_mixture(air_composition(t_c, rh), energy_ev)


def air_transmission(energy_ev, path_cm: float, t_c: float = 20.0,
                     pressure_kpa: float = 101.325, rh: float = 0.0):
    """**[EXACT]** Transmission of an air path of ``path_cm`` at ``energy_ev``."""
    rho = air_density_g_cm3(t_c, pressure_kpa, rh)
    mu = np.asarray(air_mu_rho(energy_ev, t_c, rh), dtype=float) * rho
    return np.exp(-mu * path_cm)


def attenuation_length_cm(energy_ev: float, t_c: float = 20.0) -> float:
    """1/e path length in air, cm."""
    mu = float(air_mu_rho(energy_ev, t_c)) * air_density_g_cm3(t_c)
    return 1.0 / mu


# ---------------------------------------------------------------------------
# 2. Aerosol sampling
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AerosolSample:
    """A filter sample: concentration in, areal density out."""

    concentration_ug_m3: float
    flow_lpm: float                 # litres per minute
    duration_min: float
    filter_area_cm2: float
    inlet_efficiency: float = 1.0   # PM2.5/PM10 inlet cut, [MODEL] default 1
    collection_efficiency: float = 1.0  # filter capture, [MODEL] default 1

    @property
    def volume_m3(self) -> float:
        return self.flow_lpm * self.duration_min / 1000.0

    @property
    def collected_mass_ug(self) -> float:
        return (self.concentration_ug_m3 * self.volume_m3
                * self.inlet_efficiency * self.collection_efficiency)

    @property
    def areal_ug_cm2(self) -> float:
        return self.collected_mass_ug / self.filter_area_cm2

    @property
    def areal_g_cm2(self) -> float:
        return self.areal_ug_cm2 * 1e-6

    def element_areal(self, element_fractions: Mapping) -> Dict[int, float]:
        """Split the deposit into element areal densities (g/cm^2)."""
        total = self.areal_g_cm2
        return _elements.mass_fraction_to_areal(element_fractions, total)


def sampled_volume_m3(flow_lpm: float, duration_min: float) -> float:
    return flow_lpm * duration_min / 1000.0


def areal_density_ug_cm2(concentration_ug_m3: float, flow_lpm: float,
                         duration_min: float, filter_area_cm2: float,
                         inlet_efficiency: float = 1.0) -> float:
    """**[EXACT]** areal density on the filter, ug/cm^2."""
    mass = concentration_ug_m3 * sampled_volume_m3(flow_lpm, duration_min) * inlet_efficiency
    return mass / filter_area_cm2


def pm_mass_from_areal(areal_ug_cm2: float, flow_lpm: float, duration_min: float,
                       filter_area_cm2: float) -> float:
    """Inverse of ``areal_density_ug_cm2``: recover ug/m^3 from the filter."""
    mass = areal_ug_cm2 * filter_area_cm2
    return mass / sampled_volume_m3(flow_lpm, duration_min)


#: Common filter formats: (diameter_mm, active_area_cm2).
FILTER_FORMATS = {
    "37mm": (37.0, 9.6),     # 37 mm, 34 mm deposit
    "47mm": (47.0, 11.3),    # 47 mm, 38 mm deposit
    "25mm": (25.0, 3.14),
    "pallflex_37": (37.0, 8.0),
}


# ---------------------------------------------------------------------------
# 3. Aerosol endmembers
# ---------------------------------------------------------------------------
#: **[MODEL / NORMATIVE]** mass fractions of minerals within each aerosol class.
AEROSOL_ENDMEMBERS: Dict[str, Dict[str, float]] = {
    "mineral_dust": {
        "quartz": 0.55, "orthoclase": 0.15, "albite": 0.10,
        "anorthite": 0.08, "kaolinite": 0.12,
    },
    "sea_salt": {"halite": 1.0},
    "sulfate": {"ammonium_sulfate": 0.70, "gypsum": 0.30},
    "soot": {"soot": 1.0},
    "pollen": {"pollen": 1.0},
    "iron_oxide": {"hematite": 0.70, "goethite": 0.30},
    "carbonate": {"calcite": 0.80, "dolomite": 0.20},
}

#: The crustal elements an XRF aerosol measurement usually reports.
CRUSTAL_ELEMENTS = ("Na", "Mg", "Al", "Si", "S", "Cl", "K", "Ca",
                    "Ti", "Mn", "Fe")


@lru_cache(maxsize=None)
def endmember_fractions(name: str) -> Dict[int, float]:
    """**[EXACT CHEMISTRY]** element mass fractions of an aerosol endmember."""
    try:
        mix = AEROSOL_ENDMEMBERS[name]
    except KeyError:
        raise KeyError(f"unknown endmember {name!r}; have {sorted(AEROSOL_ENDMEMBERS)}") from None
    acc: Dict[int, float] = {}
    for mineral_name, w in mix.items():
        for z, f in _minerals.mineral_fractions(mineral_name).items():
            acc[z] = acc.get(z, 0.0) + w * f
    total = sum(acc.values())
    return {z: v / total for z, v in acc.items()}


def endmember_areal(name: str, concentration_ug_m3: float, flow_lpm: float,
                    duration_min: float, filter_area_cm2: float) -> Dict[int, float]:
    """Element areal densities (g/cm^2) for a pure endmember deposit."""
    s = AerosolSample(concentration_ug_m3, flow_lpm, duration_min, filter_area_cm2)
    return s.element_areal(endmember_fractions(name))


def endmember_symbol_fractions(name: str) -> Dict[str, float]:
    return {_elements.BY_Z[z].symbol: f for z, f in endmember_fractions(name).items()}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
#: Standard dry-air densities, kg/m^3 (CRC / US Standard Atmosphere).
DENSITY_ANCHORS = {0.0: 1.2923, 15.0: 1.2250, 20.0: 1.2041, 25.0: 1.1843}


def validate_air(verbose: bool = False) -> dict:
    """Density anchors, composition closure, and the NIST attenuation check."""
    dens = []
    for t, ref in DENSITY_ANCHORS.items():
        got = air_density(t, 101.325, 0.0)
        dens.append({"t_c": t, "reference": ref, "computed": got,
                     "dev_pct": 100.0 * (got - ref) / ref})
        if verbose:
            print(f"{t:5.1f} degC  ref {ref:.4f}  computed {got:.4f} kg/m3 "
                  f"({dens[-1]['dev_pct']:+5.2f} %)")
    comp = sum(AIR_COMPOSITION.values())
    att = _atten.validate_nist_air(verbose=verbose)
    return {
        "density": dens,
        "composition_sum": comp,
        "nist_attenuation": att,
        "max_nist_dev_pct": max(abs(r["dev_pct"]) for r in att),
    }


def self_check() -> list[str]:
    problems = []
    if abs(sum(AIR_COMPOSITION.values()) - 1.0) > 1e-9:
        problems.append("air mass fractions do not sum to 1")
    if abs(MOLAR_MASS_DRY_AIR - 28.96) > 0.05:
        problems.append(f"dry-air molar mass {MOLAR_MASS_DRY_AIR:.3f} g/mol")
    for name in AEROSOL_ENDMEMBERS:
        if abs(sum(endmember_fractions(name).values()) - 1.0) > 1e-9:
            problems.append(f"endmember {name} fractions do not sum to 1")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("dry air mass fractions:",
          {_elements.BY_Z[z].symbol: round(f, 5) for z, f in AIR_COMPOSITION.items()})
    print("M =", round(MOLAR_MASS_DRY_AIR, 3), "g/mol")
    print(validate_air(verbose=True))
    print("self_check:", self_check() or "clean")
