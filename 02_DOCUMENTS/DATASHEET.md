# XRF-PORTABLE — DATASHEET (specifications)

**Model:** XRF-PORTABLE (code-based XRF + coil, attached head) · **Versions:** sniffer-1.0.0 · engine-1.1.0 · coil-1.0.0 · firmware ESP32 (`FIRMWARE/xrf_portable/`, compiled SUCCESS)
**Date:** 2026-11-02 · **Register source:** 71-metal certified register; receipt chain ES256 seq 1–12 at 2026-11-03 (SOUL_SEED 1900; seq 10 the F1 deposit falsifier, seq 11 the F3 transfer falsifier, seq 12 the engineering round 2)

## Analytical performance

| specification | value | basis |
|---|---|---|
| Chemical range | **71 metals quantified**; emission window K-lines 1,040 eV (Na-class edge)…L-lines to 25,268 eV (heavies) | `engine/metals.py` register |
| Spoken drops | Li (49 eV), Be (109 eV), B (183 eV), Na (1,040 eV) below the analyzer window — **named in every sealed payload** | drop-record discipline |
| Resolution | **Mn Kα FWHM 125.1 eV** (vendor-class ≤ 140 eV) | QA battery B-resolution |
| Detection limit (Au, air) | 3σ MDL **1.32×10⁻⁵ µg/m³** (Au Lβ₁ — engine line table 11,443.0 eV; the law's record labels the window 11,443.2 eV); 24 h @16.7 LPM deposit headroom **2.89×10⁴×** MDL — **F1 run in-code (seq 10): declared arm 2.894×10⁴× vs declared MDL, PASS; `PROOF/`** | Law 2396 STAGE 5 (F1 write-up) |
| Reading layer | Law 2396 κ=1: `C(1) = φ·C_classical + φ⁻²`; canonical unit ppm; **floor 0.3819660113 ppm, element-independent**, invariance ≤ **2×10⁻¹⁵** across a 3-city 11.5× PM10 swing (17.0/38.2/194.6 µg/m³) | receipts seq 6–8 |
| Classical reproduction (the instrument's κ→0 audit) | line-energy max deviation **1.5 eV = 0.029%** (145 classical checks); NIST XCOM mass-attenuation max **0.089%**; Law 1347/1345 identities exact | `engine/README.md`, validation records |
| Independent units agreement | coil (σ/μ_r EM ear) vs register — metal-by-metal coin-class agreement except the semiconductor (Si): honest negative spoken | receipt seq 6 |

## Built-in verification (what ships self-checked)

| artifact | result |
|---|---|
| per-element law audit | **71/71 PASS** (`AUDIT/per_element_audit.json`) |
| external cross-check battery (xraylib + PyMca, live pulls, source strengths labeled) | **5/5 PASS** (`VENDOR/external_cross_check.json`) |
| vendor QA battery (10 items, see certificate) | **10/10 ALL GREEN** (`QCBATTERY/battery_report.json`, chain seq 5) |
| test suite | **226 passed** (`engine/tests` + `sniffer/tests`) |
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
| radiation | **none** — no tube, no source, no detector hardware (the instrument reads feeds; safety chapter = data handling) |
| firmware platform | ESP32 (PlatformIO); RAM 18% · Flash 74% (compiled, not flashed) |
| dashboard | Wi-Fi AP **XRF-PORTABLE**, password **81654404**, `http://192.168.4.1` |
| environment dependency | Python ≥3.11; feeds: open-meteo (keyless) for air; published assay tables for tissue |

## Compliance notes

Classical chains reproduce standard references to vendor tolerances; the φ-reading layer is a **[DECLARED]** convention above them, carry a registered falsifier program (F1–F6). No radiation source: CE/FCC/IEC-61010 hardware scopes are N/A in the honest sense — no emitting hardware.

*Every number above is checkable: commands in `DOCUMENTS/QUICKSTART.md`; certificate per run in this directory.*
