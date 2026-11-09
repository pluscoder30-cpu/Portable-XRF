"""Build the static reference tables shipped in ``engine/data/``.

DEV TOOL ONLY.  The engine itself never imports this module and never touches
the network: it reads the JSON/NPZ files this script produces.

Provenance of every number written here
---------------------------------------
``xraydb`` (Matt Newville, https://github.com/xraypy/xraydb, v4.5.8) packages
the following primary sources:

* edge energies, line energies, line intensities, jump ratios, fluorescence
  yields  --  Elam, Ravel & Sieber, Rad. Phys. Chem. 63 (2002) 121, which is
  itself built on the NIST X-ray Transition Energies Database and on
  Krause & Oliver, J. Phys. Chem. Ref. Data 8 (1979) 329.
* mass attenuation coefficients (photoelectric, coherent, incoherent)
  --  the same Elam et al. (2002) parameterisation of the NIST XCOM data.

We copy those numbers into a static file so that the delivered package has a
single dependency (numpy) and is byte-for-byte reproducible.  The copy is a
verbatim transcription, not a re-fit.

Run:  python tools/build_reference_data.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

Z_MAX = 92

# The Siegbahn lines the engine exposes.  xraydb key -> canonical name.
LINE_KEY_MAP = {
    "Ka1": "Ka1",
    "Ka2": "Ka2",
    "Ka3": "Ka3",
    "Kb1": "Kb1",
    "Kb2": "Kb2",
    "Kb3": "Kb3",
    "Kb4": "Kb4",
    "Kb5": "Kb5",
    "La1": "La1",
    "La2": "La2",
    "Ll": "Ll",
    "Ln": "Ln",
    "Lb1": "Lb1",
    "Lb2,15": "Lb2",
    "Lb3": "Lb3",
    "Lb4": "Lb4",
    "Lb5": "Lb5",
    "Lb6": "Lb6",
    "Lg1": "Lg1",
    "Lg2": "Lg2",
    "Lg3": "Lg3",
    "Lg6": "Lg6",
    "Ma": "Ma1",
    "Mb": "Mb",
    "Mg": "Mg",
    "Mz": "Mz",
}

EDGE_NAMES = ["K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "O1", "O2", "O3", "O4", "O5", "P1", "P2", "P3"]

# Attenuation grid: 0.5 keV .. 40 keV (Elam validity).  Every absorption edge of
# every element is inserted twice -- once a hair below and once a hair above the
# edge -- so that log-log interpolation never smooths over a discontinuity.
E_MIN, E_MAX, N_BASE = 500.0, 40000.0, 700


def _require_xraydb():
    try:
        import xraydb  # noqa: F401
    except ImportError:  # pragma: no cover - dev tool
        sys.exit(
            "xraydb is required to REGENERATE the data (pip install xraydb).\n"
            "The shipped engine/data/*.json|npz files are already generated."
        )
    return xraydb


def build_elements(xraydb) -> dict:
    out = []
    for z in range(1, Z_MAX + 1):
        sym = xraydb.atomic_symbol(z)
        edges = xraydb.xray_edges(sym)
        row = {
            "z": z,
            "symbol": sym,
            "name": xraydb.atomic_name(z),
            "mass": round(float(xraydb.atomic_mass(sym)), 6),
            "density": float(xraydb.atomic_density(sym)),
            "edges": {},
            "edge_jump": {},
            "fyield": {},
        }
        for e in EDGE_NAMES:
            rec = edges.get(e)
            row["edges"][e] = float(rec.energy) if rec else 0.0
            row["edge_jump"][e] = float(rec.jump_ratio) if rec else 0.0
            row["fyield"][e] = float(rec.fyield) if rec else 0.0
        out.append(row)
    return {
        "provenance": {
            "source": "xraydb 4.5.8 -> Elam, Ravel & Sieber (2002); NIST X-ray "
                      "Transition Energies DB; Krause & Oliver (1979)",
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "units": {"mass": "u", "density": "g/cm^3 (STP for gases)",
                      "edges": "eV", "edge_jump": "dimensionless "
                      "(mu_above/mu_below at the edge)", "fyield": "dimensionless"},
            "note": "edge energy 0.0 means the shell does not exist for that Z",
        },
        "elements": out,
    }


def build_lines(xraydb) -> dict:
    out = {}
    for z in range(1, Z_MAX + 1):
        sym = xraydb.atomic_symbol(z)
        raw = xraydb.xray_lines(sym)
        rows = {}
        for key, name in LINE_KEY_MAP.items():
            rec = raw.get(key)
            if rec is None:
                continue
            rows[name] = {
                "energy": float(rec.energy),
                "intensity": float(rec.intensity),
                "initial": rec.initial_level,
                "final": rec.final_level,
            }
        if rows:
            out[str(z)] = rows
    return {
        "provenance": {
            "source": "xraydb 4.5.8 (Elam et al. 2002 line table)",
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "units": {"energy": "eV", "intensity": "branching ratio within the "
                      "initial subshell (sums to 1 per initial level)"},
        },
        "lines": out,
    }


def build_mu_grid(xraydb) -> dict:
    base = np.logspace(math.log10(E_MIN), math.log10(E_MAX), N_BASE)
    extra = []
    for z in range(1, Z_MAX + 1):
        edges = xraydb.xray_edges(xraydb.atomic_symbol(z))
        for e in EDGE_NAMES:
            rec = edges.get(e)
            if rec and E_MIN <= rec.energy <= E_MAX:
                # xraydb returns the PRE-edge branch when evaluated exactly at
                # the edge energy, so bracket the discontinuity on both sides.
                extra.append(rec.energy * (1.0 - 3e-5))
                extra.append(rec.energy * (1.0 + 3e-5))
    grid = np.unique(np.concatenate([base, np.asarray(extra)]))
    n = grid.size
    mu = np.zeros((Z_MAX + 1, n), dtype=np.float32)
    pe = np.zeros_like(mu)
    coh = np.zeros_like(mu)
    inc = np.zeros_like(mu)
    for z in range(1, Z_MAX + 1):
        sym = xraydb.atomic_symbol(z)
        mu[z] = xraydb.mu_elam(sym, grid, kind="total")
        pe[z] = xraydb.mu_elam(sym, grid, kind="photo")
        coh[z] = xraydb.mu_elam(sym, grid, kind="coherent")
        inc[z] = xraydb.mu_elam(sym, grid, kind="incoherent")
    return {
        "energy_ev": grid.astype(np.float64),
        "mu_rho": mu,
        "mu_rho_pe": pe,
        "mu_rho_coh": coh,
        "mu_rho_inc": inc,
    }


def main() -> None:
    xraydb = _require_xraydb()
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(os.path.dirname(here), "data")
    os.makedirs(data, exist_ok=True)

    with open(os.path.join(data, "elements.json"), "w", encoding="utf-8") as f:
        json.dump(build_elements(xraydb), f, indent=1)
    with open(os.path.join(data, "lines.json"), "w", encoding="utf-8") as f:
        json.dump(build_lines(xraydb), f, indent=1)

    g = build_mu_grid(xraydb)
    np.savez_compressed(os.path.join(data, "mu_rho.npz"), **g)

    print(f"elements.json  {os.path.getsize(os.path.join(data,'elements.json')):,} B")
    print(f"lines.json     {os.path.getsize(os.path.join(data,'lines.json')):,} B")
    print(f"mu_rho.npz     {os.path.getsize(os.path.join(data,'mu_rho.npz')):,} B")
    print(f"mu grid: {g['energy_ev'].size} points, "
          f"{g['energy_ev'][0]:.0f}-{g['energy_ev'][-1]:.0f} eV")


if __name__ == "__main__":
    main()
