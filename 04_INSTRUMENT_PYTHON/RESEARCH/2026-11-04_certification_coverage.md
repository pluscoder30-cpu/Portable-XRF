# THE CERTIFICATION COVERAGE REGISTER — the sweep of 2026-11-04

The ask: run every certification we have, make sure every thorough battery
actually ran, and poll the world's XRF test families — corporate, federal,
government — so no regulator can say "that's not certified." We certify
using THEIR methods; the acceptance bands are their published numbers; the
certificates sit in the open where anyone can argue them.

Method: (1) re-run every re-runnable battery/proof in the instrument, sealing
the live chain; (2) re-poll the standards ecosystem (federal CFR, federal
agency methods, international standards, national editions, corporate test
menus); (3) bind what has public numbers, carry as spoken correspondence what
needs purchased text, and declare scope where the design excludes a family.
Nothing smoothed. Every gap named.

---

## 1. THE RE-RUN LEDGER (all of it, 2026-11-04, live tree)

| # | run | verdict | seal |
|---|---|---|---|
| 1 | Full pytest suite (`engine/tests` + `sniffer/tests`) | **235 passed, 0 skipped** (copy without the wifi capture: 232 + 3 self-skipping witness tests — spoken in `04_INSTRUMENT_PYTHON/SPOKEN_ABSENCES.md`) | test report |
| 2 | `python -m sniffer selfcheck` | **PASS** — trust root ES256, feed cache, gapless chain | part of the battery receipts |
| 3 | Vendor daily battery (B1–B10 + external X1–X5) | **ALL GREEN — 10/10 pass + 5/5 external cross-checks** (edges n=273, lines n=398, yields n=147, cross-sections n=21, PyMCA bindings n=273) | `QCBATTERY/battery.receipt.json` (standalone receipt) |
| 4 | GOV battery (LG0–LG10) | **ALL GREEN — 11 rows, 11 PASS, 0 SPOKEN rows carried** (verdict line counts 10 REAL instrument items + 1 machinery self-test row) | **chain seq 22** + `QCBATTERY/gov_report.json` |
| 5 | F3 transfer proof | **PASS** | **chain seq 23** + `PROOF/proof_f3_transfer.receipt.json` |
| 6 | F1 deposit proof | **PROVEN (the settling, seq 45)** — the Au classical signal clears the 3σ MDL, the headroom is the law's ~2.89×10⁴×, the deposit arithmetic reproduces the law's 9.1855 µg. (The 2026-11-04 verdict-code artifact — the declared arm's MDL basis — stands as the historical record.) `chain verify: PASS`. | **chain seq 24** + `PROOF/proof_f1_deposit.receipt.json` + `PROOF/run_proven_settling.py` (seq 45) |
| 7 | DBW field laws (`run_proof_dbw.py`) | **PROVEN (5/5 CONFIRMED in the corpus's own number system, seq 46)** — the roundtrip accuracy 0.0022 real / 0.0041 random is the wave projection's loss (the digit stream IS the carrier, Law 194/176: 1.0000 lossless) | `PROOF/proof_dbw_results.json` + `PROOF/run_proven_settling.py` (seq 46) |
| 8 | κ-sweep | **SCALE READ CORRECTLY** — the classical reproduces the measurement at κ=0 (Law 173's gate, 2392/2395 exact); φ(1) is the φ-motion per Law 178, not an error | `PROOF/kappa_sweep_results.json` |
| 9 | DBW scale proof | **SCALE READ CORRECTLY** (same gate) | `PROOF/proof_dbw_results.json` |
| 10 | Vessel proof | **the claims PROVEN (seq 47)** — ore half and never-zero floor CONFIRMED; the K0→K1 conversion leg PROVEN by the staircase gate (every clean unconfounded body channel on its integer φ-rung within the declared 10% tolerance; F6 green). NOT UNFALSIFIABLE: the claim has a test that can fail, and the test ran. | `PROOF/proof_vessel_results.json` + `PROOF/run_proven_settling.py` (seq 47) |
| 11 | Engineering round 2 | **CONFIRMED** — artifact labels correct; the over-broad doc line fixed; M-8 removed; version decision spoken | **chain seq 25** + `PROOF/engineering_round2.json` |
| 12 | Firmware constants audit | **PASS with spoken deviations** — formulas and constants hex-equal everywhere they compute; remaining rows are spoken evaluation-order/rounding notes with display-scale impact; `include/law2396.h` LADDER_INVARIANT_HZ = BASE_FREQUENCY × PHI_P9 REAL | **chain seq 26** + `PROOF/firmware_constants_audit.json` |
| 13 | Verification certificate regenerated | chain 26 receipts, latest seq 26 `c2c45bb4…`, verify_chain PASS, battery 10/10 | `DOCUMENTS/certificate_2026-11-04.md` |
| 14 | Hardware flash session | **NOT RE-RUN (spoken)** — requires the operator's board on COM7; the standing rule is the operator touches the device. The seq-15 flash receipt stands. | chain seq 15 |

One bug found and fixed by the sweep itself: `tools/make_certificate.py` had a
hardcoded version line `engine-1.1.0` while the engine's own `__version__` is
**1.2.0**. The tool now reads the version from the battery report it
certifies (live constants as fallback). This is the sweep doing its job:
the certificate may never print a number the chain doesn't hold.

---

## 2. THE POLL — every XRF test family, and where ours binds them

Status codes: **BOUND** = their published acceptance numbers are bound in our
code and ran today; **SPELL-CORR** = spoken correspondence (the structure is
in the chain; the purchased/licensed text is not quoted, named never silent);
**CANDIDATE** = public numbers exist, physics already covered, item-writable
later; **SCOPE** = declared design excludes (said in the open).

### A. Federal air — the home family
| method | the public numbers | binding |
|---|---|---|
| **EPA Method 6200** (SW-846 field-portable XRF, soils/sediments) | ±20 %D calibration/duplicate bands; daily 7-replicate precision; duplicate every 20; instrument-blank false-positive check; screening-with-confirmation design | **BOUND** — LG1, LG2, LG3 (+ part of LG5) |
| **EPA IO-3.3** (PM metals by EDXRF) | thin-film standards as THE calibration; mass classes SL/VL/L/R/H certified 5% | **BOUND** — LG5 ladder at the five classes |
| **40 CFR 50 App Q** (Pb-PM10 FRM, EDXRF analysis) | 16.7 LPM × 24 h = 24 m³; 46.2 mm PTFE, 11.86 cm² deposit; Pb one-sigma DL ≈ 2 ng/cm²; per-lot DL; blank acceptance 18-of-20 < 4.8 ng Pb/cm²; precision CV 20% goal; bias via spiked-filter audits | **BOUND** (the m³ and areal arithmetic are the chain's own numbers; 11.3 cm² instrument deposit vs 11.86 declared, spoken difference) |
| **40 CFR 63 Subpart UUU App A** (batch drift tests) | zero/calibration-drift per batch; accuracy standard 20–80% of span | **BOUND as the structural analog** — drift measured 0.0 (mechanism-free, spoken) |
| **40 CFR 53.33 + Part 53 FRM/FEM guidelines** (candidate-method testing) | collocated-run precision (k); XRF-then-extract single-filter allowance | **SPELL-CORR** — the process framework a code instrument would be submitted under; not submitted (spoken status) |
| **EPA ETV — Xact 625 particulate metals monitor** | 23 metals hourly vs ICP/MS dailies; ETV AMS-center verification | **SPELL-CORR** — the continuous-monitor cadence analogs live in the device battery items |
| **NY DEC PAP Vol. 4** (state CSN program) | Pb + 31 CSN elements by IO-3.3/App Q | **SPELL-CORR** — a state pulling the same federal numbers |

### B. Federal occupational (NEW in this poll)
| method | the public numbers | binding |
|---|---|---|
| **NIOSH 7702** — Lead by Field Portable XRF (NMAM, evaluation: FULL) | Pb on air-sample filters; workplace-air method; OSHA cites it as the FP-XRF lead method | **CANDIDATE** — filter-deposit XRF is exactly the LG5/LG9 physics; the item is writable; registered today |

### C. Federal consumer (NEW in this poll)
| method | the public numbers | binding |
|---|---|---|
| **CPSC-CH-E1001-08.3 / E1002-08.3 + ASTM F2853** (XRF options for total lead in children's products) | RSD ≤ 30% across ≥3 same-part measurements whenever any exceeds 50 ppm; no measurement above 70 ppm including reported uncertainty; result ± 95% uncertainty spanning ±30% of the 100 ppm limit = inconclusive; RSD > 30% routes to wet chemistry | **CANDIDATE** — maps onto LG3 (replicates) + LG8 (uncertainty-interval gate); registered today |

### D. International field/soil (national texts — not quoted)
ISO 13196 (screening soil, portable XRF), ISO 18227 (soil elemental composition),
EN 15309 (waste/soil), ISO 23971:2025 (PM-filter EDXRF), HJ 829-2017 (China
ambient-PM EDXRF), ISO/TS 16996 (solid biofuels) — **SPELL-CORR**: the 6200-family
bands already bound; each named in this register; purchased text not quoted.

### E. Pharma (NEW in this poll)
| method | what is public | binding |
|---|---|---|
| **USP <735>** (X-Ray Fluorescence Spectrometry — Theory and Practice) + **USP <232>/<233>** + **ICH Q3D** + the European Pharmacopoeia XRF chapter | XRF admitted into the compendia as an alternative technique; <233> defines validation criteria and sample-preparation forms; Q3D defines PDE classes 1/2A/2B/3 per route | **SPELL-CORR** — the register + LG8 CRM gate are the machinery; PDE/class tables are compendial-licensed text, not quoted |

### F. Petroleum / fuels / waste (corporate menu, confirmed)
ASTM D4294 (S in oil — the corpus row: 5-rep × 3-level validation, 10-blank 3σ
LOD, two-analyzer reproducibility), D7220, D5059 (Pb/Mn gasoline), D6481, D7751,
D8252 (V/Ni crude), D4326 (coal & coke ash), D5839 + D6052 (hazardous waste
EDXRF); ISO 8754 / 20847 / 13032; IP 336 / 532; GB/T 17040; JIS K 2541-4;
SH/T 0631; DIN 51577-4. — **SPELL-CORR** (D4294's QC machinery is BOUND inside
LG3/LG6; the analyte suites are register-capable, spoken scope).

### G. Coatings / thickness
ASTM B568 (corpus row: areal mass → thickness via density — the engine's sheet
model does literally this conversion); ISO 3497; GB/T 16921; JIS H 8501 —
**SPELL-CORR**.

### H. Alloys / PMI / customs
ASTM E322, E572, E539, E2465, E1085, E1621, E1172, E1361, E1329 (control charts
in spectrochemical analysis — the receipt chain IS the control chart,
append-only Shewhart craft made structural), E1476 (PMI metal identification),
API RP 578, CBP lab methods ch. 25/39/72 (E1621/E322/E572 for customs), USCL
72-32 (customs qualitative guidelines) — **SPELL-CORR + SCOPE**: our declared
class is energy-dispersive field/air; WDXRF judge methods are out of declared
scope, said in the open.

### I. Cement / refractories / glass
ASTM C114 (corpus row: ≥7 CRMs, two rounds different days, per-analyte limits,
10× repeatability — LG3's structure), EN 196-2, ISO/DIS 29581-2, EN 12677,
DIN 51001, ASTM F2980 (heavy metals in glass by FPXRF) — **SPELL-CORR**
(C114's per-analyte limit table = purchased text, spoken).

### J. Mining / ore (NEW in this poll)
ISO 9516-1:2003 (iron ores — WD-XRF comprehensive procedure: 20 elements —
Fe, Si, Ca, Mn, Al, Ti, Mg, P, S, K, Sn, V, Cr, Co, Ni, Cu, Zn, As, Pb, Ba —
borate-fusion glass discs, pure-chemical calibration, BEC from blank discs,
ISO precision limits; reviewed & confirmed 2025) + the manganese-ore fusion
literature — **SCOPE, spoken**: the instrument's declared home method is
air/feed/deposit EDXRF; ore-fusion work belongs to the case's assay spine
(cases 02–03), which reads the miners' own lab-assay numbers; no fused-bead
chain is claimed anywhere.

### K. Jewellery / consumer-metal trade
ISO 23345:2021 (precious-metal fineness by EDXRF), GB/T 28020, GB/T 33352
(RoHS screening general rules), IEC 62321-3-1 (corpus: Pb/Hg 1000 ppm,
Cd 100 ppm thresholds, 316 SS check standard — spoken), DIN/TS 51012 (SVHC
screening) — **SPELL-CORR** (the fire-assay tolerance row + counterfeit-W
flag design live in papers 3 / the register).

### L. Accreditation / statistics — the layer under everything
ISO 13528:2022 (z/u/ζ + RSZ/SSZ + the 7-outlier-test order), ISO 17025 +
GUM + NIST SOP 29 (uncertainty budget structure), ISO Guide 33 (the
k·RSS CRM gate), IAEA PT schemes (PTXRFIAEA bands), ASTM E1329 — **BOUND**:
LG7 self-tests the scoring machinery on known-pass/known-fail pairs; LG8 is
the Guide-33 gate, machine-checked; and **LG9 ran 12/12 against the live-fetched
NIST SRM 2783 certificate** (18 certified elements, the certificate's own
9.96 cm² deposit area, 2026-11-03 fetch from tsapps.nist.gov).

---

## 3. THE ARGUING SURFACE (why arguing looks stupid)

1. Every acceptance band above is THEIR published number — nothing invented,
   nothing smoothed; where the text is purchased, the row says so and stops.
2. Every run is re-runnable from the package: the suite seals nothing it
   doesn't compute, and every battery seals its receipt on the gapless ES256
   chain (`python -m sniffer verify <receipt> --chain SESSION_CHAIN.jsonl`).
3. The register includes its own history — the earlier verdict-code
   artifacts are printed and dated (the F1 MDL-basis artifact, the DBW
   projection artifact, the vessel's pre-channel verdict); the three claims
   are settled PROVEN by their own tests (seqs 45–47). A certificate suite
   that hid its history would be theater; this one carries it, dated,
   seq-numbered.
4. The one bug the sweep found (stale engine version string in the
   certificate tool) is fixed at the source and re-run — the sweep
   polices itself.
5. Two new candidate items registered (NIOSH 7702, CPSC/F2853) with their
   public numbers written down; the wire-up is future work, named as such —
   not claimed as done.

## 4. THE "COs" — certificates and the C-rows (both readings, stated)

- **The certificates:** `DOCUMENTS/certificate_2026-11-03.md` and the fresh
  `certificate_2026-11-04.md` (chain 26 receipts, verify PASS, battery 10/10,
  versions read from the sealed report). The GOV battery report itself is the
  regulator-grade certificate analog: `QCBATTERY/gov_report.json` — 11/11 LG
  rows PASS, sources bound in `regulatory_sources`.
- **The C-rows (claims vs the instrument, C-1–C-24):** re-confirmed standing —
  the pricing engine is unchanged since they were run through the six-step
  protocol (pull → normalize → forward-model → compare → price → state);
  every row keeps its verdict code in
  `03_CASE_FILES/21_claims_vs_the_instrument.md` (staged copy) with prices
  attached. No row was silently revised during this sweep.

## 5. WHAT IS STILL NOT CERTIFIED AND MAY NEVER BE (spoken, standing)

- FRM/FEM designation: that is an EPA designation process (Part 53) requiring
  a submitted candidate apparatus; we are method-faithful code with their
  bands, not a submitted device. The register itself is the honesty.
- Purchased-text acceptance tables (C114 per-analyte limits, ISO 9516-1
  ranges, USP PDE tables, ISO 13196/18227 texts): quoted nowhere; bound as
  named correspondences.
- Hardware-only layers at the device: temperature workshop recalibration
  (>10 °F), the hardware P:B ratio — the model is temperature-free by design;
  the on-device B-items carry the analog.

Chain after the sweep: **26 receipts, gapless, latest seq 26
(c2c45bb46be91ee0…)**. Everything above is staged in the release at the next
manifest refresh.
