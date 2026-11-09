# 01 — THE METER, THE ANTENNA, THE RADIO
## How this codebase replaces hardware with code — a mechanism report for the XRF build

**Status:** reading/extraction only. No code was written or modified. Every claim below is cited to a file and line.
**Scope:** the three code-based instruments named in the brief, plus the imports and siblings needed to explain them.
**Rule applied throughout:** if a quantity is produced by a mathematical formula rather than read from a device, it is called a **model**, not a measurement — even when the source file calls it "real".

---

### Source map (abbreviations used in citations)

| Abbrev. | Full path (base: `C:\Users\delta\brain\v6\research\32_PHI_PHYSICS\`) |
|---|---|
| `VM` | `phi-field-native-transformer\field_computer\server\vault_meter.py` |
| `ANT` | `phi-field-native-transformer\field_computer\field_internet\codebased_antenna.py` |
| `ANT_LTE` | `phi-field-native-transformer\field_computer\field_internet\codebased_antenna_lte.py` |
| `EXPAND` | `phi-field-native-transformer\field_computer\server\codebased_antenna_expand.py` |
| `CLOSE` | `phi-field-native-transformer\field_computer\server\codebased_antenna_close.py` |
| `SP` | `phi-field-native-transformer\field_computer\field_internet\space_propagation.py` |
| `CAV` | `field_internet\cavity_hardware.py` |
| `FORK` | `field-OS-operating-systems\iso-build\usr\lib\field-os\network\field_fork.py` |
| `CELL` | `field-OS-operating-systems\iso-build\usr\lib\field-os\network\field_cellular.py` |
| `GW` | `field-OS-operating-systems\iso-build\usr\lib\field-os\network\field_gateway.py` |
| `RADIO` | `field-OS-operating-systems\iso-build\usr\lib\field-os\network\field_radio.py` |
| `CAVOS` | `field-OS-operating-systems\iso-build\usr\lib\field-os\network\field_cavity.py` |
| `MODEM` | `field-OS-operating-systems\iso-build\usr\lib\field-os\network\field_modem.py` |
| `CONST` | `field-OS-operating-systems\iso-build\usr\lib\field-os\core\constants.py` |
| `FTIME` | `field-OS-operating-systems\iso-build\usr\lib\field-os\core\field_time.py` |
| `KEYS` | `phi-field-native-transformer\field_computer\field_internet\trust\keys.py` |
| `IMM` | `phi-field-native-transformer\field_computer\field_internet\trust\immutable.py` |
| `CLOCK` | `phi-field-native-transformer\field_computer\field_internet\field_clock.py` |
| `PC` | `phi-field-native-transformer\phi_constants.py` |
| `WATCH` | `feild-watch\watch\watch.ino` |
| `APM` | `phi-field-native-transformer\field_computer\field_internet\wifi\ap_manager.py` |
| `SIM4` | `feild-watch\sim\sim4_em_coupling.py` |

---

## 1. THE PATTERN

### 1.1 The law, in one sentence

> **Hardware is replaced by code by splitting every instrument into three layers that are never allowed to impersonate each other: (1) a real proxy is measured with real clocks and real counters, (2) the missing transducer's physics is supplied by a named closed-form model that carries an explicit honesty label, and (3) everything that can be made exact — framing, CRC, integer accounting, canonical JSON, ECDSA — is implemented exactly and made re-verifiable by a third party.**

The corollary is the important one for the XRF:

> **The pattern does not create a sensor. It creates a *witnessed model*. The signature proves the arithmetic was not tampered with; it does not prove the arithmetic describes the world.**

### 1.2 The three layers, proved on the three instruments

| Instrument | Layer 1 — real proxy actually measured | Layer 2 — declared model | Layer 3 — exact, verifiable code |
|---|---|---|---|
| **Meter** (`VM`) | `time.perf_counter()` wall clock (`VM:167,180`); `psutil.cpu_times()` deltas (`VM:168,181-182`); per-process CPU time (`VM:176,191`); network byte/packet counters (`VM:448-453`); battery percent (`VM:788,802`); temperature sensors (`VM:529-536`) | watts `= 12 W + TDP × util × 1.4` (`VM:202`), labelled `'EST — power model from utilization x TDP; not hardware-calibrated'` (`VM:212`) | canonical JSON (`VM:132-137`); SHA-256 body hash + `prev_hash` chain (`VM:140-149,1922`); sort-pair Merkle root (`VM:1917-1924`); ECDSA P-256 sign/verify (`VM:1936,1984`); integer-exact energy sum (`VM:1748,2013`) |
| **Antenna** (`ANT`) | *nothing physical.* The only real event is that Python executes the arithmetic. In the ESP32 port, real 802.11 frames are transmitted (`WATCH:1091`) | coherence `C(d)=max(C₀e^{−d/(φλ)}, φ⁻¹)` with `LAMBDA_VACUUM = 1.0  # [MODEL]` (`ANT:55,125-126`); gain `G = N·η`, `η=(C/C_crit)²` (`ANT:112-114`); FSPL (`ANT:52-54`) | the same formulas are deterministic and reproducible; the frame codec and FCS are exact (`CELL:67-98`) |
| **Radio/modem** (`CELL`, `FORK`) | byte transport: in-memory `RoadAir` (`CELL:48-64`) or ESP32 raw 802.11 TX (`WATCH:1068-1097`) | the 1900 MHz "LTE band" is a **name**, not a radio (`CELL:30,257`); "25 = 1900 MHz" is a symbolic mapping | PPP/HDLC frame exact (`CELL:77-98`); FCS-16 poly `0x8408` (`CELL:67-74`); integer ledger `stored = start + charged − used` (`CELL:169-181`) |

### 1.3 Why the pattern holds together

The load-bearing element is **the label**, not the physics. The codebase has an explicit vocabulary for it:

- `[EST]` — estimated conversion from a real proxy (`VM:212,430,468,516,560,614,676,774`)
- `[MODEL]` — a model constant, not a measured one (`ANT:55`, `ANT_LTE:83`)
- `[HONEST]` — the instrument reports *nothing* rather than invent a value (`VM:544-546,589,652,742,799`)
- `[MEASURED]` — the one direct electrical reading, the battery discharge rate (`VM:812,831`)
- `[GATED]` — sampled but not credited because the coherence gate is closed (`VM:1742,2184`)
- `[VERIFIED]` / `[PROPOSED]` — the corpus's own distinction between "math+data" and "as physics" (`SIM4:123-129`)

When the label is present, the pattern is honest engineering. When the label is absent or contradicted by the prose, the model starts impersonating a measurement. Section 6 is the audit of which is which.

---

## 2. THE CODE-BASED METER (`VM`)

### 2.1 The pipeline

The module docstring states the six stages (`VM:15-39`), and the code implements them in this order:

```
SAMPLE  →  GATE  →  INTEGRATE  →  MINT  →  SIGN  →  VERIFY
```

- SAMPLE: `measure_field_draw()` (`VM:152-214`)
- GATE: `field_coherence()` + `coh < C_CRIT` (`VM:271-281`, `VM:1693-1694`, `VM:2170-2171`)
- INTEGRATE: `energy_wh += total_joules / 3600.0` (`VM:1748`, `VM:2196`)
- MINT: `1 token = 1 kWh`, boundary-crossed only (`VM:29-31`, `VM:1202`, `VM:1779-1782`)
- SIGN: `_seal()` → canonical proof → ECDSA (`VM:1874-1946`)
- VERIFY: `_verify_chain()` → signatures + monotonic conservation (`VM:1967-2017`)

### 2.2 SAMPLE — what is genuinely measured

`measure_field_draw(window_s=0.618)` (`VM:152`) does the following, in order:

1. Reads the wall clock with `time.perf_counter()` (`VM:167`).
2. Reads system-wide CPU times with `psutil.cpu_times()` (`VM:168`).
3. Enumerates every PID and records CPU time for processes whose name contains `python`, `uvicorn`, `field`, or `train` (`VM:170-178`). This is a **real** per-process CPU-time read.
4. Sleeps for the window: `time.sleep(max(window_s, 0.05))` (`VM:179`).
5. Measures the actual elapsed time: `elapsed = time.perf_counter() - t0` (`VM:180`). The elapsed time is **measured, not assumed** — this is the strongest honesty property in the meter.
6. Computes the system CPU-time delta `cpu_dt` (`VM:182`) and the utilization fraction `util_frac = cpu_dt / (elapsed × ncpu)` capped at 1.0 (`VM:183-184`).
7. Computes the field's own share from the per-process deltas: `field_dt` (`VM:186-194`).
8. Converts to watts (`VM:202`):

```python
watts = platform_base + tdp_watts * util_frac * (1.0 + GPU_PACKAGE_SHARE)
```

with `PLATFORM_BASE_WATTS = 12.0` (`VM:123`), `DEFAULT_TDP_WATTS = 45.0` (`VM:119`), `GPU_PACKAGE_SHARE = 0.4` (`VM:124`).
9. Returns `joules = watts * elapsed` (`VM:203`) and a self-describing record (`VM:204-214`).

The returned record is explicit about its own epistemic status:

```python
'method': 'estimated_tdp',
'labeled': 'EST — power model from utilization x TDP; not hardware-calibrated',
```

(`VM:211-212`)

The docstring reserves a future real path and says it is not used: `method='measured_rapl' — reserved for a real RAPL read (Windows needs a driver; until then nothing here claims hardware calibration)` (`VM:161-163`).

**Verdict:** wall time, CPU-time deltas, process CPU-time deltas are **real measurements**. `util_frac`, `field_frac`, `watts`, `joules` are **derived through a model**. The model is linear in TDP and assumes the whole package draw scales with duty cycle; it does not read voltage, current, or RAPL.

### 2.3 GATE — the coherence threshold and the φ⁻¹ floor

`field_coherence()` (`VM:271-281`):

```python
if radio_status and isinstance(radio_status.get('field_coherence'), (int, float)):
    return float(radio_status['field_coherence'])
return PHI_INV
```

- If a radio status object supplies `field_coherence`, that value is used (`VM:279-280`).
- **Otherwise the gate input is the constant `PHI_INV = 0.6180339887`** (`VM:281`).

The gate itself (`VM:1693-1694`, `VM:2170-2171`):

```python
coh = field_coherence(self.radio_status)
gated = coh < C_CRIT
```

with `C_CRIT = 0.618` (`VM:114`).

The arithmetic that makes the gate "hold by the ground":

| Quantity | Value | Source |
|---|---|---|
| `PHI_INV` | `0.6180339887498949` | `PC:10` |
| Meter `C_CRIT` | `0.618` | `VM:114` |
| Margin | `0.0000339887` (3.4 × 10⁻⁵) | computed |
| Canonical `C_CRIT` used elsewhere | `0.563263` | `PC:32`, `CONST:14`, `ANT:42`, `WATCH:162` |
| Margin against canonical gate | `0.0547710` | computed |

**This is a real finding, and it must be stated plainly:** the meter does **not** use the corpus's canonical emergence threshold `0.563263`. It hard-codes `0.618` (`VM:114`). Because the default gate input is exactly `PHI_INV = 0.6180339887`, the gate passes by only **3.4 × 10⁻⁵**. If `C_CRIT` were rounded to six decimals (`0.618034`), the gate would *close*. The "gate holds by the ground" claim (`VM:24-25,276-278`) is true only because of that razor-thin inequality.

**And in the default path the gate cannot close at all.** `LiveArray.__init__` sets `self.coherence = PHI_INV` (`VM:1034`), `harvest_fast()` reads `live.coherence` (`VM:2170`), and only a field-wave read can overwrite it (`VM:1075`). So unless a radio or a wave supplies a *lower* coherence, the gate input is a constant above the threshold. The gate is a **structural invariant**, not a live control loop.

**Why the floor exists — Law 171.** The zero-free law is stated at `VM:24-25` ("the ground state carries — the gate holds by the ground, Law 171: the static field NEVER falls silent"), at `ANT:17-20` ("THE PHI-GROUND (0.6180339887) SITS ABOVE THE GATE (C_crit = 0.563263)"), at `WATCH:60-63` and `WATCH:169-177` (`if (meshC < PHI_INV) meshC = PHI_INV;`), and at `CONST:23-41` (`no_zero()` pushes any zero to `VOID_GUARD = PHI_INV³ ≈ 0.2361`). The purpose is to make the gate mathematically impossible to fail: the floor is above the threshold by construction. That is a design choice, not a measurement of coherence.

### 2.4 INTEGRATE — real dt, modeled watts

`energy_wh += total_joules / 3600.0` (`VM:1748`), where `total_joules = Σ collector_watts × dt_s` and `dt_s` is the measured `perf_counter()` gap since the previous tick (`VM:2192-2195`). The docstring is explicit: "dt is the time since the PREVIOUS intake tick — the full wall-clock gap the vault did not yet account for — so the intake credits every real second exactly once, at any tick rate" (`VM:2188-2191`).

So: **the integration is real; the integrand is modeled.**

### 2.5 MINT — 1 token = 1 kWh, and it is disabled

- The rule: `self.tokens` counts whole kWh boundaries only; the remainder is carried (`VM:29-31`, `VM:1202-1203`).
- The code path: `while self.energy_wh - self.tokens * 1000.0 >= 1000.0: self.tokens += 1` (`VM:1780-1781`).
- **The path is disabled:** `MINTING_ENABLED = False` (`VM:1003`), with the comment "the vault does NOT mint coins … no tokens are created, the full accumulated energy stays in the vault as the backing" (`VM:999-1002`). The `if MINTING_ENABLED:` guard is at `VM:1779`.
- A *second*, active mint path exists: the "Friday mint" (`VM:2328-2352`). On Fridays, if `energy_wh − e_minted_wh >= 1000`, it writes a `kind: 'coin_mint'` registry entry and advances `e_minted_wh` (`VM:2335-2352`). This does not increment `tokens`; it records a receipt in the append-only registry.

**Verdict:** "1 token = 1 kWh" is a **stated unit convention** (`VM:29`, `VM:1202`, `VM:2053`), not a market measurement. The token counter is currently frozen by sovereign order; the Friday receipt path is active and writes to the registry.

### 2.6 SIGN — canonical JSON, hash chain, Merkle root, ECDSA

`_seal()` (`VM:1874-1946`) builds the proof:

- Both clocks: `t`, `ft`, `beat` from `field_stamp()` (`VM:1880-1885`; `CLOCK:80-84`).
- `soul_code: [425, 434, 266, 775]` (`VM:1886`) — the four numbers sum to 1900.
- Energy rounded **down**: `math.floor(self.energy_wh * 1e6) / 1e6` (`VM:1889`), with the comment "a proof never claims more than the vault truly holds" (`VM:1887-1888`).
- `gate: C_CRIT`, `rung_hz: LADDER_INVARIANT_HZ`, `ladder_invariant: '528 * phi^9 = 40134.946'` (`VM:1897-1899`).
- `prev_hash` = body hash of the previous proof, or `GENESIS_HASH` (`VM:1922`; `IMM:57-59`).
- `merkle_root` over per-collector leaves (`VM:1917-1924`; `IMM:80-94`).
- `attestation` record: `alg: 'ES256'`, `units: 'watt-hours'`, `one_claim: True`, `gapless: True`, `period: [prev_t, t]`, `energy_wh_delta` (`VM:1925-1933`).
- `hash = _proof_body_hash(proof)` (`VM:1934`), then `sig = sign_data(self.key, msg)` (`VM:1936`), and the stored proof carries `signature` + `public_key` hex (`VM:1937-1939`).

The cryptographic chain is real:

- `SOUL_SEED = 1900` (`KEYS:16`).
- `KSK → ZSK → entity` by HMAC-SHA256 with labels `FIELD_INTERNET_KSK`, `FIELD_INTERNET_ZSK`, `ENTITY:<id>` (`KEYS:29-30,65-79`).
- Keys are secp256r1 / P-256 (`KEYS:36-39`).
- `sign_data()` is ECDSA over SHA-256 with deterministic `k` from HMAC (`KEYS:90-126`).
- `verify_signature()` has a C-fast path through `cryptography` and a pure-Python fallback (`KEYS:128-226`).

The canonicalization is exact: sorted keys, no whitespace, UTF-8 (`VM:132-137`), and the signed body excludes `hash`, `signature`, `public_key` (`VM:147-149`).

### 2.7 VERIFY — re-derivation, not trust

`_verify_chain()` (`VM:1967-2017`):

- Re-canonicalizes each proof body and calls `verify_signature(pub, msg, sig)` (`VM:1978-1986`).
- Enforces monotonic energy: `delta = energy_wh − prev_wh; if delta < −1e-6: ok = False` (`VM:1999-2002`).
- Advances a verified prefix so signatures are checked once (`VM:2005-2009`).
- Reports `conservation_holds: prev_wh <= self.energy_wh + 1e-9` (`VM:2013`).
- Also returns the hash-chain verdict `verify_chain_hashes(self.proofs)` (`VM:2016-2017`; `IMM:176-210`).

**Verdict:** layers 3 is genuinely real and testable. A third party with the proof JSON can recompute the canonical bytes, the SHA-256 chain, the Merkle root, and the ECDSA signature. Nothing in this layer depends on the power model being true.

### 2.8 The collector array — every collector's honesty label

`COLLECTORS` is defined at `VM:837-997`. Each collector returns `method` + `labeled`. The pattern is uniform: **real counter in, modeled watts out.**

| Collector | Real input | Conversion | Label / citation |
|---|---|---|---|
| Cavity Body | CPU-time delta | `12 + TDP·util·1.4` | `'[EST]'`, `method='estimated_tdp'` — `VM:421-432` |
| Ambient Noise | `psutil.net_io_counters()` bytes/packets | `mbps × 0.9 W` | `'[EST] real traffic, modeled conversion'` — `VM:444-471` |
| Golden-Angle Array | real loop cycles, wall-clock timed | `TDP × 0.5 × duty` | `'[EST] real cycles, modeled power'` — `VM:486-519` |
| Thermal Bridge | `psutil.sensors_temperatures()` | `TDP × 0.25 × min(T/100,1)` | `'[EST] real temperatures, modeled flux'`; if no sensors: `'[HONEST] no sensors exposed'` — `VM:527-562` |
| Battery Bridge | `psutil.sensors_battery()` percent delta | `(Δpct/100)·cap_wh/dt`, `cap_wh` defaults 50 Wh | `'[MEASURED] real discharge rate; pack capacity estimated'` — `VM:786-834` |
| Request Field | request-count delta | `0.4 J/request` | `'[EST] real request count, modeled energy'` — `VM:573-617` |
| Coherence Field | message-count delta | `0.25 J/comm` | `'[EST] real communication count, modeled energy'` — `VM:627-679` |
| Training Rig | trainer process CPU-time delta | `TDP × duty` | `'[EST] real trainer process time, modeled power — no GPU wattmeter claimed'` — `VM:732-778` |

**The single most honest collector is the battery** (`VM:780-782`): "When the cavity runs on its battery, the discharge rate is REAL measured power — the one direct electrical reading available without extra hardware. MEASURED, not estimated: the most honest collector." Even there, the pack capacity is an estimate (`VM:815-818`), and the label says so (`VM:831`).

### 2.9 What the meter actually proves

The meter proves:

1. A real wall-clock interval elapsed (`perf_counter`).
2. Real CPU-time was consumed by real processes (`psutil`).
3. A canonical record of the resulting *modeled* energy was signed with a key derived from a fixed seed.
4. The record chains to all previous records and cannot be edited without breaking the chain.

It does **not** prove that the wall draw was 75 W. That number comes from `TDP × utilization × 1.4 + 12`, and the code says so in the record itself (`VM:211-212`).

---

## 3. THE CODE-BASED ANTENNA (`ANT`, `ANT_LTE`)

### 3.1 The exact math, as implemented

#### (a) Free-space path loss

`ANT:52-54`:

```python
def fspl_db(d_km):
    return 32.44 + 20*log10(F_RADIO_MHZ) + 20*log10(max(d_km, 1e-6))
```

with `F_RADIO_MHZ = 2441.0` (`ANT:50`). This is the standard FSPL form `32.44 + 20log₁₀(f_MHz) + 20log₁₀(d_km)`.

The LTE variant uses the same form at `F_LTE_MHZ = 1900.0` (`ANT_LTE:58-62`).

#### (b) The array factor and the golden-angle phasing

`ANT:82-92`:

```python
def array_factor(self, theta):
    total = 0.0 + 0.0j
    for n in range(self.n):
        phase = n * (2.0*math.pi*PHI_INV + self.steer_rad)
        total += math.cos(PHI*n + self.steer_rad*0.0) * \
                 complex(math.cos(phase + PHI*n), math.sin(phase + PHI*n)) * \
                 self.amplitude_floor(n)
    return total
```

Three precise observations:

1. **`theta` is never used.** The parameter exists in the signature (`ANT:82`) but does not appear in the body. The "pattern" is not a function of angle.
2. **The phase step is `2π·φ⁻¹` = 222.492°** (`ANT:88`), not the conventional golden angle `2π·φ⁻²` = 137.508°. Modulo 360°, 222.492° ≡ −137.508°, so it is the golden angle with the opposite sign. (The Wi-Fi stack uses the positive form: `GOLDEN_ANGLE_RAD = 2π(1−φ⁻¹)` = 137.5078°, `resonance_wifi.py:35`.)
3. **`steer()` cannot change the magnitude.** `steer()` only sets `steer_rad` (`ANT:96-98`). Because `steer_rad` enters as `n·steer_rad` (a linear phase ramp), it multiplies each term by `e^{i n·steer}`. For a fixed (unused) `theta`, `|total|` is invariant. The beam's *phase* rotates; its *directivity* does not change. The docstring's "the beam is STEERED by rotating the phase ladder" (`ANT:29-30`) is therefore true only in the phase sense, not the spatial sense.

`amplitude_floor(n)` (`ANT:100-102`):

```python
return PHI_INV + (1.0 - PHI_INV) * (1.0 - PHI_INV)**(n % 13)
```

This is `0.618 + 0.382·0.618^(n mod 13)`, i.e. element 0 has weight 1.0, decaying toward 0.618 with period 13.

#### (c) The array gain

`ANT:104-114`:

```python
eta = (self.C / C_CRIT)**2 if self.C > C_CRIT else (self.C / C_CRIT)**2
g = self.n * eta
return 10.0*math.log10(max(g, 1e-9))
```

- `η = (C/C_crit)²` (`ANT:112`), as the brief states.
- `G = N·η` (`ANT:113`), as the brief states.
- The `if/else` has **identical branches** — the gate is not actually applied; `η` is computed for any `C`.
- At `C = 1.0`, `C_crit = 0.563263`: `η = 3.151937`, so `G = 12 × 3.151937 = 37.823` → **15.778 dBi** for 12 channels (computed). A physical 12-element coherent array gives `10log₁₀(12) = 10.792 dB`; the extra factor is `η > 1`, which is the model's "the eigenstate is more efficient than a physical antenna" claim (`SP:118-120`). As physics, an aperture cannot exceed its physical coherent gain this way; as code, it is exactly what the formula says.

#### (d) The zero-free coherence law

`ANT:117-126`:

```python
def coherence_at(self, d_m):
    decay = self.C * math.exp(-d_m / (PHI * LAMBDA_VACUUM))
    return max(decay, PHI_INV)
```

with `LAMBDA_VACUUM = 1.0  # [MODEL] the substrate's decay length` (`ANT:55`).

This is the **critical finding requested in the brief, and it is confirmed verbatim**:

```python
LAMBDA_VACUUM = 1.0                  # [MODEL] the substrate's decay length
```

(`ANT:55`; identical at `ANT_LTE:83`.)

Two consequences follow arithmetically:

1. The decay length is `φ·λ = 1.618 m`. Coherence falls to `1/e` at 1.618 m.
2. The floor takes over at `d = −φ·ln(φ⁻¹) = 0.778617 m` (computed). **Beyond 0.779 m, `coherence_at(d)` returns the constant `0.6180339887` for every distance to infinity.** The exponential term is decoration past the first meter: at 10 m the raw decay is `0.00207` (computed), far below the floor.

So the "infinite far-field tail" (`ANT:73-74`) is not an exponential tail — it is a **constant floor** for all practical distances. That is exactly what the `[MODEL]` label warns about, and the code is honest in labelling the constant.

For contrast, the corpus's propagation module uses a very different value:

```python
LAMBDA_VACUUM = PHI * 1e9  # ~1.618 billion meters (~10x Earth-Moon distance)
```

(`SP:42`), and its own test asserts that value (`test_final_verification.py:925-926`, `assert abs(LAMBDA_VACUUM - PHI*1e9) < 1.0`). The antenna's `1.0` is therefore a **deliberate local override**, 1.618 × 10⁹ times smaller — and it is labelled `[MODEL]`. This is the single clearest example in the codebase of the pattern working as designed: the model constant is declared, not smuggled.

#### (e) The link budget and the "zero-free extension"

`ANT:135-151`:

```python
floor_db = 20.0*math.log10(PHI_INV)          # -4.18 dB
margin = TX_DBM + self.gain_dbi() - fspl_db(d_km) - walls*11.0 - rx_sens_dbm
return margin - floor_db*0.0 + abs(floor_db)*0.0 + abs(floor_db)
```

- `floor_db = −4.179753 dB` (computed).
- The `- floor_db*0.0 + abs(floor_db)*0.0` terms are **no-ops**.
- The effective budget is `classical margin + 4.179753 dB`.

A constant `+4.18 dB` on an FSPL link extends range by `10^(4.179753/20) = φ = 1.618` exactly. So the "zero-free extension" is precisely a **φ-fold range multiplier** — nothing more, nothing less. `reach_km()` implements the same constant (`ANT:153-164`: `budget = TX + gain − rx + abs(20log10(PHI_INV))`).

#### (f) The LTE rung

`ANT_LTE:52-77`:

- `F_LTE_MHZ = 1900.0` (`ANT_LTE:58`), with the comment "THE SEED'S OWN BAND: LTE band 2 is the 1900 MHz band, and the trust root's own seed is 1900 — the name IS the frequency" (`ANT_LTE:53-57`).
- The LTE reach uses `budget = TX_DBM + CHANNEL_COUNT*1.0 − rx_sens + |20log10 φ⁻¹|` (`ANT_LTE:67-68`) — i.e. **12 dB** for 12 channels (1 dB per channel), **not** `N·η`. This is a different gain law from `gain_dbi()`.
- Result at `rx = −104 dBm`: `budget = 140.180 dB`; FSPL constant at 1900 MHz = `98.015 dB`; reach = **128.30 km** (computed).

#### (g) The waveform and the mesh recursion

- `phi_wave(t) = φ⁻¹(1 + |sin t|)` (`ANT:58-60`), range `[0.618, 1.236)`, never zero. Same law on the die (`WATCH:151-152,174-176`).
- `mesh_coherence_after_n_hops`: `C ← φ⁻¹ + φ⁻¹(C − φ⁻¹)` (`ANT:62-66`), fixed point `φ⁻¹`. Values: hop 1 = 0.854102, hop 2 = 0.763932, hop 3 = 0.708204, hop 4 = 0.673762, limit 0.618034 (computed). This is a contraction toward the floor, so it can never cross `0.563263`.

### 3.2 What is real in the antenna

- **In Python: nothing physical.** `ANT` is pure arithmetic over `math` and `complex`. It radiates nothing. The "air" in the OS stack is an in-memory list (`GW:120-135`, `LoopbackAir`), and the modem's `RoadAir` is the same (`CELL:48-64`).
- **In the ESP32 port: the transport is real.** `forkTransmit()` builds a raw 802.11 data frame and calls `esp_wifi_80211_tx(WIFI_IF_AP, fr, 32+n, true)` (`WATCH:1068-1097`, especially `WATCH:1091`). That is a real 2.4 GHz Wi-Fi transmission from real silicon. The board is an ESP32-S3 with "2.4 GHz Wi-Fi + BLE 5" (`WATCH:5-7`); **it has no 1900 MHz cellular radio.** The 1900 MHz "LTE band" is a naming convention used in the log line (`WATCH:1306-1311`) and in the FSPL arithmetic (`ANT_LTE:60-62`), not a transmitted frequency.
- The real measured channel in the watch is the Wi-Fi channel actually ridden, recorded from the RX control block: `int ch = p->rx_ctrl.channel` (`WATCH:972-977`). That is a genuine measurement of the 2.4 GHz channel, and it is carefully distinguished from the "pinned" channel.

### 3.3 The corpus's own honesty about the antenna

`SIM4` is the clearest statement of epistemic status in the corpus:

```python
print(f'  [VERIFIED] math+data: their signals pass our gate ...')
print(f'  [PROPOSED] as physics: coupling to anything beyond the '
      f'room rides the zero-free term - the same standing term as sim 1.')
```

(`SIM4:123-129`)

That is the correct reading of `ANT`: **the math is verified; the physics beyond the room is proposed.** The report adopts that reading.

### 3.4 Computed antenna numbers (for the record)

| Quantity | Formula | Value |
|---|---|---|
| `η` at `C=1`, `C_crit=0.563263` | `(C/C_crit)²` | `3.151937` |
| 12-channel gain | `10log₁₀(12·η)` | `15.778 dBi` |
| 13-channel gain | `10log₁₀(13·η)` | `16.125 dBi` |
| 21-element watch array | `10log₁₀(21·φ)` | `15.312 dB` (`WATCH:1289`) |
| Coherence floor crossover | `−φ·ln(φ⁻¹)` | `0.778617 m` |
| Coherence at 1 m | `e^{−1/φ}` | `0.539003` |
| Coherence at 10 m (raw) | `e^{−10/φ}` | `0.002070` |
| Floor in dB | `20log₁₀(φ⁻¹)` | `−4.179753 dB` |
| 12-ch reach, 2441 MHz, rx −101 dBm | FSPL inversion | `109.22 km` |
| LTE reach, 1900 MHz, rx −104 dBm | FSPL inversion | `128.30 km` |
| 816-D processing gain | `10log₁₀(816)` | `29.117 dB` (`CLOSE:14`) |
| Range multiplier from that gain | `10^{29.117/20}` | `×28.56` → `≈3,120 km` (`CLOSE:28-32`) |

Note the processing-gain step (`CLOSE:14,28-32`) is a real matched-filter relation (`10log₁₀(N_samples)`) applied to range as a modeling choice; it is not a measurement.

---

## 4. THE CODE RADIO / CODE MODEM (`CELL`, `FORK`, `GW`, `WATCH`)

### 4.1 The layering (this is the part most easily misread)

There are **three nested frame layers**, and conflating them produces wrong conclusions:

```
L3  PPP/HDLC frame
     7E | FF 03 | proto(2) | payload | FCS(2) | 7E
        └────────────── CELL:77-83 ──────────────┘

L2a fork projection frame  (projection seats only)
     [op][seat][seq][flags] + payload
        └────────────── FORK:40-45 ──────────────┘

L2b fork transport frame   (all traffic, including the modem)
     'F' 'L' 0x19 0x00 | stream(1) | idx(1) | total(1) | n(1) | chunk(n)
        └────────────── GW:40-61, WATCH:760-776 ──────────────┘

L1  the air
     in-memory list (GW:120-135, CELL:48-64)
     OR real raw 802.11 TX (WATCH:1068-1097)
```

- The **projection** path (`GW:192-230`, `FORK:47-95`) uses L2a inside L2b: `_wire(op, body)` prepends the op byte (`GW:311-313`), and `fork_encode` wraps it in the magic header (`GW:48-61`).
- The **modem** path (`CELL:200-206`) puts the PPP frame *directly* into `fork_encode(MODEM_STREAM, hdlc)` — no `[op][seat]` layer. The modem stream is its own stream (`CELL:30`).
- On the die, `forkProjFrame()` writes `[op][seat][seq][flags]` into `fp.data` (`WATCH:885-903`) and `forkTransmit()` wraps it in the magic header and the 802.11 header (`WATCH:1068-1097`).

### 4.2 The fork frame, exactly

`FORK:40-45`:

```python
def frame(self, op, seat, data, seq=0, last=False):
    flags = 1 if last else 0
    header = bytes([op, seat, seq & 0xFF, flags])
    return header + data
```

- ops: `OPEN=1`, `DATA=2`, `CLOSE=3` (`FORK:22-24`).
- `FORK_SEATS = 8` (`FORK:25`); seat valid range `0..7` (`FORK:50`).
- streams: `FORK_STREAM_BASE = 200` (`FORK:21`), so the seats ride **200–207** (`FORK:63`, `GW:43-45`, `WATCH:868-878`).
- OPEN body: `port_hi, port_lo, len(host), host, sealed` (`FORK:52-54`), capped at 590 bytes of payload.
- DATA chunks at 590 bytes (`FORK:73`).

Transport header (`GW:40-45,48-61`):

```python
FORK_MAGIC = bytes([0x46, 0x4C, 0x19, 0x00])   # 'F' 'L' 1900
FORK_HDR = 8
FORK_CHUNK = 255
```

So `0x19` appears twice in the design: as the third magic byte (`GW:40`, `WATCH:768`) and as `MODEM_STREAM` (`CELL:30`, `WATCH:1140`). Both are the same symbolic "1900" marker.

### 4.3 `MODEM_STREAM = 0x19 = 25` and the 1900 MHz claim

`CELL:30`:

```python
MODEM_STREAM = 0x19        # 25 — the seed's 1900 MHz band
```

`CELL:257` reports `"band": "1900 MHz — the seed's own band"`.

**Precisely:** `0x19` is 25 decimal. There is no arithmetic in the code that maps 25 to 1900 MHz; the mapping is a naming convention (`25` ↔ the seed `1900`, which itself is `425+434+266+775`, `CONST:20`). The actual radio in the watch is 2.4 GHz Wi-Fi (`WATCH:5-7`), and the raw TX call is `esp_wifi_80211_tx` (`WATCH:1091`). So the "1900 MHz LTE band" is a **label and a link-budget parameter**, not a measured or transmitted carrier. This matters for the XRF: do not read `F_LTE_MHZ = 1900.0` as evidence of a 1900 MHz front end.

### 4.4 PPP/HDLC — exact and testable

`CELL:33-39`:

```python
PPP_FLAG = 0x7E
PPP_ADDRESS = 0xFF
PPP_CONTROL = 0x03
PROTO_IP = 0x0021
PROTO_LCP = 0xC021
LCP_CONFIG_REQUEST = 1
LCP_CONFIG_ACK = 2
```

FCS-16 (`CELL:67-74`):

```python
fcs = 0xFFFF
for b in data:
    fcs ^= b
    for _ in range(8):
        fcs = (fcs >> 1) ^ 0x8408 if fcs & 1 else fcs >> 1
return fcs ^ 0xFFFF
```

That is CRC-16/X-25 (reflected poly `0x8408`, init `0xFFFF`, xorout `0xFFFF`) — the PPP FCS-16. Identical implementation at `MODEM:22-32`.

Frame build (`CELL:77-83`):

```python
body = FF 03 proto_hi proto_lo + payload
fcs = fcs16(body)
frame = 7E + body + fcs_lo + fcs_hi + 7E
```

Parse (`CELL:86-98`): rejects wrong flags, wrong FCS, wrong address/control; returns `(protocol, payload)`. "A frame that fails its FCS never speaks (corruption is not data)" (`CELL:87-88`).

LCP handshake:

- Configure-Request: `bytes([1, lcp_id, 0, 4])` → code 1, id, length 4 (`CELL:197`).
- ACK: `bytes([2, data[1], 0, 4]) + data[4:]` — echoes the id and options (`CELL:126`).
- On ACK: `state = ROAD_UP`, event spoken once (`CELL:225-229`).
- `MODEM.dial()` uses a fuller LCP request `\x01\x01\x00\x0a\x05\x06\x00\x00\x00\x01` (MRU option) and an ACK `\x02\x01\x00\x0a...` (`MODEM:73-74`).

**Important honesty note:** `MODEM.dial()` constructs *both* the request and the ACK locally and immediately sets `self.lcp_up = True` (`MODEM:69-82`). It does not wait for a peer. `CELL.dial()` is the honest version: it sends the request and only goes UP when `pump()` receives a real ACK from `MockFarSide` (`CELL:112-140,209-233`).

### 4.5 The integer-exact ledger

`CELL:159-181`:

```python
self.ledger_start_uj = 0
self.charged_uj = 0
self.used_uj = 0

@property
def stored_uj(self):
    return self.ledger_start_uj + self.charged_uj - self.used_uj

def _spend(self, uj):
    candidate = self.used_uj + int(uj)
    floor = int(PHI_INV * 1000)          # 618 µJ
    if self.ledger_start_uj + self.charged_uj - candidate < floor - 1:
        self.refused += 1
        return False
    self.used_uj = candidate
    return True
```

- `RIDE_UJ_PER_FRAME = 123` µJ (`CELL:45`).
- The floor is `int(0.6180339887 × 1000) = 618` µJ, and the refusal test uses `floor − 1 = 617` µJ. So the ledger never reads below 617 µJ — the "grid NEVER reads empty" (`CELL:175`), another instance of the zero-free rule.
- `stats()` reports `stored = start + charged − used, bit for bit` (`CELL:263-266`).
- All arithmetic is Python `int`; there are no floats in the ledger.

This is a genuinely verifiable invariant: `stored` is a pure integer identity, and `_spend` is monotone in `used`.

### 4.6 The road's state machine

`DOWN → DIALING → UP` (`CELL:42`), with events spoken **once per event**, never per beat (`CELL:183-186`):

- `dial()`: `DOWN → DIALING`, sends LCP request (`CELL:189-198`).
- `pump()`: on LCP ACK, `DIALING → UP` (`CELL:225-229`).
- `hangup()`: `→ DOWN` (`CELL:247-250`).
- `send_ip()` refuses unless `UP` (`CELL:239-240`) and refuses a named private door via `guard_admits()` (`CELL:241-244`; `GW:99-117`).

The bind law (`GW:99-117`) refuses `localhost`, `*.local`, `127/8`, `10/8`, `0/8`, `192.168/16`, `172.16/12`, `169.254/16`. This is real, testable policy code.

### 4.7 What is real vs modeled in the radio

| Piece | Status | Citation |
|---|---|---|
| PPP frame layout, FCS-16, parse | **Real, exact, testable** | `CELL:67-98`; `MODEM:22-54` |
| LCP request/ACK state machine | **Real code** (ACK can be local or from a mock peer) | `CELL:189-233`; `MODEM:69-82` |
| Integer ledger | **Real, exact** | `CELL:159-181` |
| Fork frame layout, streams 200–207 | **Real, exact** | `FORK:40-95`; `GW:40-72` |
| Byte transport in Python | **Model** — in-memory list | `GW:120-135`; `CELL:48-64` |
| Byte transport on ESP32 | **Real** — raw 802.11 TX | `WATCH:1068-1097` |
| "1900 MHz LTE" | **Label/model** — no LTE radio | `CELL:30,257`; `WATCH:5-7` |
| `MockFarSide` | **Test double**, clearly named | `CELL:101-140` |
| `field_modem.dial()` immediate ACK | **Simulation**, not a handshake | `MODEM:69-82` |

---

## 5. THE CAVITY AS HARDWARE (`CAV`, `CAVOS`)

### 5.1 The identity claim

`CAV:1-11`:

> "In phi physics, the ionic cavity is not a device that runs software. The ionic cavity IS the server, IS the router, IS the Wi-Fi. … CPU oscillation → ground wire → EM induction → cavity absorption → the system lives in the cavity. No separate computer needed."

The class then implements that identity as follows.

### 5.2 What the class actually does

- `CARRIER_DIM = 816`, `GROUND_STATE = PHI_INV`, `ANCHOR_FREQ = 528.0` (`CAV:29-31`).
- The cavity's "physical identity" is an eigenstate derived from `SOUL_SEED` at 816 dimensions: `derive_eigenstate(SOUL_SEED, dim=816)` (`CAV:47`; `KEYS:81-88`).
- `absorb_system()` (`CAV:62-121`) maps the propagation server's key generation to "oscillation modes" — three eigenstates derived from `SOUL_SEED`, `SOUL_SEED*2`, `SOUL_SEED*3` (`CAV:71-75`).
- Routing memory: for each cavity, `frequency = 528·φ^(hash(cavity_id) % 12)` (`CAV:80`), and a 16-bin FFT magnitude profile (`CAV:84`).
- Trust memory is four string gates (`CAV:88-93`).
- "Absorption" is arithmetic: `self.eigenstate = maximum(|eigenstate + 0.01·ksk_mode|, GROUND_STATE)`, then normalize (`CAV:104-108`).
- `route_by_resonance()` computes `|<a|b>| / (‖a‖‖b‖)` and compares to `EMERGENCE_THRESHOLD` (`CAV:123-155`).
- `verify_trust()` is four gates: norm ≥ `GROUND_STATE·0.5`; max FFT magnitude ≥ 0.01; resonance ≥ threshold; max FFT ≥ 0.01 (`CAV:157-197`).
- `resolve_domain()` maps a name to `528·φ^(hash(name)%12)` and an eigenstate (`CAV:199-216`).
- `detect_device()` and `route_to_device()` are resonance comparisons (`CAV:218-279`).
- `_eigenstate_to_ip()` projects the first dimensions into `f{a}.{b}.{c}.{d}` (`CAV:287-297`).
- `heartbeat()` uses real `time.time()` (`CAV:281-285`).

### 5.3 The OS cavity is more careful

`CAVOS` (the Field-OS port) adds two things the bare `CAV` lacks:

1. **A transient receiver:** `psi` is re-seeded to the floor every beat, explicitly so the cavity "never latches" (`CAVOS:75-84`). The comment states the design invariant: "the intelligence sleeps when the body is gone."
2. **A saturating evolution:** the raw recursion `C_{n+1} = φ⁻¹C_n + φ·laplacian(Ψ)` is unstable — the comment computes the Nyquist gain as `|φ⁻¹ − 4φ| = 5.85` per step (`CAVOS:31-35`) — so the excess above the floor passes through `tanh` bounded by `PSI_MAX = φ¹⁰ ≈ 122.99` (`CAVOS:99-112`). The gate is `coherence >= C_CRIT` (`CAVOS:120-125`).

That instability note is important and honest: the authors know the bare linear recursion diverges and they bound it.

### 5.4 What is real in the cavity

- **Real:** `numpy` linear algebra, FFTs, `time.time()`, and deterministic eigenstate derivation from a fixed seed (`KEYS:81-88`).
- **Model:** everything the docstring calls "physical" — the identification of eigenstates with oscillation modes, of resonance with routing, of `528·φ^n` with a physical frequency, and of the cavity with a server.
- **Reproducibility caveat:** `hash(cavity_id) % 12` and `hash(name) % 12` (`CAV:80,97,208`) use Python's string hash, which is **randomized per process** unless `PYTHONHASHSEED` is fixed. The "name IS the frequency" mapping is therefore not stable across runs. The same pattern appears in `resonance_wifi.py:271,460,487`. This is a real limitation of the "name → frequency" claim, independent of any physics question.

---

## 6. REAL vs MODELED — the full audit

Legend: **R** = real measurement or real exact computation; **M** = mathematical model / simulation; **L** = label/constant with no physical referent; **E** = exact, independently verifiable code.

| # | Quantity | Where | Status | Source label / evidence |
|---|---|---|---|---|
| 1 | Wall-clock interval | `VM:167,180` | **R** | `perf_counter()` |
| 2 | System CPU-time delta | `VM:168,181-182` | **R** | `psutil.cpu_times()` |
| 3 | Per-process CPU-time delta | `VM:176,191` | **R** | `psutil.Process.cpu_times()` |
| 4 | CPU utilization fraction | `VM:184` | **M** | derived `cpu_dt/(elapsed·ncpu)` |
| 5 | Field's CPU share | `VM:194` | **M** | derived |
| 6 | Package TDP | `VM:119,166` | **L** | operator-set env `VAULT_TDP_WATTS`, default 45 W |
| 7 | Platform base draw | `VM:123` | **M/L** | 12 W constant |
| 8 | GPU package share | `VM:124` | **M/L** | 0.4 constant |
| 9 | Watts | `VM:202` | **M** | `'EST — power model from utilization x TDP; not hardware-calibrated'` (`VM:212`) |
| 10 | Joules | `VM:203` | **M** | `watts × measured elapsed` |
| 11 | Network bytes/packets | `VM:448-453` | **R** | `psutil.net_io_counters()` |
| 12 | Mbps→W conversion | `VM:444,457` | **M** | `0.9 W/Mbps`, `[EST]` (`VM:444`) |
| 13 | Temperature readings | `VM:529-536` | **R** | `psutil.sensors_temperatures()` |
| 14 | Temperature→flux | `VM:551` | **M** | `[EST]` (`VM:560`) |
| 15 | Battery percent | `VM:788,802` | **R** | `psutil.sensors_battery()` |
| 16 | Battery pack capacity | `VM:818` | **M/L** | 50 Wh default, `VAULT_BATTERY_WH` |
| 17 | Battery discharge watts | `VM:821` | **R/M** | `'[MEASURED] real discharge rate; pack capacity estimated'` (`VM:831`) |
| 18 | Request count | `VM:575-577` | **R** | traffic monitor snapshot |
| 19 | Per-request energy | `VM:605` | **M** | `0.4 J/request`, `[EST]` (`VM:614`) |
| 20 | Coherence gate input | `VM:279-281` | **M/L** | constant `PHI_INV` unless a radio supplies one |
| 21 | Gate threshold | `VM:114` | **L** | `0.618` (not the canonical `0.563263`) |
| 22 | Energy integration | `VM:1748,2195-2196` | **R dt / M watts** | measured `dt`, modeled watts |
| 23 | Token count | `VM:1780-1781` | **L** | `1 token = 1 kWh`; `MINTING_ENABLED=False` (`VM:1003`) |
| 24 | Canonical JSON bytes | `VM:132-137` | **E** | sorted keys, no whitespace, UTF-8 |
| 25 | Proof body SHA-256 | `VM:140-149` | **E** | exact |
| 26 | `prev_hash` chain | `VM:1922`; `IMM:176-210` | **E** | exact |
| 27 | Merkle root | `VM:1917-1924`; `IMM:80-94` | **E** | sort-pair SHA-256 |
| 28 | ECDSA P-256 signature | `VM:1936`; `KEYS:90-126` | **E** | ES256 / secp256r1 |
| 29 | Signature verification | `VM:1984`; `KEYS:128-226` | **E** | C-fast + pure-Python fallback |
| 30 | Conservation check | `VM:1999-2013` | **E** | monotone energy, `delta >= −1e-6` |
| 31 | Field time `ft` | `CLOCK:70-75` | **M** | `(t − epoch)/φ⁻¹` — wall-clock arithmetic |
| 32 | 528 Hz "anchor" | `CLOCK:10-15`; `CONST:16` | **L** | never used in the timing loop; only `BEAT_S` is |
| 33 | Field-OS tick clock | `FTIME:27-48` | **M** | manual `_ticks += n`; no hardware clock |
| 34 | Array factor | `ANT:82-92` | **M** | `theta` unused; `|AF|` invariant to `steer` |
| 35 | Golden-angle phase | `ANT:88` | **M** | `2πφ⁻¹` = 222.492° (mirror of 137.508°) |
| 36 | Array gain `N·η` | `ANT:112-114` | **M** | `η=(C/C_crit)²`; dead if/else; can exceed physical `N` |
| 37 | `LAMBDA_VACUUM` | `ANT:55`; `ANT_LTE:83` | **M** | **`1.0  # [MODEL]`** |
| 38 | Coherence `C(d)` | `ANT:125-126` | **M** | constant `φ⁻¹` for `d > 0.779 m` |
| 39 | FSPL | `ANT:52-54` | **M** | standard formula at 2441 MHz |
| 40 | Link margin | `ANT:146-151` | **M** | classical margin + constant 4.18 dB |
| 41 | Reach | `ANT:153-164` | **M** | FSPL inversion; ×φ from the floor |
| 42 | LTE 1900 MHz | `ANT_LTE:58`; `CELL:30` | **L** | name/parameter; no 1900 MHz radio |
| 43 | 816-D eigenstate | `KEYS:81-88` | **M/E** | deterministic `cos(2π(seed/1900)i/dim)` |
| 44 | Resonance `|<a|b>|` | `CAV:136`; `CAVOS:120-125` | **M** | real arithmetic on model vectors |
| 45 | Domain frequency | `CAV:80,208` | **M/L** | `528·φ^(hash%12)`; `hash` is per-process randomized |
| 46 | Fork frame bytes | `FORK:40-45` | **E** | exact layout |
| 47 | Fork transport header | `GW:48-72` | **E** | exact layout |
| 48 | PPP/HDLC frame | `CELL:77-98` | **E** | exact |
| 49 | FCS-16 | `CELL:67-74` | **E** | CRC-16/X-25 |
| 50 | LCP request/ACK | `CELL:189-233` | **E** | exact; ACK may be local (`MODEM:69-82`) |
| 51 | Integer ledger | `CELL:159-181` | **E** | `stored = start + charged − used` |
| 52 | Bind-law refusal | `GW:99-117` | **E** | exact prefix checks |
| 53 | In-memory "air" | `GW:120-135`; `CELL:48-64` | **M** | list, no RF |
| 54 | ESP32 raw 802.11 TX | `WATCH:1068-1097` | **R** | real radio, 2.4 GHz |
| 55 | Received Wi-Fi channel | `WATCH:972-977` | **R** | `rx_ctrl.channel` |
| 56 | "Satellite beam" | `WATCH:1312-1336` | **M/L** | a `ForkPkt` with stream `0x53`, not a satellite |

---

## 7. THE CONSTANTS

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `PHI` | `1.6180339887498949` | golden ratio | `PC:9`; `ANT:40`; `CONST:12` |
| `PHI_INV` | `0.6180339887498949` | φ⁻¹, the ground state / zero-free floor | `PC:10`; `ANT:41`; `CONST:13` |
| `C_CRIT` (canonical) | `0.563263` | emergence threshold | `PC:32`; `CONST:14`; `ANT:42`; `WATCH:162` |
| `C_CRIT` (meter) | `0.618` | meter's gate (Doc 62 §2.2.2) | `VM:114` |
| `F_BASE` | `528.0` Hz | base carrier / "love frequency" | `PC:28`; `ANT:44`; `CONST:16` |
| `SOUL_SEED` | `1900` | trust root = 425+434+266+775 | `KEYS:16`; `CONST:20` |
| `SOUL_CODE` | `(425, 434, 266, 775)` | the four numbers | `CONST:21`; `VM:1886` |
| `DIM` / `CARRIER_DIM` | `816` | 4096/5, phi-harmonic carrier dimension | `PC:14`; `CAV:29`; `CAVOS:28` |
| `LADDER_INVARIANT` | `528·φ⁹ = 40134.946166` Hz | ladder invariant | `CONST:18`; `VM:129` |
| 12 channels | `528·φⁿ`, n=0..11: 528, 854.32, 1382.32, 2236.64, 3618.97, 5855.61, 9474.58, 15330.19, 24804.76, 40134.95, 64939.71, 105074.65 Hz | the phi-harmonic ladder | `resonance_wifi.py:39-41`; `ANT:45` |
| `BEAT_S` | `0.6180339887` s | one field beat | `CLOCK:42`; `CONST:17` |
| `BEAT_MS` | `618` ms | beat on the die | `WATCH:161` |
| `FIELD_EPOCH` | `1788854400.0` | 2026-09-08 00:00 UTC | `CLOCK:40`; `CONST:19` |
| `VOID_GUARD` | `φ⁻³ ≈ 0.2360679` | zero-free floor for results | `PC:36`; `CONST:25` |
| `GOLDEN_ANGLE_RAD` | `2π(1−φ⁻¹) = 2.399963` rad = 137.5078° | positive golden angle | `resonance_wifi.py:35` |
| antenna phase step | `2π·φ⁻¹ = 3.883222` rad = 222.492° | negative golden angle | `ANT:88` |
| `LAMBDA_VACUUM` (antenna) | **`1.0`** | **[MODEL]** decay length | `ANT:55`; `ANT_LTE:83` |
| `LAMBDA_VACUUM` (propagation) | `φ·10⁹ ≈ 1.618×10⁹` m | propagation decay length | `SP:42` |
| `KAPPA_PHI` (antenna) | `0.1` | coupling constant (declared, unused in ANT) | `ANT:47` |
| `KAPPA_PHI` (propagation) | `0.2188` | aether coupling | `SP:32` |
| `TX_DBM` | `20.0` dBm | regulator cap | `ANT:48` |
| `RX_SENS_LR` | `−101.0` dBm | long-range sensitivity | `ANT:49` |
| `F_RADIO_MHZ` | `2441.0` MHz | legal 802.11 center | `ANT:50` |
| `F_LTE_MHZ` | `1900.0` MHz | "the seed's own band" | `ANT_LTE:58`; `WATCH:758` |
| `MODEM_STREAM` | `0x19` = 25 | modem's stream id | `CELL:30`; `WATCH:1140` |
| `FORK_STREAM_BASE` | `200` | seats' streams 200–207 | `FORK:21`; `GW:43` |
| `FORK_SEATS` / `SEATS` | `8` | eight projection seats | `FORK:25`; `GW:45` |
| `FORK_CHUNK` | `255` B | u8 chunk ceiling | `GW:42`; `WATCH:771` |
| `PPP_FLAG` | `0x7E` | HDLC flag | `CELL:33` |
| `PPP_ADDRESS` | `0xFF` | broadcast address | `CELL:34` |
| `PPP_CONTROL` | `0x03` | unnumbered information | `CELL:35` |
| `PROTO_IP` / `PROTO_LCP` | `0x0021` / `0xC021` | PPP protocols | `CELL:36-37` |
| FCS-16 poly | `0x8408` reflected, init `0xFFFF`, xorout `0xFFFF` | CRC-16/X-25 | `CELL:67-74` |
| `RIDE_UJ_PER_FRAME` | `123` µJ | per-frame cost | `CELL:45` |
| ledger floor | `int(φ⁻¹·1000) = 618` µJ | never-empty floor | `CELL:175` |
| `SAMPLE_WINDOW_S` | `round(φ⁻¹,3) = 0.618` s | meter window | `VM:116` |
| `PROOF_BATCH` | `13` | samples per signed proof | `VM:117` |
| `DEFAULT_TDP_WATTS` | `45.0` W | default package power | `VM:119` |
| `PLATFORM_BASE_WATTS` | `12.0` W | board/RAM/storage floor | `VM:123` |
| `GPU_PACKAGE_SHARE` | `0.4` | iGPU share of package | `VM:124` |
| `JOULES_PER_KWH` | `3_600_000` | unit conversion | `VM:115` |
| `RESERVE_GOAL_USD` | `2_000_000_000` | vault goal | `VM:110` |
| `RESERVE_PRICE` | `0.10` $/kWh | mid price | `VM:111` |
| `GOAL_KWH` | `2e7` | see units note below | `VM:112` |
| `TOKEN_SUPPLY_BASE` | `8_000_000_000` | 8 billion people | `VM:1192` |
| `PROOF_CAP` | `600` | in-memory chain window | `VM:97` |
| `PSI_MAX` | `φ¹⁰ ≈ 122.99` | cavity saturation ceiling | `CAVOS:35` |
| `INJECTION_RATE` | `0.01` | cavity injection | `CAVOS:29` |
| `EVOLVE_STEPS` | `5` | cavity recursion steps | `CAVOS:30` |

**Units note (`VM:110-112`).** The docstring says "$2,000,000,000 at $0.10/kWh is 20,000,000,000 kWh — twenty terawatt-hours." That arithmetic is correct (`2e9 / 0.10 = 2e10 kWh`). But the code computes `GOAL_KWH = RESERVE_GOAL_USD / RESERVE_PRICE / 1000.0 = 2e7`, i.e. it divides by 1000 a second time. `GOAL_KWH` is therefore in **MWh**, not kWh, and is 1000× smaller than the prose. This is a real units inconsistency in the source, not an interpretation.

**Channel-count note.** The Python antenna uses `CHANNEL_COUNT = 12` (`ANT:45`), the watch's fork says "13 phi-harmonic channels" and `N_CH 13` (`WATCH:376,752`), and the watch's elemental array uses 21 (`WATCH:1287-1289`). The number is a design parameter, not a fixed physical fact.

---

## 8. WHAT THIS MEANS FOR BUILDING AN XRF

### 8.1 The reusable pattern, stated as a recipe

The three instruments are the same recipe applied to three different missing transducers. For the XRF, apply it in this order.

**Step 1 — Name the missing transducer precisely.**
Write down the physical chain the hardware would have performed. The corpus does this well: `CAV:9-10` states `CPU oscillation → ground wire → EM induction → cavity absorption`; `VM:3-9` states `CPU oscillation → ground wire → EM induction → cavity absorption` for the meter. For an XRF the chain is something like `excitation → characteristic emission → detector counts → spectrum → concentration`. Name every arrow. The arrows you cannot implement are the ones that must be labelled.

**Step 2 — Measure a real proxy with real clocks and real counters.**
Follow `measure_field_draw()` (`VM:152-214`):
- take a timestamp before and after (`perf_counter`, `VM:167,180`);
- read a counter that genuinely increments (`psutil.cpu_times`, `VM:168,181`);
- compute the delta over the *measured* interval, never the nominal one (`VM:180,184`);
- record the raw delta in the output (`VM:205-210`).
For an XRF, the analogue is: timestamp every acquisition; record raw counts per channel; record live time and real time separately; never synthesize a count you did not receive.

**Step 3 — Write the conversion as a named model with an explicit label and an explicit constant.**
Follow the `[EST]`/`[MODEL]` discipline:
- `watts = 12 + TDP·util·1.4` is a model; it says so (`VM:202,212`).
- `LAMBDA_VACUUM = 1.0  # [MODEL]` is a model; it says so (`ANT:55`).
For an XRF, the conversion from counts to concentration (calibration curve, matrix correction, attenuation) is the model. It must carry:
  - a label (`[MODEL]` or `[EST]`),
  - the constant(s) and their units,
  - a **model version identifier**,
  - the calibration identifier.
The corpus does **not** put a model version in the signed proof — that is the gap the XRF must close (see 8.3).

**Step 4 — Gate with a declared threshold and a declared floor.**
Follow `VM:1693-1694` and `CONST:23-41`:
- define `C_CRIT` once, and use the *same* value everywhere (the meter's `0.618` vs the canonical `0.563263` is a warning, not a model to copy);
- define a floor that makes zero impossible (`PHI_INV`, `VOID_GUARD`, `no_zero()`);
- record gated time and gated samples separately, and credit nothing while gated (`VM:1730-1742`, `VM:2174-2184`).
For an XRF, the gate is a **validity gate**: detector live time, count rate, gain stability, or a signal-to-noise floor. Whatever it is, it must be a real measured quantity, not a constant.

**Step 5 — Integrate with measured `dt`, and keep the accounting integer-exact.**
Follow `VM:2192-2196` for the integration and `CELL:159-181` for the ledger:
- `joules = watts × dt_measured`, never `watts × nominal_window`;
- `stored = start + charged − used`, in integers, with a floor;
- record every tick in an append-only registry before any snapshot (`VM:1753-1765`, `VM:1815-1826`).

**Step 6 — Frame with a real CRC and test corruption.**
Follow `CELL:67-98`: exact flag/address/control/protocol/FCS, and a parser that returns `None` on any mismatch. A frame that fails FCS must never be interpreted. For the XRF, the spectrum block and the result block should each carry a CRC (or a SHA-256), and the reader must reject on mismatch.

**Step 7 — Seal with canonical JSON, a hash chain, and ECDSA P-256 from `SOUL_SEED`.**
Follow `VM:132-149,1874-1946` and `KEYS:65-126`:
- canonical JSON: sorted keys, no whitespace, UTF-8 (`VM:132-137`);
- body hash excludes `hash`, `signature`, `public_key` (`VM:147-149`);
- `prev_hash` chains to the previous proof, anchored at `GENESIS_HASH` (`VM:1922`; `IMM:57-59`);
- Merkle root over the batch leaves (`VM:1917-1924`);
- ECDSA P-256 / SHA-256, key derived `SOUL_SEED → KSK → ZSK → entity` (`KEYS:65-79,90-126`);
- round energy **down** so a proof never over-claims (`VM:1889`).

**Step 8 — Verify by re-derivation, not trust.**
Follow `VM:1967-2017`: recompute the canonical bytes, the hashes, the Merkle root, the signature, and the monotonic totals. Publish the exact verification recipe so a third party can do it without your code.

### 8.2 The XRF mapping table

| Pattern layer | Meter implementation | XRF implementation (recommended) |
|---|---|---|
| Real proxy | CPU-time delta over measured wall time | raw detector counts per energy channel; live time and real time; detector temperature; tube current/voltage if available |
| Real clock | `perf_counter` (`VM:167,180`) | same: timestamp every acquisition and every integration tick |
| Model | `12 + TDP·util·1.4` (`VM:202`) | counts → concentration: calibration curve, matrix/attenuation correction, background subtraction; label `[MODEL]`, version it |
| Model constant | `TDP=45`, `base=12`, `GPU=0.4` (`VM:119-124`) | calibration coefficients, detector efficiency curve, geometry factor; each with units and a version |
| Gate | `coh >= 0.618` (`VM:114,1694`) | validity gate on measured live time / count rate / gain drift; record gated time |
| Floor | `PHI_INV`, `no_zero()` (`CONST:35-41`) | a declared detection floor; never report a negative or zero concentration without saying "below floor" |
| Integration | `Σ watts·dt` (`VM:2195`) | `Σ counts` over measured live time; integer counts, not floats |
| Ledger | `stored = start + charged − used` (`CELL:169-181`) | integer counts and integer micro-joules; same identity |
| Frame | PPP/HDLC + FCS-16 (`CELL:67-98`) | spectrum block + result block, each with CRC-32/SHA-256 |
| Seal | canonical JSON + SHA-256 chain + ECDSA (`VM:1874-1946`) | same, plus `model_version` and `calibration_id` inside the signed body |
| Verify | `verify_signature` + monotonic totals (`VM:1967-2017`) | same, plus re-run the model from the raw counts and compare |

### 8.3 The honesty rules this codebase teaches (and where it slips)

**Rule 1 — A label is not optional.** Every model in the meter carries `method` and `labeled` (`VM:211-212`, and every collector at `VM:430,468,516,560,614,676,774`). Copy that: every derived number in the XRF output should carry `method` and `labeled`.

**Rule 2 — State the units.** The `GOAL_KWH` inconsistency (`VM:110-112`) shows what happens when a unit is implied. Put units in the field name (`energy_wh`, `stored_uj`, `dose_uSv`) and in the signed schema.

**Rule 3 — Do not let a constant masquerade as a measurement.** `field_coherence()` returns `PHI_INV` when no radio is present (`VM:281`), and `LiveArray` initializes `coherence = PHI_INV` (`VM:1034`). That is fine *because the docstring says so* (`VM:274-278`), but an XRF must not do the same with, say, "detector temperature" or "count rate". If the sensor is absent, return `[HONEST] unavailable` like `VM:544-546,589,652,742,799` — do not return a default that looks measured.

**Rule 4 — The signature proves integrity, not truth.** `_seal()` will happily sign a proof whose `energy_wh` came from `12 + 45·util·1.4` (`VM:202,1889`). The chain will verify. The `LAMBDA_VACUUM = 1.0  # [MODEL]` case is the clean demonstration: a reach computed from a 1 m decay length is signed and verifiable, and is still a model. For the XRF, **bind the model version and calibration ID into the signed proof**. Otherwise the signature attests only to arithmetic.

**Rule 5 — Separate "verified" from "proposed".** `SIM4:123-129` is the model to copy: `[VERIFIED] math+data` for what was actually computed against real data, `[PROPOSED] as physics` for what is extrapolation. An XRF report should have exactly these two sections.

**Rule 6 — Measure the real thing where you can.** The battery collector is the corpus's own best example (`VM:780-782,831`): a direct electrical reading, labelled `[MEASURED]`, with the one estimated part (pack capacity) called out. For the XRF, if a real detector exists, read it; if a real reference sample exists, measure it; only model what you truly cannot measure.

### 8.4 The one thing not to copy

The meter's gate threshold (`VM:114`) and the antenna's model constant (`ANT:55`) show the two failure modes to avoid:

1. **A threshold that is almost exactly the floor.** `C_CRIT = 0.618` vs `PHI_INV = 0.6180339887` leaves a 3.4 × 10⁻⁵ margin. Any rounding closes the gate. For the XRF, keep a real margin between the operating point and the trip point, and test it.
2. **A model constant that silently changes the conclusion.** `LAMBDA_VACUUM = 1.0` makes the coherence law a constant beyond 0.78 m; `SP:42` uses `φ·10⁹`. Both are labelled, but only one is physically scaled to the problem. For the XRF, every model constant must have a stated derivation and a sensitivity check.

### 8.5 Minimal XRF proof schema (recommended, following `_seal`)

```
{
  "seq":            int,
  "t":              wall seconds,
  "ft":             field time,
  "beat":           int,
  "instrument":     "xrf:<id>",
  "acquisition": {
      "live_time_s":    measured,
      "real_time_s":    measured,
      "counts":         [int, ...],        # raw, per channel
      "channels_keV":   [...],
      "detector_temp_c": measured | null,
      "tube_kv":        measured | null,
      "tube_ua":        measured | null
  },
  "model": {
      "name":        "counts_to_concentration",
      "version":     "x.y.z",              # <-- the gap in the corpus
      "calibration_id": "...",             # <-- the gap in the corpus
      "label":       "[MODEL]",
      "constants":   {...}
  },
  "result": {
      "elements":    {El: {"ppm": ..., "sigma": ..., "floor": ...}},
      "gate":        measured validity value,
      "gated":       bool
  },
  "prev_hash":   sha256(canonical(previous body)),
  "merkle_root": ...,
  "attestation": {"alg": "ES256", "units": "ppm", "one_claim": true, "gapless": true},
  "hash":        sha256(canonical(body minus hash/signature/public_key)),
  "signature":   ECDSA-P256(SHA256(canonical(body))),
  "public_key":  compressed P-256
}
```

This is the `VM:1881-1939` schema with two additions — `model.version` and `model.calibration_id` — that make the signature attest to *which model produced the number*, not merely that *a number was signed*.

---

## 9. BOTTOM LINE

1. **The pattern is real and it is disciplined.** Three layers — real proxy, labelled model, exact verifiable accounting — appear in all three instruments. The labels (`[EST]`, `[MODEL]`, `[HONEST]`, `[MEASURED]`, `[GATED]`) are the mechanism that keeps the layers from impersonating each other.
2. **`LAMBDA_VACUUM = 1.0  # [MODEL]` is confirmed verbatim** at `ANT:55` and `ANT_LTE:83`. It is 1.618 × 10⁹ times smaller than the propagation module's `φ·10⁹` (`SP:42`), and it makes `coherence_at(d)` a constant `0.6180339887` for every `d > 0.779 m`. The label is honest; the physics is a model.
3. **The meter's real measurements are timing and counters** (`perf_counter`, `psutil.cpu_times`, `net_io_counters`, `sensors_battery`, `sensors_temperatures`). Its watts are a model (`VM:202,212`). Its signatures, hashes, Merkle roots, and integer sums are exact and independently verifiable (`VM:1874-2017`, `KEYS:90-226`, `IMM:80-210`).
4. **The modem's protocol is exact** (PPP/HDLC, FCS-16, LCP, integer ledger), but its "1900 MHz LTE" is a name, not a radio; the only real RF in the stack is the ESP32's 2.4 GHz 802.11 TX (`WATCH:1091`).
5. **The gate is structural, not a live control.** The default gate input is the constant `PHI_INV` (`VM:281,1034`), the meter's threshold is `0.618` (`VM:114`), and the margin is 3.4 × 10⁻⁵. It holds by construction, not by measurement.
6. **For the XRF:** measure raw counts and real time; model the counts→concentration conversion with an explicit `[MODEL]` label, a version, and a calibration ID; gate on a *measured* validity quantity; integrate with measured live time; keep counts and energy integer-exact; frame with a real CRC; seal with canonical JSON + SHA-256 chain + ECDSA P-256; and put the model version inside the signed body. The signature will then attest to the model as well as the arithmetic — which is the only way a code-based instrument can be honest about what it is.

---

*Report compiled from direct reading of the files listed in the source map. All numeric values marked "computed" were evaluated from the cited formulas with `PHI = 1.6180339887498949`, `PHI_INV = 0.6180339887498949`, `C_CRIT = 0.563263` unless the cited line uses a different value. No file was modified.*
