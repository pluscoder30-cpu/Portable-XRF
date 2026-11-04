# XRF-PORTABLE — VERIFICATION CERTIFICATE

**Issued:** 2026-11-04 · **Instrument:** code-based XRF + coil (attached head)
**Versions:** sniffer-1.0.0+engine-1.2.0 · **Calibration id:** battery-standard-v1/SDD-25mm2
**Seed:** 20261102 (logged per item: [('B4', 20261113), ('B5_base', 20261125), ('B6_base', 20261139), ('B7_base', 20261153), ('B8', 20261173)])

## 1. Verification of the receipt chain

- chain length: **26 receipts** (append-only, `SESSION_CHAIN.jsonl`)
- latest: seq **26**, hash `c2c45bb46be91ee0…`
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

## 3. Standing certifications (whole chain)

- per-element law audit: **71/71 PASS** (`AUDIT/per_element_audit.json`)
- external cross-check (xraylib + PyMca, live pulls, check classes labeled X1-X3 cross-edition / X4-X5 same-source guards): **5/5 PASS**
- test suite: **226 passed**
- falsifier register: F2 enforced per-read (≤10⁻¹²); F1 run in-code (seq 10: PASS with spoken deviation, PROOF/06); F3 run in-code (seq 11: PASS, exit 0 — the ground bitwise rung-invariant at the invariant, crossings registered, EM→mass margin 11.3 orders, PROOF/07); engineering round 2 confirmed (seq 12: X4/X5 labels, M-8); F6 runnable (tissue channel G3)

## 4. How to re-verify (independent)

```powershell
python -m pytest engine\tests sniffer\tests -q
python -m sniffer verify QCBATTERY\battery.receipt.json --chain SESSION_CHAIN.jsonl
python tools\make_certificate.py    # regenerate this certificate
```

*Certification model: each item's measured/reference/tolerance rows are inside `QCBATTERY/battery_report.json`; this certificate binds that report by its chain placement, so the report cannot drift from the certificate without breaking a signature.*
*Issued by the instrument, not by a person — per the provenance discipline (PAPERS/paper_5).*
