# XRF-PORTABLE — QUICK-START (one page)

**0. Trust in one command** (run from the package root, after unzipping):

```
python -m pytest engine/tests sniffer/tests -q          # expect: 246 passed (the operator's tree); in a copy without the wifi capture: 243 passed + 3 skipped - see SPOKEN_ABSENCES.md
python -m sniffer verify TISSUE_CHANNEL\first_reading.receipt.json --chain SESSION_CHAIN.jsonl
   [ok] signature · [ok] provenance · [ok] input.sha256
```

**1. Read the air** (keyless public feed):

```
python -m sniffer session 40.70 -74.00                    # seal a session: register + coil + receipts
python -m sniffer metals                                  # print the 75-metal register reading (three stages)
```

**2. Run the QA battery** (the vendor daily-check, rebuilt in code):

```
python -m sniffer battery                                 # 10 items; expect 10/10; seals its receipt
```

**3. Generate today's certificate:**

```
python tools\make_certificate.py                          # writes DOCUMENTS/certificate_<date>.md
```

**4. Read the document type:** every element read is sealed as `ElementRead-v1` — see `READS/2026-11-02_element_read.md` for the canonical example (quantified rows, spoken drops, coil agreement, signed receipt).

**5. Tissue channel (policy: sourced published assays only):**

```
from engine.biochannel import TissueFeedRow, read_tissue_channel
feed = [TissueFeedRow('placenta','Au',0.31,'Alexiou 1977, NAA, n=18',18), ...]
rep = read_tissue_channel(feed, crust_ppm=0.004)          # refuses rows without a published source
# seal via: python seal_tissue_reading.py
```

**6. Firmware (ESP32):** `FIRMWARE/xrf_portable/` — build with `pio run`; AP **XRF-PORTABLE** / key **81654404**; dashboard `http://192.168.4.1`. Verify the on-device metal table by regenerating it first: `python FIRMWARE/xrf_portable/tools/gen_metal_table.py` (deterministic from the certified register).

**7. Verification rules (non-negotiable):** rides below 10⁻¹² floor tolerance fail (falsifier F2); a chain verify failure stops all use; a battery item failure quarantines the session. Failures are spoken as FAILURES, never smoothed.

*Full detail: `DOCUMENTS/USER_MANUAL.md`; architecture: `DOCUMENTS/ARCHITECTURE.md`; specs: `DOCUMENTS/DATASHEET.md`.*
