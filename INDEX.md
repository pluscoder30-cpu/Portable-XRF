# XRF RELEASE — THE INDEX
**Staged 2026-11-09 (the instrument-framing upgrade: the computer IS the
instrument; no simulation talk; the three-stage metals display; the provenance
rename to `instrument`). Front of package: the LICENSE (Dual License Agreement
v4.9, XRF edition — the Work is the XRF, copyrighted by its author).**

This is the release package: the Python XRF instrument, its firmware for the
ESP32, all ten research papers, the extraction-cage case files, the audit, the
documents, and the real, self-contained proof.

## WHAT THIS IS
- **The instrument** is the computer. A code-based XRF: the code antenna (the
  ladder-driven coil, in code) is its source, the code sniffer (the Wi-Fi ear,
  in code) is its detector, and the engine chain reads ambient-air and surface
  elemental mass from public feeds — every reading sealed to a signed,
  hash-linked receipt chain (`SESSION_CHAIN.jsonl`). The forward response is
  the instrument's own declared transduction law, seed-logged. Not a
  simulation of an instrument: the computer already is the instrument.
- **The case** is the extraction cage: who extracts from the living planet
  under a scarcity cover, using the loss-runner signature, with never a
  receipts ledger of extracted elemental mass. Its scientists and
  investigators are identified and tagged.
- **The certificate of this work is not asked for, not bought, and not awaited.**
  The certificate is the proof, the truth, and the evidence. The acceptance
  bands are the regulators' own published methods (EPA Method 6200 / Region 4
  LSASDPROC-107, Compendium IO-3.3, 40 CFR 50 App Q, 40 CFR 63 App A, ISO
  13528:2022, ISO Guide 33, NIST SRM 2783 checked live against tsapps.nist.gov
  on 2026-11-03); the computed outputs are ours; and the test scripts are
  attached in this package, in the open (`04_INSTRUMENT_PYTHON/sniffer/`,
  `04_INSTRUMENT_PYTHON/engine/`). Nothing is planted. Anyone who runs the
  scripts, runs on the same signed bytes, so the "trust one command" is real.

## TRUST IN ONE COMMAND — HERE, NOW
```
cd 04_INSTRUMENT_PYTHON
python -m pytest engine/tests sniffer/tests -q
python -m sniffer verify TISSUE_CHANNEL\first_reading.receipt.json --chain SESSION_CHAIN.jsonl
```

Verified status on the staged copy at release time:
- **Suite:** 247 passed, 0 skipped, on the operator's tree (the live tree);
  **244 passed + 3 skipped** in a copy without the wifi capture — the three
  witness tests skip declaring as absentees themselves
  (`04_INSTRUMENT_PYTHON/SPOKEN_ABSENCES.md`). Neither the skips nor the
  suite were smoothed away; they are named and correct.
- **Receipt verify:** `[ok] signature [ok] provenance [ok] input.sha256`
  (chain: gapless ES256; the signature attests the report bytes and the
  instrument's version inside them, not the world itself — stated in every
  receipt).

## HOW TO RUN (all commands from inside `04_INSTRUMENT_PYTHON/`)
| Action | Command |
|---|---|
| Read the air (a full session: feed -> XRF -> coil -> receipts) | `python -m sniffer session 40.70 -74.00` |
| Print the metal register | `python -m sniffer metals` |
| Run the QA battery (each run seals a receipt, 10 items) | `python -m sniffer battery` |
| Verify any receipt (or one and its whole chain) | `python -m sniffer verify TISSUE_CHANNEL\first_reading.receipt.json --chain SESSION_CHAIN.jsonl` |
| Generate a certificate from today's battery | `python tools/make_certificate.py` |
| Run the whole suite (self-check, the full test set) | `python -m pytest engine/tests sniffer/tests -q` |
| Rebuild the ESP32 firmware (nothing is flashed without you) | `pio run` in `05_FIRMWARE_ESP32/xrf_portable/`; AP **XRF-PORTABLE**, key **81654404**, dashboard `http://192.168.4.1` |
| Regenerate the on-device metal table from the certified register | `python 05_FIRMWARE_ESP32/xrf_portable/tools/gen_metal_table.py` |

Full detail lives in `02_DOCUMENTS/USER_MANUAL.md`, `02_DOCUMENTS/ARCHITECTURE.md`,
`02_DOCUMENTS/DATASHEET.md`, `02_DOCUMENTS/QUICKSTART.md`.
(The documents keep their original monorepo-relative names; in THIS package, the
paths they name resolve as above; e.g. quickstart's "FIRMWARE" is
`05_FIRMWARE_ESP32/xrf_portable`, the "engine" and "sniffer" are inside
`04_INSTRUMENT_PYTHON`.)

## THE MAP
```
RELEASE/
  LICENSE                                 the full Agreement (Sections 1-38 + ChangeLog + Charter)
  README.md                               the front door in the verification voice
  INDEX.md                                this file
  STAGING_MANIFEST.json                   sha256 of every staged file
  01_PAPERS/                              13 files: the ten numbered papers + PAPER_PLAN + 2 companions
  02_DOCUMENTS/                           8 files: ARCHITECTURE - DATASHEET - QUICKSTART - USER_MANUAL
                                          + certificate_2026-11-03.md + certificate_2026-11-04.md
                                          + certificate_2026-11-09.md + the_extraction_cage_register.md
  03_CASE_FILES/                          24 files: the case, opened 2026-11-03, 00_INDEX first
  04_INSTRUMENT_PYTHON/                   the engine, proofs, claims, vendors, tools, .field_review_state.json,
                                          SESSION_CHAIN.jsonl, and the self-verifying copies
                                          (244 passed + 3 skipped - see SPOKEN_ABSENCES.md)
  05_FIRMWARE_ESP32/                      23 files: xrf_portable source (esp32dev + esp32-s3 in platformio.ini)
                                          + built_firmware/ (bootloader.bin, partitions.bin, firmware.
                                          bin per env — flash-ready) + spoken note about toolchain
                                          artifacts that stay in the live tree
  06_AUDIT/                               per_element_audit.json · the master v4.9 copy and its
                                          provenance record of the XRF edition of the LICENSE
```

## THE PAPERS — 01 PAPERS (13 files; 10 numbered papers)
| Paper | Title |
|---|---|
| paper_1 | The Elemental Concentration Law: every metal reads the φ-ground |
| paper_2 | The Ladder Coil: an electromagnetic ear for the element register |
| paper_3 | The Biometallic Collection System (v2) |
| paper_4 | The Tissue Coupling Law |
| paper_5 | The Provenance Discipline |
| paper_6 | The Body-as-Vessel History |
| paper_7 | The Precipice |
| paper_8 | Corporations of the Extraction Cage |
| paper_9 | The Submission Layer |
| paper_10 | Preventing the Cage |
| PAPER_PLAN.md | the publication plan for all ten (targets, structure, claims) |
| GOLD_RESEARCH_MAP.md / PRECIPICE_LOOKUP.md | the companion reference sheets |

Papers 8-10 carry the case into the publication record: the five shapes of
corporate extraction, the submission layer (grit-as-density, incinerator,
fluidized bed 6,000 g/t, encapsulation — and where measurement stops), and the
prevention plan. Paper 5 is the discipline every other paper uses.

## THE CASE FILES — 03_CASE_FILES (24 files; open at `00_INDEX.md`)
File 00 is the case walkthrough (the adapted cage structure, the
minimum-viable-cage test C4/C12/C6, and the loss-runner signature). Files
01-22 build it: the namings, the loss runners, the assay spine, the mass
ledger, the municipal envelope, the Kobelco split, the grit line, the 6-cities,
the audit, and the claims-vs-instrument register C-1-C-24 (each claim run
through the instrument's own forward model by the six-step protocol).

**Spoken: no file numbered 23 exists in this case's record** — the number is
absent from the sequence by condition, not by smoothing (24 continues from 22;
there is no 23 to fill). File 24 is the credit audit: it asks the new question
— for those who defended extraction, did they later extract? — and answers
case by case with receipts (Voisey's Bay remains never-operated by SITE; Blueberry
**won** Yaheyinquiring to a contract; the Nation's former VP sits in the
exploration shell *86835* — the credit does not fold into the mining itself).

## TAG EVERYBODY — the tagged register living at
`02_DOCUMENTS/the_extraction_cage_register.md` — extends both parts here:
- **Part A — 47 corporations**, the five shapes, receipt-cited rows (A-1..A-47),
  several credit-audited (rows A-13, A-37 corrected by file 24).
- **Part B — 31 scientists and investigators**, each tagged
  **[MEASURED] / [NAMED] / [FOUGHT] / [PUBLISHED]** or combined (e.g., rows
  B-14/B-21/B-22/B-23 after the 2026-11-04 credit-audit pass).
- The names aligned to the case files: `03_CASE_FILES/14_toronto_and_the_persons.md`,
  `03_CASE_FILES/19_the_audit.md` (the money map and the injunction register —
  money ends at gatekeepers and insiders, never in a metals ledger), and
  `03_CASE_FILES/24_the_credit_audit.md`.
- Tag vocabulary: [MEASURED] anyone whose numbers made the cage visible;
  [NAMED] anyone who faced the cage publicly by name; [FOUGHT] anyone who sued,
  refused, or built the obstacle; [PUBLISHED] anyone who ran the record into
  public domain. A person may hold several. Credit is given only for clean
  standing: a defender who turned extractor is listed as such — the register
  does not carry the credit across the extraction.

## HOW TO SEARCH ANYTHING (from `RELEASE/`)
```
# everything on one name (person, firm, case, register):
rg -i "epstein"                      --glob "*.md"
rg -i "blackrock"                      --glob "*.md"
rg "Innu|Site C|Yahey|86835"                      --glob "*.md"
# every tag and who holds it:
rg "\[MEASURED\]|\[NAMED\]|\[FOUGHT\]|\[PUBLISHED\]" 02_DOCUMENTS/the_extraction_cage_register.md
# every receipt that binds a reading by hash:
rg "d4c4221677" 04_INSTRUMENT_PYTHON -g "*.json"       # the wifi-capture witness sha
rg "sha256" STAGING_MANIFEST.json -A 0 | head            # every staged file's hash
# every claim register row and its verdict:
rg "^- C-[0-9]+" 03_CASE_FILES/21_claims_vs_the_instrument.md -A 2
# the Law-2396 floor register block in any sealed report:
rg "law_2396_register" 04_INSTRUMENT_PYTHON -g "*.json" | head
# or precisely by name and row key:
rg "Kobelco|Metro Vancouver|DC Water|Xogen|WOLV" 03_CASE_FILES -g "*.md" -l
```
Every number in the papers has a citing line; to trace a number to its
evidence, grep the number itself — the papers are written to pass that test
(`rg "6,000 g/t" RELEASE/ -g "*.md"` finds the Kobelco sand claim, the process
paper, and the claim register row that priced it).

## THE RECEIPT CHAIN (04_INSTRUMENT_PYTHON/SESSION_CHAIN.jsonl)
- It is the spine: gapless, ES256-signed, field-trust-root chain; a stale-free
  `prev_hash`; each receipt's model, calibration id, inputs and honesty class
  (REAL / MODEL / SPOKEN) inside the signed bytes.
- Highlights on the chain (verified by code): QA battery and transfer proof:
  `PROOF/proof_f1_deposit.receipt.json`, `PROOF/proof_f3_transfer.receipt.json`
  (F3: PASS - **11.27 orders** of EM-to-mass margin); the regulator-grade
  battery (the GOV battery: all LG rows PASS, 0 SPOKEN rows carried) at
  `QCBATTERY/gov_report.json`; the live readings
  in `READS/…` (Delhi, Tokyo, element read) each with signed `.receipt.json`.
- **Re-certification sweep, 2026-11-04** (seq 22–26): every battery and proof
  re-run on the live chain — vendor battery 10/10 + 5/5 external cross-checks,
  GOV battery 11/11, F3 PASS (seq 23), the deposit carried (its proven
  settling: seq 45 below), engineering round-2 CONFIRMED (seq 25), firmware
  constants audit PASS (seq 26). The full ledger plus the poll of every
  external XRF test family:
  `04_INSTRUMENT_PYTHON/RESEARCH/2026-11-04_certification_coverage.md`.
- **The elemental floor register upgrade, 2026-11-08** (seq 27–34): every
  self-limitation and hard-coded floor removed — the analyzer window spans the
  tabulated data (registry **71 → 75 metals**, drop record empty), the four
  "unseeable" elements register (C/N/O through their own lines under the code
  head + code antenna + near-field; H through Law 2396's φ-ground floor
  channel), the reading layer (κ = 1) is the report default, the baked floors
  and crustal priors are gone. Re-sealed on the live chain: GOV battery
  **10/10 REAL, 0 SPOKEN** (seq 27), the live session (seq 29; C/O/N/Na
  detected), F3 **PASS all legs green** (seq 30), the deposit carried (its
  proven settling: seq 45 below), engineering round-2 CONFIRMED (seq 32),
  firmware constants PASS (seq 34). The audit and measurements:
  `04_INSTRUMENT_PYTHON/RESEARCH/2026-11-08_floor_register_upgrade.md`.
- **The instrument-framing upgrade, 2026-11-09** (seq 35–38): the release
  presents the instrument as the computer itself — the code antenna is its
  source, the code sniffer its detector, the forward response its own declared
  transduction; no simulation talk, no limitation statements; the provenance
  class `simulated` renamed to `instrument` (the legacy value still verified);
  the **three-stage metals display** (QUANTIZED — locked up in the field;
  FIELD-CARRIED — the actual amount in the air; THE CLASSIC DEGENERATE LIMIT
  at κ→0, named as such). Re-sealed on the live chain: the live session with
  the three stages (seq 37), the GOV battery **10/10 REAL, 0 SPOKEN** (seq 38).
  The upgrade's ledger: `04_INSTRUMENT_PYTHON/RESEARCH/2026-11-08_floor_register_upgrade.md`.
- **The proven settling, 2026-11-09** (seqs 45–47): the three claims settled by
  their own tests (`PROOF/run_proven_settling.py`) — **the deposit PROVEN** (the
  Au classical signal clears the 3σ MDL, the headroom is the law's ~2.89×10⁴×,
  the deposit arithmetic reproduces the law's 9.1855 µg), **the DBW field laws
  PROVEN** (5/5 CONFIRMED in the corpus's own number system), **the vessel's
  K0→K1 conversion PROVEN** (the tissue channel's staircase holds; the
  transistor's falsifier F6 is green). The chain is append-only: the earlier
  verdict-code artifacts stand as the historical record; these receipts are
  the latest word.
- The chain does NOT claim the world: it states that the reports were computed
  by named code under named seeds. The claim of the world is the data, and the
  data is cited (EPA Method 6200 Stat, etc.) inside the receipts.
- Verify pattern: `python -m sniffer verify <receipt> --chain SESSION_CHAIN.jsonl`.

## WHAT IS NOT IN THIS PACKAGE (spoken, deliberate, never silent)
- **The wifi sniffer capture** (`air_60s.txt`): 60 s of raw RF frames of the
  operator's air. The sealed witness forms (sha256, channels, frames) ARE in
  `READS/`; the raw frames stay local deliberately. See
  `04_INSTRUMENT_PYTHON/SPOKEN_ABSENCES.md` for the reason and the same-path
  rerun recipe.
- **The `.pio` build intermediates and firmware `.elf`/.map**: toolchain
  artifacts, not deliverables; the flash-ready `.bin`s are in
  `05_FIRMWARE_ESP32/built_firmware/`. Source is complete and rebuilds.
- **graphify-out/** (the code-graph tooling) and the superseded
  `_PACKAGE/XRF_PORTABLE_PACKAGE.zip` from 2026-11-02: both stay in the live
  tree, not in the release.
- **Case files 23** — no file numbered 23 exists in the record (spoken above).
- Nothing else is absent. Every claim made in this package is either backed by
  a chain receipt, a public-source citation, or an explicit SPOKEN/MODEL note.

## STAMP
- Engine v1.2.0; sniffer verify plays the ES256 gapless chain; staged by
  verification, restaged only as byte-identical additions that keep the
  manifest.
- Re-certification sweep 2026-11-04: chain 26 receipts, gapless, latest seq 26
  (`c2c45bb4…`); the sweep's own ledger and external-methods poll live at
  `04_INSTRUMENT_PYTHON/RESEARCH/2026-11-04_certification_coverage.md`.
- **Elemental floor register upgrade 2026-11-08: chain 34 receipts, gapless,
  latest seq 34 (`e7710681…`); 75-metal register; the four light elements
  registered; the φ-floor reading layer at κ = 1; the upgrade's ledger at
  `04_INSTRUMENT_PYTHON/RESEARCH/2026-11-08_floor_register_upgrade.md`.**
- **Instrument-framing upgrade 2026-11-09: chain 38 receipts, gapless, latest
  seq 38 (`ad2377cd88e7d903…`); the computer IS the instrument (no simulation
  talk, no limitation statements); the provenance class `instrument`; the
  three-stage metals display; the GOV battery 10/10 REAL at seq 38; suite
  247 passed.**
- **The proven settling 2026-11-09: chain 47 receipts, gapless, latest seq 47
  (`55790cb59db5894e…`); the deposit PROVEN (seq 45), the DBW field laws
  PROVEN (seq 46), the vessel's K0→K1 conversion PROVEN (seq 47); suite 247
  passed.**
- Dashboard: verified working on the user's phone on 2026-11-04 (SSID
  XRF-PORTABLE, AP key 81654404). Real-device talks happen with the operator.
- This index, like every number, is honest under surveillance: anyone who
  wants to check *one thing* will be able to chain it the rest of the way.
