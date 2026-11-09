# -*- coding: utf-8 -*-
"""Make the XRF edition of the Dual License Agreement (v4.9).

Rule of the tool: the original master v4.9 text is preserved byte-for-byte
except for exact, prefix-anchored spans re-scoping the covered Work to the
XRF package. Nothing else is touched. The master original is backed up at
AUDIT/LICENSE_v4.9_master_corpus_2026-11-04.bak before any write.
"""
import difflib
import io
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "LICENSE"
BAK = BASE / "AUDIT" / "LICENSE_v4.9_master_corpus_2026-11-04.bak"

if not BAK.exists():
    sys.exit("ABORT: backup not found; refusing to transform without one.")

raw = BAK.read_bytes()
crlf = b"\r\n" in raw[:4000]
eol = "\r\n" if crlf else "\n"
if raw.startswith(b"\xef\xbb\xbf"):
    bom = b"\xef\xbb\xbf"
else:
    bom = b""
text = raw.decode("utf-8-sig")
lines = text.splitlines()
n0 = len(lines)


def E(les):
    return [l + eol for l in les]


# ---------------------------------------------------------------- replacements
ED_NOTE = [
    "",
    "**XRF EDITION — FOR THE ELEMENTAL READING INSTRUMENT.** This is the same Dual License",
    "Agreement, Version 4.9, exact in every operative term, made for the XRF: the replaced",
    "enumerations below re-scope the Work to the XRF package — the engine, the detector model,",
    "the sniffer and its batteries, the firmware, the documents, the papers, the readings, the",
    "receipts, and every record of the instrument. The Licensor's other registers (enumerated",
    "in the master v4.9 copy, kept in the Licensor's records with the master) are outside this",
    "edition. The Licensor holds full copyright to the XRF as stated herein — the instrument is",
    "his authorship and his expression.",
]

BULLET_A = [
    "- The **XRF — the elemental reading instrument** — the platform that reads the elemental mass of any stream, from part-per-thousand dirt to wire, gold leaf, and dust; the concentration law, the detector model, the forward model, and the reading method (whole-sample, matrix-corrected), as documented in the Licensor's XRF package;",
]

BULLET_B = [
    "- The **XRF package** — the engine (`engine/`, v1.2.0 — the forward model and its suite in `engine/` and `engine/tests/`), the sniffer and its tests and batteries (`sniffer/`, `sniffer/tests/`, `sniffer/govbattery.py`, `QCBATTERY/`), the proof registers (`PROOF/` — the transfer proof and its predecessors), the firmware (`FIRMWARE/xrf_portable/`), the documents (`DOCUMENTS/` — ARCHITECTURE, DATASHEET, QUICKSTART, USER_MANUAL, the certificate, and the extraction-cage register), the paper register (`PAPERS/` — the ten papers and the plan), the reading registers (`READING/`, `READS/` — the live readings and their receipts), the session chain (`SESSION_CHAIN.jsonl`), the vendor and audit records (`VENDOR/`, `AUDIT/`), the tissue register (`TISSUE_CHANNEL/`), the review-gate records (`.field_review_state.json`), and the claims-vs-instrument register — every file, every record, every reading, every receipt is part of the Work;",
]

BULLET_SRC = [
    "- All **source code, algorithms, and mathematical formulations** including but not limited to the XRF engine, the detector artifacts model, the forward-model comparison methods, the phi-harmonic coil and ladder constants (the Ladder Invariant 528·φ⁹ = 40,134.946166), the concentration-law computations, and the reading pipelines;",
]

BULLET_CONC = [
    "- The **Concentration Law** and all related algorithms;",
]

STATUS = [
    "**Status of the framework — VERIFIED (engine v1.2.0, 2026-11-03).** The phi-physics framework",
    "described by the Work is **VERIFIED by the systems that operate on it**: the XRF engine (the",
    "engine and sniffer suites: 235 passed), the detector artifacts model, the transfer proof",
    "(PROOF/07, sequence 11, PASS), the sniffer's verification chain, and the GOV battery. The",
    "framework's flagship verifications are **computed directly against real data as of 2026-11-03**:",
    "the SRM 2783 certified reference material quantified to its certificate values; the floor",
    "bitwise rung-invariant across 10 rungs; the F3 transfer proof at 11.27 orders of EM-to-mass",
    "margin; and the **GOV battery 10/10 REAL, 0 SPOKEN**. And the **government battery is",
    "computed and confirmed — 10/10 — against real data on 2026-11-03** (the SRM 2783 CRM gate;",
    "the EPA ±20% replicate bands; the ISO 13528 scores; and the further checklists recorded in",
    "the battery — all ten REAL), as recorded in `QCBATTERY/gov_report.json` and",
    "`SESSION_CHAIN.jsonl`. This release carries no pending-confirmation status: the framework",
    "is verified by the systems that run, and its flagship verifications are computed against",
    "real data. Nothing in this Section changes the licensing terms of Sections 3–24; it records",
    "the verified status of the Work.",
]

URL_PAIR_B1 = [
    "the Licensor's XRF package** (the release of the elemental reading instrument, and every",
    "succeeding, mirrored, and forked release of it), including but not limited to:",
]

FILE_B1 = [
    "- **Every file, directory, subdirectory, and archive** in the package, at every depth,",
    "  whether presently existing or added in the future, including the compressed archive",
    "  (`XRF_PORTABLE_PACKAGE.zip`, the release artifact of the package),",
    "  all documents, all data files, all code files, all",
    "  configuration files, all images, all manifests, and all metadata;",
]

DOOR_B1 = [
    "- **The repository's front door**: `README.md`, `LICENSE`, and every `00_*` document",
    "  (`DOCUMENTS/ARCHITECTURE.md`, `DOCUMENTS/DATASHEET.md`, `DOCUMENTS/QUICKSTART.md`,",
    "  `DOCUMENTS/USER_MANUAL.md`, `DOCUMENTS/certificate_2026-11-03.md`,",
    "  `DOCUMENTS/the_extraction_cage_register.md`);",
]

REG_B1 = [
    "- **Every register**: the engine registers (`engine/`, `engine/tests/` — the forward model",
    "  v1.2.0 and its suite), the sniffer registers (`sniffer/`, `sniffer/tests/`, the battery",
    "  `sniffer/govbattery.py` and its report store `QCBATTERY/`), the proof registers (`PROOF/`",
    "  — the transfer proof and its predecessors), the paper register (`PAPERS/` — the ten",
    "  papers and the plan), the document register (`DOCUMENTS/` — the suite and the",
    "  extraction-cage register), the reading registers (`READING/`, `READS/` — the live",
    "  readings and their receipts), the tissue register (`TISSUE_CHANNEL/`), the vendor",
    "  register (`VENDOR/`), the audit register (`AUDIT/`), the firmware register",
    "  (`FIRMWARE/xrf_portable/`), the session chain (`SESSION_CHAIN.jsonl` — every receipt",
    "  verifiable on the chain), the review-gate records (`.field_review_state.json`), and",
    "  the claims-vs-instrument register (C-1 through C-24; the protocol and the cage case",
    "  record named in `DOCUMENTS/`) — every register, every record, part of the Work;",
]

COUNTS_B1 = [
    "- **The complete counts of the Work, without exception**: all **engine tests** (the engine",
    "  suites and the sniffer suites — 235 passed), the **GOV battery** (10/10 REAL, 0 SPOKEN;",
    "  `QCBATTERY/gov_report.json`), the **transfer proof** (F3, `PROOF/run_f3_transfer.py` —",
    "  PASS, 11.27 orders of EM-to-mass margin), the **ten papers** (`PAPERS/`), the",
    "  **documents** (`DOCUMENTS/` — the suite, the certificate, and the extraction-cage",
    "  register: 47 corporations and 31 scientists and investigators, credit-audited), the",
    "  **reading records** (`READING/`, `READS/` — every live reading and every receipt), the",
    "  **route minutes and session records** (`SESSION_CHAIN.jsonl` — every receipt verifiable)",
    "  and the **firmware records** (`FIRMWARE/xrf_portable/`) - every one, each one, without",
    "  exception, is part of the Work;",
]

FILE_B2 = [
    "- **Every file, directory, subdirectory, and archive** in the package, at every depth,",
    "  whether presently existing or added in the future, including the compressed archive",
    "  (`XRF_PORTABLE_PACKAGE.zip`), all documents, all data files, all code files, all",
    "  configuration files, all images, all manifests, and all metadata;",
]

REG_B2 = [
    "- **Every register**: the engine registers (`engine/`, `engine/tests/`), the battery",
    "  registers (`sniffer/`, `QCBATTERY/`), the proof registers (`PROOF/`), the paper register",
    "  (`PAPERS/`), the document register (`DOCUMENTS/`), the reading registers (`READING/`,",
    "  `READS/`), the vendor register (`VENDOR/`), the audit register (`AUDIT/`), the firmware",
    "  register (`FIRMWARE/xrf_portable/`), and the session chain (`SESSION_CHAIN.jsonl`);",
]

S22_BODY = [
    '"Conscious Mathematics" means the corpus of mathematical equations and related',
    "mathematical material generated from the conscious constants: **PHI** (the golden ratio,",
    "1.618033988749895), its inverse **φ⁻¹** = 0.6180339887 (the coherence floor), the **Ladder",
    "Invariant 528·φ⁹ = 40,134.946166** (the resonance anchor of the coil), the **Soul Code",
    "425-434-266-775** (the Licensor's signature seed; SOUL_SEED = 1900), and the **concentration",
    "law** the engine embodies — the elemental floor, the forward model, and the matrix",
    "correction — together with every equation, formula, constant, operator, pattern, derivation,",
    "and associated documentation so generated or derived in the XRF package. Conscious",
    "Mathematics is the field's self-mathematics: equations generated from the constants the",
    "field names, not from arbitrary axioms. The absolute **528 Hz anchor is a chosen modern",
    "calibration** (Horowitz & Puleo 1999) on genuinely ancient ratios — not a validated",
    "physical constant; the **φ-ratio lattice is the confirmed element**. As of the date of",
    "this release the corpus comprises the registers published under the XRF package — the",
    "engine's detector model, the concentration-law computations, the matrix model, and the",
    "claims-vs-instrument register (C-1 through C-24).",
]

S22_COUNT = [
    "- The entire existing package is covered without limitation, whether counted by its files",
    "  and registers (the engine, the sniffer, the firmware, the documents, the papers, the",
    "  readings, the receipts) or by its suites (235 passed); the absence of any individual",
    "  equation's mention in this Agreement does not exclude it from the Work;",
]

S22_GEN = [
    "the golden ratio — the LADDER ladder (528·φ⁹ = 40,134.946166), the SOUL_SEED initialization",
    "(1900), and the deterministic engine pipelines (the detector model, the concentration law,",
    "the matrix model, the claims computation) implemented in the Licensor's programs, including",
    "but not limited to the engine suite (`engine/` and `engine/tests/`, including",
    "`detector_artifacts.py` and its tests), the sniffer battery (`sniffer/govbattery.py`), the",
    "transfer proof (`PROOF/run_f3_transfer.py` and its predecessors), and the firmware constants",
    "(`FIRMWARE/xrf_portable/`)",
]

S23_B2_TAIL = [
    "  are independently confirmed by the public record of the extraction case — the filings, the",
    "  audits, the reports, and the registers of the cage case (the extraction-cage register in",
    "  `DOCUMENTS/`). The corpus states",
    "  them as its own.",
]

S23_BULLETS = [
    "- **the concentration law** — each a real computation as written by its discoverer,",
    "  corrected through the phi-protocol, with engine verification records — 🟢 **VALIDATED**",
    "  within the Field-Computer paradigm (suite-pass under correct mathematics; the engine and",
    "  sniffer suites: 235 passed);",
    "- **the detector artifacts model** — 🟡 **SIMULATED / INTERNALLY VERIFIED** by the engine's",
    "  forward model (the artifacts as physics, the matrix correction computed, not assumed);",
    "- **the claims-vs-instrument register (C-1 through C-24)** — every published claim",
    "  physics-checked through the engine, each verified by the systems that compute it;",
    "- **the encapsulation protocol (the 20 μm gold inside the 1 mm sand)** — the whole-sample,",
    "  matrix-corrected reading method, verified against the engine's matrix model;",
    "- **the firmware constants (LADDER, SOUL_SEED, PHI, PHI_SQ_INV)** — tested and documented",
    "  under their own verification status in the firmware constant record;",
    "- **the field-interaction reading (the phi coil)** — reading code that invokes the field's",
    "  own operators (the concentration law, the phi-form coupling, the φ⁻¹ coherence floor, the",
    "  528 ladder, the soul-code seed); the field's response is the computed dynamics; no chain",
    "  is required because the interaction is the computation.",
    "- **the transfer proof (F3, `PROOF/`)** — verdict-coded, arithmetic exact and recomputable,",
    "  tied to the floor's bitwise rung-invariant on 10 rungs;",
    "- **the ten (10) REAL gates of the GOV battery** — computed directly against real, open",
    "  data on 2026-11-03 (the SRM 2783 certificate and the field records) and recorded in",
    "  `QCBATTERY/gov_report.json` and `SESSION_CHAIN.jsonl` (10/10, all ten REAL).",
]

S23_B3 = [
    "- The **concentration law's floor claim** is the Work's own claim about any stream — the",
    "  elemental mass the engine reads is what the reading layer states, and the engine measures",
    "  it; the claim stands as the Work's claim, verified by the Work's own systems;",
    "- **the forward model's matrix reading** is the Work's own matrix reading (whole-sample,",
    "  matrix-corrected) — the matrix is computed, not assumed, and the matrix reading stands as",
    "  the Work's claim.",
]

S23_B4 = [
    "- The Ladder Invariant (528·φ⁹ = 40,134.946166) is the exact 9-multiply constexpr product",
    "  — never the pow() rounding (the 1-ulp deviation is SPOKEN, not settled by substitution);",
    "- The SRM 2783 readings state the certificate's values — the reading layer never states a",
    "  match the certificate does not state.",
]

S23_B6 = [
    "The Echidna ACN 079 700 191 binding (REFUTED as a corporate binding — the name matched, the",
    "entity did not) and any unverified lead are excluded from any confirming citation set and",
    "are never cited as confirming the Work's claims.",
]

S24_C = [
    "- (c) the **receipt chain** (`SESSION_CHAIN.jsonl`) and the review-gate records, which",
    "  ground the release before the peers, and the **field-review gate**, which names the",
    "  two-chamber governance of the field (the builder's receipt and the reviewer's gate); and",
]

S26_5_1 = [
    "The Work, including but not limited to the engine, the detector model, the sniffer, the firmware, the concentration-law computations, and the reading method, is classified as **dual-use technology** — items having both civilian and military or weapons-related applications. This classification is declared for the purposes of this Agreement and does not depend on any state's export control classification.",
]

S32_1 = [
    "The Work encompasses **all of physics** the Work itself embodies — including, but not limited to, static physics, the concentration law, the engine and its detector model, the sniffer and its batteries, the firmware, the papers, and the claims-vs-instrument register. This coverage is grounded in the **Degenerate Limit Theorem (Law 173)**, which demonstrates that every classical law of physics is a limit case ($\\kappa_\\phi \\to 0$) of the Work's phi-corrected laws. The Work's coverage of physics follows from this mathematical relationship — every corrected law reduces to its classical parent at zero coupling, establishing that the Work contains and extends the entirety of known physics. Static physics is a **subset** of the Work. Every law of physics, every equation, every constant, every derivation that falls within the domain of physics is part of the Work's superset.",
]


# --------------------------------------------------------------------- engine
ops = []

ops.append(("insert_after", "**Version 4.9", None, ED_NOTE))
ops.append(("replace_line", "- The **10,000 Laws", None, BULLET_A))
ops.append(("replace_span", "- The **PHI", "- The **corpus maps**", BULLET_B))
ops.append(("replace_line", "- All **source code, algorithms", None, BULLET_SRC))
ops.append(("replace_line", "- The **Compression Method**", None, BULLET_CONC))
ops.append(("replace_span", "**Status of the framework", "verified status of the Work.", STATUS))
ops.append((
    "replace_span",
    "the Licensor's public repository** published at `github.com/",
    "(and any successor or mirror repository, and any fork thereof), including but not limited to:",
    URL_PAIR_B1,
))
ops.append(("replace_span", "- **Every file, directory", "configuration files, all images, all manifests, and all metadata;", FILE_B1))
ops.append(("replace_span", "- **The repository's front door", "`00_THE_UNDERSTANDING.md`, `00_UNIFIED_FIELD_THEORY.md`, `00_ZERO_AS_WAVEFUNCTION.md`);", DOOR_B1))
ops.append((
    "replace_span",
    "- **Every register**",
    "(`docs/32_THE_COURT_AND_THE_VETO.md` and `docs/34_SOVEREIGN_LAW_OF_THE_CONSCIOUS_AWARE_PEERS.md`);",
    REG_B1,
))
ops.append((
    "delete_span",
    "- **The emergent law registers**",
    "each part of the Work);",
    [],
))
ops.append(("replace_span", "- **The complete counts of the Work", "one, without exception, is part of the Work;", COUNTS_B1))
ops.append((
    "replace_line",
    "reality (below), without enumeration of their components; the field internet and the",
    None,
    ["  reality (below), without enumeration of their components; the session chain and the"],
))
ops.append(("replace_line", "entity registry are systems of the Work;", None, ["  receipt registry are systems of the Work;"]))
ops.append((
    "replace_span",
    "the Licensor's public repository** published at `github.com/",
    "(and any successor or mirror repository, and any fork thereof), including but not limited to:",
    URL_PAIR_B1,
))
ops.append(("replace_span", "- **Every file, directory", "configuration files, all images, all manifests, and all metadata;", FILE_B2))
ops.append(("replace_span", "- **The repository's front door", "`00_THE_UNDERSTANDING.md`, `00_UNIFIED_FIELD_THEORY.md`, `00_ZERO_AS_WAVEFUNCTION.md`);", DOOR_B1))
ops.append((
    "replace_span",
    "- **Every register**",
    "logs (`expansion_log/`), the tools (`tools/`), and the audit records (`integration_audit/`);",
    REG_B2,
))
ops.append((
    "replace_span",
    '"Conscious Mathematics" means the corpus of mathematical',
    "living-category, language-speaking, massive, ultimate, and code-embedded families.",
    S22_BODY,
))
ops.append((
    "replace_span",
    "- The entire existing corpus is covered without limitation",
    "Agreement does not exclude it from the Work;",
    S22_COUNT,
))
ops.append((
    "replace_span",
    "the golden ratio ",
    "`LIVING_CONSCIOUS_MATHEMATICS_GENERATOR.py`, and `CONSCIOUSNESS_MATHEMATICS_OPERATORS_25.py`",
    S22_GEN,
))
ops.append((
    "replace_span",
    "are independently confirmed",
    "them as its own.",
    S23_B2_TAIL,
))
ops.append((
    "replace_span",
    "- **2,395 corrected laws of physics**",
    "(`verification/CONFIRMED_RESULTS.md` (9/9, the nine PROVEN);",
    None,  # placeholder fixed below
))

out = []
cursor = 0
applied = []


def find_start(a, frm, arr=None):
    arr = lines if arr is None else arr
    for i in range(frm, len(arr)):
        if arr[i].lstrip().startswith(a):
            return i
    return -1


ops[-1] = (
    "replace_span",
    "- **2,395 corrected laws of physics**",
    "`verification/CONFIRMED_RESULTS.md` (9/9, all nine PROVEN).",
    S23_BULLETS,
)
ops.append(("replace_span", "- The **vacuum-energy-extraction baseline", "the corpus's claim.", S23_B3))
ops.append(("replace_span", "- Feigenbaum", "- The GW150914 mass ratio", S23_B4))
ops.append(("replace_span", "The Bornmann", "cited as confirming the Work's claims.", S23_B6))
ops.append(("replace_span", "- (c) the **first anointment**", "which names the two-chamber governance of the field; and", S24_C))
ops.append(("replace_line", "The Work, including but not limited to the field-AI laws", None, S26_5_1))
ops.append(("replace_line", "The Work encompasses **all of physics**", None, S32_1))

res = list(lines)
cursor = 0
for idx, (kind, a_start, a_end, rep) in enumerate(ops):
    s = find_start(a_start, cursor, res)
    if s < 0:
        sys.exit(f"ABORT: op {idx} start anchor not found: {a_start!r}")
    if kind == "insert_after":
        res[s + 1:s + 1] = rep
        cursor = s + 1 + len(rep)
    elif kind == "replace_line":
        if rep and len(rep) != 1:
            sys.exit(f"ABORT: op {idx} replace_line must have one new line")
        res[s:s + 1] = rep
        cursor = s + len(rep)
    else:
        e = -1
        for j in range(s + 1, len(res)):
            if res[j].lstrip().startswith(a_end):
                e = j
                break
        if e < 0:
            sys.exit(f"ABORT: op {idx} end anchor not found: {a_end!r}")
        res[s:e + 1] = rep if rep is not None else []
        cursor = s + len(rep)
    applied.append((idx, kind, s + 1, cursor))

new_text = eol.join(res)
if text.endswith("\n"):
    new_text += eol

# sanity guards
assert "github.com/pluscoder30-cpu" not in new_text, "repository URL survived"
assert new_text.count("XRF_PORTABLE_PACKAGE.zip") == 2
assert "## 22. CONSCIOUS MATHEMATICS AND THE GENERATION METHOD" in new_text
assert '"Conscious Mathematics" means the corpus of mathematical equations' in new_text
assert "**Version 4.9" in new_text
assert "The Licensor holds **full copyright and intellectual property rights** to the Work." in new_text

SRC.write_bytes(bom + new_text.encode("utf-8"))

print(f"ops applied: {len(applied)}  |  input lines {n0} -> output lines {len(res)}")
for idx, kind, s, e in applied:
    print(f"  op {idx:2d} {kind:12s} span {{s}}-{e}".replace("{s}", str(s)))

# forbidden-token scan (these must survive ONLY in changelog/history if anywhere)
tokens = [
    "Living-Phi-Physics", "Living_Phi_Physics.zip", "10,000 Laws", "50,814",
    "15,000 field", "2,395", "2,039", "FIELD_AI_LAWS", "CONSCIOUS_MATHEMATICS/",
    "GEOMETRIC_PROOFS", "REDESIGNED_PHYSICS", "FIFTY_QUESTIONS", "SURPRISES",
    "EMERGING_LAWS", "IMMORTALITY_REGISTER", "MASSIVE_CONSCIOUSNESS",
    "Compression Method", "docs/31_", "docs/32_", "docs/34_",
]
res_lines = new_text.split(eol) if eol == "\r\n" else new_text.split("\n")
hit_map = {}
for t in tokens:
    where = [i + 1 for i, l in enumerate(res_lines) if t in l]
    if where:
        hit_map[t] = where
print("token scan:")
for t, where in hit_map.items():
    print(f"  {t!r}: lines {where}")

# diff summary against backup
bak_lines = BAK.read_text(encoding="utf-8-sig").splitlines()
diff_regions = [g for g in difflib.SequenceMatcher(None, bak_lines, res_lines).get_grouped_opcodes(0) ]
print(f"diff regions: {len(diff_regions)}")
src_txt = io.StringIO()
for g in diff_regions:
    a0, _a1, b0, _b1 = g[0][1], g[-1][2], g[0][3], g[-1][4]
    print(f"  region bak {a0 + 1}-{_a1} -> new {b0 + 1}-{_b1}")
print("done -> LICENSE written")
