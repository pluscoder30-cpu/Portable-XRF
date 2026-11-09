"""THE ELEMENTAL FLOOR REGISTER — Law 2396 over the full table.

WHAT THIS IS
------------
The reading layer of the code-based XRF.  The corpus's own verdict for the
*line physics* is exact classical form (Law 1347: fluorescence energies
equal the single-hole binding-energy differences exactly for all
couplings), so nothing here touches a line energy.  What sits HERE is the
reading law commissioned for this instrument:

    LAW 2396 (elemental concentration):

        C_phi(kappa) = C_classical*(1 + kappa*(phi-1)) + kappa*phi^-1*C_ground

        C_ground = phi^-1  (unit-covariant; declared unit: ppm of air)

Applied to "no element counts", this is the ELEMENTAL FLOOR:

    floor(kappa) = kappa * phi^-2          (= 0.3819660113 ppm at kappa=1)

The corpus's no-quiet-zero (Law 171's ground, Law 2396's floor): the
reading of absence is the phi-ground, never a bare zero.  The classical
value is the degenerate limit kappa -> 0 (exact identity).

WHAT EVERY ELEMENT GETS
-----------------------
Every element Z = 1..92 is registered in one of two channels, decided
mechanically from the tabulated data (no baked exclusion lists):

``xrf_line``
    The table carries at least one characteristic line inside the analyzer
    window [``engine.metals.MIN_WINDOW_EV``, ``MAX_WINDOW_EV``] with
    intensity >= ``MIN_LINE_INTENSITY``.  The row records the strongest
    such line.  Transport (a windowed detector's Be window, the air path)
    is applied later by the declared forward model — it gates nothing here.
``phi_ground_floor``
    Zero tabulated lines (chemically true for exactly H, Z=1, and He, Z=2).
    For hydrogen this IS Law 1344's verdict: the K-alpha frequency form
    (3/4) c R (Z-1)^2 reads 0 at Z=1 — and zero is not a quiet zero, it is
    the phi-ground: the element's reading channel is Law 2396's floor,
    kappa * phi^-2 of the declared unit, carried by the code coil's
    floor witness and the wifi-sniffer witness per scan.

Every row is JSON-safe and is sealed into every sniffer report and session
receipt, so "the elemental floor is registered" is not a sentence — it is
a chain of signed artifacts.

FIELDS AND THEIR KINDS (honesty labels)
---------------------------------------
``symbol/name/z, channel, strongest line, line energy``  [REFERENCE]
    from ``data/elements.json`` / ``data/lines.json`` verbatim.
``floor_ppm, ground_ppm``                                 [EXACT]
    phi arithmetic only; degenerate identity holds by construction.
``scan_mdl_ug_cm2``                                       [MEASURED/simulated]
    attached per scan when the sniffer computed the element's 3-sigma
    detection limit; absent (never zero) when not computed.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from . import elements as _elements
from . import lines as _lines
from . import metals as _metals
from . import phi_laws as _phi

REGISTRY_MIN_Z = 1
REGISTRY_MAX_Z = 92

#: Elements with zero tabulated characteristic lines in the registered
#: table — computed mechanically (``lineless_z`` in ``register``); asserted
#: in ``self_check`` to be exactly H (Z=1) and He (Z=2).
LINELESS_Z: tuple = (1, 2)

PHI_GROUND_NOTE_H = (
    "Law 1344's K-frequency form (3/4)cR(Z-1)^2 reads 0 at Z=1; zero is the "
    "phi-ground (Law 2396), never a quiet zero (Law 171).  The reading "
    "channel is the floor: kappa*phi^-2 of the declared unit, witnessed by "
    "the code coil and the wifi sniffer per scan."
)
PHI_GROUND_NOTE_HE = (
    "No characteristic line exists in the registered table for He (z=2); "
    "the reading channel is Law 2396's floor: kappa*phi^-2 of the declared "
    "unit, never a quiet zero (Law 171)."
)


def floor_ppm(kappa: float = _phi.KAPPA_FULL) -> float:
    """Law 2396's elemental floor: kappa * phi^-2 of the declared unit.

    The declared canonical unit is the mass mixing ratio in ppm of air
    (``engine.phi_laws``).  At kappa = 1 this is phi^-2
    = 0.3819660112501052 ppm of air — the no-quiet-zero.  At kappa -> 0
    the floor degenerates to the exact classical reading of 0 (Law
    2396 stage 3, the floorless limit); the coupling is always reported
    next to the number so the degenerate limit is never hidden.
    """
    return float(kappa) * _phi.PHI_SQ_INV


def element_row(z: int, kappa: float = _phi.KAPPA_FULL,
                mdl_ug_cm2: Optional[float] = None,
                scan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """One register row: element z's channel, line and Law-2396 floor.

    ``scan`` (optional, from the reading instrument): ``{"detected_z": set,
    "areal_by_z": {z: classical areal}, "reading_by_z": {z: κ=1 reading}}``.
    It attaches the THREE STAGES the instrument reports:

    ``quantized_ug_cm2``          the κ=1 reading — the field-locked value
                                 (Law 2396's quantized stage)
    ``degenerate_limit_ug_cm2``  the κ→0 classical value — the classic
                                 degenerate limit (the conventional picture,
                                 shown so the difference is explicit)
    ``stage``                    ``"quantized"`` (detected, locked in the
                                 field) or ``"field_carried"`` (not locked
                                 up; the actual amount in the air — the
                                 phi-ground where no line was quantified,
                                 the measured reading ``phi*areal + phi^-2``
                                 where a line was quantified below the
                                 phi-floor gate; never zero, Law 171)
    """
    z = int(z)
    if not (REGISTRY_MIN_Z <= z <= REGISTRY_MAX_Z):
        raise ValueError(f"z out of register range: {z}")
    el = _elements.BY_Z[z]
    sym = el.symbol

    in_window = [ln for ln in _lines.lines(z)
                 if _metals.MIN_WINDOW_EV <= ln.energy <= _metals.MAX_WINDOW_EV
                 and ln.intensity >= _metals.MIN_LINE_INTENSITY]

    scan = scan or {}
    detected_z = set(scan.get("detected_z") or ())
    areal_by_z = scan.get("areal_by_z") or {}
    reading_by_z = scan.get("reading_by_z") or {}
    stage = "quantized" if z in detected_z else "field_carried"
    degenerate = float(areal_by_z[z]) if z in areal_by_z else 0.0
    quantized = (float(reading_by_z[z]) if z in reading_by_z
                 else float(kappa) * _phi.PHI_SQ_INV)

    if in_window:
        best = max(in_window, key=lambda ln: ln.intensity)
        channel = "xrf_line"
        row: Dict[str, Any] = {
            "z": z,
            "symbol": sym,
            "name": el.name,
            "channel": channel,
            "line": best.name,
            "line_energy_ev": float(best.energy),
            "n_window_lines": len(in_window),
            "floor_ppm": float(kappa) * _phi.PHI_INV * _phi.PHI_INV,
        }
    else:
        channel = "phi_ground_floor"
        row = {
            "z": z,
            "symbol": sym,
            "name": el.name,
            "channel": channel,
            "line": None,
            "line_energy_ev": None,
            "n_window_lines": 0,
            "floor_ppm": float(kappa) * _phi.PHI_INV * _phi.PHI_INV,
            "declaration": (PHI_GROUND_NOTE_H if z == 1 else PHI_GROUND_NOTE_HE),
            "law": "PHI-2396 + Law 1344 (degenerate zero at Z=1)"
                   if z == 1 else "PHI-2396",
        }

    # The coupling is always carried with the number (degenerate identity is
    # visible by construction; nothing is hidden).
    row["kappa"] = float(kappa)
    row["ground_ppm"] = _phi.PHI_INV
    row["floor_at_full_coupling_ppm"] = _phi.PHI_SQ_INV
    # The three stages: the quantized (field-locked) reading, the classic
    # degenerate limit, and the stage this element reads in.
    row["stage"] = stage
    row["quantized_ug_cm2"] = quantized
    row["degenerate_limit_ug_cm2"] = degenerate
    if mdl_ug_cm2 is not None:
        row["scan_mdl_ug_cm2"] = (None if not math.isfinite(float(mdl_ug_cm2))
                                  else float(mdl_ug_cm2))
    return row


def register(kappa: float = _phi.KAPPA_FULL,
             mdl_by_ug: Optional[Dict[int, Optional[float]]] = None,
             scan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The full 92-element register as a report block.

    ``mdl_by_ug`` maps Z -> the scan's 3-sigma detection limit (ug/cm2) or
    None for elements whose limit was not computed in this scan.

    ``scan`` (optional): ``{"detected_z": set, "areal_by_z": {...},
    "reading_by_z": {...}}`` — the reading instrument's per-element results,
    which place every element in one of the THREE STAGES:

    1. ``quantized``      the detected elements — locked up in the field,
                         reading the κ=1 quantized value (φ·areal + φ⁻²)
    2. ``field_carried``  the below-floor elements — not locked up; carried
                         at the φ-ground, which IS the actual amount in the
                         air (never zero, Law 171)
    3. ``degenerate_limit`` the κ→0 classical column for every element —
                         the classic degenerate limit, shown so the
                         conventional picture is explicit and named
    """
    mdl_by_ug = mdl_by_ug or {}
    scan = scan or {}
    rows: List[Dict[str, Any]] = []
    n_line, n_floor = 0, 0
    n_quantized, n_field_carried = 0, 0
    for z in range(REGISTRY_MIN_Z, REGISTRY_MAX_Z + 1):
        row = element_row(z, kappa, mdl_by_ug.get(z), scan=scan)
        rows.append(row)
        if row["channel"] == "xrf_line":
            n_line += 1
        else:
            n_floor += 1
        if row["stage"] == "quantized":
            n_quantized += 1
        else:
            n_field_carried += 1
    return {
        "law": "PHI-2396",
        "label": "[EXACT phi arithmetic; [REFERENCE] line data]",
        "kappa": float(kappa),
        "ground_ppm": _phi.PHI_INV,
        "floor_ppm": floor_ppm(kappa),
        "floor_at_full_coupling_ppm": _phi.PHI_SQ_INV,
        "window_ev": [_metals.MIN_WINDOW_EV, _metals.MAX_WINDOW_EV],
        "n_elements": len(rows),
        "n_xrf_line_channels": n_line,
        "n_phi_ground_floor_channels": n_floor,
        "n_quantized": n_quantized,
        "n_field_carried": n_field_carried,
        "lineless_z": [r["z"] for r in rows
                       if r["channel"] == "phi_ground_floor"],
        "note": (
            "Every element is registered.  Elements with tabulated lines in "
            "the analyzer window carry the xrf_line channel; elements with "
            "zero tabulated lines (H, He) carry the phi_ground_floor channel "
            "of Law 2396 — the reading of absence is kappa*phi^-2 in the "
            "declared unit, never a bare zero.  The classical scalar of the "
            "fit is the kappa->0 degenerate limit of the same law."
        ),
        "stages": {
            "quantized": ("the detected elements — locked up in the field, "
                          "reading the kappa=1 quantized value phi*areal + "
                          "phi^-2"),
            "field_carried": ("not locked up in the field — the actual amount "
                              "in the air: the phi-ground where no line was "
                              "quantified, the measured reading "
                              "phi*areal + phi^-2 where a line was quantified "
                              "below the phi-floor gate (never zero, Law 171)"),
            "degenerate_limit": ("the kappa->0 classical column for every "
                                 "element — the classic degenerate limit, "
                                 "named and shown so the conventional "
                                 "picture is explicit"),
        },
        "elements": rows,
    }


def self_check() -> List[str]:
    problems: List[str] = []
    reg = register()
    if reg["n_elements"] != 92:
        problems.append(f"register lost rows: {reg['n_elements']}")
    lineless = reg["lineless_z"]
    if lineless != [1, 2]:
        problems.append(f"lineless set is not exactly [1, 2]: {lineless}")
    if abs(floor_ppm(_phi.KAPPA_FULL) - _phi.PHI_SQ_INV) > 1e-15:
        problems.append("floor at full coupling is not phi^-2")
    # the degenerate identity: kappa -> 0 gives the exact classical zero
    if floor_ppm(0.0) != 0.0:
        problems.append("degenerate floor identity fails")
    for k in (0.0, 0.25, 0.5, 1.0):
        if abs(floor_ppm(k) - k * _phi.PHI_SQ_INV) > 1e-15:
            problems.append(f"floor arithmetic wrong at kappa={k}")
    # hydrogen's declaration must be pinned
    h_row = element_row(1)
    if h_row["channel"] != "phi_ground_floor" or "Law 1344" not in h_row["declaration"]:
        problems.append("H floor declaration drifted")
    c_row = element_row(6)
    if c_row["line"] != "Ka1" or abs(c_row["line_energy_ev"] - 277.0) > 0.5:
        problems.append(f"C line channel drifted: {c_row.get('line')} "
                        f"@ {c_row.get('line_energy_ev')}")
    o_row = element_row(8)
    if o_row["line"] != "Ka1" or abs(o_row["line_energy_ev"] - 524.9) > 0.5:
        problems.append("O line channel drifted")
    return problems


if __name__ == "__main__":  # pragma: no cover
    reg = register()
    print(f"ELEMENTAL FLOOR REGISTER (Law 2396) — {reg['n_elements']} elements, "
          f"floor {reg['floor_ppm']:.12f} ppm at kappa={reg['kappa']}")
    print(f"  xrf_line channels  : {reg['n_xrf_line_channels']}")
    print(f"  phi-ground channels: {reg['lineless_z']}")
    for r in reg["elements"]:
        if r["channel"] == "phi_ground_floor":
            print(f"  Z={r['z']} {r['symbol']}: PHI-GROUND FLOOR (Law 2396)")
        elif r["z"] <= 11:
            print(f"  Z={r['z']} {r['symbol']}: {r['line']} "
                  f"{r['line_energy_ev']:.1f} eV (line-exact)")
    print("self_check:", self_check() or "clean")
