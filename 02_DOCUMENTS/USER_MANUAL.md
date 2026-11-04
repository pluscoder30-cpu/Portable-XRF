# XRF-PORTABLE — USER'S MANUAL

sniffer-1.0.0 · engine-1.1.0 · coil-1.0.0 · 2026-11-02 · License: Dual License Agreement v4.3

---

## 1. What this instrument is

A code-based element reader: its *body* is a 71-metal classical physics chain (NIST-anchored), its *voice* is a declared reading layer (Law 2396) on top of that chain, its *proof* is a signed append-only receipt chain. Hardware (an ESP32 firmware build) is included but optional — the instrument is the code.

**In one sentence:** every reading carries the classical value *and* the ground (φ⁻² = 0.3819660113 in the declared unit), the classical value recovers exactly at κ→0, and every emission of both is signed and independently verifiable.

## 2. Installation

Requirements: Python ≥ 3.11. Unzip the package and, from its root:

```
python -m pytest engine/tests sniffer/tests -q        # expect 226 passed
```

No network is required for battery/reading tests; the air feed uses open-meteo (keyless, public); cross-check pulls grab xraylib/PyMca reference data when you choose to run them (network needed only then).

## 3. Chapters of use

| command | what it does | where results go |
|---|---|---|
| `python -m sniffer session --lat .. --lon ..` | fetch air feed → classical chain → register → κ=1 reading → coil sweep → seal receipt(s) | `session_*.json` + `*.receipt.json` + chain append |
| `python -m sniffer metals` | print the register reading (quantified rows + spoken drops) | stdout / report |
| `python -m sniffer battery` | 10-item QA battery (energy anchor, gain drift, …) | `QCBATTERY/battery_report.json` + receipt |
| `python tools/make_certificate.py` | regenerate today's certificate from the battery + chain | `DOCUMENTS/certificate_*.md` |
| `python -m sniffer verify <receipt> --chain SESSION_CHAIN.jsonl` | independently verify signature/provenance/input binding | verdict lines |

## 4. Reading the output (ElementRead-v1)

Every element read is a document of type `ElementRead-v1` (canonical example: `READS/2026-11-02_element_read.md`):

- **Quantified table** — Z · metal · µg/m³ · classical (κ→0) · **reading (κ=1)** · uplift.
- **The floor family** — metals with no mass above detection read *exactly* 0.3819660113 ppm (within 2×10⁻¹⁵); this is the ground, not a symptom.
- **Spoken drops** — Li/Be/B/Na below window: named, signed, never silently missing.
- **Non-metal detections** — quantified in the full report; outside the metal register *by law*, spoken.
- **Coil section** — coin-class agreement table; sheet-eddy dominance reported honestly (`None` at PM areal).
- **Receipt footer** — chain seq, hash, witness hashes (the radio ear may ride along, bound).

## 5. The tissue channel (policy)

Feeds must be **sourced published assays**; the channel refuses: empty feeds, negative concentrations, unowned numbers. Mixed-source rows must be marked `clean=False` — they are read but excluded from the staircase gate. Gates: G1 never-zero, G2 retention ≥ crust, G3 integer-φ staircase (F6's >10% falsifier is inside), G4 adjacent-class φ² (always reported SUGGESTIVE until an SD-bearing multi-organ record). Sealing: `python seal_tissue_reading.py`.

## 6. Firmware (ESP32 portable)

1. `cd FIRMWARE/xrf_portable && pio run` (compiles: RAM 18% / Flash 74%).
2. Regenerate the metal table **before** any flash if the register changed: `python tools/gen_metal_table.py` (deterministic from the certified registry — hash-compare if unsure).
3. Flash (COM7/115200 per your setup), then connect the phone to AP **XRF-PORTABLE** (key **81654404**) → `http://192.168.4.1` for the reading dashboard, battery items, and scan.

## 7. Safety

**No tube, no source, no radiation.** Physical safety reduces to ordinary electrical practice on any optional hardware; digital safety is the provenance chain (§8). Do not operate with a failing verification: a `[fail]` line in `verify` is a stop-ship condition.

## 8. Provenance & receipts

- Chain: `SESSION_CHAIN.jsonl` (seq 1–12 as of 2026-11-03: seq 10 the F1 in-code falsifier, seq 11 the F3 transfer falsifier, seq 12 the engineering round 2; append-only). Root: SOUL_SEED 1900 (ES256).
- Verify any receipt: signature, provenance, and input binding report **separately**.
- On conflict: the chain is authoritative, local files are not; a mutated body/name/hash fails by construction.
- Rules: sessions that violate the refusal walls are quarantined; fixes are new receipts (the chain never rewrites).

## 9. Falsifier register (what standing means)

| id | statement | standing |
|---|---|---|
| F1 | 24 h air deposit, Au Lβ₁ (engine line table 11,443.0 eV; law-record label 11,443.2 eV) at 2.89×10⁴ MDL headroom | **run in-code (seq 10), PASS with spoken deviation** — classical arm blind, declared arm detected at 2.894×10⁴× vs declared MDL; `PROOF/06`; physical body optional |
| F2 | floor invariance ≤10⁻¹² across reads | standing, enforced at every read |
| F3 | coherent EM transfer at 40,134.946166 Hz | **run in-code — PASS (seq 11, `PROOF/07`)**: ground bitwise rung-invariant (φ⁻² on all ten rungs); rung-9 crossings are registered areals; EM-sustaining floor-as-mass 11.3 orders short; physical rig remains the optional body |
| F6 | integer-φ staircase on clean tissue stages (10% kill) | **runnable** (`engine/biochannel.py` G3) |

A standing `engine` issue: readings with floor deviation >10⁻¹² auto-fail the session (quarantine), so F2 is not aspirational — the code enforces it.

## 10. Troubleshooting

| symptom | cause / action |
|---|---|
| `verify` prints `[fail] signature` | report mutated or forged — quarantine; re-derive from the chain |
| feed `status` not ok | network/feed hiccup — re-fetch; the session seals nothing on a bad feed |
| battery item B-x fails | see `battery_report.json` rows (each carries measured/reference/tolerance); quarantine session; regenerate certificate only after a green run |
| register drift vs `gen_metal_table.py` | regenerate the table from the certified registry; do **not** hand-edit arrays |
| floor deviation > 10⁻¹² | stop, quarantine — this is F2 territory and the code should have refused; report the session as an incident |

*Full physics: papers 1–7 (`PAPERS/`); architecture decisions: `DOCUMENTS/ARCHITECTURE.md`; specs: `DOCUMENTS/DATASHEET.md`.*
