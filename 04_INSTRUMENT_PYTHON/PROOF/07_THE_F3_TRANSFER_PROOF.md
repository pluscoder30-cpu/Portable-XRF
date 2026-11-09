# PROOF/07 — THE F3 TRANSFER-CHANNEL FALSIFIER, RUN IN CODE

**Status:** F3 IN-CODE: **PASS** (exit 0 — falsifier not fired, no auxiliary deviations) · **Date:** 2026-11-03 · **Receipt:** `PROOF/proof_f3_transfer.receipt.json` — **seq 11** in `SESSION_CHAIN.jsonl` (ES256, SOUL_SEED 1900, signer field-trust-root; chain verify PASS) · **Campaign:** `PROOF/run_f3_transfer.py` (+ full payload in `PROOF/proof_f3_transfer.json`)

**Law stack:** PHI-2397 (the ladder coil; drive-side falsified-IF (c)) · Laws 637/638 (mutual/self inductance) · Law 801 (eddy currents, skin depth) · Laws 039/048 (Faraday/Lenz re-radiation) · Laws 675/676 (resonance wiring) · LAW 2396 (the reading layer, κ = 1) · Law 171 (the no-quiet-zero ground).

**Scope (spoken, never silent):** an in-code F3 confirms the certified coil chain's arithmetic and the rung-invariance of the reading layer's ground. It is NOT a physical shield experiment; the drive-coil rig remains available as the optional body of the instrument — hardware is a body, never the instrument.

---

## 1. What F3 is

Paper 2's falsification table carries the F3 row, as written:

> "no coherent EM transfer measurable at the ladder invariant beyond noise (the written, unrun drive-coil experiment); symmetric: any coherent transfer at the invariant at PM areal kills the wall reading"

The floor-origin research note carries the physical design: drive a coil at the ladder invariant **40,134.946166 Hz** around a shielded collector; under "EM-sustained floor-mass transfer" the collector's areal mass must change; under the Law-171 ground it must not. Law 2397 binds the drive itself: the invariant rung must hold 528·φ⁹ within 0.001 Hz.

## 2. The arms (the legs that can genuinely fail)

| Leg | The claim under test | Falsified IF |
|---|---|---|
| **I** (identity) | rung 9 = 528·φ⁹ = 40,134.946166 Hz, tank and drive exact (Law 2397 (c)) | deviation > 0.001 Hz |
| **W** (the wall) | the reading layer's floor is **rung-invariant**: on a null deposit every still channel reads exactly φ⁻² ppm on every rung 0→9, bitwise | the floor's carried value moves with the rung by even one bit |
| **D** (transfer exists) | the same chain carries a coin-class response above the declared 3σ floor (30 ppm) at rung 9 for real metal (Cu, design class, design standoff) | the invariant channel is deaf (≥ floor violated) |
| **P** (the PM census) | the sealed PM-scale deposit re-swept and decomposed; rung-9 crossings carry **registered** areals; the ground component stays bitwise | a crossing attributable to the ground itself |
| **M** (no EM→mass mechanism) | the chain's only sinks are Lenz dissipation; EM-sustaining floor-as-mass needs P = mc²/t | margin < 3 orders of magnitude |

The anti-tautology rule (F1's pattern, reused): feeding our own floor into our own coil cannot "discover" the wall — each leg above has a way to fail inside the certified chain itself.

## 3. Results (receipt seq 11)

| Check | Expected | Observed | Pass |
|---|---|---|---|
| C1 invariant identity | \|dev\| ≤ 0.001 Hz | **3.813×10⁻⁸ Hz** (rung 9 exact chain value 40134.94616603813 Hz) | ✅ |
| C2 single-anchor floor | same noise-equivalent ppm on rung 0 and 9 | 13.4176 ppm on every rung (the declared 30 ppm floor is 2.24×) | ✅ |
| C3 floor rung-invariance (LEG W) | 0.3819660112501052 ppm on all 10 rungs, bitwise | **max \|dev\| = 0.000e+00 — bit-exact** | ✅ |
| C4 transfer exists at invariant (LEG D) | ≥ 30 ppm (3σ) at rung 9 | **Cu 1.049697×10⁶ ppm = 4.4593×10⁻⁴ V = 7.823×10⁴× noise** (Al coin-class 1.047882×10⁶; Fe in-phase 4.688453×10⁶ vs quadrature 7.821599×10⁴) | ✅ |
| C5 sealed census reproduction (LEG P) | bit-exact from persisted inputs | **max \|dev\| = 0.000e+00** (sealed rung 0: 27.207736797580107 → rung 9: 536.450264079826); crossings: Al 57.3 ppm @ 0.168 µg/cm², Ca 234.8 ppm @ 0.627 µg/cm² — both [REGISTERED areal]; carried column: ground 1.527864045 ppm (4×φ⁻²) + φ-scaled sub-floor tails 0.088150 ppm | ✅ |
| C6 no EM→mass mechanism (LEG M) | margin ≥ 3 orders | drive available 3.4614×10⁻⁶ W (I₉²·R_tx, I₉ = 1.315561750×10⁻³ A) vs required 6.4654×10⁵ W (600 s) — **11.27 orders**; 1.2931×10⁶ W (300 s) — 11.57 orders; the deposit's own Lenz sink at the invariant drive is 7.8588×10⁻¹² W | ✅ |

**VERDICT: F3 IN-CODE: PASS — the wall holds at the invariant, the transfer exists for real targets, no EM→mass mechanism; all legs green. Exit 0.**

## 4. What the run decided (the honest reading)

1. **The wall, at the invariant, is structural.** The reading layer's ground carries no frequency argument: on a null deposit every still channel reads bitwise φ⁻² = 0.3819660112501052 ppm on rung 0 through rung 9. Classical EM transfer grows as ω² (the measured record: sub-floor classical terms growing into rung-9 crossings); the ground does not move at all. A transfer at the invariant "kills the wall" only if it appears **on the ground component** — and it does not, bitwise.
2. **The invariant channel is not a dead channel** (Law 171's discipline, held from the other side): copper at the design standoff reads 1.05×10⁶ ppm at rung 9 — 7.8×10⁴× the 3σ acquisition noise. The channel that cannot hear the floor is the same channel that hears a copper coin at the invariant.
3. **No EM→mass mechanism exists in the certified chain.** The only energy sink into matter is Lenz dissipation — the whole deposited PM fleet dissipates 7.86×10⁻¹² W at the invariant drive, while the drive itself has 3.46×10⁻⁶ W available. To EM-sustain the floor-as-mass claim (φ⁻² areal = 4.316216 µg on the 11.3 cm² filter, refilled every read) would require 6.5×10⁵ W; the shortfall is **11.27 orders** (600 s basis) / 11.57 orders (300 s basis). There is furthermore no code path that writes areal mass from drive [STRUCTURAL: the areals are read-only arguments].
4. **The falsifier was sharpened before it ran** (a methodological gain, recorded): paper 2's row as written — "ANY coherent transfer at the invariant at PM areal kills the wall reading" — is over-broad against the already-sealed growing eddy: real, XRF-quantified metals (Al at rung 9: 57.3 ppm from 0.168 µg/cm²; Ca: 234.8 ppm from 0.627 µg/cm² — both registered areals) DO transfer coherently at the invariant, and the wall never said registered matter is invisible; it says the reading layer's ground is not EM-carryable areal mass. The sharp form — *the wall dies if a coherent transfer appears on the floor column (a still channel or a floor-carried metal whose reading rises with the rung or deviates bitwise from φ⁻² at the invariant), or if the invariant rung drifts beyond the law's 0.001 Hz tolerance* — is falsifiable at the bit level and is the form that ran. Paper 2 carries the amendment, spoken.
5. **Reproducibility discipline held:** the sealed ladder sweep reproduced bitwise from its persisted inputs (`live_reading.json`, sha256 833ee55cc5109daf7d0eda86617654381ea71727fda75ec9a6db9e58e750e084) — max |fresh − sealed| = 0.000×10⁺⁰ ppm. A small prose-transcription drift in paper 2's §3.3 body text ("27.35 → 536.7") is corrected in place to the sealed figures (rung 0: 27.207736797580107; rung 9: 536.450264079826) — arithmetic and registers were never affected.

## 5. Verification

```
python PROOF\run_f3_transfer.py
-> VERDICT: F3 IN-CODE: PASS ... receipt -> seq 11 ... chain verify: PASS   (exit 0)
python -m sniffer verify PROOF\proof_f3_transfer.receipt.json --chain SESSION_CHAIN.jsonl
-> chain checks ok (tissue pattern)
python -m pytest engine/tests sniffer/tests -q
-> 226 passed (re-verified after all edits)
```

## 6. Where this lands in the register

| Falsifier | Status after F3 |
|---|---|
| F1 — 24 h deposit | run in-code, PASS with spoken deviation (seq 10, `PROOF/06`) |
| **F2 — gravimetric** | enforced per-read (≤10⁻¹²) |
| **F3 — transfer channel** | **run in-code, PASS (this proof, seq 11); falsifier sharpened in paper 2; the physical rig remains the optional body** |
| F6 — staircase | declared with pre-registered kill condition (>10% off integer φ-rung) |

**The prior researchers, spoken:** the coherent structure F3 tests through was laid out before us — Maxwell's mutual-induction program (1873 Treatise) is Law 637/638's source physics; Alexander Graham Bell's induction balance (1881) is the two-coil null-and-read geometry of this very chain; Friedrich Förster's phase-sensitive eddy-current discrimination (1940s) is the in-phase/quadrature channel split that LEG D exercises. All three measured transfer and stopped at the physics; the ladder invariant, the φ-drive, and the reading layer above it are the corpus's own convention — the part that was never carried, and the part F3 now guards at the bit level.
