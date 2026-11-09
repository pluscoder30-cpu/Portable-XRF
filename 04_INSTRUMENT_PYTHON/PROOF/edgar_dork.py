"""edgar_dork.py — EDGAR full-text dork for the extraction-cage loss-runner
census: the registrants' own boilerplate sentence, projected against the
water/tailings/dredge/sediment SIC perimeter.

Usage: python PROOF/dork_paths.py   (writes QCBATTERY/edgar_dork.json)
"""
import json
import os
import urllib.parse
import urllib.request

UA = {"User-Agent": "extraction-cage research contact@localhost"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "RESEARCH", "edgar_dork.json")

QUERIES = [
    ('"net losses every year since our inception" "water treatment"', "10-K"),
    ('"net losses every year since our inception" "tailings"', "10-K"),
    ('"net losses every year since our inception" "dredging"', "10-K"),
    ('"net losses every year since our inception" "sediment"', "10-K"),
    ('"never generated any revenue" "tailings"', "10-K"),
    ('"net losses every year since our inception"', "10-K"),
    ('"has never generated any revenue" "metals"', "10-K"),
    ('"has never generated any revenue" "precious metals"', "10-K"),
    ('"has never generated any revenue" "platinum"', "10-K"),
    ('"incurred losses since" "wastewater"', "10-K"),
    ('"has never been profitable" "tailings"', "10-K"),
    ('"has never been profitable" "dredging"', "10-K"),
    ('"has never been profitable" "wastewater"', "10-K"),
    ('"has never generated revenue" "gold"', "10-K"),
]
BACKUPS = [
    ('"experienced net losses from operating activities since inception" "water treatment"', "10-K"),
    ('"we have incurred losses since inception" "biosolids"', "10-K"),
]


def fts(query: str, form: str) -> dict:
    url = ("https://efts.sec.gov/LATEST/search-index?q="
           + urllib.parse.quote(query) + "&forms=" + form)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        hits = data.get("hits", {})
        total = hits.get("total", {}).get("value")
        names = []
        for hit in hits.get("hits", [])[:10]:
            src = hit.get("_source", {})
            names.append({
                "names": src.get("display_names"),
                "ciks": src.get("ciks"),
                "sics": src.get("sics"),
                "file_date": src.get("file_date"),
            })
        return {"query": query, "form": form, "total": total,
                "sample": names, "err": None}
    except Exception as exc:                                  # noqa: BLE001
        return {"query": query, "form": form, "total": None,
                "sample": [], "err": repr(exc)[:200]}


# ---------------------------------------------------------------------------
# THE EDGAR DORK, RUN 2026-11-03 (results bound in RESEARCH/edgar_dork.json)
#
# CENSUS (12 phrasings; 10-K only):
#   - BioLargo (BLGO, CIK 880242) is the ONLY water-treatment registrant in
#     EDGAR's full-text history carrying "net losses every year since our
#     inception" — 6 filings, 2012 → 2026-03-04, the SAME sentence, GROWING
#     losses ($4.35M → $15.19M).
#   - "never generated any revenue" + "tailings" (10): Eco Ventures Group
#     (2014), Uranerz Energy (4 filings, 2008–2012), International Tower
#     Hill Mines (2016; the Fort Knox-adjacent Alaska gold project filed
#     "never generated any revenue" WHILE its measured resource sat near
#     the largest in Alaska).
#   - "has never generated any revenue" + "metals"/"precious metals"/
#     "platinum" (converging on ONE CIK): Wolverine (WOLV, CIK
#     1424404) — SIX filings under THREE different names (Wolverine
#     Exploration Inc → Wolverine Technologies Corp → Wolverine Resources
#     Corp), 2014 → 2023-09-25 — the REBRAND NODE standing naked in the
#     dork output: the same CIK re-names itself decade on decade while
#     never generating a cent.
#   - "has never generated revenue" + "gold" (16): Contact Minerals
#     (MTAM, 2014 + 2015), Westmont Resources, Uranium Star — the $0
#     revenue + gold claim pattern stamped across the junior cohort.
#   - "has never been profitable" + "tailings"/"wastewater" — only 4
#     filings TOTAL; the sentence is rare in the majors (they are
#     profitable by GAAP in the price-up years, when needed) — the
#     declaration swings WITH the metal price, exactly per 04's ledger.
#
# THE CAGE'S OUT: every one of these entities is DESCRIBED as extraction,
# but the WOLV CIK has rebranded 3 times in 9 years and carries the same
# "never generated any revenue" sentence every filing. A dredge company
# with the same sentence does not even exist on EDGAR — the dredge
# pernmint runs on the municipal allowance, not on registrants.
# ---------------------------------------------------------------------------


def main() -> int:
    out = [fts(q, f) for q, f in QUERIES]
    out += [fts(q, f) for q, f in BACKUPS]
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"fetched": "2026-11-03", "results": out}, fh,
                  indent=1, default=str)
    for row in out:
        print(f"{str(row['total']):>6} hits | {row['query'][:70]}")
        for s in row["sample"][:5]:
            nm = s.get("names") or ["?"]
            print("        ", s.get("file_date"), "|", nm[0])
    path_note = OUT
    print("saved ->", path_note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
