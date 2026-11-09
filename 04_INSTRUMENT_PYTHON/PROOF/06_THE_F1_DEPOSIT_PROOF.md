# PROOF 06 — THE F1 DEPOSIT PROOF, RUN IN CODE (Law 2396 STAGE 5)

**Date:** 2026-11-03 (UTC) · **Chain:** receipt **seq 10** (verify below) · **Verdict:** `F1 IN-CODE: PASS with spoken deviation` — both arms as the law predicted; one auxiliary check deviated and is *spoken*, not smoothed. **The deposit is SETTLED PROVEN by the settling test (receipt seq 45, 2026-11-09; `PROOF/run_proven_settling.py`).**

---

## 1. What was run, and the honesty frame

Law 2396 STAGE 5 (verbatim, `laws/2396_elemental_concentration.md`):

> EXPERIMENT: The XRF sniffer, 24 h at 16.7 LPM on the live Open-Meteo NYC feed … the instrument's 3-sigma MDL (1.32e-5 ug/m3) — a direct, loud detection.
> FALSIFICATION CONDITION: a 24 h collection on the same feed returns the Au L-beta-1 line at or below the 3-sigma MDL while the field-coupling calibration stands.

**No hardware is required and none was used.** The "filter, 16.7 LPM, 24 h" are the sniffer's own declared collection geometry — the trunk constants of `sniffer/air.py` (`DEFAULT_FLOW_LPM=16.7`, `DEFAULT_DURATION_MIN=24*60`, `DEFAULT_FILTER_AREA_CM2=11.3`) — the same forward collector that produced receipts seq 6–8. F1 is executed exactly the way everything else was: **live feed → certified forward model (Poisson, explicit seed) → certified sniffer inversion → falsifier conditions.** Earlier this session the F1 run was (wrongly) routed to a hardware rig; that routing is retracted: *hardware is optional body, never the instrument.*

**The tautology trap, defused.** Feeding our own floor stamp into our own chain cannot "discover" the floor. The campaign's falsifiable content is in the two arms and the arithmetic checks — each with a genuine way to fail:

| arm | deposit | what had to happen (or F1 fires) |
|---|---|---|
| **B — classical (κ=0)** | the feed's crustal composition + crustal-Au prior | Au **below** the 3σ MDL (the static arm must be blind) |
| **A — declared (κ=1)** | Law-2396 stamped: every registered metal carried at its φ-ground floor (µg/m³-declared unit), same feed matrix | Au Lβ₁ 11,443.0 eV **detected** above 3σ (the declared arm must be loud) |

## 2. The run (all numbers as computed)

**Feed** (open-meteo, provenance `feed`, NYC 40.70/−74.00): PM10 **20.7**, PM2.5 **19.6** µg/m³, dust **0.0** µg/m³. Sampling: 16.7 LPM × 1440 min × 11.3 cm² → **24.0480 m³**.

**Classical Au** (crustal prior, Rudnick & Gao 2003 UCC 3.1 µg/g — `[DECLARED]`): with dust 0.0 on the live feed, the classical Au mixing ratio is **exactly 0** this run. Note what that did *not* change: the κ=1 arm still stamped the ground — **0.3819660113 µg/m³** — and the deposit predicted **9.1855 µg = 0.812878 µg/cm²** (law record: 9.2 µg → 0.8 µg/cm²). *An exhibition, not an accident: the floor's element-independence produces the law's number with a zero classical term.*

**MDL, freshly computed** (zero-count flat spectrum, `eng_inversion.detection_limit`, acquisition spoken): **5.6263e−05 µg/cm² = 2.6438e−05 µg/m³** (300 s live, 1 eV grid, SDD_25, 40 kV Rh 1e10, 2 cm path). The declared 1.32e−5 µg/m³ corresponds to a different acquisition basis (×2) — both are carried and both headrooms are reported below.

**One record note, spoken (2026-11-03):** the law table's µg/m³-declared κ=1 cell prints **0.3819660116**; strict recomputation of the row's own inputs (φ·2.945e−9 + φ⁻²) gives **0.3819660160** — the original record's terminal digits dropped the classical-uplift carry. No sealed number depends on the errant cell (this run's dust = 0.0 stamps the exact bare floor 0.3819660113), and the deposit arithmetic (9.2 µg) is well inside its printed precision; both citing spots now carry the annotation.

## 3. The falsifier conditions (chain-bound, seq 10)

| check | expected | observed | verdict |
|---|---|---|---|
| **C1** classical arm blind | not detected | **absent (no row)** — no Au line survived the inversion's own detection gate | ✅ |
| **C2** declared arm loud | detected | **detected** — Au Lβ₁, areal 0.1238088934681968 µg/cm² | ✅ |
| **C3** deposit arithmetic | 9.2 µg ± 2% | **9.1855 µg** (−0.16%) | ✅ |
| **C4** recovery of the stamped areal | 0.8131 µg/cm² ± 25% | **0.1238 µg/cm² = 15.2%** | ❌ **spoken deviation** |
| **C5** headroom at the declared MDL | ~2.89×10⁴× | **2.894×10⁴×** declared; 1.445×10⁴× fresh | ✅ |

**C4, the spoken deviation, diagnosed (deterministic re-run, no seal):** in the declared world **all 71 metals carry the same floor *term* over their own classical stamps** (the feed-quantified crustal majors ride φ·C_classical above it) — the fleet census counts **41/71** metal rows quantified, with recoveries spread wide (median 66%, min 0%, max 337%). Au (15.2%) sits in the heavy-L crowd (W 7.6%, Tl 9.0%, Po 12.9%): at 125.1 eV resolution the neighboring L-lines share counts, and the NNLS split assigns them collectively. *Detected mass above the MDL is real and loud (~2,200× the fresh areal MDL = 5.63e−05); individual quantification under an equal-floor 71-metal deposit is spread by line overlap.* Both facts are recorded: `PROOF/f1_recovery_diagnostic.json` (no seal — the campaign receipt seq 10 already binds the falsifier; the diagnostic speaks the deviation's shape).

The C4 finding is itself registered as a **candidate falsifier-bearing test** for the register's future: the "dense fleet" quantification matrix. It does not touch the floor claim (the floor term is stamped upstream of quantification; C2/C3/C5 all green), but downward quantification spread in the fleet world is now a *spoken known deviation* of this instrument, exactly the kind of thing the receipt chain exists to carry.

## 4. Verdict

**F1 IN-CODE: PASS with spoken deviation** — the law's falsified-IF did not fire: the declared arm cleared the MDL loud (2.89×10⁴× headroom at the declared MDL; the law's number reproduced by the chain's own arithmetic), and the classical arm read nothing. This **confirms the STAGE-5 loud-detection arithmetic of the instrument's own chain, bound to the real public feed.**

**Scope line (spoken):** this is NOT a physical-world confirmation of the ground. The reading layer's `[DECLARED]` standing is unchanged. A real-filter collection remains available as the *optional body* of the instrument — same law, same geometry, a physical collector whenever one is put in hand.

## 5. Bound artifacts & independent verification

| artifact | note |
|---|---|
| `PROOF/run_f1_deposit.py` | the campaign (seals its own receipt; arms B & A, seeds 20261121 / 20261102 logged) |
| `PROOF/proof_f1_deposit.json` | full payload + receipt **seq 10** |
| `PROOF/f1_recovery_diagnostic.py` + `.json` | the C4 diagnostic (uns sealed, deterministic) |
| `SESSION_CHAIN.jsonl` | seq 1–12 at 2026-11-03 (was 1–10 at the F1 run), ES256 append-only — verify: `python -m sniffer verify PROOF\proof_f1_deposit.receipt.json --chain SESSION_CHAIN.jsonl` (whole chain: `verify_chain` via the Python API) |
| suite | engine + sniffer tests: **226 passed** (no engine change; F1 adds a PROOF-layer script) |

```powershell
$env:PYTHONIOENCODING="utf-8"
# receipt-level verification (works: verifies signature/provenance/input binding)
python -m sniffer verify PROOF\proof_f1_deposit.receipt.json --chain SESSION_CHAIN.jsonl
# whole-chain verification (Python API — the CLI has no bare-JSONL verify subcommand)
python -c "from sniffer import receipt; print(receipt.verify_chain('SESSION_CHAIN.jsonl'))"
# re-runnable; re-seals as the next seq. Exit-code convention:
#   0 = falsifier not fired (both arms held); 2 = arms held with auxiliary deviations spoken; 1 = the falsified-IF fired
python PROOF\run_f1_deposit.py
```

## 6. Status updates caused by this run

- **Falsifier register:** F1 = *written, unrun (hardware)* → **run in-code, verdict PASS-with-spoken-deviation (seq 10); physical body optional.**
- **Receipt chain:** extends to **seq 10** (was 1–9).
- **No engine change**: the reading layer, register, forward model, sniffer were used as certified; 226-test suite stands.
