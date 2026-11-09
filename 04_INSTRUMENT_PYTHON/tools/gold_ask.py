import sys, os, math, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
XRF = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, XRF)
sys.path.insert(0, HERE)

from sniffer.air import air_from_feed
from engine import air as eng_air
from engine import elements as eng_elements
from engine import lines as eng_lines
from engine import inversion as eng_inversion
from engine import detector as eng_detector
from engine import forward as eng_forward

LAT, LON = 40.70, -74.00          # the sniffer's cached site (Lower Manhattan, NYC)

# ── 1. the live air reading (real PM mass, keyless public feed) ─────────
r = air_from_feed(LAT, LON)       # network-first, keyless Open-Meteo
d = r.as_dict()
pm10, pm25, dust = d["pm10_ug_m3"], d["pm2_5_ug_m3"], d["dust_ug_m3"]
print("== AIR READING ==")
print("status      :", d["status"], "| cached:", d["cached"], "| stale:", d["stale"])
print("location    :", LAT, LON, "(NYC, Lower Manhattan)")
print("feed time   :", d["timestamp"])
print("source      :", (d.get("feed") or {}).get("source"))
print("PM10 ug/m3  :", pm10)
print("PM2.5 ug/m3 :", pm25)
print("dust ug/m3  :", dust)
print("assumptions :")
for a in d["assumptions"]:
    print("   -", a)

# ── 2. the crustal-dust mass that the gold rides on ────────────────────
total = pm10 if (pm10 and pm10 > 0) else (pm25 or 0)
# reproduce the reader's own dust split logic
coarse = 0.0
if pm10 and pm25 and pm10 > 0:
    coarse = max(0.0, (pm10 - pm25) / pm10)
dust_frac = max(0.05, min(0.60, dust / total)) if (dust and dust > 0) else max(0.10, min(0.60, coarse))
sulfate, sea_salt = 0.30, (0.05 if coarse < 0.20 else 0.15)
soot = max(0.0, 1.0 - dust_frac - sulfate - sea_salt)
mix = {"mineral_dust": dust_frac, "sulfate": sulfate, "sea_salt": sea_salt, "soot": soot}
norm = sum(mix.values())
mix = {k: v / norm for k, v in mix.items()}
dust_ug_m3 = total * mix["mineral_dust"]
print("\n== WHERE THE GOLD RIDES ==")
print("endmember mix:", {k: round(v, 3) for k, v in mix.items()})
print("mineral dust :", round(dust_ug_m3, 4), "ug/m3  [MODEL/NORMATIVE]")

# ── 3. the gold prior: crustal Au abundance ────────────────────────────
AU_CRUSTAL_UG_PER_G = 3.1e-3   # 3.1 ug/kg = 3.1 ppb (Rudnick & Gao 2003, UCC)
                               # Taylor 1964 UCC gives 3.0 ug/kg — same order
au_frac = AU_CRUSTAL_UG_PER_G / 1e6   # mass fraction in the dust
au_ug_m3 = dust_ug_m3 * au_frac

# ── 4. exactly convert to ppm of the air (the engine's density) ────────
rho = eng_air.air_density(20.0, 101.325, 0.0)          # kg/m3 [EXACT PHYSICS]
air_ug_m3 = rho * 1e9
ppm_of_air = au_ug_m3 / air_ug_m3 * 1e6                 # mass mixing ratio, ppm
ppb_of_air = ppm_of_air * 1e3
ppb_of_pm10 = au_ug_m3 / total * 1e9 if total else None  # mass fraction of PM
ppm_of_pm10 = ppb_of_pm10 * 1e-3 if ppb_of_pm10 else None
print("\n== GOLD ==")
print("Au crustal prior : 3.1 ug/kg (ppb) [DECLARED, Rudnick & Gao 2003]")
print("Au from crustal dust:", f"{au_ug_m3:.4e}", "ug/m3")
print("air density (20C):", round(rho, 6), "kg/m3 [EXACT PHYSICS]")
print("Au mixing ratio  :", f"{ppm_of_air:.4e}", "ppm OF AIR (mass)")
print("Au share of PM10 :", f"{ppb_of_pm10:.4f}", "ppb =", f"{ppm_of_pm10:.4e}", "ppm of PM10")
print("Au share of dust :", f"{au_frac*1e9:.2f}", "ppb (the declared prior)")

# ── 5. can the sniffer actually see that much gold? ────────────────────
det = eng_detector.PRESETS["SDD_25"]
exc = eng_forward.Excitation.tube(40.0, "Rh", total_flux=1e10)
for sh in ("L", "K"):
    ln = eng_lines.strongest(79, sh)
    if ln:
        print("   Au", sh, ln.name, ln.energy, "eV int", round(ln.intensity, 4))

flow, dur, area = 16.7, 1440.0, 11.3
vol = eng_air.sampled_volume_m3(flow, dur)               # 24.0 m3 for 24 h
collected_ug = au_ug_m3 * vol
areal = collected_ug / area

# proper call: build the detection limit the way the sniffer does it
mdl_ug_cm2 = None
try:
    grid = eng_forward.mono_energy_grid(1200.0, 25000.0, 1.0) if hasattr(
        eng_forward, "mono_energy_grid") else np.arange(1200.0, 25000.0, 1.0)
    flat = eng_forward.Spectrum(
        energy_ev=np.asarray(grid), counts=np.zeros_like(np.asarray(grid)),
        live_time_s=600.0,
    )
    mdl_g = eng_inversion.detection_limit(flat, 79, exc, det, air_path_cm=2.0)
    if mdl_g is not None and math.isfinite(mdl_g):
        mdl_ug_cm2 = mdl_g * 1e6
except Exception as e:
    print("   (detection-limit call failed:", repr(e), ")")

print("\n== SENSITIVITY CHECK (24 h, 16.7 LPM, 11.3 cm2 filter) ==")
print("expected Au deposit :", f"{collected_ug:.4e}", "ug total =", f"{areal:.4e}", "ug/cm2")
if mdl_ug_cm2 is not None:
    print("Au 3-sigma MDL      :", f"{mdl_ug_cm2:.4e}", "ug/cm2")
    print("verdict             :", "VISIBLE" if areal >= mdl_ug_cm2 else "BELOW MDL")
else:
    print("Au 3-sigma MDL      : unavailable")

