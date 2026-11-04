# XRF-PORTABLE — ARCHITECTURE (ADR-grade)

**Status:** current (engine-1.1.0 · sniffer-1.0.0 · coil-1.0.0) · Documented 2026-11-02 · Suite 226 green; chain seq 1–12 (2026-11-03: seq 10 F1 in-code, seq 11 F3 in-code, seq 12 engineering round 2)

---

## 1. The one-line architecture

```
feed  →  classical chain  →  REGISTER  →  reading layer (Law 2396/2397/2398)  →  sealed receipt
(hash-bound)  (NIST-anchored, NO φ)   (71 metals)  (explicit named step, κ=1)     (ES256 chain)
```

## 2. Design rules (load-bearing)

| # | rule | why |
|---|---|---|
| R1 | **The no-φ guard**: the classical chain contains zero φ; the reading layer enters only through an explicit named step | makes the classical reproduction numbers (0.029% line / 0.089% XCOM) an audit of the split — convention begins where it says it begins |
| R2 | **Refusal walls**: sources required; negative concentrations refused; register drops spoken (never silent); coil readings state their column | no invented numbers, structurally |
| R3 | **Receipts around everything**: report + input hash + ES256 → append-only JSONL (`SESSION_CHAIN.jsonl`); independent verify command | binding, tamper-evidence, time |
| R4 | **Falsifiers registered with the feature** (F1–F6), never after a result | a test that cannot fail is not a test |
| R5 | **Additive growth; version bump on landing**; verdict codes on every claim ([VERIFIED]/[PV]/[INFERENCE]/[DECLARED]/[SIMULATED]) | honest ledger discipline |

## 3. Module map

```
engine/
  metals.py       71-metal register: matched lines, spoken drop record, crust tables
  quantum.py      classical atomic-selection chain (Law 1347/1345 identities, energy splits)
  phi_laws.py     reading layers: phi_motion, ladder_frequencies (asserts invariant), coil_response_phi
  coil.py         the code coil (Law 2397): laws 637/638/801/039/048/675-676 + declared geometry + one anchor
  biochannel.py   the tissue channel (Law 2398): sourced-feed policy, gates G1–G4, refusal walls
  xrf_vendor.py   external cross-check battery (xraylib, PyMca live pulls)
  tests/          130+ tests (classical reproduction, register, coil, biochannel, vendor)
sniffer/
  session.py      session lifecycle: feed fetch → spectrum → inversion → register → receipts
  cli.py          commands: session | metals | battery | verify
  qcbattery.py    the 10-item vendor QA battery (B1..B10 analogs)
  receipt.py      seal/verify/verify-chain (ES256 canonicalization, input.hash, seq linkage)
  air.py          open-meteo feed + forward filter model (Poisson, explicit seed)
FIRMWARE/xrf_portable/   ESP32 port: law2396/coil/battery/scan headers, gen_metal_table.py (deterministic from the register), dashboard
DOCUMENTS/        this suite (+ certificate per battery run via tools/make_certificate.py)
READS/ RESEARCH/ PROOF/ AUDIT/ VENDOR/ QCBATTERY/ TISSUE_CHANNEL/   certified artifacts + campaigns
```

## 4. Data flow & binding (a session, step by step)

1. **fetch** feed (open-meteo; `ok` status bound) → canonical JSON.
2. **hash** the feed (SHA-256 over canonical form) — the same value later signed in the receipt's `input.sha256`.
3. **forward model**: element composition → filter deposit → Poisson spectrum (explicit seed; every seed logged).
4. **classical inversion** (matrix-corrected, Law-cited) → the κ→0 concentration table. *(No φ anywhere before this point.)*
5. **register** (`metals.py`): 71 metals mapped, drops spoken, per-element law audit identities applied.
6. **reading layer** (`phi_laws.py`): `C(κ=1) = φ·C + φ⁻²` — the single named step.
7. **coil ear** (`coil.py`): rung sweep + coin-class check; channel classes spoken; PM-areal sheet below 3σ recorded **as a result**.
8. **seal**: canonical report → ES256 → append to chain; return receipt (seq, hash) → verify command available immediately.

## 5. Failure policy

A verify failure, a battery fail, a floor-tolerance excursion (>10⁻¹², F2), or a refusal-wall trip: the session is quarantined; nothing rewrites history — the chain is append-only; fixes land as **new** receipts. The chain's honesty is the product.

## 6. Extension points (declared)

- New element/window → extend the register + re-run the per-element audit; bump minor.
- New channel (e.g., a drive-coil F3 rig) → new gate following the receipt pattern; new falsifier registered *with* the gate; bump minor.
- Reading-layer change → **major** version + a falsifier table refresh + re-run of the whole validation battery.

## 7. ADR record (decisions made, in order)

| # | decision | standing |
|---|---|---|
| 1 | feed-based instrument, code-only; hardware optional body | adopted (v1.0) |
| 2 | one calibration anchor per channel, physics-scale everything else | adopted |
| 3 | receipts as product, not byproduct | adopted |
| 4 | φ inserted only past a named guard | adopted |
| 5 | refusal walls over validation warnings | adopted |
| 6 | tissue channel + session chain merged (seq 9 seals the Law 2398 reading) | adopted 2026-11-02 |
| 7 | DOCUMENTS suite ships with each package; certificate regenerated per battery run | adopted 2026-11-02 |
