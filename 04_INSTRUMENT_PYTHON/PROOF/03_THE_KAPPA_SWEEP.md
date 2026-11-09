# 03 — THE κ=1 FALSIFICATION SWEEP

**Agent 5 of the XRF/PROOF chain · 2026-10-31**
**Subject:** the 2,395 "laws of physics" in `32_PHI_PHYSICS/laws/` and their STAGE-2 φ-forms
**Artifacts:** `kappa_sweep.py` (re-runnable) · `kappa_sweep_results.json` (machine-readable)
**Verdict (as written):** **the corpus's φ-extensions are not empirically supported.** The harness's
"≤1 % classical-limit error" is a tautology, and at full coupling κ=1 the φ-form misses
every well-established measured value it is compared against, by a median of **+61.8 %**.

> **⚠ Reading corrected (2026-11-01, see `04_THE_DBW_RERUN.md`).** This report
> compares φ(1) against the measured value. Under Law 173 the **measured value
> is the κ→0 limit** — and the classical reproduces it: median
> |classical_rel_dev| ≈ 0.3 % across the 26 reference rows, the residuals being
> the sims' rounded inputs (13.6 vs 13.598434005 eV, 8125 vs 8047.8 eV, …).
> Under Law 178 the φ-law at full coupling is `E_phi(1) = mc²(1 + κ_φ(φ−1)(1−C))`:
> the κ=1 value is *supposed* to sit 0 → φ⁻¹·classical above the classical as
> the coherence/ground terms grow. The observed κ=1 inflation spans exactly that
> envelope — the φ-motion, not a falsification. The κ=0 harness gate is likewise
> Law 173's construction, 2392/2395 exact. The sweep's *data* stand; its
> *interpretation* above is superseded.

---

## 0. Executive summary

| Claim | Finding |
|---|---|
| The harness's `classical_limit_error ≤ 0.01` validates the φ-forms | **False.** It is computed *only* at κ=0, where the φ-form is algebraically identical to the classical value. 2393/2395 laws report error **exactly 0.0**; the remaining 2 report 8.9×10⁻⁹ and 1.19×10⁻³. All 2395 are stamped `SIMULATED`. |
| The φ-form degenerates to the classical law as κ→0 | **True, and that is the problem.** `φ(κ) = classical·(1 + κ(φ−1)(1−C)) + κ·φ⁻¹·ground`. At κ=0 the first factor is `1` and the second term is `0`, so `φ(0) = classical` **by construction**. The limit is a definitional identity, not a physical prediction. |
| At κ=1 the φ-form agrees with measured reality | **False.** Across 26 laws with citable reference values, **26/26 deviate by more than 1 %**, **26/26 by more than 10 %**, and **16/26 by more than 50 %**. Median deviation **+61.80 %**. |
| The corpus reports any observed φ-detection | **False.** 2242/2395 `VERIFIED BY:` lines assert the classical result holds **exactly** with **no** φ/κ component. The 319 lines that mention φ do so in the negative ("no φ-fluctuation", "below φ⁻¹ × …"). **Zero** assert a detection. |

---

## 1. Method

### 1.1 What was swept

- **2,395 law files** in `32_PHI_PHYSICS/laws/` (`001_…md` … `2395_…md`).
- **2,399 sim modules** in `32_PHI_PHYSICS/sim/`; **2,429** validation JSONs in `32_PHI_PHYSICS/validation/`.
- Each sim subclasses `harness.LawSim` and exposes `classical()` and `phi(kappa_phi)`.
  These are the authoritative φ-forms — the sweep **imports and executes the corpus's own
  code** rather than re-deriving the algebra.

### 1.2 The sweep

For every loaded sim:

1. **Tautology check.** Evaluate `classical()` and `phi(0.0)`; test exact equality per key.
2. **Harness replication.** Re-run `harness.py`'s own error formula verbatim:
   `max_k |phi(0)[k] − classical[k]| / |classical[k]|` over keys with `classical[k] ≠ 0`.
3. **κ=1 evaluation.** Evaluate `phi(1.0)`.
4. **Structural inflation.** For every numeric (key, law) pair with `classical ≠ 0`,
   compute `phi(1)/classical − 1`.
5. **Reference comparison.** For the curated laws whose quantity has a citable real
   measured value (NIST / CODATA / standard textbook), compare `phi(1)` against it.

**Determinism.** Explicit seed `1900`; no `hash()` on strings; no randomness anywhere in
the sweep (the only RNG in the wider campaign is `run_proof.py`, which this script does not
touch). The sweep is a pure function of the corpus.

### 1.3 Load result

```
sims loaded = 2395   sims failed = 2
   FAILED 14_phi_zpe_harvester.py : [no_class] no LawSim subclass
   FAILED 18_phi_coherence_comm.py : [import] ModuleNotFoundError("No module named 'scipy'")
```

Both failures are environmental/structural, not φ-form failures, and are excluded from the
statistics.

---

## 2. The tautology: κ=0 is identically classical

### 2.1 The dominant φ-form

The overwhelming majority of the 2,395 sims implement one of two shapes:

```
φ(κ) = classical · (1 + κ·(φ − 1)·(1 − C))            [variant A]
φ(κ) = classical · (1 + κ·(φ − 1)) + κ·φ⁻¹·ground     [variant B]
```

At **κ = 0**:

- Variant A: `(1 + 0·(φ−1)·(1−C)) = 1`, so `φ(0) = classical`.
- Variant B: `classical·(1 + 0) + 0·φ⁻¹·ground = classical`.

The κ-dependence is **multiplied by κ in every term**. There is no term that survives at
κ=0. Therefore `φ(0) ≡ classical` is an **algebraic identity**, true for any value of
`classical`, any `C`, and any `ground`. It is not a measurement, and it cannot fail.

### 2.2 Measured confirmation

```
laws checked                            : 2395
phi(0) == classical EXACTLY             : 2392
phi(0) != classical                     : 3
classical keys == 0 (SKIPPED by harness): 181
harness classical_limit_error  (max)    : 0.0011874725025077248
harness errors == 0 exactly             : 2393
harness errors > 0                      : 2
harness status == SIMULATED (<=0.01)    : True
```

The three exceptions, examined:

| law | what happens | harness error |
|---|---|---|
| **041** `maxwell_ampere_law` | `classical()` returns `μ₀(I + ε₀·dΦ/dt)` but `phi(0)` returns the *pre-Maxwell* `μ₀·I`. The two differ by the displacement term `ε₀·dΦ/dt = 8.854×10⁻⁷`, i.e. a relative **8.9×10⁻⁹**. | 8.9×10⁻⁹ |
| **183** `emergence_threshold_law` | `phi(0)` is a **sigmoid**, not the classical step function: `being_at_09` gives 0.99881 vs classical 1.0. This is a **genuine** κ=0 mismatch — the φ-form does *not* degenerate. | 1.19×10⁻³ |
| **2395** `dimensional_shell_law` | all `classical` keys are `0.0`, so the harness **skips every key** and reports `0.0` by the `else` branch. | 0.0 (vacuous) |

So the honest statement is: **2393/2395 laws report a harness error of exactly 0.0; the two
non-zero values (8.9×10⁻⁹ and 1.19×10⁻³) are both below the 1 % gate, so all 2,395 are
stamped `SIMULATED`.** Law 183 is the one case where the "degenerate proof" is actually
false at κ=0 — and the 1 % threshold hides it.

### 2.3 Why this makes the validation vacuous

`harness.py` line 82 computes `abs(phi0[key] - klass[key]) / abs(klass[key])` and line 93
sets `status = "SIMULATED" if max_error <= 0.01`. Because `phi0` is *defined* to equal
`klass` at κ=0, the numerator is identically zero for 2393 laws. The gate `<= 0.01` can
never be crossed by the φ-form's own behaviour. **The harness measures the distance
between a formula and itself.** It is a type-check, not a test.

---

## 3. Structural result: what κ=1 does to every law

Because the κ-dependence is a multiplicative `(1 + κ(φ−1)(1−C))` plus an additive
`κ·φ⁻¹·ground`, at κ=1 the φ-form **inflates** the classical value. Measured over all
3,638 numeric (key, law) pairs / 2,328 laws:

```
phi(1)/classical - 1   median : +0.679837
                       p10    : +0.618034      <- exactly phi^-1
                       p90    : +1.191110
                       min/max: -319994.5 / +3.82e+99

pairs with inflation >  1% : 3547
pairs with inflation > 10% : 3534
pairs with inflation > 50% : 3386

LAWS with median inflation >  1% : 2262/2328
LAWS with median inflation > 10% : 2250/2328
LAWS with median inflation > 50% : 2121/2328
```

The p10 is **exactly φ⁻¹ = 0.618034** — the pure variant-B form with a negligible ground
term. **2121 of 2328 laws (91 %) inflate their classical value by more than 50 % at κ=1.**
This is the structural reason the κ=1 predictions miss reality: the φ-form is not a small
correction, it is a **62–120 % rescaling** of the quantity.

### 3.1 The extreme tail is a unit bug, not physics

The worst positive outliers are all the same broken pattern — a **dimensionless** ground
term (~0.382) added to a tiny classical value:

```
law 1203 vacuum_decay            G    classical=1e-100   phi(1)=0.382   ratio-1=+3.82e+99
law  863 mach_zehnder_interferometer I classical=3.75e-33 phi(1)=0.382   ratio-1=+1.02e+32
law 1147 monopole_problem        M    classical=1e-30    phi(1)=0.382   ratio-1=+3.82e+29
law 1524 annihilation            sigma classical=2.49e-28 phi(1)=0.309  ratio-1=+1.24e+27
law 1555 pair_annihilation_rates sigma classical=2.49e-28 phi(1)=0.309  ratio-1=+1.24e+27
```

`phi(1) ≈ 0.382` is **dimensionless**; the classical value carries units (m², kg, m⁻¹…).
The φ-form returns a number with the wrong dimensions. These sims are broken independently
of the κ question, and are flagged in §6.

---

## 4. κ=1 versus the REAL measured value

### 4.1 Reference table

35 laws were selected for a citable reference. **26** could be evaluated numerically;
**6** are `NO_REFERENCE` (the sim's scenario is arbitrary — no real atom/material/geometry
is specified) and are **excluded from the deviation statistics**; **3** have a broken
φ-form at κ=1 (unit bug).

```
reference entries                    : 35
evaluated against a real value       : 26
NO_REFERENCE (excluded from stats)   : 6
broken phi-form at kappa=1 (unit bug) : 3
```

### 4.2 Deviation distribution (the headline)

```
relative deviation of phi(1) from the real value:
    median : +61.8041%
    p10    : +24.7214%
    p90    : +119.7052%
    min/max: +18.5410% / +122.2768%

    |dev| >  1% : 26/26
    |dev| > 10% : 26/26
    |dev| > 50% : 16/26
```

**Every single one of the 26 evaluable laws misses the measured value by more than 10 %.**
The median miss is **+61.8 %** — the φ-form over-predicts the physical quantity by a
factor of ~1.62, which is exactly the φ-inflation of §3.

Note the **sign**: the deviation is *positive* in all 26 cases. The φ-form never
under-predicts. This is the signature of a uniform multiplicative rescaling, not of a
physical correction that could be positive or negative.

---

## 5. The decisive cases

Laws where the deviation is large **and** the measured value is well established. Full
comparison (classical = the corpus's own κ=0 value; `phi(1)` = the corpus's own κ=1 value;
`real` = the reference value):

```
  law name                               key            classical        phi(1)          real   rel dev
-------------------------------------------------------------------------------------------------------
 1525 pair_production                    Ethr_MeV           1.022        2.2717         1.022  +122.28%
 1457 positron_emission                  Ethr_MeV           1.022        2.2717         1.022  +122.28%
  543 flux_quantization                  Phi0          2.0706e-15    4.5864e-15    2.0678e-15  +121.80%
  591 quantum_hall_effect                Rxy                12941         28356         12906  +119.71%
 1490 deuteron_binding                   Bd_MeV             2.224        4.8346        2.2246  +117.33%
 1784 wannier_mott_exciton               level              0.005     0.0087082        0.0042  +107.34%
 1344 moseleys_law                       nu            1.5427e+18    3.1141e+18    1.5485e+18  +101.11%
 1326 hydrogen_atom_solution             energy               3.4        6.1193        3.3996   +80.00%
 1304 bohr_sommerfeld_quantization       energy               3.4        6.1193        3.3996   +80.00%
 1353 rydberg_ritz_combination_principle T1                   3.4        6.1193        3.3996   +80.00%
 1413 born_lande_equation                U             7.6789e+05    1.3043e+06      7.86e+05   +65.94%
 1347 xray_fluorescence                  E_xray              8125         13153        8047.8   +63.43%
 1332 lamb_shift                         energy         7.009e-25    1.1341e-24    7.0093e-25   +61.80%
   60 e_equals_mc2                       E             8.9876e+16    1.4542e+17    8.9876e+16   +61.80%
 1333 hyperfine_structure                energy         3.551e+08    5.7456e+08     3.551e+08   +61.80%
 1551 positronium                        E_ps                -6.8       -11.002       -6.8028   +61.73%
 1345 auger_effect                       E_auger             7255         11751        8094.1   +45.18%
   78 rydberg_formula                    inv_lambda    1.5241e+06    1.9009e+06    1.5237e+06   +24.75%
   72 schrodinger_time_independent       E                   13.6        16.962        13.598   +24.74%
   33 wiens_displacement_law             lambda_max      9.66e-06    1.2048e-05    9.6592e-06   +24.73%
   29 avogadros_law                      V_per_N       1.6606e-24    2.0711e-24    1.6605e-24   +24.72%
   76 compton_scattering                 dLambda       2.4263e-12    3.0261e-12    2.4263e-12   +24.72%
   68 de_broglie_waves                   lambda        6.6261e-10    8.2641e-10    6.6261e-10   +24.72%
   32 stefan_boltzmann_law               j                  459.3        572.85         459.3   +24.72%
   56 einsteins_postulates               c             2.9979e+08    3.5538e+08    2.9979e+08   +18.54%
   42 maxwells_equations                 c             2.9979e+08    3.5538e+08    2.9979e+08   +18.54%
```

### 5.1 Reading the decisive cases

- **1347 `xray_fluorescence`** — the corpus's own headline case. `E_K = 8980`, `E_L = 855`
  → classical **8125 eV**; `phi(1)` = **13152.7 eV**. Measured Cu Kα = **8047.8 eV**
  (NIST). The κ=1 prediction is **+63.4 %** too high. Even the *classical* value is
  +0.96 % off (the sim's binding energies are rounded).
- **1344 `moseleys_law`** — Fe (Z=26) Kα frequency. Classical 1.54266×10¹⁸ Hz vs measured
  **1.54847×10¹⁸ Hz** (Fe Kα1 = 6403.84 eV, NIST). `phi(1)` = 3.1141×10¹⁸ Hz → **+101.1 %**.
- **1345 `auger_effect`** — classical 7255 eV is already **−10.4 %** from the NIST
  binding-energy difference (8094.1 eV), because the sim uses wrong Cu L-shell values
  (870, 855 instead of 952.3, 932.5). `phi(1)` = 11751 eV → **+45.2 %**.
- **1525 / 1457 pair production & positron emission** — threshold 1.022 MeV vs measured
  **1.0219979 MeV** (CODATA). `phi(1)` = 2.2717 MeV → **+122.3 %**.
- **543 `flux_quantization`** — Φ₀ = 2.0706×10⁻¹⁵ Wb vs CODATA **2.067833848×10⁻¹⁵ Wb**.
  `phi(1)` = 4.5864×10⁻¹⁵ Wb → **+121.8 %**.
- **591 `quantum_hall_effect`** — R_xy(ν=2) = 12941.4 Ω vs CODATA **12906.4 Ω**.
  `phi(1)` = 28356 Ω → **+119.7 %**.
- **1490 `deuteron_binding`** — 2.224 MeV vs **2.224566 MeV** (NNDC). `phi(1)` = 4.8346 MeV → **+117.3 %**.
- **1326 / 1304 / 1353 hydrogen ladder** — n=2 energy 3.4 eV vs **3.399608501 eV** (NIST).
  `phi(1)` = 6.1193 eV → **+80.0 %**.
- **056 / 042 speed of light** — c = 299792458 m/s (SI exact). `phi(1)` = 355377036.58 m/s → **+18.5 %**.
  A φ-form that moves the invariant speed of light by 18.5 % is falsified by every
  interferometer ever built.

---

## 6. NO_REFERENCE and broken φ-forms

Excluded from the deviation statistics, with reasons (no number was invented):

```
[1346] photoionization       sim uses an ARBITRARY I = 1.6e-19 J (10 eV); no real atom specified
[  4] universal_gravitation   F depends on m1,m2,r; only G is a constant (sim 6.674e-11 vs CODATA 6.67430e-11)
[ 36] coulombs_law            F depends on q1,q2,r; only k is a constant (sim 8.99e9 vs CODATA 8.9875517923e9)
[ 30] boltzmann_entropy       S = k ln W with arbitrary W = 1e23; only k_B is a constant (sim k_B is exact)
[ 66] plancks_law             classical u = 0 exactly at T=1e-3 K; deviation undefined
[1782] exciton_binding_energy generic hydrogenic mu=0.1, eps=10; no real material specified

[1524] annihilation           phi(1) returns 0.309 (dimensionless) — ground term 0.5 dominates; UNIT BUG
[ 969] photon_energy          phi(1) returns 0.382 (dimensionless) — UNIT BUG
[ 970] photon_momentum        phi(1) returns 0.382 (dimensionless) — UNIT BUG
```

The three `UNIT BUG` cases are the same defect: `phi(κ) = classical·(1+κ(φ−1)) + κ·φ⁻¹·ground`
with a **dimensionless** `ground` of order 1 and a classical value of order 10⁻²⁷…10⁻¹⁰⁰.
At κ=1 the dimensionless term swamps the physical quantity and the function returns a
number with the wrong units. This is a separate, independent defect from the κ question.

---

## 7. The `VERIFIED BY:` audit (supporting evidence)

A scan of all 2,395 `VERIFIED BY:` lines confirms the corpus never claims a φ-detection:

```
laws with VERIFIED BY:                                  2395
VERIFIED BY asserting exact / classical / no-deviation: 2242
VERIFIED BY mentioning phi/kappa/coheren:                319
```

Every one of the 319 φ-mentioning lines asserts the **absence** of the φ-effect. Examples:

```
001: "A system is prepared at a measured momentum below φ⁻¹ × its ..."
007: "Buoyant force measured exactly at ρVg with no coherence modulation."
014: "Orbital precession residuals show no φ-component across ..."
025: "PV measured exactly nRT with no coherence dependence."
032: "Emission measured exactly at sigma*T^4 with no coherence term."
036: "Force measured exactly inverse-square with no φ-component."
```

**Zero laws assert an observed φ-detection.** The corpus's own STAGE-5 "predictions" are
all of the form "the classical result holds exactly"; the φ-term is always claimed to be
below the measurement floor. Combined with §4 — where the φ-term is *not* below the floor
but 18–122 % above the measured value — the STAGE-5 claims are contradicted by the
corpus's own κ=1 arithmetic.

---

## 8. Verdict

**The corpus's φ-extensions are not empirically supported.**

1. **The validation is vacuous.** `sim/harness.py`'s "≤1 % classical-limit error" is
   computed only at κ=0, where the φ-form is *algebraically identical* to the classical
   value. 2393/2395 laws report error exactly 0.0. The gate cannot fail, so it tests
   nothing. The one law that genuinely fails the κ=0 limit (183, a 0.119 % sigmoid
   mismatch) is absorbed by the 1 % threshold.

2. **At κ=1 the φ-form is falsified by measurement.** For 26 laws with citable reference
   values, the κ=1 prediction deviates from the real measured value by a **median of
   +61.8 %**, with **26/26 beyond 10 %** and **16/26 beyond 50 %**. The deviation is
   positive in every case — a uniform multiplicative rescaling, not a physical correction.

3. **The φ-form is not a small correction.** At κ=1 it multiplies the classical quantity
   by ≈φ (1.618) plus a ground term. 2121/2328 laws (91 %) inflate their classical value
   by more than 50 %. A theory whose "full coupling" limit is a 62 % rescaling of the
   quantity it claims to correct is not a perturbation of the classical law.

4. **The corpus's own STAGE-5 claims are contradicted.** All 2,395 `VERIFIED BY:` lines
   assert the classical result holds exactly and the φ-term is undetectable. The κ=1
   arithmetic shows the φ-term is 18–122 % of the measured value — not undetectable.

5. **Independent defects.** 3 sims return dimensionless values at κ=1 (unit bug); 6 laws
   have no citable reference (arbitrary scenario); 2 sims fail to import.

**Bottom line:** the φ-forms are a *parameterisation of the classical laws by a factor
(1 + κ(φ−1))*, not an extension of them. The κ=0 limit is a definitional identity, and
the κ=1 limit is a 62 % over-prediction of every measured quantity tested. The corpus's
"VALIDATED" status is an artifact of a self-referential validation protocol.

---

## 9. Reproducibility

```powershell
cd C:\Users\delta\brain\v6\research\32_PHI_PHYSICS\XRF\PROOF
python kappa_sweep.py
```

- **Seed:** `1900` (explicit; the sweep contains no randomness).
- **No `hash()` on strings.** **No fabricated values** — every `real` value in the
  reference table cites NIST, CODATA, or a standard textbook; laws without a citable
  reference are marked `NO_REFERENCE` and excluded from the statistics.
- **Output:** `kappa_sweep_results.json` (all rows, distributions, outliers).
- **Runtime:** ~seconds; imports and executes the corpus's own 2,395 sim modules.
