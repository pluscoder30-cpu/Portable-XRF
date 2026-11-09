# XRF-PORTABLE — the instrument in your pocket (code, not chips)

The certified desktop instrument's reading chain carried onto an ESP32.
**No XRF hardware, no flashing required by this build you hold** — `pio
run` compiles, `pio run -t upload` would flash if you choose.

## the two bodies (2026-11-03)

| env | board | status |
|---|---|---|
| `esp32dev` | classic ESP32 | the certified first build (RAM 18% / Flash 74.4%) |
| `esp32-s3` | ESP32-S3 (devkitc-1) — **the user-held board** | compiled SUCCESS, Flash 27.4% (915,773 / 3,342,336 bytes); `Serial` rides the native USB connector (HWCDC) at 115200 AND flashing (one cable) |

**Chip-agnostic proof, machine-checked (`PROOF/run_firmware_constants_audit.py`,
receipt seq 14; chain seq 13 = same audit's pre-artifact seal):** zero hits for
every classic-only or S3-only API (`hallRead/touchRead/dacWrite/ledc*/BT*/neopixelWrite/pinMode`
audited across `src/` + `include/`); the device law (`include/law2396.h`) is
the **engine's law bit-for-bit** — A1–A4 + A6 hex-equal (`phi`, `phi_inv`,
`phi_sq_inv`, `mu_0` exact; `phiMotion` vs `phi_motion` hex-equal on an
11-point probe grid); the remaining rows are **spoken**: A5 (the ladder
constant's 9-multiply constexpr chain vs the engine's `math.pow` — a 1-ulp
evaluation-order note, ~2.4e-12 relative, zero compute impact: the header is
its only use), A7/A8 (the device's `1.2041e9 µg/m³` air density is the
**declared** table value vs the engine's computed rho — display-scale at the
5th significant digit; device thresholds self-consistent). The metal table is
**byte-identical on regeneration** (71 metals + 4 spoken drops, sha256
`1f868e7b…`). Both envs compile from the identical source: the instrument
is the code; the chip is the body.

## what it does

1. **connects to your phone** — opens the access point `XRF-PORTABLE`
   (key `81654404`, the corpus door port) and serves the reading
   dashboard at `http://192.168.4.1`
2. **scans like the desktop instrument** — fetches the SAME keyless
   public air-quality feed the certified chain reads, applies the
   engine's normative endmember model (ported exactly), computes the
   **Law 2396 register** (every metal's reading at κ = 1: quantified or
   the φ⁻² = 0.3819660113 ppm ground floor), and the **Law 2397
   coin-class check** from the GENERATED metal table
   (`tools/gen_metal_table.py` regenerates from `engine/metals.py` — the
   portable register can never drift from the certified one)
3. **runs the same corporate battery in firmware** — the device items
   (F-B1 standardization, F-B2 gain drift + correction, F-B3 FWHM
   resolution, F-B5 determinism, F-B7 blank budget, B10 ledger) at the
   same tolerances, plus DESKTOP-VOUCHED spoken pointers to the certified
   battery (B4/B6/B8, chain seq 5 — on-device they are spoken, never faked)

## idea note — pad-coupled directed scans (NOT yet implemented)

the coil already couples through a near-field standoff; a **disposable
electrode pad** (the ECG-type pad — the same pad family the molecular
assembler uses) can bring the coupler into CONTACT with a target. lay the
pad on the target (skin, a surface, a sample), run the scan from the pad,
and the instrument reads the pad's exact footprint — a directed scan
instead of an air reading. the ESP32's ladder drive and the pad's contact
area are the whole coupling chain; no tube, no detector, no radiation
source. this is a feature note for a later firmware — the idea is
recorded here so the path is visible: **pad down, run from the pad, scan
the pad.**

## what the phone shows

the air block (PM10/PM2.5/dust + status) · EVERY metal's reading in ppm ·
the coin-class rows (channel class, ppm of carrier) · every battery item ·
the φ⁻² floor and the ladder invariant · the provenance stamp
(*direct-feed/model*, spoken) · "hardware was optional. it was always
optional. they lied."

## honesty

- provenance is `direct-feed/model` — the desktop chain's forward+
  inversion step is NOT carried on-device (numpy NNLS); the feed path's
  readings carry the same Law 2396 arithmetic; the desktop's sealed
  receipts (`SESSION_CHAIN.jsonl`) are the vouching documents. the device
  is not a signer; no receipt is forged on device.
- without a WiFi uplink the device serves `waiting_for_link` — no
  fabricated numbers ever.

## the flash session (2026-11-03, receipt seq 15)

| fact | value |
|---|---|
| chip gate (pre-flash, esptool) | **ESP32-S3 (QFN56) rev v0.2**, Wi-Fi + BT5(LE), 240 MHz, PSRAM 8 MB embedded, MAC `84:c7:bb:5a:5b:74` |
| port | COM7 — **FTDI FT232RL bridge** (vendor 0403 / product 6001); NFF's auto-ID mislabel ("ESP8266") reproduced live — never used as a board choice |
| flashes | two uploads, **esptool "Hash of data verified" both**; the second carries the range-scan feature + UART0 print routing (the CDC flags retired after the plug-in discovery) |
| boot capture | `[XRF-PORTABLE] boot — the instrument is the code` · `[AP] 192.168.4.1  ssid=XRF-PORTABLE` · `[BATTERY] 9/9 ALL GREEN` (`tools/boot_capture.py`, raw + text bound by hash) |
| NFF | `get_device_info` via MCP (the bridge sheet) + `diagnose` on the captured output: **no crash signature** |
| dashboard check | **user-gated — phone**: the PC was instructed NOT to connect (no auto-rejoin: the profile is manual-mode; no netsh runs without instruction) |

**Sign in from the phone**: join Wi-Fi `XRF-PORTABLE` / key `81654404` · open `http://192.168.4.1` · the new **SCAN RANGES** card carries the four buttons — SCAN 10 cm · SCAN 1 m · SCAN 5 m · WHOLE RANGE — and every button opens a results popup: per metal, the best rung + frequency, the ppm of the nulled carrier, the channel class (in-phase ferrous / quadrature eddy), and the verdict above/below the 3σ floor; WHOLE RANGE adds each metal's maximal detectable range in meters. The scan is the certified code chain at the declared standoff — `[MODEL]`, spoken on screen, and provable offline.

## build

```bash
cd FIRMWARE/xrf_portable
pio run                 # compiles BOTH envs (esp32dev + esp32-s3)
pio run -e esp32-s3 -t upload --upload-port COMx   # flash only if you say so
```

**Chip-identity gate before upload (spoken):** `npx esptool.py --port COMx chip_id`
(or `python -m esptool ...`) first — an esp32dev image never goes on an S3 and
vice versa; the S3 env above is the user-held board's target. Via NFF, the same
hardware flow runs through the MCP (`nff compile`/`nff flash` accept this PIO
project directory directly — verified live).

## files

| file | role |
|---|---|
| `include/law2396.h` | the reading law + unit chain (device doubles) |
| `include/metal_table.h` | GENERATED from `engine/metals.py` (75 metals, 0 dropped — the register spans the tabulated data) |
| `include/coil.h` | Laws 637/638/801/039/048 ported; design anchor (Cu coin = 10,000 ppm) |
| `include/scan.h` / `src/scan.cpp` | the feed fetch + endmember model + register + coin check |
| `include/battery.h` / `src/battery.cpp` | the corporate battery, firmware items + desktop-vouched |
| `src/main.cpp` | AP + dashboard + API + scan loop |
| `tools/gen_metal_table.py` | regenerates the metal table from the certified registry |
