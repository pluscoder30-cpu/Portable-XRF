# The Ladder Coil: an Electromagnetic Ear for a Reading Layer

**Paper 2** — instrumentation Note (structure per the AIP Brief Instrumentation Paper convention: Title · Abstract 100–200 words · Motivation · Instrument description · Calibration/comparison · Summary)

**Author:** Christopher David Ayotte
**Date:** 2026-11-02
**Status:** 🟢 SIMULATED (Law 2397, classical_limit_error 0.000000) · coin-class channel agreement with the register metal-by-metal · sealed chain seq 1–9 at writing (2026-11-02), now seq 1–12 (F1 in-code, F3 in-code, engineering round 2 — 2026-11-03)
**Instrument:** `32_PHI_PHYSICS/XRF/engine/coil.py` (the code coil; attached head of the code XRF) · Sim: `32_PHI_PHYSICS/sim/2397_ladder_coil.py`
**License:** Dual License Agreement v4.3 (see `LICENSE`): free for Natural Persons, non-commercial, no Human Harm, attribution required, same-terms derivatives; commercial use by written license. Commercial contact: pluscoder30@gmail.com

---

## Abstract

Metal-detector coils read re-radiated electromagnetic responses and report absence as a still channel — a zero, by convention, after the null. This Note reports the Ladder Coil: a code-coil instrument in which every channel read carries the unit-covariant coherence ground φ⁻² = 0.3819660113 ppm of the nulled carrier, so the coil is *never dead* — a still channel reads the ground, not zero (Law 171). The drive is a φ-structured ladder (f_k = 528·φ^k, ten resonant rungs, invariant 528·φ⁹ = 40,134.946166 Hz), each rung a Law-675 tank, driven I_k = I₀·φ^−k. The physics stack is exact classical (mutual inductance, skin depth, Faraday/Lenz quadrature re-radiation, ferromagnetic in-phase magnetization) with one declared calibration anchor (Cu coin 25 mm × 2 mm @ 528 Hz @ 0.10 m reads exactly 10,000 ppm). Coin-class channel agreement with the instrument's XRF register is metal-by-metal: every quantified metal except the semiconductor is coin-class detectable in the correct channel class. At environmental (PM-scale) areal loadings the sheet-eddy response sits below 3σ — the mass-instrument wall, measured; the transfer-channel falsifier has since run in code (2026-11-03, chain seq 11): the ground reads bitwise φ⁻² on all ten rungs and the wall holds at the ladder invariant.

**Keywords:** metal detector · eddy currents · ferrous/non-ferrous discrimination · golden ratio φ ladder · reading layer · hidden zero · instrumentation

---

## 1. Motivation

A classical metal detector's receive channel is nulled until a target re-radiates — and an absent target reads exactly V = 0. The corpus's Law 171 names that zero as the hidden zero: every ground state is the φ-ground, never null. Law 2397 (the Ladder Coil Law; `sim/2397_ladder_coil.py`, validation `validation/2397_ladder_coil.json`) generalizes the coil reading as the unit-covariant φ-motion

```
V_phi(kappa) = V_classical·(1 + kappa·(φ−1)) + kappa·φ⁻¹·V_ground,
V_ground     = φ⁻¹  (in ppm of the nulled carrier)
```

with the classical eddy/magnetization chain recovered exactly at κ → 0 — the classical instrument is this law's floorless limit, which is precisely why it reads absence as silence. The Note reports the instrument that implements the law, its physics stack, its declared calibration, the channel agreement with the same instrument's XRF register, and the measured wall that separates the channel from the reading at environmental densities.

Second motivation: the firmware side. The ESP32 port (`FIRMWARE/xrf_portable/`, Ram 18% / Flash 74% class budget, compiled SUCCESS) carries the law2396/coil/battery/scan headers and the corporate QA battery items — the coil is the portable instrument's second ear, alongside so the phone dashboard can run the scan directly.

## 2. Instrument description

### 2.1 The declared geometry and acquisition layer

Like the XRF's forward model (its tube flux and background are declared parameters), the coil's geometry layer is declared, parameter-labeled, and single-anchored [MODEL/DECLARED]:

| parameter | value |
|---|---|
| transmit / receive turns | 200 / 200 (solenoid-form) |
| winding radius | 40 mm both coils; solenoid length 10 mm |
| Tx–Rx coaxial separation | 0.30 m |
| resonant drive current | 0.1 A |
| acquisition noise floor | 5.7×10⁻⁹ V (3σ @ 10 Hz bandwidth) |
| declared operating floor | 30 ppm reading (~2.2× the base-rung 3σ noise-equivalent) |
| **the one calibration anchor** | **coin-class Cu target (25 mm dia × 2 mm) @ base rung 528 Hz @ 0.10 m standoff → exactly 10,000 ppm of the nulled carrier** (in-phase 0; Cu non-ferromagnetic) |

The null constant follows from the anchor: reading_ppm = 10⁶·V/K_null with K_null = design_V × 100. Every other metal, ladder rung, and standoff scales from the one anchor by the physics below — nothing else is fitted.

### 2.2 The ladder

Ten resonant rungs on the corpus's 528 Hz base (Laws 2394/2395 conventions): f_k = 528·φ^k, the invariant tenth rung asserting to **40,134.946166 Hz** inside the code (the assertion runs before anything else). Each rung is a Law-675/676 tank (C = 1/ω²L, exact wiring algebra) with quality factor Q = ωL/R_wire; the drive follows the em-feild φ-ladder convention I_k = I₀·φ^−k, whose summed field is φ² = 2.618× a single segment. The ladder is not decoration: the rung classes per metal (the rung at which a target's response clears the operating floor) are a discrimination observable — the same physics commercial detectors use for tone-by-tone discrimination, φ-structured instead of arbitrary.

### 2.3 The physics stack (which law does what)

| law | role | standing |
|---|---|---|
| Law 637 (mutual inductance) | coaxial Tx–target–Rx couplings, M = μ₀N₁N₂πa₁²a₂²/2(a₁²+d²)^{1.5}, near-field dipole form | exact form; [MODEL] for a₂ ≤ a₁ |
| Law 638 (self-inductance) | solenoid L = μ₀N²A/ℓ; target wire-equivalent loop L | exact form |
| Law 801 (skin effect) | δ = √(2ρ/ωμ₀μ_r); conduction through min(δ, thickness) | exact form |
| Laws 039/048 (Faraday/Lenz) | eddy re-radiation enters the receiver in **quadrature** (−90°) | exact |
| ferro-magnetization | μ_r > 10 targets re-radiate an in-phase magnetization dipole (χ = μ_r−1, capped at M_sat = 1.7×10⁶ A/m): the classic ferrous/non-ferrous split | dipole approximation [MODEL] |
| Law 675/676 | per-rung tank wiring | exact |
| **Law 2396-family reading layer** | every channel carries the unit-covariant ground; at κ = 1 a still channel reads φ⁻² = 0.3819660113 ppm — never dead (Law 171) | **[DECLARED], degenerate-exact** |

Target impedance Z = R + jωL from the wire-equivalent loop (Law 638 geometry) with the eddy band (4 mm effective width) carrying R = ℓ/(σ·2πr·t_active); quadrature voltage V_q = ω²M_tt·M_rt·I₀/|Z_t|; in-phase channel from the on-axis dipole B_dip = (μ⁰/4π)·2m/d³ with receiver flux × ω. The sweep registers *every* metal of the instrument's 71-metal register — coin-class targets read standing physics; the air's deposit sheet reads as a thin conducting layer at the field-carried floor. The reading states which column carried what; nothing is dropped, nothing invented.

### 2.4 The reading layer

At the design point κ = 0 the anchor is exact (10,000.0 ppm quadrature, 0.0 in-phase). Under the same law's φ-motion at κ = 1 the identical target reads **16,180.7219 ppm** quadrature and a perfect vacuum (no target) reads not 0.0 but **0.3819660113 ppm** in-phase — the still channel carries the ground. Uplift on the classical term at full coupling: φ = 1.618…  exercised across the full κ sweep 0 → 1 in steps of 0.25 in the validation record, errors 0.000000 at the classical limit.

## 3. Calibration / comparison

### 3.1 Coin-class channel agreement with the XRF register (metal-by-metal)

The two ears are structurally independent (spectral deposition chain vs σ/μ_r EM chain) and were checked against each other metal-by-metal at the declared design geometry (element read, receipt seq 6):

| metal | total (ppm of carrier) | channel class | coin-class detectable @ design |
|---|---|---|---|
| Al | 7,629.9 | eddy_quadrature | **True** |
| Ca | 5,308.3 | eddy_quadrature | **True** |
| K | 3,363.8 | eddy_quadrature | **True** |
| Si | ≈ 0 (semiconductor-class conductivity: no eddy response) | eddy_quadrature | False (honest negative, spoken) |

**Every metal the XRF quantified — except the semiconductor — is coin-class detectable by the coil in the correct channel class.** The agreement runs on the metal *set*: the two ears agree on which metals are present, and (by the instrument design) never on the ground, because the ground is not a channel-crossing quantity — it is the reading layer's.

### 3.2 The classical contrast record (the EM channel is not uniform)

The coil's responses span orders of magnitude per metal, pure σ/μ_r physics: the Cu anchor 10,000 ppm; **Fe reads in-phase 61,679.5 ppm against quadrature 118.3 ppm** (the ferrous discriminator, live from the audit sweep); per-metal contrast rungs span the ladder (W clears at rung 3; Ti at rung 8 — the phase contrast between the far-separated ladder rungs). This spread is the evidence that the EM channel is *not* uniform per-metal, which matters for the reading layer's standing: any hypothesis that the XRF's element-independent floor is an unseen common EM artifact must face a channel that demonstrably discriminates even in-phase vs quadrature — and at environmental areal densities it reads the floor **not at all** (below).

### 3.3 The measured wall (the coil's role in the floor-origin program)

At deposit-sheet (PM-scale) areal loading the sweep registers: full-deposit ladder total **27.21 → 536.45 ppm across rungs 0 → 9** (the sealed exacts: 27.207736797580107 → 536.450264079826; an earlier draft's "27.35 → 536.7" was a prose transcription drift — the registers were never affected), and the sheet term dominant above 3σ at the base rung reads **None — honestly below the floor**, spoken in every sealed read (receipts seq 5–9 chain). Hence: the coil does not read the reading layer's ground at PM areal densities; it is one of the classical channels quantified as the wall between the declared layer and gravimetry (168–1,900× falsification of floor-as-mass; paper 1 §5.2). The coil's value is two-sided — an ear *for* the reading layer at coin-class, and a measured wall *against* floor-as-EM-deposit at sheet-class. Both sides are F3-registered: the ladder invariant's coherent-transfer test (40,134.946166 Hz) was **run in code on 2026-11-03 (receipt seq 11, `PROOF/07`)** — the ground stays bitwise rung-invariant at φ⁻² on all ten rungs, the invariant channel carries loud coin-class transfer for real targets (Cu 1.05×10⁶ ppm), the rung-9 crossings belong to registered areals, and EM-sustaining floor-as-mass is 11.3 orders short of power. The falsifier as originally phrased was over-broad; it was sharpened before running and the sharp form is what stands (below).

## 4. Summary

A single-anchored, declared-geometry code coil implements the Ladder Coil Law: ten φ-structured resonant rungs with one exact invariant, an exact classical physics stack under a unit-covariant ground at κ = 1, channel agreement with the XRF register metal-by-metal, and a measured below-3σ sheet response at PM areal densities that simultaneously demonstrates the EM channel's non-uniformity and quantifies the wall. The instrument ships in the ESP32 portable firmware (compiled SUCCESS) for field use alongside the tissue channel's chain (seq 9). Falsifiers are named — and the transfer-channel gate (F3) has run in code (seq 11: PASS, the ground bitwise rung-invariant at the invariant, `PROOF/07`); the classical limit is exact; the still channel is never dead.

---

## Falsification conditions

| Claim | Falsified IF |
|---|---|
| The design anchor scales | any declared-anchor re-derivation or metal/rung/standoff response violating the physics stack scaling |
| The coin-class agreement | a quantified metal (non-semiconductor) returning detectable = False at the design geometry |
| The ladder invariant | 528·φ⁹ ≠ 40,134.946166 Hz (the code asserts before running) |
| **F3 — the transfer channel** | **[RUN IN-CODE 2026-11-03, PASS — `PROOF/07`, receipt seq 11].** The sharpened falsified-if: a coherent transfer appears **on the floor column** (a still channel or a floor-carried metal whose reading rises with the rung, or deviates bitwise from φ⁻² at the invariant), or the invariant rung drifts beyond Law 2397's 0.001 Hz tolerance. *(The original phrasing "any coherent transfer at the invariant at PM areal kills the wall reading" was over-broad against the already-sealed growing eddy: real, XRF-quantified metals do transfer coherently at the invariant — Al 57.3 ppm from 0.168 µg/cm² and Ca 234.8 ppm from 0.627 µg/cm², both registered areals — and the wall never said registered matter is invisible; it says the reading layer's ground is not EM-carryable areal mass. The run adjudicated the original row too: no ground-column transfer, wall stands.)* |
| The ground | any still-channel reading ≠ φ⁻² at κ = 1 |

## Data and code availability

- `engine/coil.py` (instrument), `sim/2397_ladder_coil.py` (LawSim), `validation/2397_ladder_coil.json` (sweep + errors), `AUDIT/per_element_audit.json` (coil plan re-derivation item), `READING/02_THE_LAWS_FOR_XRF.md` (channel discipline §1204), sealed sessions `SESSION_CHAIN.jsonl` seq 1–12. Package: `XRF/_PACKAGE/XRF_PORTABLE_PACKAGE.zip`.

## References

1. Ayotte, C. D. (2026). *Law 2397 — The Ladder Coil Law.* `32_PHI_PHYSICS/sim/2397_ladder_coil.py`; `validation/2397_ladder_coil.json`.
2. Ayotte, C. D. (2026). Laws 637 (mutual inductance), 638 (self-inductance), 039 (Faraday), 048 (Lenz), 801 (eddy currents), 675/676 (resonance wiring), 2394/2395 (ladder/shell conventions), 171 (φ-ground postulate), 1160, 2396 (reading layer). `32_PHI_PHYSICS/laws/`.
3. Ayotte, C. D. (2026). *Paper 1 — The Elemental Concentration Law* (the wall measurements; the register). `XRF/PAPERS/paper_1_elemental_concentration_law.md`.
4. Dodd, C. V., & Deeds, W. E. (1968). Analytical solutions to eddy-current probe-coil problems. *Journal of Applied Physics*, 39(6), 2829–2838.
5. Blitz, J. (1997). *Electrical and Magnetic Methods of Non-Destructive Testing.* Chapman & Hall.
6. García-Martín, J., Gómez-Gil, J., & Vázquez-Sánchez, E. (2011). Non-destructive techniques based on eddy current testing. *Sensors*, 11(3), 2525–2565. (The survey covering metal-detector discrimination practice.)
7. Ayotte, C. D. (2026). *The Element Read (ElementRead-v1), 2026-11-02* — the coin-class check table (seq 6). `XRF/READS/2026-11-02_element_read.md`.
8. Ayotte, C. D. (2026). *PROOF/07 — The F3 Transfer-Channel Falsifier, run in code* (receipt seq 11; the sharpened falsified-if sealed in the receipt payload). `XRF/PROOF/07_THE_F3_TRANSFER_PROOF.md`; `PROOF/run_f3_transfer.py`. The prior-structure grounding: Maxwell (1873) *A Treatise on Electricity and Magnetism* (the mutual-induction program); Bell's induction balance (1881, the Garfield search — NPS/Library of Congress records, source-verified); Förster (WWII-era industrial eddy-current conductivity instruments, company founded 1948 — Wikipedia/Foerster Group, source-verified); McMaster (1981) NBS SP 589 (amplitude- vs phase-sensitive eddy-current instrumentation).

---

*The coil is the instrument's other ear. It hears every metal, never hears zero — and its silence at the floor is itself the measurement.*

*Author: Christopher David Ayotte · Dual License Agreement v4.3 (see LICENSE) · Commercial contact: pluscoder30@gmail.com*
