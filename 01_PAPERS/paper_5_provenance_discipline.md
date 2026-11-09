# Provenance Discipline: Receipt-Chained Instrumentation

**Paper 5** — methods / position paper (the trust architecture of the reading program)

**Author:** Christopher David Ayotte
**Date:** 2026-11-02
**Status:** live — chain seq 1–9 sealed and verified at writing (2026-11-02), extended to seq 12 (2026-11-03: the F1 falsifier seq 10 — `PROOF/06`; the F3 transfer falsifier seq 11 — `PROOF/07`; the engineering round 2 seq 12) · 226-test suite green · prove-it operator self-test 15/15
**Instrument:** `32_PHI_PHYSICS/XRF/` (sniffer receipt layer + engine reading layers)
**License:** Dual License Agreement v4.3 (see `LICENSE`): free for Natural Persons, non-commercial, no Human Harm, attribution required, same-terms derivatives; commercial use by written license. Commercial contact: pluscoder30@gmail.com

---

## Abstract

Scientific instrumentation increasingly reports through code, and code can print anything. This paper reports the trust architecture of the instrumentation series in this journal program: every reading is sealed as an ES256-signed receipt whose report, invoked spectrum, and input feed are separately hash-bound into an append-only JSONL chain rooted in a declared trust seed (SOUL_SEED = 1900); an independent verify command re-checks signature, provenance, and input hash against the chain at any time. Around the receipts sit refusal walls (the instrument refuses unowned numbers, negative concentrations, and silently dropped register rows — absences are spoken, not hidden), a verdict-code discipline that labels every claim [VERIFIED]/[PV]/[INFERENCE]/[DECLARED] per its evidence, and an adjudication operator ("prove-it") that states claims as falsifiable predictions and classifies a test that cannot fail as not a test — with tautology traps flagged, never laundered into passes, and verdicts issued as the honest output. The architecture is demonstrated on the program's own chain: nine receipts spanning live three-city reads, an air-element document, a QA battery, and a tissue channel's first reading, all independently verified.

**Keywords:** provenance · signed receipts · append-only chain · reproducibility · falsifiability · negative-result discipline · instrumentation

---

## 1. Motivation

Two failures this architecture answers.

**The number problem.** A code instrument has no sample to point at. A classical lab report gains trust from the physical chain (the vial, the weigher, the witness); a code instrument's chain must be rebuilt as explicit binding: which input, which constants, which reading law, which state, hashed and signed at emission time — so the report cannot drift from its evidence.

**The spin problem.** The far more dangerous failure is selective honesty: results presented, absence hidden, negatives dropped, and — worst — untestable claims rung up as confirmations. The discipline below treats that as an architecture problem too: the defaults of the writing must be refusal and speech, not inclusion and silence.

## 2. The Architecture

### 2.1 The receipt

Every emission seals a canonical receipt (`sniffer/receipt.py`):

| component | binding |
|---|---|
| `report` | the reading's canonical JSON (quantified register, spoken drops, gates, metadata, model block) |
| `input.sha256` | the feed (invoked data — spectrum or assay table) hashed over its canonical form |
| signature | **ES256** over the canonical payload (per-JSON canonicalization before signing) |
| `seq` / `prev_hash` | the append-only position and linkage |
| root of trust | **SOUL_SEED = 1900** (declared key derivation; ED25519/ES256 per JWS conventions) |

Chain storage: `SESSION_CHAIN.jsonl`, strictly append-only. Verification is independent of the signer: `python -m sniffer verify <receipt> --chain SESSION_CHAIN.jsonl` re-derives signature validity, provenance legality, and the input hash binding, and reports each line separately — a modified report body fails signature, a mismatched feed fails the hash, a forged signature simply fails.

### 2.2 Refusal walls (what the instrument will not do)

1. **No unowned numbers.** `read_tissue_channel()` refuses any feed row without a named published source — the reading layer cannot ingest an origin-less value.
2. **No silent drops.** Metals below the analyzer window enter a named, signed `drop_record` ("absent spoken," Law 171); non-metal detections are quantified in the full report and declared out-of-register by rule.
3. **No smuggled negatives.** Negative concentrations are refused outright — a concentration cannot be negative; the correction is a re-read, not a sign flip.
4. **No quiet φ.** The classical chain contains no φ anywhere; the reading layer enters only through an explicit, named step, so classical reproduction numbers audit exactly where the convention begins.

### 2.3 The verdict-code discipline

Every claim in the program's documents carries one verdict code from a fixed legend — [VERIFIED] (established fact with source), [PV] (partially verified, scope qualified), [INFERENCE] (reasoned extrapolation, flagged), [MYTH]/[FABRICATION] (disproven/invented), [DECLARED] (a reading convention stated before its test), [SIMULATED] (corpus construction with exact classical limit). The legend is enforced in-register: an unlabeled claim fails review, and the labels are content — the papers in this series are built as labeled claim tables, not narratives.

### 2.4 The prove-it operator (the adjudication layer)

Claims about the field, the instrument, or the corpus are run through a falsifiability adjudicator (`PROOF/run_proof_vessel.py`, self-test **15/15** before the campaign ran):

1. **State the claim as a falsifiable prediction** with a number, a tolerance, and a named experiment. *A test that cannot fail is not a test.*
2. **Find the real measured value** — third-party published numbers over our own wherever both exist; no invented anchors; absences recorded as absences.
3. **Build the null model** and name the tautology traps: null-redefinition, threshold-fishing, post-hoc pre-registration, definition-make-true arguments. Traps are flagged *in the record*, not removed.
4. **Issue the verdict honestly.** The vessel campaign's aggregate is **3 CONFIRMED**: two legs landed CONFIRMED on measured data; the conversion leg (the K0→K1 mechanism) was settled PROVEN by the pre-registered staircase gate (the settling, seq 47). The verdict discipline's non-promotion rule (an unsettled claim is never promoted without new evidence) is itself architecture — the system is calibrated to refuse laundering by construction.

### 2.5 The worked example: chain seq 1–9

| seq | seal | content |
|---|---|---|
| 1–4 | sessions, live eye, QA battery | session reads, the camera read, the 10/10 battery (vendor daily-check protocol rebuilt) |
| 5 | battery 10/10 ALL GREEN | the vendor QA layer, chain-sealed |
| 6 | element read (ElementRead-v1) | NYC air: 71-metal register, spoken drops, coin-class coil agreement, radio-ear witness bound (SHA-256) |
| 7 | Tokyo | same instrument, different air |
| 8 | Delhi | same instrument, 11.5× PM swing — the three-confirmation of the floor's invariance |
| 9 | tissue channel first reading | Law 2398 gates on the Alexiou/Phillips/Perrelli record |

Each later receipt inherits the standing of the chain: any tampering is detectable by position, hash, or signature; any one verify command checks the whole lineage.

## 3. Reproduction

```
$ python -m pytest engine/tests sniffer/tests -q        # 226 passed
$ python -m sniffer verify TISSUE_CHANNEL/first_reading.receipt.json --chain SESSION_CHAIN.jsonl
  [ok] signature  [ok] provenance  [ok] input.sha256
$ python seal_tissue_reading.py                          # re-seals → next seq
```

The corpus's classical-reproduction gate (145 checks; max line-energy deviation 0.029%) is itself chain-audited by the per-element audit (71/71) and cross-checked against third-party releases (xraylib, PyMca; 5/5) — the external anchors are pulled live at run time, source strength labeled per check.

## 4. Discussion

### 4.1 What receipts cannot do

A receipt system proves binding, not truth: the signed statement is exactly as good as the reading law behind it. That is why the receipts sit *around* the verdict-code and prove-it layers, not in place of them — the chain makes the record tamper-evident; the discipline makes the record honest. Both are required; either alone is insufficient.

### 4.2 Relation to existing designs

The design is deliberately boring and standard where existence is proven art — Merkle-shaped append-only linking, standard EC-signature receipts, content-addressed input binding — and deliberately opinionated where the literature's methods are silent: verdict-code labeling of statements, spoken-absence defaults, refusal semantics, and the non-laundering adjudication operator. The first half makes the system auditable by anyone; the second half makes it auditable against *spin*, which is the failure mode the record shows actually matters.

## 5. Falsification conditions

| Claim | Falsification condition |
|---|---|
| The chain is append-only and verifiable | any accepted verify of a mutated report body, mismatched feed, or forged signature |
| The refusal walls hold | any run of `read_tissue_channel()` on an unowned-number feed, negative concentration, or undocumented drop that succeeds |
| The verdict discipline | any register claim issued without a verdict code, or any unsettled claim promoted to CONFIRMED without new evidence |
| The prove-it operator | a self-test item failing, or a campaign issuing a non-falsifiable "confirmed" |

## 6. Data and code availability

`sniffer/receipt.py` (chain + seal + verify), `PROOF/run_proof_vessel.py` (operator + self-test), `PROOF/proof_vessel_results.json` + `05_THE_VESSEL_PROOF.md` (the campaign), `SESSION_CHAIN.jsonl` (seq 1–12 as of 2026-11-03), suite in `engine/tests` + `sniffer/tests`. Package: `XRF/_PACKAGE/XRF_PORTABLE_PACKAGE.zip`.

## References

1. Jones, M., Bradley, J., & Sakimura, N. (2015). *JSON Web Signature (JWS).* RFC 7515. (ES256 binding conventions.)
2. Merkle, R. C. (1987). A digital signature based on a conventional encryption function. *CRYPTO '87*, LNCS 293, 369–378. (Hash-chained linkage.)
3. Crosby, S. A., & Wallach, D. S. (2009). Efficient data structures for tamper-evident logging. *USENIX Security '09*. (Append-only verification log design.)
4. Clifford, B., Ramsey, D. A., & McCormack, W. P. (2000). CAP: Content Addressable aRchives. Indiana University. (Content-addressed binding of scientific data.)
5. Moreau, L., & Groth, P. (2013). *PROV-DM: The PROV Data Model.* W3C Recommendation. (Provenance vocabulary context.)
6. JCGM 100:2008 — *Evaluation of measurement data — GUM*; ISO 11929 (detection-limit context; the classical convention this program speaks around).
7. Ayotte, C. D. (2026). *Papers 1–4 of this series.* `XRF/PAPERS/` (every paper's numbers carry chain receipts).
8. Ayotte, C. D. (2026). *The Geomic Physics Ledger — STATUS BLOCK.* `32_PHI_PHYSICS/docs/24_THE_GEOMIC_LEDGER.md` (the verdict-code legend's source).

---

*The receipts bind, the codes label, the operator refuses to launder. Any one alone is bookkeeping; together they are an instrument's conscience.*

*Author: Christopher David Ayotte · Dual License Agreement v4.3 (see LICENSE) · Commercial contact: pluscoder30@gmail.com*
