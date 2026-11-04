# THE EXTRACTION CAGE — 07 — THE DORK CENSUS + THE FURNACE RECORD
## The EDGAR full-text census (run live 2026-11-03, PROOF/edgar_dork.py)
## and the Sagamihara furnace's corporate sheet (Kobelco Eco-Solutions)

---

## 7.1 THE EDGAR DORK — the census (SEC full-text search, 10-K only)

| phrasing | hits | the sample |
|---|---|---|
| "net losses every year since our inception" + "water treatment" | **18** | **BioLargo only** (BLGO, CIK 880242) — filings 2012 → 2026-03-04, the SAME sentence on every 10-K for 14 years, losses growing $4.35M → $15.19M |
| same + "tailings" | **6** | BioLargo again (their wastewater-metal overlap carried the phrase) |
| same + "dredging" | **0** | the dredge perimeters don't carry the sentence — they run on municipal allowance, not on registrants |
| "never generated any revenue" + "tailings" | **10** | Eco Ventures Group (2014); Uranerz Energy (4 filings 2008–2012); **International Tower Hill Mines (THM, 2016)** — one of Alaska's largest gold resources, filed "never generated any revenue" in the same era its measured resource sat at the scene |
| "has never generated any revenue" + "metals" / "precious metals" / "platinum" | **22 / 22 / 15** — converging on ONE CIK | ** Wolverine (WOLV, CIK 1424404)**: SIX filings under THREE names — Wolverine Exploration Inc → **Wolverine Technologies Corp** → **Wolverine Resources Corp** — 2014 → Sept 2023; the same CIK re-names itself decade-on-decade carrying "has never generated any revenue" every time |
| "has never generated revenue" + "gold" | **16** | Contact Minerals (MTAM, 2014+2015), Westmont Resources, Uranium Star — the $0-revenue + gold-claim stamp across the junior cohort |
| broad sentence alone | **150** | OXiGene, Maxim Pharmaceuticals, and the whole biotech/mining junior shelf |
| "has never been profitable" + "tailings"/"wastewater" | **1** / **3** | Valhi (VHI) — the majors rarely carry it: their books swing profitable in price-up years (the 2012–2013 avalanche confirms the declaration moves with price, per 04) |

**The census verdict:** the loss-runner sentence is not a rhetorical
flare — it is a **normalized registrant artifact**. One CIK (Wolverine)
rebrands THREE times in 9 years while the same sentence stands in every
filing; one water-treatment company (BioLargo) carries it for 14
straight filings while its losses TRIPLE. The cage's paperwork is
searchable, and the search returns the pattern cleanly. The output
artifact: `RESEARCH/edgar_dork.json` + `PROOF/edgar_dork.py` (the
dork is rerunnable — the census grows as filings land).

## 7.2 THE FURNACE RECORD — the Sagamihara corporate sheet

| fact | value | source |
|---|---|---|
| the furnace that held >6,000 g Au/t | **Kobelco Eco-Solutions' Fluidized-Bed Gasification and Melting Furnace** (Kobe Steel Group) | Kobelco Eco product page (track record lists Sagamihara City Minami WtE first) |
| the plant | Sagamihara City Minami Waste to Energy & Recovery Plant; **525 t/day (175 t/24 h × 3 lines); 10,000 kW generation; completed March 2010** | Kobelco Eco track record |
| the gold recovery (FY2021) | ~15 kg gold + ~15 kg silver; suspended every 3–4 months to lift the bottom sand | gov-online.go.jp (Oct 2022) |
| the recovery R&D start | 2018 (the operator's own statement: "Fujita says, In 2018, when we started developing the precious metal recovery technology...") | gov-online.go.jp |
| the discovery point | the bottom of the **fluidized sand layer** — NOT the fly ash (the usual suspect), NOT the ash (the usual pilot target) — the gold sat in the FURNACE FLOOR for the plant's first EIGHT YEARS | gov-online.go.jp (their own account) |
| the sister plant (same city) | Sagamihara **Kita** WtE: 3×150 tpd stokers (MHI 1991, then a ¥6.3B MHIEC refurbishment 2017→Mar 2021) — the "biggest-city-intensity" waste stream pair | mhi.com 2017-11-09 |
| the technology peer group | TAKUMA (kiln-type gasification melting furnaces, ~360 plants since 1963) + MHIEC + JFE — the array of Japanese makers whose furnaces run the same physics and whose recoveries are NOT publicly costed as gold | takuma.co.jp corporate reports 2017–2020; mhi.com |

**The timing reads directly:**
- plant commissioned **March 2010** — the window's edge;
- recovery R&D started **2018** — the EIGHT-year gap;
- the sand sat under the same cyclonic flow, mining itself every day,
  for eight years, undisturbed.

The plant didn't discover gold. **An operator looked** — because the
2021 price of gold made the look cheap. The same look is available
everywhere else the furnace-floor sand has been accumulating since the
sixties: Japan's 4M tonnes/yr of MSW ash (NIES), Toronto's Highland
Creek, Metro Vancouver's WTEF, every one of the 2,400+ US WTE/incinerator
sites.

## 7.3 THE UNIT-VALUE LEDGER (what the floor is worth, per plant)

Sagamihara Minami FY2021 (one plant, ONE recovery cycle-year):
- ~15 kg Au ≈ US$0.88M (at 1,800 $/oz ≈ $58/gram)
- ~15 kg Ag ≈ US$0.013M
- ≈ **US$0.9M/plant-year**, at one plant, with the plant's heat free of
  fossil fuel per Kobelco's spec, and the CO₂ burden <1/10 of ore refining
- ×17 installed equivalent furnaces (their own fleet count) = ~**$15M/yr**
  recoverable where Kobelco's current public path still lists the VM
  (road-asphalt slag) as the product — and gold is not on the bill of
  materials.
- ×4M tonnes of Japan ash (NIES 2019 total), ×6,000 g/t floor-sand
  fraction (if the fluidized-bed fleet behaved like Minami) — the
  FAR upper bound is tens of billions of yen/yr; the FAR lower bound,
  from Suwa-ash-only basis (1.89 kg/t), is still hundreds of kg/yr per
  prefecture.

The gold is not scarce at the plant scale. **The gold is at the plant
scale on the RECEIPTS** — and the receipts (gov-online.go.jp, Kobelco's
own track record, the operator's own accounting statement) are public.
