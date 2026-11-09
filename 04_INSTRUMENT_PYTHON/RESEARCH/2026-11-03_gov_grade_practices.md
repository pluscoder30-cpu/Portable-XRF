# THE GOVERNMENT-GRADE CORPUS — WHAT INDUSTRY ACTUALLY DOES TO ITS XRFs
# (thesaurus/ compiled 2026-11-03 · 20 source-verified searches · RESEARCH/)

The ask: pull the instrument-qualification practice of the corporations, the
regulatory bodies, and the standards ecosystems, convert every test into the
code chain, and make this instrument hold up under institutional scrutiny.
This file carries the corpus: what they do, the source, and the conversion.
Every converted test lives in `sniffer/govbattery.py` (the GOV battery); the
acceptance criteria are the regulator's own published numbers wherever the
numbers are public — never invented.

---

## A. THE AIR-PARTICULATE XRF ECOSYSTEM (the instrument's home method)

|源 practice | source | the conversion |
|---|---|---|
| **Thin-film standards are THE calibration** ("they most closely resemble the layer of particles on a filter"); Microتمatter on Nuclepore/Mylar; mass classes **SL 0.5–2 / VL 3–8 / L 15–25 / R 40–60 / H 80–120 µg/cm²**, certified 5% | EPA IO-3.3 §11.2–11.4; 40 CFR Part 50 App Q §6.2.2; Micromatter order form; UCD Indresand 2013 | **LG5 ladder-linearity**: the deposit ladders at the four mass classes through the certified forward+inversion; acceptance ±20% (EPA 6200's %D) per class + linear correlation |
| **Shape standards**: ultra-pure mono-elemental films acquired long, defining the pulse-height spectrum shapes (peak/FWHM per element) | IO-3.3 §11.4; App Q §6.2 "shape standards"; EPA NERL 2006 | **LG7 shape/energy-scale**: the forward model places every registered element's strongest line exactly on the tabulated energy (273 lines vs vendor ≤0.22% edges / ≤0.28% lines, chain seq 5); the in-code detector response is the shape standard — carried, not acquired |
| **Calibration verification vs NIST SRM 2783** (Air Particulate on Filter Media, 47 mm, 2+2 blanks; certified Pb) — annual or after major repair | App Q §6.2; Thermo ARL QUANT'X air-filter note | **LG9 (SPOKEN/external)**: SRM 2783 values are NIST-licensed certificate data — not fetched/purchased; the verification gate is BOUND in-code (ISO Guide 33 rule, LG8) and awaits the certificate. Spoken absence, not silence |
| **Field-blank-derived MDL**: MDL = max(95th-pctile blank mass − median blank, analytical MDL from lab blanks); 454+568 blank filters analyzed to derive it | UCD IMPROVE SOP 301 §MDL; empirical-approach paper (Hyslop/White) | **LG6 field-blank MDL**: N=30 blank-filter replicas through the certified Poisson forward+inversion; the 95th−median statistic vs the fresh analytical 3σ MDL; the adopted MDL must be the GREATER (their rule) |
| **Daily/weekly/monthly stability cadence**: blanks + ME-RMs (multi-element RMs mimicking ambient loads) + re-analysis sets + SRM 2783; control charts with tolerances + named corrective actions | UCD IMPROVE TI 301C v2.5 Table 1; SOP 301 §11.1 | **LG1 energy/drift + LG2 blanks** run the daily layer; the control-chart layer is the receipt chain itself (seq append-only — the Shewhart craft made structural) |
| **ME-RM interlaboratory acceptance**: slopes within 20% of unity, R²>0.95; EDXRF bias within 10% for most elements; certified by GRAVIMETRY on the SAME filters/size classes as the field | EPA 2016 ME-RM study; AQRC CRM system 2017 | **LG8 scores machinery**: z/u/ζ + ISO 13528 bands bound for any future intercomparison; RM-style mass quantified by our own gravimetric chain (the areal conversion) |
| **Continuous electric-PM XRF (Xact 625)**: DAILY energy calibration (auto-fine-tune), response-stability checks (Cd/Cr/Pb), tape blanks per change, internal standard Pd (or Nb) | Near-real-time intercomparison preprint 2026 | the device battery's F-items run the on-boot analog; the internal-standard concept = our single declared anchor (the design choice, spoken) |
| **ISO 23971:2025** — PM-filter EDXRF: elements Z>11, deposits >10 ng; filter-material list (PTFE/PC/quartz/cellulose/nylon); explicitly excludes FP-only reference-free analysis for PM filters | ISO 23971:2025 (published Nov 2025) | the instrument's scope statements align; the register's Z range and 11.3 cm² deposit basis record conformance (spoken; the purchased text is not quoted verbatim) |
| **40 CFR Part 50 App Q** (lead-PM10 reference method): sensitivity factor from film standards; attenuation corrections; annual recalibration; blanks same-lot | App Q §6.2 | the areal→µg/m³ conversion is the numbered chain (VOL_M3 exact; the deposit basis 11.3 cm² matches the PTFE 11.86 cm² class size — recorded, SPOKEN difference 0.56 cm² declared) |

## B. FIELD/REGULATORY PORTABLE PROTOCOLS

| practice | source | conversion |
|---|---|---|
| **On-power-up internal calibration → NIST-traceable performance check ±20% → instrument BLANK (false-positive check) before any sample; ambient temperature recorded per measurement; >10 °F swing → recalibrate; gain check each 10–20 measurements** | EPA Region 4 LSASDPROC-107-R6 §2.4; Method 6200 §9.2/9.4 | **LG2 instrument blank** (no false positives above 3σ MDL); the ±20% band appears in LG3/LG5; temperature: the chain has no thermal state — [SPOKEN] the model is temperature-free by design; the device battery's B2 gain-drift item covers the on-device analog |
| **Energy-calibration check**: characteristic lines shifting = drift; also the GAIN check under temperature swing | Method 6200 §9.2; CFR App Q §9.2 | **LG1 energy/drift degeneracy**: every line position bit-determined by the table (drift mechanism absent by structure — BOUND as a check, not assumed) |
| **Calibration verification check sample ±20% (%D)** at each working day start/mid/end; reanalysis ladder on failures | Method 6200 §9.4 | **LG3 seven-replicate + LG4 duplicate-20**: RSD band; two-seed duplicate ≤20% |
| **Zero-drift + calibration-drift test PER BATCH** (analyzer output vs initial calibration on zero and mid-range standards; % of span); accuracy-assessment standard **20–80% of span** | 40 CFR 63 Subpart UUU App A §9.2–9.4 | the deterministic chain: drift = 0.0 measured, recorded as the batch-table analog (spoke: mechanism-free) |
| **HUD PCS**: 3 readings pre/at-4h/post vs a NIST paint film (accept 0.8–1.2 mg/cm²); retest-tolerance ladder on repeated 10 surfaces; per-substrate inconclusive ranges; PCS system EP RAW by model (EPA 747-R-95-008) | HUD PCS sheets (SciAps X-550 Feb 2022 / HEURESIS Sep 2022); Maine C.M.R. | **LG4 three-reading check**: 3 seeded runs on the declared internal film; mean in-window (±20% band declared; the 0.8–1.2 window is NIST-film-specific and the NIST film is not held — the STRUCTURE is converted, the film value awaits purchase, spoken) |
| **IEC 62321-3-1 RoHS screening**: Pb/Hg 1000 ppm, Cd 100 ppm thresholds; screen-positive → confirmatory wet chemistry; >700 ppm Pb caution; 316 SS external check standard | IEC 62321-3-1:2013; electronics.org E39/methods note | the register RESPECTS thresholds (quantified vs MDL); a screen-positive row routes to confirmatory steps by design (the κ→0 classical layer is per-read recordable); the 316 SS check standard = declared CR? [SPOKEN — the alloy's certificate is not held] |
| **PMI / API RP 578 / ASTM E1476+E2209**: grade verification from factory calibrations traceable to standards; verification frequency in programs | API 578; Bruker TITAN PMI page; Intertek | the instrument's metal register + coin-class grades is the smith's analog; program-frequency = the battery cadences (spoken schedule: the chain versions carry them) |

## C. DETECTOR/INSTRUMENT PHYSICS QC

| practice | source | conversion |
|---|---|---|
| **Mn Kα 5.9 keV FWHM acceptance**: SDD 126–140 eV guaranteed; peak-to-background 8,000:1...20,000:1; gain stability <20 ppm/°C; peak-shift stability <1 eV @100 kcps; periodic resolution check | Amptek FAST SDD sheet; KETEK VITUS; IAEA training | the FWHM/gain stability claims are the DETECTOR vendor's numbers — our [MODEL] detector's declared resolution is the same family (B3's vendor tolerance); the numbers were already checked vs the vendor bridge (battery B3); the P:B ratio is a hardware layer — [SPOKEN] not modeled |
| **Dead time under 50%; OCR = ICR·exp(−τ1·ICR); pile-up rejection τ2 from the sum-line ratio; resolution-vs-ICR stress** | Amptek recommended practices; DANTE arXiv; IAEA | **LG10 (SPOKEN)**: the chain models sufficiency not saturation — no dead-time mechanism in the declared forward model; the practice's formulas are bound as the DOCUMENTED equations in the corpus pull; candidate future item |
| **Escape peaks (Si 1.74 keV) belong to the SIGNAL and must be included; sum peaks are artifacts; PHA window evaluation; two-source dead-time/PUR verification** | Purdue AXIOS theory; IAEA EDXRF lecture; FRMAC guide | [SPOKEN + design note]: the engine's inversion treats escape lines at the table level; the escape/sum PEAK modules (per Amptek XRS-FP) are future chain candidates — recorded here so the absence is DOCUMENTED, not silent |
| **Type standardization** (Bruker/EPA): Actual = Slope·Measured + Offset, per element vs reference values | Bruker App_xrf_474; IAEA Patterson slides | **design correspondence (not a fit)**: law2396's reading IS declared as φ⁻² + φ·x — the declared (not empirically fitted) correction is the instrument's own type-standardization family, recorded; if a future empirical correction is adopted it must NOT silently reshape the reading layer (falsifier F-promises) |
| **Calibration practices**: identical conditions unknown⊆standard composition; counts→precision (4× counts for 2× precision); uncertainty never reported without numbers | Amptek recommended-XRF-practices | carried: single declared acquisition geometry everywhere (VOL/Filter/Excitation constants); every register row carries its own uncertainty arithmetic on the report |

## D. INDUSTRIAL QC FORMATS

| practice | source | conversion |
|---|---|---|
| **ASTM D4294** (sulfur in oil): calibration per range with certified standards; 5-repeat ×3 levels validation; **10-blank 3σ LOD**; **two-analyzer 10-day reproducibility** (1.5–2× repeatability) | ASTM D4294; Rigaku/Thermo/Aмptek notes | **LG6's LOD half** = the 10-blank rule used at LG2; the two-analyzer reproducibility = our two-env (desktop vs device) crosschecks where the print paths bind; the 5-repeat validation structure sits inside LG3 |
| **ASTM C114** (cement rapid test): ≥7 CRMs, TWO ROUNDS ON DIFFERENT DAYS; per-analyte accuracy limits; 10× consecutive repeatability (SRM 1889a); 30-hour precision without drift correction | ASTM C114-18; Rigaku XRF1110/1113; Bruker S8-LION LR93 | **LG3's structure** mirrors it (multi-replicate, tolerance bands, no drift correction required); per-analyte C114 limit table = purchased-text data — [SPOKEN], we do not quote |
| **ASTM B568** (coating thickness): mass-per-area with density conversion; standards per plating/substrate pair; 0.01–75 µm; 5+ readings | ASTM B568-98(2021) | the areal-style deposit quantification is the SAME arithmetic the instrument does (µg/cm² ↔ thickness via density — the engine's sheet model does exactly this conversion); spoken correspondence |
| **Precious metals trade**: XRF vs fire assay ±0.1–0.2% (flat) / ±0.5 wt% (irregular) / ±1/8 karat; W-contaminant flags; multi-spot protocol; 100% mass-balance check; ≥15–30 s statistics; daily standardization (Cu/14K disk) | Thermo fire-assay note; VRAY/ESI gold guides | the register's full-stack reconciliation (the metallic-fleet mass balance) is the 100% check's analog (paper 3); counterfeit flags (W) are REGISTERED elements by design; multi-spot = repeated reads with explicit seeds (the chain's per-read identities) |
| **composite LIBS/OES/XRF** (C/light vs heavy splits; combining methods) | Quality Magazine 2020; Hitachi blogs | [SPOKEN design]: the chain does not claim carbon; the register's spoken-absence rule covers the LIBS/OES-only elements (spoken_nonmetal mode in the portable scan) |

## E. THE ACCREDITATION-STATISTICS LAYER

| practice | source | conversion |
|---|---|---|
| **ISO 17025 / GUM / NIST SOP 29**: uncertainty budget table (Type A from the process; Type B from certificates; u_o others); expanded U = k·u_c | NIST SOP 29 2019; EA-4/02 | **LG8** implements the budget STRUCTURE for register rows: u_c = RSS of Poisson (process) + declared constants; follows the SOP's rule that each significant contributor is a named row |
| **ISO Guide 33 bias rule**: found-vs-certificate acceptable iff \|x_found − x_cert\| ≤ k·√(u_found² + u_CRM²) | NIST "How NOT to use CRMs" (ISO Guide 33 2015) | **LG8 binds the rule as the register's verification GATE** — any future certificate comparison runs through this exact inequality (no informal %D alone for new work) |
| **ISO 13528 / IAEA PTXRFIAEA scoring**: z = (x−X)/σ_pt (\|z\|≤2 satisfactory / 2–3 questionable / ≥3 unsatisfactory); u-score via reported σ (\|u\|≤2.58 @99%); ζ/zeta; **RSZ** (~N(0,1), catches small consistent bias) + **SSZ** (χ², L df) as the complementary pair; En numbers; 7 outlier tests before consensus; **Shewhart + CUSUM z-charts** (cumulative sum exposes drifting bias) | ISO 13528:2022; IAEA-AQ-20/36/9 + newsletters; Sorbo EURL PT charts | **LG7 implements the scoring functions** (z/u/ζ + RSZ/SSZ + the outlier-rejection order) machine-checked inside the battery; applied to EXTERNAL schemes when data exists — self-tests inside now bind the machinery |

## THE CONVERSION REGISTER (what `sniffer/govbattery.py` runs today)

| item | the hardware test it converts | acceptance (whose number) |
|---|---|---|
| LG0 energy/drift degeneracy | 6200 §9.2 energy-cal check | bit-determined positions (0.0 dev measured) |
| LG1 instrument blank | Region 4 / 6200 §2.4.1 blank check | zero false positives above 3σ MDL (EPA) |
| LG2 seven-replicate precision | 6200 daily 7-replicate; C114 structure | %D ≤ ±20% (EPA) |
| LG3 duplicate-of-20 | 6200 §2.4.2 duplicate every 20 | %D ≤ ±20% (EPA) |
| LG4 three-reading film check | HUD PCS 3-reading calibration check | mean in declared window (EPA band; NIST film value awaits purchase, spoken) |
| LG5 ladder linearity | IO-3.3 / Micromatter SL-VL-L-R-H classes | recovered within ±20% per class (EPA band) + r ≥ 0.999 (D4294-class correlation) |
| LG6 field-blank MDL | IMPROVE SOP 301 MDL rule | adopted MDL = max(blank-statistic, analytical) (their rule) |
| LG7 scores machinery | ISO 13528 z/u/ζ + RSZ/SSZ + IAEA bands | machinery self-tests: known-pass/known-fail pairs behave per formula |
| LG8 ISO Guide 33 gate | the CRM-vs-found comparison rule | the inequality bound; PASSED/FAILED only via k·RSS |
| **LG9 SRM 2783 verification** | App Q / IO-3.3 SRM use | **REAL — the certificate fetched live (2026-11-03, tsapps.nist.gov/srmext/certificates/archives/2783.pdf): 18 certified elements × the certificate's own 9.96 cm² deposit area → the chain runs the federal loadings → ISO Guide 33 gate at the certificate's coverage: 12/12 reported elements PASS (Al 23,564.7 vs 23,210±530 ng). The 6 below-report-bound rows SPOKEN per element. NO standard purchase, NO hardware — the certificate is data and the physics is the instrument.** |
| **LG10 escape/sum/dead-time modules** | Purdue/IAEA/FRMAC/Amptek practice | **REAL — engine/detector_artifacts.py (engine v1.2.0, the additive module; ADR gate): OCR = ICR·e^(−τ·ICR) with the max at ICR = 1/τ; Int(2)/Int(1) = ICR·τ₂/2 linear in both; escape photon at E − SiKα (1.739 keV) with the bounded probability. The hardware's behaviour ported AS PHYSICS.** |

The battery seals its receipt through the same chain (next seq), same as
the vendor battery — nothing runs outside the receipt discipline.
