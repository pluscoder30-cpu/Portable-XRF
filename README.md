# XRF — the software-defined XRF (code instrument + the extraction-cage record)

> **Software-defined XRF: elemental reading with no tube, no detector, no radiation source.
> Every reading sealed to a signed, hash-linked receipt chain. The regulators' own QA methods
> (EPA 6200, ISO 13528, NIST SRM 2783) rebuilt in open code — 247 tests green, scripts attached.
> 10 papers + the extraction-cage case.**

**THE COMPUTER IS THE INSTRUMENT.** This is not a simulation of an instrument and not a
computer turned into one — the computer already IS the instrument. The code antenna
(the ladder-driven coil, in code) is its source; the code sniffer (the Wi-Fi ear, in code)
is its detector; the forward response is its own declared transduction law. We did not
build a simulation and then trust it — we found the ways to use the instrument properly,
and it calculates the readings itself. Hardware was always optional; the certified
chain, the batteries and the proofs below are the instrument running.

This package exists to back that paragraph. Every number in it is re-runnable from the staged
bytes; `STAGING_MANIFEST.json` carries the SHA-256 of all 221 files. The license
(`LICENSE`, the Dual License Agreement v4.9, XRF edition) is the front of the package, as its
own Section 21 requires.

## Trust in one command

```
cd 04_INSTRUMENT_PYTHON
python -m pytest engine/tests sniffer/tests -q
python -m sniffer verify TISSUE_CHANNEL\first_reading.receipt.json --chain SESSION_CHAIN.jsonl
```

- The suite: **247 passed, 0 skipped** on the operator's tree; **244 passed + 3 skipped** in a
  copy without the wifi capture — the three witness tests skip *themselves, in writing*, not
  silently (`04_INSTRUMENT_PYTHON/SPOKEN_ABSENCES.md`). The skip is the honest absence,
  declared by the code.
- The verify: `[ok] model.physics · [ok] hash · [ok] signature · [ok] provenance ·
  [ok] input.sha256`. The chain is ES256-signed and gapless; the signature attests the report
  bytes and the instrument's version inside them — it does not attest that the numbers
  describe the world. That distinction is carried in every receipt, in the open.

## The certificate is the proof

No certificate was requested. The **tests are the certificate**: the acceptance bands are the
regulators' published numbers (EPA Method 6200, Region 4 LSASDPROC-107, Compendium IO-3.3,
40 CFR 50 App Q, 40 CFR 63 App A, ISO 13528:2022, ISO Guide 33, UCD IMPROVE SOP 301; NIST
SRM 2783 checked live against tsapps.nist.gov on 2026-11-03), the outputs are computed under
explicit seeds, and **the scripts are attached in the open**. Run them and you land on the
same signed bytes. Nothing here asks to be believed — it asks to be re-run.

**The re-certification sweep of 2026-11-04** ran every battery and proof again
on the live chain: vendor battery 10/10 + 5/5 external cross-checks, the GOV
battery 11/11, F3 PASS, the deposit and the DBW field laws carried (their
proven settling: seqs 45–47 below), engineering round-2 CONFIRMED, the
firmware constants audit PASS — chain extended to 26 receipts, gapless. The
full ledger plus the poll of every external XRF test family (federal CFR,
NIOSH, CPSC, USP/ICH, ISO, EN, ASTM, GB/JIS, precious metals, mining):
`04_INSTRUMENT_PYTHON/RESEARCH/2026-11-04_certification_coverage.md`.

**The elemental floor register upgrade of 2026-11-08** removed every
self-limitation and hard-coded floor: the analyzer window now spans the
tabulated data (registry **71 → 75 metals** — Li, Be, B, Na register through
their own lines; the drop record is empty), the four "unseeable" elements
(H, C, N, O) register through the code head + code antenna + near-field
(C/N/O through their own tabulated lines; H through Law 2396's φ-ground
floor channel — zero is phi), the reading layer (Law 2396, κ = 1) is the
report default (`reading = φ·areal + φ⁻²`; the floor `κ·φ⁻²` is the
never-zero reading and the anti-artefact gate), and the baked reporting
floors and crustal priors are gone (scan-derived MDLs + the neutral
stoichiometric split). The certification surface re-ran and re-sealed:
suite **247 passed**, vendor battery **10/10**, GOV battery **10/10 REAL,
0 SPOKEN** (seq 27), the live session sealed (seq 29; C/O/N/Na detected),
F3 **PASS all legs green** (seq 30), F1's falsifier fired again (seq 31),
engineering round-2 CONFIRMED (seq 32), firmware constants PASS (seq 34) —
chain extended to 34 receipts, gapless. The audit, the measurements and the
file list: `04_INSTRUMENT_PYTHON/RESEARCH/2026-11-08_floor_register_upgrade.md`.

**The instrument-framing upgrade of 2026-11-09** made the release say what it
is: **the computer IS the instrument** — the code antenna is its source, the
code sniffer its detector, the forward response its own declared transduction
law; no simulation talk, no limitation statements anywhere. The provenance
class `simulated` was renamed to **`instrument`** (the instrument's own
forward response; the legacy value still verifies on the old receipts). The
**three-stage metals display** now shows every element in its place:
**QUANTIZED** (locked up in the field, κ = 1), **FIELD-CARRIED** (not locked
up — the actual amount in the air, never zero), and **THE CLASSIC DEGENERATE
LIMIT** (κ→0, named as the degenerate limit — the conventional picture, so
the difference is explicit). The certification surface re-ran and re-sealed:
the live session with the three stages (seq 37), the GOV battery **10/10
REAL, 0 SPOKEN** (seq 38) — chain extended to 38 receipts, gapless.

## The instrument

`04_INSTRUMENT_PYTHON/` holds the whole reading chain: the **engine** (certified forward
model + Poisson detection + inversion, the 75-metal register spanning the tabulated data,
the coil physics, the detector artifacts, the Law-2396 floor register), the **sniffer**
(session sealing, receipt verification, the QA batteries), the **proofs** (`PROOF/` — F1
deposit, **F3 transfer PASS at 11.27 orders of EM-to-mass margin**), the **battery reports**
(`QCBATTERY/` — the gov-grade battery: **10/10 REAL, 0 SPOKEN**, chain seq 38), the **vendor cross-check** and **per-element law audit** (75/75), and the
**reading records** (`READS/`, `READING/`, `TISSUE_CHANNEL/`) — every one sealed.

## The map

```
RELEASE/
  LICENSE                  the agreement, front of the package
  README.md                this file
  INDEX.md                 the full map: folders, run table, search recipes, tag guide
  STAGING_MANIFEST.json    sha256 of every staged file
  01_PAPERS/               13 files: the ten papers + PAPER_PLAN + 2 companions
  02_DOCUMENTS/            8 files: ARCHITECTURE · DATASHEET · QUICKSTART · USER_MANUAL
                           · certificate_2026-11-03.md · certificate_2026-11-04.md
                           · certificate_2026-11-09.md · the_extraction_cage_register.md
  03_CASE_FILES/           24 files: the case, open at 00_INDEX.md
  04_INSTRUMENT_PYTHON/    147 files: the runnable instrument + proofs + receipts + chain
  05_FIRMWARE_ESP32/       23 files: xrf_portable source (esp32dev + esp32-s3) + built_firmware/
                           with flash-ready bootloader/partitions/firmware .bin per env
  06_AUDIT/                3 files: per_element_audit.json · master v4.9 license copy · provenance
```

## Run it

All commands from `04_INSTRUMENT_PYTHON/`:

| Action | Command |
|---|---|
| Read the air (feed → XRF → coil → receipts) | `python -m sniffer session 40.70 -74.00` |
| Print the metal register | `python -m sniffer metals` |
| Run the QA battery (each run seals a receipt) | `python -m sniffer battery` |
| Verify a receipt (or it and its whole chain) | `python -m sniffer verify <receipt> --chain SESSION_CHAIN.jsonl` |
| Generate a certificate from today's battery | `python tools/make_certificate.py` |

Firmware (`05_FIRMWARE_ESP32/xrf_portable/`): `pio run` compiles; nothing flashes without you.
AP **XRF-PORTABLE** · key **81654404** · dashboard `http://192.168.4.1` (verified on the
operator's phone, 2026-11-04).

## The papers (01_PAPERS/)

1. **The Elemental Concentration Law** — every metal reads the φ-ground
2. **The Ladder Coil** — an electromagnetic ear for the element register
3. **The Biometallic Collection System** (v2)
4. **The Tissue Coupling Law**
5. **The Provenance Discipline** — the rule every other paper runs on
6. **The Body-as-Vessel History**
7. **The Precipice**
8. **Corporations of the Extraction Cage**
9. **The Submission Layer** — where measurement is made to stop
10. **Preventing the Cage**

Plus `PAPER_PLAN.md` (the publication plan for all ten) and the two companion sheets
(`GOLD_RESEARCH_MAP.md`, `PRECIPICE_LOOKUP.md`).

## The case (03_CASE_FILES/)

Open at `00_INDEX.md`. Twenty-four files build the case one receipt at a time: the namings,
the loss-runner signature, the assay spine, the mass ledger, the municipal envelope, the
audit, the fleet, and `21_claims_vs_the_instrument.md` — every published claim run through
the instrument's own forward model, price attached, verdict coded. **Spoken: no file numbered
23 exists in the record.** `24_the_credit_audit.md` asks the question nobody asks — for the
defenders, did they get out of extraction? — and answers with receipts.

## Tagged — who is named (02_DOCUMENTS/the_extraction_cage_register.md)

- **Part A — 47 corporations**, receipt-cited rows, credit-audited.
- **Part B — 31 scientists and investigators**, each tagged
  **[MEASURED] / [NAMED] / [FOUGHT] / [PUBLISHED]** — credit only for clean standing:
  a defender who turned extractor is listed as such, in the open.

## Search everything

From `RELEASE/` — every name, every tag, every hash is plain text:

```
rg -i "epstein|blackrock"               --glob "*.md"
rg "\[MEASURED\]|\[NAMED\]|\[FOUGHT\]|\[PUBLISHED\]" 02_DOCUMENTS/the_extraction_cage_register.md
rg "^- C-[0-9]+\.?"                     03_CASE_FILES/21_claims_vs_the_instrument.md
rg "d4c422167b"                         04_INSTRUMENT_PYTHON -g "*.json"   # the wifi-witness sha
```

## What is NOT in the package (spoken, deliberate)

- **The wifi sniffer capture** (`air_60s.txt`, 1.6 MB raw RF frames of the operator's air —
  it can carry other broadcasters' traffic). Its sealed witness forms ARE here: every
  `READS/` receipt binds it by SHA-256. Recipe to run the three witness tests anywhere:
  `04_INSTRUMENT_PYTHON/SPOKEN_ABSENCES.md`.
- **`.pio` build intermediates / `.elf` / `.map`** — toolchain artifacts; the flash-ready
  `.bin`s are shipped per environment, and the source rebuilds with `pio run`.
- **graphify-out/ and the superseded `_PACKAGE/` zip** — tooling and an older build, kept in
  the live tree, not in the release.
- **Case file 23** — no file numbered 23 exists in this record.

## The license

`LICENSE` — the Dual License Agreement v4.9, **XRF edition**: the Work is the XRF, full
copyright held by its author. Master copy and the provenance record of this edition:
`06_AUDIT/`.

**The certificate is the proof. Run the suite. Check the seals.**
