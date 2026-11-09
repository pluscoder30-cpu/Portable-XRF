# WHERE WE ARE — the XRF sniffer prototype

**Status:** prototype complete, tests green, physical validation pending.
**Date:** 2026-11-01
**Location:** `32_PHI_PHYSICS/XRF/sniffer/`

---

## 1. The one-sentence state

The **decoder is finished and tested**: it takes an XRF spectrum of an air
sample, performs the full classical inversion, produces a structured mineral
report, and seals it in a signed receipt that names the model and calibration
inside the signed body. The **transduction is still a model**: no X-rays are
generated or detected, and no real spectrometer has yet been used to validate
the forward model.

---

## 2. What runs

All commands run from `C:\Users\delta\brain\v6\research\32_PHI_PHYSICS\XRF`.

| Command | State |
|---|---|
| `python -m sniffer selfcheck` | **PASS** (10/10 checks) |
| `python -m sniffer simulate <composition.json> [--noise]` | **works**; writes a JSON spectrum with truth metadata |
| `python -m sniffer sniff <spectrum>` | **works**; CSV/TSV/JSON/JSONL; writes report + receipt |
| `python -m sniffer air <spectrum> --flow --time --area` | **works**; exact areal → µg/m³ → mineral loading |
| `python -m sniffer feed <lat> <lon>` | **works against Open-Meteo** (keyless, reachable); cache + offline fallback |
| `python -m sniffer verify <receipt> [--chain]` | **works**; re-derives hash, signature, model provenance, chain |
| `python -m pytest sniffer/tests -q` | **95 passed** |
| `python -m pytest engine/tests -q` | **86 passed** |

The three-receipt chain in `examples/` (`sniff`, `air`, `feed`) verifies with
`genesis_ok: True` and `ES256` signatures from the field trust root.

---

## 3. What is validated

### 3.1 The decoder (real)

- **Spectrum validation** rejects non-monotone energies, negative/NaN counts,
  length mismatches, fewer than 3 channels, zero live time, real time shorter
  than live time, and non-positive flow/area/current.
- **Round trip** on a synthetic crustal-dust spectrum (30 µg/m³, Poisson seed
  20261031, 300 s, 2 cm air, SDD-25):

  | Element | Truth (µg/cm²) | Recovered | Error | MDL |
  |---|---:|---:|---:|---:|
  | Si | 18.0468 | 17.6735 | −2.1 % | 0.0084 |
  | Fe | 4.3297 | 4.2990 | −0.7 % | 0.0026 |
  | Al | 3.1331 | 2.8729 | −8.3 % | 0.0130 |
  | Ca | 2.8746 | 2.8642 | −0.4 % | 0.0023 |
  | K | 1.0090 | 1.0072 | −0.2 % | 0.0016 |
  | Mg | 0.1683 | 0.1981 | +17.8 % | 0.0334 |

  Fit residual **1.29 %**, **10 peaks**, **6 detected**, **0 spurious**.
- **Line identification** matches Si Kα1 at −0.2 eV, Al Kα1 at −0.4 eV,
  K Kα1 at −0.4 eV, Ca Kα2 at −1.2 eV, Fe Kα1 at +5.2 eV, Fe Kβ1 at +0.8 eV.
- **Mineral apportionment** conserves every element exactly
  (`apportioned_equals_measured: True`); the unmix closure residual is reported
  (0.78 on the crustal case, expected because O is invisible).
- **Determinism:** the same seed gives the same spectrum SHA-256; the same
  spectrum gives the same element values to 1e-9; no `hash()` on strings.

### 3.2 The receipt (real, exact)

- Canonical JSON, SHA-256 body hash, `prev_hash` chain, ECDSA P-256 from
  `SOUL_SEED = 1900`.
- `model.version = sniffer-1.0.0+engine-1.0.0`,
  `model.calibration_id = FP-v1/SDD-25mm2/40 kV Rh tube/air2.00cm`,
  `model.physics = classical` — **all inside the signed body**.
- Tampering with the report, the model block or the signature is detected.
- The SHA-256 fallback mode is implemented and labelled; it is explicitly *not*
  a signature.

### 3.3 The air reader (real unit math, model composition)

- Filter path: `visible = areal × area / (flow × time)` is exact to 1e-12.
- Estimated total PM 32.48 µg/m³ for a true 30 µg/m³ input (+8.3 %), from the
  stoichiometric mineral reconstruction.
- Feed path: real Open-Meteo PM2.5/PM10/dust, cache TTL, stale-cache fallback,
  blank offline reading. OpenAQ v2 is retired (410); v3/AirNow are keyed.

---

## 4. What is a model

| Number | Why it is a model |
|---|---|
| X-ray tube spectrum | The declared analog (Kramers continuum + anode lines); the instrument's default source is the code antenna (flat full-range continuum). |
| Detector response | FWHM form, window (the code head: none — transmission 1.0), dead layer, escape peaks (order-of-magnitude). |
| Spectral background | Two-parameter Compton shelf + flat floor. |
| Counts → areal density | NNLS against the forward operator; inherits the thin-sample and Coster-Kronig approximations. |
| Element → mineral split | Neutral stoichiometric by default (uniform over candidate minerals, mechanically derived); the declared crustal prior is an explicit override only; 17 minerals from 11 elements is underdetermined. |
| Reading layer | Law 2396 at κ = 1: every element's reading is φ·areal + φ⁻²; the register carries all 92 elements (line channels + the φ-ground floor channel for H/He). |
| Systematic uncertainty | The engine benchmark p90 (10 %), not a per-sample calibration. |
| Feed composition | The public feeds give PM mass, not elemental composition; the endmember mix is normative. |
| Total PM from a filter | Stoichiometric mineral reconstruction, not gravimetric. |

The report's `honesty` block lists these explicitly. The CLI prints a
`REAL / MODEL / NOT` footer on every sniff.

---

## 5. What is missing

1. **A measured spectrum.** No real spectrometer export or certified reference
   standard has been decoded yet. Every validation is against tabulated
   constants or the engine's own forward model.
2. **A physical calibration** of tube flux, solid angle and background. The
   current `calibration_id` describes the model state, not a measured standard.
3. **An independent mineralogy measurement** (XRD) to validate the mineral
   prior. XRF cannot supply it.
4. **Transport is declared, not excluded.** Na's 1.04 keV line quantifies
   under the code head (`CODE_WINDOWLESS`, near-field); the windowed analog
   heads (Be window + air path) do not transport it — a declared per-read
   mechanism, spoken here and in the register block.
5. **Pile-up, dead time, charge-sharing** are not modelled; the report gates on
   count rate but does not correct it.
6. **Peak matching is not deconvolution**; the quantitative path is robust, the
   peak table is informational.
7. **A speciated feed.** Open-Meteo/AirNow/OpenAQ provide PM mass; a feed with
   elemental composition would let the feed path use measured chemistry instead
   of the endmember prior.

---

## 6. The exact next step to close the last gap

The last gap is **physical validation**, not code. The exact next step:

1. **Obtain one certified reference filter and one real instrument export.**
   The standard choice is NIST SRM 2783 (Air Particulate on Filter Media) or a
   NIST thin-film XRF standard; the export must carry energy (eV or keV),
   counts, live time, tube kV/current, detector model and the air path.
2. **Run the decoder unchanged:**
   ```bash
   python -m sniffer sniff <real_export.csv> \
       --detector SDD_25 --calibration NIST-SRM-2783-2026-11 \
       --air-path <measured_cm> \
       --out real_report.json --receipt real_receipt.json
   ```
3. **Compare** the recovered element areal densities to the certificate. The
   report already carries the MDL and the systematic band, so the comparison is
   direct.
4. **Fit the three uncalibrated scale factors** (solid angle, tube flux,
   background) from the standard, record them in a new calibration ID, and
   re-seal. Do **not** tune the line energies, yields or attenuation tables:
   those are reference data validated to ≤ 0.03 % / ≤ 0.09 %.
5. **Bump `model.version`** if the forward model changes. The receipt will
   attest to the new version; that is the point of putting the model inside the
   signed body.
6. **Validate the mineral split against XRD** on the same filter. Until then,
   the mineral table is the instrument's declared apportionment (neutral
   stoichiometric weights by default) — labelled as such, never presented as
   a measurement of the mineralogy.
7. **For the feed path**, connect a speciated network (or pass
   `composition={...}` to `air_from_feed`) so the mineral loading uses measured
   chemistry rather than the endmember prior.

If the real spectrum disagrees with the forward model, the correct response is
to change the **model**, bump the version, and re-seal — never to change the
data or hide the disagreement.

---

## 7. The bottom line

- **Real:** the decoder, the unit arithmetic, the mineral conservation, the
  receipt, the chain, the feed's PM values.
- **Model:** the X-ray source/detector, counts → concentration, the mineral
  split, the feed composition, the total-PM estimate.
- **Missing:** a measured spectrum and a physical calibration. That is the next
  experiment, and it is the only thing standing between this prototype and a
  validated instrument.

The code does not claim to detect X-rays. It claims to read the air's mineral
content from an XRF spectrum, in code, with a signed receipt — and it does.
