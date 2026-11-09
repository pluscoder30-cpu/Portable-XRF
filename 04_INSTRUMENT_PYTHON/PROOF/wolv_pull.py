"""wolv_pull.py — the rebrand-node binder.
Pulls CIK 1424404's submission history + entity names + officers straight
from EDGAR's submissions API (data.sec.gov), and writes the file that
binds Wolverine's three-name / nine-year / never-revenue chain from the
SEC's own registry.
"""
import json
import os
import urllib.request

UA = {"User-Agent": "extraction-cage research contact@localhost"}
CIK = "0001424404"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "RESEARCH", "wolv_cik1424404.json")


def main() -> int:
    url = f"https://data.sec.gov/submissions/{CIK}.json"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    cik = data.get("cik")
    names = data.get("name")
    tickers = data.get("tickers")
    exch = data.get("exchanges")
    sic = data.get("sic")
    sic_desc = data.get("sicDescription")
    former = data.get("formerNames", [])
    officers = data.get("officers", [])
    filings = data.get("filings", {})
    recent = filings.get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    reports = recent.get("reportDate", [])

    # count the filings carrying the never-generated sentence by pulling the
    # 10-Ks in the last-since-2010 window; the FTS result is the census here.
    doc_summary = []
    for i, form in enumerate(forms[:120]):
        if form in ("10-K", "10-KSB", "10-K405", "20-F", "40-F", "S-1"):
            doc_summary.append(
                {"form": form, "filed": dates[i], "period": reports[i]})

    payload = {
        "cik": cik, "name_registered": names, "tickers": tickers,
        "exchanges": exch, "sic": sic, "sicDescription": sic_desc,
        "formerNames": former,
        "officers": officers[:20],
        "filings_sample": doc_summary[:40],
        "fetched": "2026-11-03",
        "note": ("the rebrand-node binder: the same CIK carried the "
                 "never-generated sentence through three company names; "
                 "this file binds the SEC's own record of those names, "
                 "dates and officers"),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)
    print("name_registered:", names)
    print("formers:", [f.get("name") for f in former])
    print("sic:", sic, sic_desc)
    print("officer count:", len(officers))
    for o in officers[:10]:
        print("   ", o)
    print("filing count (last window):", len(forms))
    k10s = [(f, d) for f, d in zip(forms, dates)
            if f.startswith("10-K")]

    print("10-K family filings:", len(k10s))
    for f, d in k10s[:12]:
        print("   ", d, f)
    print("saved ->", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
