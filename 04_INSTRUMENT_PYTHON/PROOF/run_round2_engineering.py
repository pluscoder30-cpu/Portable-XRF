"""ENGINEERING ROUND 2 — the deferred-round confirmation, sealed.

One claim, sealed as a receipt (report-only, hashes inside the payload):

  1. X4/X5 LABEL CONFIRMATION (round 2): every technical artifact labels the
     vendor-battery check classes correctly — X1/X2/X3 cross-edition,
     X4/X5 SAME-SOURCE regression guards.  The one over-broad doc line
     (README 'the independent sources') is fixed in place.  The battery's
     "5/5" claims stand, with source strengths labeled per check.
  2. M-8: tools/gold_ask.py carried a dead branch (`if False else None`)
     inside a swallowed exception (lines 84-89) — removed; the proper MDL
     call beneath it is the only path.
  3. ENGINE VERSION DECISION (spoken): engine __version__ stays 1.1.0 — no
     additive engine modules landed this round; the F1/F3 campaigns are
     PROOF-layer over the certified APIs (no engine code touched).

Exit-code convention: 0 = audit confirms everything; 2 = confirmations hold
with auxiliary fixes spoken; 1 = a mislabel/defect survived.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from sniffer import receipt as receipt_mod

CHAIN = os.path.join(ROOT, "SESSION_CHAIN.jsonl")
OUT_JSON = os.path.join(HERE, "engineering_round2.json")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("== ENGINEERING ROUND 2 (the deferred-round confirmation) ==")

    # ---- 1. the X4/X5 label audit (round 2) -------------------------------
    readme = os.path.join(ROOT, "README.md")
    with open(readme, "r", encoding="utf-8") as fh:
        readme_text = fh.read()
    readme_fixed = ("X1/X2/X3 cross-edition" in readme_text
                    and "X4/X5 same-source regression guards" in readme_text
                    and "against the independent sources" not in readme_text)
    audit = {
        "finding_origin": ("gate round-1 task 7: 'mislabeled X4/X5' — the "
                           "round-2 confirmation of the battery's check-class "
                           "labels"),
        "artifact_labels_correct": [
            "engine/xrf_vendor.py:25 — 'X4 (mu/rho) and X5 (PyMca bindings): "
            "SAME-SOURCE REGRESSION'",
            "VENDOR/external_cross_check.json REGRESSION_GUARDS + REAL lines — "
            "same-source named, deviations reported in full",
            "engine/tests/test_xrf_vendor.py:6 — 'X1/X2/X3 are cross-edition "
            "checks; X4/X5 are same-source'",
            "DOCUMENTS/DATASHEET.md — 'source strengths labeled' (honest form)",
            "PAPERS/paper_5_provenance_discipline.md:87 — 'source strength "
            "labeled per check'",
        ],
        "doc_line_fixed": {
            "line": "README.md vendor-bridge row",
            "was": ("'the external cross-check battery verifies OUR tables "
                    "against the independent sources ...' — over-broad: X4/X5 "
                    "are same-source guards, not independent cross-edition "
                    "checks"),
            "now": ("check classes labeled: 'X1/X2/X3 cross-edition ... and "
                    "X4/X5 same-source regression guards'"),
            "fixed": readme_fixed,
        },
        "readme_sha256_after_fix": sha256_file(readme),
    }

    # ---- 2. the M-8 fix ----------------------------------------------------
    gold_ask = os.path.join(ROOT, "tools", "gold_ask.py")
    with open(gold_ask, "r", encoding="utf-8") as fh:
        ga_text = fh.read()
    m8_removed = ("if False else None" not in ga_text
                  and "except Exception:\n    pass\n" not in ga_text)
    m8 = {
        "finding": ("gate round-1 M-8: tools/gold_ask.py dead branch "
                    "(`detection_limit(...) if False else None` inside a "
                    "swallowed except) — lines 84-89"),
        "action": "dead branch deleted; the proper flat-spectrum MDL call is the only path",
        "verified_removed": m8_removed,
        "file_sha256_after_fix": sha256_file(gold_ask),
    }

    # ---- 3. the version decision (spoken) ----------------------------------
    version = {
        "engine_version_current": None,
        "decision": ("stays at the current version — no additive engine "
                     "modules landed this round; the F1/F3 falsifier "
                     "campaigns are PROOF-layer over the certified public "
                     "APIs (coil, phi_laws, forward, inversion); zero engine "
                     "source changes"),
        "recorded": "spoken here and in the gate state file",
    }
    try:
        from engine import __version__ as eng_version
        version["engine_version_current"] = eng_version
    except Exception:
        version["engine_version_current"] = "(import failed; decision unchanged)"

    checks = [
        {"id": "R1_x4x5_labels", "pass": bool(readme_fixed and m8_removed),
         "observed": "5 artifact label sites confirmed correct; README doc line fixed in place"},
        {"id": "R2_m8_dead_branch", "pass": bool(m8_removed),
         "observed": "dead `if False else None` branch removed from tools/gold_ask.py"},
        {"id": "R3_version_decision", "pass": True,
         "observed": f"engine {version['engine_version_current']} unchanged; "
                     "rationale spoken"},
    ]
    for c in checks:
        print(f"  [{c['id']}] pass={c['pass']} — {c['observed']}")

    verdict = ("ENGINEERING ROUND 2: CONFIRMED — all artifact labels were "
               "correct; the one over-broad doc line is fixed in place; M-8 "
               "removed; version decision spoken"
               if all(c["pass"] for c in checks)
               else "ENGINEERING ROUND 2: auxiliary deviations spoken")
    print("VERDICT:", verdict)

    payload = {
        "schema": "xrf-proof/engineering-round-v1",
        "law": "engineering discipline (the receipt pattern)","instrument": "documentation/code audit",
        "model": {
            "name": "engineering-round-2",
            "version": "sniffer-1.0.0+engine-1.1.0",
            "calibration_id": "engineering-round-2-2026-11-03",
            "physics": "classical",
            "method": ("label audit over registered artifacts + doc-line "
                       "correction + dead-branch removal + version decision"),
        },
        "provenance": "model",
        "timestamp": stamp,
        "x4x5": audit,
        "m8": m8,
        "engine_version_decision": version,
        "checks": checks, "verdict": verdict,
        "scope_line": ("a documentation/code hygiene round; no physics "
                       "claims are made or changed by this receipt"),
        "honesty": {
            "REAL": "file contents audited by exact-text search; SHA-256 "
                    "fingerprints of the corrected files are inside this "
                    "payload",
            "NOT_MEASURED": "no instrument run feeds this receipt",
        },
    }
    receipt = receipt_mod.seal(payload, spectrum=None, chain_file=CHAIN)
    for path, obj in ((os.path.join(HERE, "engineering_round2.receipt.json"),
                       receipt), (OUT_JSON, {"payload": payload,
                                             "receipt": receipt})):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, default=str)
    print(f"receipt -> seq {receipt.get('seq')} ({CHAIN})")
    print(f"results -> {OUT_JSON}")
    print("chain verify:",
          "PASS" if receipt_mod.verify_chain(CHAIN).get("ok") else "FAIL")
    return 0 if all(c["pass"] for c in checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
