"""F1 recovery diagnostic — WHY does the declared arm recover ~15% of the
stamped Au areal?  Re-runs arm A (deterministic seed, the same feed cache)
and tabulates recovered-vs-predicted areals per registered metal.  No seal:
the campaign receipt (seq 10) already carries the falsifier; this speaks the
deviation's shape."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from engine import air as eng_air
from engine import elements as eng_elements
from engine import metals as eng_metals
from engine import phi_laws

from run_f1_deposit import (areal_g_cm2, au_row, run_arm, AU_CRUSTAL_UG_PER_G,
                            LIVE_TIME_S, SEED_A, VOL_M3, AREA_CM2)
from sniffer.air import air_from_feed

reading = air_from_feed(40.70, -74.00)
d = reading.as_dict()
elements = dict(reading.elements_ug_m3 or {})
metals = {m.symbol: m for m in eng_metals.registry()}

# the arm A deposit, exactly as the campaign builds it
au_c_ug_m3 = (d["dust_ug_m3"] or 0.0) * AU_CRUSTAL_UG_PER_G / 1e6
areal_a, predicted = {}, {}
for m in metals.values():
    c_class = float(elements.get(m.symbol, 0.0) or 0.0)
    if m.z == 79:
        c_class = au_c_ug_m3
    c_phi = phi_laws.phi_motion(c_class, 1.0)
    predicted[m.symbol] = c_phi * VOL_M3 / AREA_CM2
    areal_a[m.z] = areal_g_cm2(c_phi)
skipped = []
for sym, c in elements.items():
    if sym not in metals and c and float(c) > 0:
        try:
            z = eng_elements.element(sym).z
            areal_a[z] = areal_g_cm2(float(c))
        except (KeyError, ValueError) as exc:
            skipped.append(f"{sym}: {type(exc).__name__}: {exc}")
if skipped:
    print("unknown-symbol skipped (spoken):", "; ".join(skipped))

_, rep_a = run_arm(areal_a, SEED_A, "F1 diagnostic: declared arm (kappa=1)")
recovered = {row["symbol"]: row["areal_ug_cm2"] for row in rep_a["elements"]}
rows = []
for sym in metals:
    if sym in recovered:
        r = recovered[sym] / predicted[sym]
        rows.append((sym, predicted[sym], recovered[sym], r))
rows.sort(key=lambda t: -t[3])
print(f"{'sym':>4} {'pred ug/cm2':>12} {'recovered':>12} {'recovery':>8}")
for sym, p, rec, r in rows:
    print(f"{sym:>4} {p:12.6f} {rec:12.6f} {100*r:7.1f}%")
ratios = [t[3] for t in rows]
print(f"\nmetals with rows: {len(rows)}/{len(metals)}")
if ratios:
    print(f"recovery: median {100*sorted(ratios)[len(ratios)//2]:.1f}%  "
          f"min {100*min(ratios):.1f}%  max {100*max(ratios):.1f}%")
out = os.path.join(HERE, "f1_recovery_diagnostic.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"rows": rows, "n_rows": len(rows), "skipped": skipped}, f, indent=1)
print("table ->", out)
