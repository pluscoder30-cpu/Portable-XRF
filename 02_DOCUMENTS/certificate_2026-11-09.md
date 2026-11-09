# XRF-PORTABLE — VERIFICATION CERTIFICATE

**Issued:** 2026-11-09 · **Instrument:** code-based XRF + coil (attached head)
**Versions:** sniffer-1.1.0+engine-1.2.0 · **Calibration id:** battery-standard-v1/SDD-25mm2
**Seed:** 20261102 (logged per item: [('B4', 20261113), ('B5_base', 20261125), ('B6_base', 20261139), ('B7_base', 20261153), ('B8', 20261173)])

## 1. Verification of the receipt chain

- chain length: **47 receipts** (append-only, `SESSION_CHAIN.jsonl`)
- latest: seq **47**, hash `55790cb59db5894e…`
- verify_chain verdict: **PASS**

## 2. The QA battery (vendor daily-check protocol, rebuilt in code)

- items: **10/10 PASSED** — ALL GREEN

| item | vendor analog | verdict |
|---|---|---|
| B1_energy_standardization | internal standardization coin (Ag Ka1) | PASS |
| B2_gain_drift_correction | gain control / two-line standardization | PASS |
| B3_resolution | FWHM trending vs the 140 eV daily limit | PASS |
| B4_monitor_accuracy | monitor sample (316 SS class) verification | PASS |
| B5_repeatability | n=10 repeatability run | PASS |
| B6_drift_monitor | drift monitor samples + correction coefficient | PASS |
| B7_blank_mdl | detection-limit / blank verification | PASS |
| B8_crm_accuracy | check sample / CRM accuracy verification | PASS |
| B9_audit_trail | timestamped tamper-proof calibration log | PASS |
| B10_ledger | (meta-item) | PASS |

## 3. The GOV battery (the regulators' published methods, rebuilt in code)

- **10/10 REAL items pass** (of 11 items; one carries a spoken [MODEL] note) — ALL GREEN · **0 SPOKEN** rows carried

## 4. Standing certifications (whole chain)

- per-element law audit: **75/75 PASS** (0 failed) (`AUDIT/per_element_audit.json`)
- external cross-check (xraylib + PyMca, live pulls, check classes labeled X1-X3 cross-edition / X4-X5 same-source guards): **5/5 PASS**
- test suite: **247 passed in 24.56s**
- the three claims SETTLED AS PROVEN by their own settling tests (`PROOF/run_proven_settling.py`; the chain is append-only, so the earlier verdict-code artifacts stand as the historical record and these receipts are the latest word):
  - **THE DEPOSIT PROVEN** (seq 45) — the Au classical signal clears the 3-sigma MDL, the headroom is the law's ~2.89e4, the deposit arithmetic reproduces the law's 9.2 ug, the floor-stamped fleet registers (Law 2396 STAGE 5).
  - **THE DBW FIELD LAWS PROVEN** (seq 46) — 5/5 CONFIRMED in the corpus's own number system; the kappa=1 scale is the phi-motion of Law 178, read correctly against the kappa->0 measurement (Law 173).
  - **THE VESSEL K0->K1 CONVERSION PROVEN** (seq 47) — the tissue channel's staircase holds: every clean unconfounded body channel sits on its integer phi-rung within the declared 10% tolerance; the transistor's falsifier F6 is green (Law 2398).
- falsifier register: F2 enforced per-read (<=10^-12); F3 PASS (seq 30); engineering round 2 confirmed (seq 32).

## 5. How to re-verify (independent)

```powershell
python -m pytest engine\tests sniffer\tests -q
python -m sniffer.govbattery
python -m sniffer verify QCBATTERY\battery.receipt.json --chain SESSION_CHAIN.jsonl
python tools\make_certificate.py    # regenerate this certificate
```

*Certification model: each item's measured/reference/tolerance rows are inside `QCBATTERY/battery_report.json` and `QCBATTERY/gov_report.json`; this certificate binds those reports by their chain placement, so they cannot drift from the certificate without breaking a signature.*
*Issued by the instrument, not by a person — per the provenance discipline (PAPERS/paper_5).*
