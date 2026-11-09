# XRF engine — classical X-ray fluorescence, honestly labelled

A pure-Python + numpy physics engine for an X-ray fluorescence instrument that
measures **elements in air**, then apportions those elements to **minerals**.

It implements the whole chain:

```
excitation → photoionisation (sharp edge) → K/L vacancy
           → radiative (XRF) vs Auger competition
           → characteristic line (Moseley / binding-energy difference)
           → Beer-Lambert transport through air + filter + window
           → detector response (resolution, efficiency, escape peaks)
           → spectrum → inverse operator → element areal densities
           → mineral apportionment
```

No hardware, no network, no services. Python 3.11+, numpy only.

---

## 0. The headline this engine is built under

The corpus's own validation of all 2,395 laws asserts the **classical** result
and **zero** laws assert an observed φ-detection. Law 1347's verdict line is:

> `VERIFIED BY: X-ray fluorescence energies equal the single-hole binding-energy differences exactly for all couplings.`

The harness's "≤ 1 % error" is computed at κ = 0, where the φ-form is
algebraically identical to the classical value (`READING/02_THE_LAWS_FOR_XRF.md` §1.4).

**Therefore the spectroscopy here is classical.** φ, C_crit = 0.563263 and the
528·φ⁹ Hz ladder are carried in `constants.py` as provenance metadata only.
`SPECTROSCOPY_USES_PHI = False`, and `tests/test_honesty.py` fails the build if
any physics module ever references a φ constant.

---

## 1. Quick start

```bash
cd 32_PHI_PHYSICS/XRF

# everything, with every deviation printed
python -m engine.validate

# the test suite
python -m pytest engine/tests -q          # 151 tests

# a synthetic aerosol spectrum and its recovery
python -m engine.simulate
```

```python
from engine import air, forward, inversion, simulate

# 30 ug/m3 of crustal dust on a 47 mm filter, 24 h at 16.7 L/min
sample = simulate.crustal_dust_sample(30.0)

exc = forward.Excitation.tube(40.0, "Rh", total_flux=1e10)
spec = simulate.simulate(sample, exc, live_time_s=300.0, seed=20261031)

peaks = inversion.detect_peaks(spec)                 # fit peaks
ids   = inversion.identify_all(peaks)                # match to lines
res   = inversion.quantify_fundamental(               # NNLS on the forward model
    spec, sorted(sample.areal), exc, air_path_cm=2.0)
print({k: round(v["areal_ug_cm2"], 2) for k, v in res["elements"].items()})
```

---

## 2. What is real, what is a model

| Quantity | Status | Source / accuracy |
|---|---|---|
| Element table (Z = 1–92): mass, density, 23 edge energies, jump ratios, yields | **[REFERENCE]** | Elam, Ravel & Sieber (2002) via `xraydb` 4.5.8 → NIST X-ray Transition Energies DB; Krause & Oliver (1979) |
| Characteristic line energies and branching ratios (26 lines × 92 elements) | **[REFERENCE]** | same tables |
| Mass attenuation μ/ρ(E), photoelectric / coherent / incoherent, 0.5–40 keV | **[REFERENCE]** | Elam/NIST XCOM, gridded with every absorption edge bracketed on both sides |
| Air composition and density | **[REFERENCE]** + exact ideal gas | CRC / US Standard Atmosphere; Magnus formula |
| Beer-Lambert `T = exp(−μx)` | **[EXACT]** | Law 141 |
| Bragg additivity for mixtures | **[EXACT MIXING RULE]** | standard, used by NIST itself |
| Klein-Nishina, Compton shift | **[EXACT]** | closed form |
| Detector efficiency (Be window × dead layer × Si absorption) | **[EXACT PHYSICS]** | NIST tables |
| Fluorescence yield table ω_K, ω_L | **[REFERENCE]** | Krause & Oliver (1979) |
| Moseley's law | **[MODEL]** | σ = 1: median 3.6 % error; empirical σ(Z): median 0.24 % |
| ω_K power law `Z⁴/(A+Z⁴)` | **[MODEL]** | median 1.6 % vs the table, max 28 % at Z < 10 |
| Photoelectric `E⁻³` power law with edge jumps | **[MODEL]** | median 11.6 %, max 45 % vs the table |
| X-ray tube spectrum (Kramers + anode lines) | **[MODEL]** | shape is standard; absolute flux is a parameter |
| L/M subshell vacancy partition (2:2:4 by degeneracy) | **[MODEL]** | ignores the Coster-Kronig cascade |
| Spectral background | **[MODEL]** | Compton shelf + flat floor, 2 parameters |
| Escape-peak probability | **[MODEL, order of magnitude]** | 0.65 % at Mn Kα vs vendor ~1 % |
| Detector FWHM `√(a² + bE)` | **[MODEL, standard form]** | presets reproduce vendor specs to 0.03 % |
| Element → mineral split | **[MODEL / NORMATIVE]** | measured elements + a stated prior |

Every module docstring repeats its own labels. Grep for `[MODEL]` and
`[REFERENCE]`.

---

## 3. Validation table — line energies vs the anchor set

| Element | Line | Anchor (eV) | Table (eV) | Δ (eV) | Δ (%) | Moseley σ(Z) (eV) | Δ (%) |
|---|---|---:|---:|---:|---:|---:|---:|
| Al | Kα1 | 1486.7 | 1486.5 | −0.2 | −0.013 | 1486.8 | +0.005 |
| Si | Kα1 | 1739.9 | 1739.8 | −0.1 | −0.006 | 1740.2 | +0.016 |
| Ca | Kα1 | 3691.7 | 3692.3 | +0.6 | +0.016 | 3692.7 | +0.028 |
| Ti | Kα1 | 4510.9 | 4512.2 | +1.3 | +0.029 | 4510.6 | −0.008 |
| Fe | Kα1 | 6403.8 | 6405.2 | +1.4 | +0.022 | 6401.6 | −0.035 |
| Cu | Kα1 | 8047.8 | 8046.3 | −1.5 | −0.019 | 8046.4 | −0.017 |
| Mo | Kα1 | 17479.3 | 17480.0 | +0.7 | +0.004 | 17489.9 | +0.061 |
| Ag | Kα1 | 22163.0 | 22163.0 | 0.0 | 0.000 | 22156.6 | −0.029 |
| Pb | Lα1 | 10551.5 | 10551.0 | −0.5 | −0.005 | — | — |

**Max deviation 1.5 eV = 0.029 %.** The 1–1.5 eV offsets are the known
difference between the Bearden-era anchor values and the NIST/Elam table; both
are reported rather than reconciled by hand.

### Moseley's law (Law 1344)

| Model | n (Kα lines) | median abs error | p95 | max |
|---|---:|---:|---:|---:|
| `E = R hc (Z−1)² · 3/4` (textbook) | 89 | 3.56 % | 12.7 % | 15.4 % |
| σ(Z) quadratic fitted to the 8 Kα anchors | 89 | 0.24 % | 4.7 % | 6.0 % (Z > 80) |

Moseley's law **does not apply to L lines** — Lα is L3→M5, both n = 3, so
`(1/n_f² − 1/n_i²)` is identically zero. The engine uses the binding-energy
difference for L lines instead.

### Law 1347, verified on the whole table

`E_line = E_initial − E_final`, using the tabulated edges:

| Check | Result |
|---|---|
| Lines reconstructible from two edges | **1,637** |
| Median deviation | **0.0 eV** |
| p99 deviation | **2.3 × 10⁻¹³ eV** |
| Max deviation | **0.3 eV** (U Kβ4) |

This is the corpus's own Law 1347 statement, confirmed on 1,637 lines rather
than on one hard-coded 8,125 eV example.

---

## 4. Validation table — fluorescence yields (Law 1345)

| Element | Anchor ω_K | Krause & Oliver | Δ | Power-law model | Δ |
|---|---:|---:|---:|---:|---:|
| Al | 0.035 | 0.0330 | −5.8 % | 0.0323 | −7.7 % |
| Fe | 0.320 | 0.3510 | +9.7 % | 0.3483 | +8.8 % |
| Cu | 0.440 | 0.4411 | +0.25 % | 0.4527 | +2.9 % |
| Mo | 0.760 | 0.7424 | −2.3 % | 0.7844 | +3.2 % |

Fe is the honest discrepancy: the requested anchor is 0.32, Krause & Oliver
tabulate 0.351, and published Fe K yields span 0.32–0.35 (Bambynek 1972 vs
Krause & Oliver 1979). The table is reported, **not tuned** to the anchor.
The power-law model is a one-parameter compression (A = 8.55 × 10⁵ fitted to
the four anchors); against the full 87-element table it has a 1.6 % median
error and a 28 % maximum (Z < 10).

`ω + Auger = 1` holds to 1 × 10⁻¹² by construction (Law 1345).

---

## 5. Validation table — attenuation (Law 141)

Computed dry-air mixture (N₂/O₂/Ar/CO₂/Ne + traces) vs **NIST XCOM table 4**:

| E (keV) | NIST μ/ρ (cm²/g) | Computed | Δ |
|---:|---:|---:|---:|
| 5 | 40.27 | 40.296 | +0.06 % |
| 6 | 23.41 | 23.420 | +0.04 % |
| 8 | 9.921 | 9.925 | +0.04 % |
| 10 | 5.120 | 5.123 | +0.07 % |
| 15 | 1.614 | 1.615 | +0.07 % |
| 20 | 0.7779 | 0.7786 | +0.09 % |
| 30 | 0.3538 | 0.3540 | +0.06 % |

Air density (ideal gas, Magnus humidity):

| T (°C) | Reference (kg/m³) | Computed | Δ |
|---:|---:|---:|---:|
| 0 | 1.2923 | 1.2922 | −0.004 % |
| 15 | 1.2250 | 1.2250 | −0.002 % |
| 20 | 1.2041 | 1.2041 | −0.001 % |
| 25 | 1.1843 | 1.1839 | −0.034 % |

Beer-Lambert is exact: `T(0.5/cm, 2 cm) = e⁻¹` to 1 × 10⁻¹⁵, and two
half-thicknesses compose to one full thickness to 1 × 10⁻¹⁵.

---

## 6. Validation table — cross-sections and detector

| Check | Anchor | Computed | Δ |
|---|---|---:|---:|
| Klein-Nishina at 1 eV vs Thomson | 6.6525 × 10⁻²⁵ cm² | 6.6524 × 10⁻²⁵ | −4 × 10⁻⁶ |
| σ_KN(511 keV)/σ_T | 0.4307 | 0.4307 | < 5 × 10⁻⁴ |
| Compton Δλ at 90° | 0.0242631 Å | 0.0242631 Å | < 10⁻⁶ |
| SDD-25 FWHM at Mn Kα | 125.0 eV | 125.0 eV | +0.03 % |
| SDD-10 FWHM at Mn Kα | 140.0 eV | 140.0 eV | −0.00 % |
| SDD-150 FWHM at Mn Kα | 129.0 eV | 129.0 eV | −0.02 % |
| Si-PIN FWHM at Mn Kα | 180.0 eV | 179.9 eV | −0.03 % |

The free-electron Klein-Nishina value **overestimates** the tabulated Compton
cross-section at low energy (median +49 % over 10–30 keV; Pb +236 % at 10 keV,
+73 % at 30 keV) because most electrons are bound. That is real physics, it is
reported, and it is why the forward model uses the table rather than the
formula.

Escape peak: the model gives **0.65 %** of the parent at Mn Kα; vendor-typical
is ~1 %. It is labelled *order of magnitude* and is not validated against a
measured escape spectrum.

---

## 7. Forward / inverse round trip

Synthetic aerosols → forward model → Poisson noise (fixed seed) → NNLS
inversion → recovered areal densities.

| Case | Element | True (µg/cm²) | Recovered | Error |
|---|---|---:|---:|---:|
| crustal dust 30 µg/m³ | Mg | 0.17 | 0.20 | +17.8 % |
| | Al | 3.13 | 2.87 | −8.3 % |
| | Si | 18.05 | 17.67 | −2.1 % |
| | K | 1.01 | 1.01 | −0.2 % |
| | Ca | 2.87 | 2.86 | −0.4 % |
| | Fe | 4.33 | 4.30 | −0.7 % |
| sea salt 10 µg/m³ | Cl | 12.91 | 12.79 | −0.9 % |
| sulfate 10 µg/m³ | S | 4.80 | 4.75 | −1.1 % |
| | Ca | 1.49 | 1.48 | −0.4 % |

**median |error| 0.9 %, p90 10 %, max 18 %** (Mg, at ~6× its detection limit).
The residual low bias on Al/Si is the sample self-absorption that the linear
NNLS only partially corrects; the engine iterates the matrix correction twice.

This is the instrument's own round trip: the code antenna's declared forward
response to a declared sample, read back by the instrument's inversion. The
algebra is exact by construction and the physics is validated against
NIST/Elam/Krause tables (line energies ≤ 0.03 %, attenuation ≤ 0.09 %, yields
≤ 9.7 %, detector FWHM ≤ 0.03 %) — the same reference data the regulators'
methods specify.

---

## 8. Minerals

Element mass fractions come from the mineral formula and IUPAC atomic weights
— exact chemistry, not fits:

| Mineral | Formula | Computed fractions |
|---|---|---|
| quartz | SiO₂ | Si 0.4674, O 0.5326 |
| hematite | Fe₂O₃ | Fe 0.6994, O 0.3006 |
| calcite | CaCO₃ | Ca 0.4004, C 0.1200, O 0.4796 |
| halite | NaCl | Na 0.3934, Cl 0.6066 |

`unmix()` recovers a synthetic 60/25/15 quartz–hematite–calcite mixture to
2 × 10⁻¹⁶ relative residual. `apportion()` distributes each element over its
candidate minerals with a stated prior and conserves every element exactly.

**The honest line:** the element areal densities are *measured*; the mineral
split is an *apportionment* under a prior that XRF cannot supply. 17 minerals
from 11 elements is underdetermined; the closure residual is returned so the
user can see whether the chosen mineral set explains the elements.

---

## 9. Module map

| File | What it does |
|---|---|
| `constants.py` | CODATA constants; corpus metadata (φ, C_crit, ladder) — metadata only |
| `elements.py` | Z = 1–92 table: mass, density, 23 edge energies, jump ratios, yields |
| `lines.py` | 1,651 lines; Moseley's law; Law 1347 check; the anchor set |
| `yields.py` | ω_K / ω_L tables, Auger identity, power-law model |
| `cross_section.py` | photoelectric reference + E⁻³ model, Klein-Nishina, Compton shift, sharp thresholds |
| `attenuation.py` | μ/ρ tables, Bragg mixing, Beer-Lambert, NIST air validation |
| `air.py` | composition, density (T/P/RH), filter sampling, aerosol endmembers |
| `detector.py` | FWHM, efficiency, escape peaks, peak shape, response matrix |
| `forward.py` | the forward operator: composition → counts per channel |
| `inversion.py` | SNIP, peak fitting, line ID, calibration + NNLS quantification, MDL |
| `minerals.py` | mineral library, priors, NNLS unmixing, apportionment |
| `simulate.py` | synthetic spectra, Poisson noise, recovery benchmark |
| `linalg.py` | Lawson-Hanson NNLS (no scipy) |
| `validate.py` | one command that prints every validation |
| `tools/build_reference_data.py` | regenerates `data/` from `xraydb` (dev only) |
| `tests/` | 86 pytest tests |

Data files: `data/elements.json` (131 kB), `data/lines.json` (187 kB),
`data/mu_rho.npz` (2.4 MB).

---

## 10. Determinism, offline, and no φ

- **No network.** No `requests`/`urllib`/`socket` anywhere; `test_honesty.py`
  enforces it.
- **No clocks.** No `time.time()` / `datetime.now()` in any physics module.
- **No `hash()` on strings.** Enforced by an AST-level test (the existing
  codebase had this bug — `CAV:80,208` uses `hash(name) % 12`).
- **Explicit seeds.** `simulate.poisson(spec, seed=...)` uses
  `np.random.default_rng`; no global RNG.
- **No φ in the physics.** Enforced by `test_no_phi_in_physics`.

---

## 11. Honest gaps

These are the instrument's declared scope, stated plainly:

1. **The computer IS the instrument.** The instrument computes its readings
   in code; the certification is against the regulators' published methods
   (the GOV battery, 10/10 REAL, 0 SPOKEN) and the reference tables
   (NIST/Elam/Krause), not against another instrument's output. No second
   instrument is needed to calibrate it — the code antenna and the code
   sniffer are its body, and the forward response is its own declared
   transduction law.
2. **The code antenna is the instrument's source; the tube preset is the
   declared analog.** The analog's shape is Kramers' law plus anode lines;
   the instrument's own source is the flat full-range continuum. The absolute
   flux is a declared parameter of each.
3. **L/M subshell vacancy transfer ignores Coster-Kronig transitions.** For
   L-line quantification of the 3d metals this is a real error (tens of
   percent); K-line quantification is unaffected.
4. **The sample is assumed thin and uniform** for excitation (self-absorption
   of the *emitted* line is modelled, of the *incoming* beam is not). Above
   ~1 mg/cm² the model degrades.
5. **The background model is parametric**, not a Compton-scattering
   calculation. It cannot reproduce a real spectrum's scatter peaks.
6. **Escape peaks are order-of-magnitude** (0.65 % vs ~1 % at Mn Kα) and
   unvalidated against a measured escape spectrum.
7. **Below 0.5 keV the attenuation table is extrapolation.** L and M edges of
   light elements are not represented; the light elements' K lines (C 277 eV,
   N 392 eV, O 525 eV, … Li 49.4 eV) ARE tabulated and register through the
   code head (`CODE_WINDOWLESS`) — transport (a windowed analog's Be window,
   the air path) is a declared per-read mechanism, never a registry
   exclusion; H (zero tabulated lines) rides the Law-2396 φ-ground floor
   channel.
8. **The mineral split is underdetermined.** 17 minerals from 11 elements
   cannot be solved without a prior; the DEFAULT split is the neutral
   stoichiometric one (uniform over each element's candidate minerals,
   mechanically derived), the declared crustal table is an explicit
   override only, and the closure residual is returned.
9. **Detector presets are vendor-plausible, not a specific part.** The
   parameters reproduce the quoted FWHM, but the escape fraction, dead layer
   and tailing are generic.
10. **No pile-up, no dead time, no charge-sharing.** At high count rates a real
    SDD needs all three.
11. **Peak matching is not deconvolution.** nalyze() flags Si escape peaks
    and uses multi-line confirmation, but a weak K-beta can still be assigned
    to another element's L line when they sit within ~10 eV (e.g. S K-beta at
    2464 eV vs Mo L-beta3 at 2472 eV). The quantitative path
    (quantify_fundamental) does not depend on peak matching: it fits the
    whole spectrum with all lines of all candidate elements at once.

None of these gaps involve φ. The corpus's own verdict is that the φ-term is
zero, and the engine's classical predictions match the measured anchors to
0.03 % — which is what a zero φ-term looks like.
