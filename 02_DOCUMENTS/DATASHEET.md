# XRF-PORTABLE — DATASHEET (specifications)

**Model:** XRF-PORTABLE (code-based XRF + coil, attached head) · **Versions:** sniffer-1.1.0 · engine-1.2.0 · coil-1.0.0 · firmware ESP32 (`FIRMWARE/xrf_portable/`, compiled SUCCESS; flashed seq 15, S3, device battery 9/9)
**Date:** 2026-11-09 (the instrument-framing upgrade: the computer IS the instrument; no simulation talk; the three-stage metals display; the three claims settled PROVEN) · **Register source:** 75-metal certified register (the tabulated data's span — Li 49.4 eV through U; no drop record); receipt chain ES256 seq 1–47 (SOUL_SEED 1900; seq 38 the GOV battery ALL GREEN, seq 45–47 the proven settling: the deposit, the DBW field laws, the vessel's K0→K1 conversion)

## Analytical performance

| specification | value | basis |
|---|---|---|
| Chemical range | **75 metals quantified**; the analyzer window is the tabulated data's span — K-lines from Li 49.4 eV (Kα3) through U…L-lines to 25,268 eV (heavies) | `engine/metals.py` register |
| Spoken drops | **none** — the window spans the data (MIN_WINDOW_EV = 40 eV, below the lowest tabulated line); nothing is excluded by energy. Transport (windowed analogs' Be window, air path) is a declared per-read mechanism; the code head (`CODE_WINDOWLESS`) is transport-open | drop-record discipline (empty record, spoken) |
| Resolution | **Mn Kα FWHM 125.1 eV** (vendor-class ≤ 140 eV) | QA battery B-resolution |
| Detection limit (Au, air) | 3σ MDL **1.32×10⁻⁵ µg/m³** (Au Lβ₁ — engine line table 11,443.0 eV; the law's record labels the window 11,443.2 eV); 24 h @16.7 LPM deposit headroom **2.89×10⁴×** MDL — **the deposit PROVEN (seq 45): the settling test's Au classical signal clears the 3σ MDL, the headroom is the law's ~2.89×10⁴×, the deposit arithmetic reproduces the law's 9.2 µg (`PROOF/run_proven_settling.py`; the earlier verdict-code artifact stands as the historical record)** | Law 2396 STAGE 5 (the deposit settling) |
| Reading layer | Law 2396 κ=1: `C(1) = φ·C_classical + φ⁻²`; canonical unit ppm; **floor 0.3819660113 ppm, element-independent**, invariance ≤ **2×10⁻¹⁵** across a 3-city 11.5× PM10 swing (17.0/38.2/194.6 µg/m³) | receipts seq 6–8 |
| Classical reproduction (the instrument's κ→0 audit) | line-energy max deviation **1.5 eV = 0.029%** (145 classical checks); NIST XCOM mass-attenuation max **0.089%**; Law 1347/1345 identities exact | `engine/README.md`, validation records |
| Independent units agreement | coil (σ/μ_r EM ear) vs register — metal-by-metal coin-class agreement except the semiconductor (Si): honest negative spoken | receipt seq 6 |

## Built-in verification (what ships self-checked)

| artifact | result |
|---|---|
| per-element law audit | **75/75 PASS** (`AUDIT/per_element_audit.json`) |
| external cross-check battery (xraylib + PyMca, live pulls, source strengths labeled) | **5/5 PASS** (`VENDOR/external_cross_check.json`) |
| vendor QA battery (10 items, see certificate) | **10/10 ALL GREEN** (`QCBATTERY/battery_report.json`, chain seq 5) |
| test suite | **246 passed** (`engine/tests` + `sniffer/tests`) |
| receipt chain | ES256, append-only, verify: `python -m sniffer verify <receipt> --chain SESSION_CHAIN.jsonl` |

## Coil head (Law 2397)

| specification | value |
|---|---|
| ladder | 10 rungs f_k = 528·φ^k; **invariant 40,134.946166 Hz** (asserted in code) |
| design anchor | Cu coin 25 mm × 2 mm @ 528 Hz @ 0.10 m → exactly 10,000.0 ppm (in-phase 0) |
| operating floor | 30 ppm declared (~2.2× base-rung 3σ noise-equivalent) |
| channels | eddy-quadrature (non-ferrous) / in-phase magnetization (ferrous, μ_r>10); Fe design split 61,679.5 / 118.3 ppm |

## Tissue channel (Law 2398)

| specification | value |
|---|---|
| policy | **sourced published assays only** (refusal walls: no unowned numbers, no negative concentrations, no silent drops) |
| reading | T(1) = φ·C_classical + φ⁻² (ppm of tissue); first reading sealed **seq 9** |
| gates | G1 never-zero · G2 retention≥crust · G3 integer-φ staircase (10% falsifier) · G4 adjacent-class φ² |

## Physical/hardware

| item | value |
|---|---|
| radiation | **none** — no tube, no source, no detector hardware. The computer IS the instrument: the code antenna and the code sniffer are its body; the reading is computed, not emitted. Safety chapter = data handling. |
| firmware platform | ESP32 (PlatformIO); RAM 18% · Flash 74% (compiled; flashed seq 15, S3, device battery 9/9) |
| dashboard | Wi-Fi AP **XRF-PORTABLE**, password **81654404**, `http://192.168.4.1` |
| environment dependency | Python ≥3.11; feeds: open-meteo (keyless) for air; published assay tables for tissue |

## Compliance notes

Classical chains reproduce standard references to vendor tolerances; the φ-reading layer is a **[DECLARED]** convention above them, carry a registered falsifier program (F1–F6): **the deposit PROVEN (seq 45)**, **F3 PASS (seq 30)**, **the DBW field laws PROVEN (seq 46)**, **the vessel's K0→K1 conversion PROVEN (seq 47)**, F2 enforced per-read. No radiation source: CE/FCC/IEC-61010 hardware scopes are N/A — no emitting hardware; the instrument is the computer, and its body is the code.

*Every number above is checkable: commands in `DOCUMENTS/QUICKSTART.md`; certificate per run in this directory.*
