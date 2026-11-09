"""The signed receipt: canonical JSON + model provenance + hash chain + ECDSA.

HONESTY
-------
A receipt proves **integrity and model identity**, not truth.  It proves that:

1. the report bytes have not changed since sealing (SHA-256),
2. the report is linked to the previous receipt (``prev_hash``),
3. the model that produced the numbers is named inside the signed body
   (``model.version``, ``model.calibration_id``, ``model.physics``),
4. the signature verifies against the field's trust root (ECDSA P-256 from
   ``SOUL_SEED = 1900``) when that root is importable.

It does **not** prove that the model describes the world.  The instrument's
forward response, signed by the trust root, is still the instrument's own
computation; the receipt's ``provenance`` field says which kind of reading
it is (``measured`` / ``instrument`` / ``feed``).

The gap this module closes
--------------------------
Agent 1's audit (``READING/01_THE_METER_ANTENNA_RADIO.md`` §8.3, Rule 4) found
that the existing meter's signed proof carries no model version or calibration
id, so the signature attests only to arithmetic.  Here the model version,
calibration id and ``physics="classical"`` are inside the signed body.  Changing
the model changes the signature.

Signing modes
-------------
``ES256``
    The field trust root at
    ``phi-field-native-transformer/field_computer/field_internet/trust/keys.py``
    is importable.  Keys are derived deterministically from ``SOUL_SEED`` and
    the signature is ECDSA P-256 / SHA-256 (64 bytes, compressed public key).
``SHA256-CHAIN``
    The trust root is unavailable.  The "signature" is a SHA-256 hash of the
    canonical body.  This detects accidental tampering and preserves the chain,
    but it is **not a signature**: anyone can recompute it.  The receipt says
    which mode was used and the verifier reports it.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .spectrum import canonical_json, _json_safe

RECEIPT_SCHEMA = "xrf-sniffer/receipt-v1"
SNIFFER_VERSION = "1.0.0"

#: Anchor for the first receipt in a chain.
GENESIS_HASH = hashlib.sha256(b"XRF-SNIFFER-GENESIS-1900").hexdigest()

_TRUST_KEYS_REL = Path(
    "phi-field-native-transformer/field_computer/field_internet/trust/keys.py"
)
_TRUST_MODULE = None
_TRUST_LOAD_ATTEMPTED = False


# ---------------------------------------------------------------------------
# Trust root
# ---------------------------------------------------------------------------
def find_trust_keys() -> Optional[Path]:
    """Locate the field trust root's ``keys.py`` without importing the world."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / _TRUST_KEYS_REL
        if candidate.exists():
            return candidate
    return None


def load_trust_module():
    """Load the field trust root's ``keys.py``, or return ``None``.

    Imported by file location under a private module name so that the sniffer
    does not pollute ``sys.path`` and cannot collide with another ``keys``.
    """
    global _TRUST_MODULE, _TRUST_LOAD_ATTEMPTED
    if _TRUST_LOAD_ATTEMPTED:
        return _TRUST_MODULE
    _TRUST_LOAD_ATTEMPTED = True
    path = find_trust_keys()
    if path is None:
        _TRUST_MODULE = None
        return None
    try:
        spec = importlib.util.spec_from_file_location("xrf_field_trust_keys", path)
        if spec is None or spec.loader is None:
            _TRUST_MODULE = None
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # sanity: the API we need must exist
        for name in ("generate_ksk", "generate_zsk", "generate_entity_key",
                     "sign_data", "verify_signature"):
            if not hasattr(module, name):
                _TRUST_MODULE = None
                return None
        _TRUST_MODULE = module
    except Exception:
        _TRUST_MODULE = None
    return _TRUST_MODULE


def trust_root_available() -> bool:
    return load_trust_module() is not None


class Signer:
    """Sign and verify receipt bodies with the field root or the hash fallback."""

    def __init__(self, entity_id: str = "xrf-sniffer"):
        self.entity_id = entity_id
        module = load_trust_module()
        self.module = module
        if module is not None:
            self.alg = "ES256"
            self.mode = "field-trust-root"
            self._ksk = module.generate_ksk()
            self._zsk = module.generate_zsk(self._ksk)
            self._entity = module.generate_entity_key(self._zsk, entity_id)
            self.public_key_hex = self._entity.public_key.hex()
        else:
            self.alg = "SHA256-CHAIN"
            self.mode = "self-sha256"
            self._entity = None
            self.public_key_hex = "self-sha256"

    def sign(self, body_bytes: bytes) -> str:
        if self.module is not None and self._entity is not None:
            return self.module.sign_data(self._entity, body_bytes).hex()
        return hashlib.sha256(b"xrf-sha256-chain-v1\0" + body_bytes).hexdigest()

    def verify(self, body_bytes: bytes, signature_hex: str,
               public_key_hex: str) -> bool:
        if self.alg == "ES256":
            module = self.module or load_trust_module()
            if module is None:
                return False
            try:
                return bool(module.verify_signature(
                    bytes.fromhex(public_key_hex), body_bytes,
                    bytes.fromhex(signature_hex)))
            except Exception:
                return False
        expected = hashlib.sha256(b"xrf-sha256-chain-v1\0" + body_bytes).hexdigest()
        return _constant_time_equals(expected, signature_hex)


def _constant_time_equals(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    acc = 0
    for x, y in zip(a.encode(), b.encode()):
        acc |= x ^ y
    return acc == 0


# ---------------------------------------------------------------------------
# Canonical body
# ---------------------------------------------------------------------------
_SIGNATURE_FIELDS = ("hash", "signature", "public_key")


def _body(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in receipt.items() if k not in _SIGNATURE_FIELDS}


def body_bytes(receipt: Mapping[str, Any]) -> bytes:
    return canonical_json(_body(receipt)).encode("utf-8")


def receipt_hash(receipt: Mapping[str, Any]) -> str:
    return hashlib.sha256(body_bytes(receipt)).hexdigest()


def _sha256_payload(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    if hasattr(payload, "sha256") and callable(payload.sha256):
        return str(payload.sha256())
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _read_last_receipt(chain_file: str | Path) -> Optional[Dict[str, Any]]:
    path = Path(chain_file)
    if not path.exists():
        return None
    last = None
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: malformed receipt line") from exc
    return last


def _append_receipt(chain_file: str | Path, receipt: Mapping[str, Any]) -> None:
    path = Path(chain_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(canonical_json(receipt) + "\n")


# ---------------------------------------------------------------------------
# Seal
# ---------------------------------------------------------------------------
def seal(report: Any,
         spectrum: Any = None,
         feed: Any = None,
         prev_receipt: Optional[Mapping[str, Any]] = None,
         chain_file: Optional[str | Path] = None,
         timestamp: Optional[float] = None,
         signer: Optional[Signer] = None) -> Dict[str, Any]:
    """Seal a report into a canonical, signed receipt.

    ``report`` may be a :class:`sniffer.sniffer.Report` or a dict.
    ``spectrum`` (optional) is bound by its deterministic SHA-256.
    ``feed`` (optional) is bound by a SHA-256 of its canonical JSON.
    ``chain_file`` appends the receipt to a JSONL chain and reads the previous
    hash/seq from it.
    """
    payload = report.as_dict() if hasattr(report, "as_dict") else dict(report)
    if "model" not in payload:
        raise ValueError("report has no model block; refusing to seal an anonymous number")
    model = payload["model"]
    for key in ("version", "calibration_id", "physics"):
        if not model.get(key):
            raise ValueError(f"report.model.{key} is required; refusing to seal")
    if model.get("physics") != "classical":
        raise ValueError(
            f"report.model.physics must be 'classical', got {model.get('physics')!r}"
        )

    previous = prev_receipt
    if previous is None and chain_file is not None:
        previous = _read_last_receipt(chain_file)
    if previous is not None:
        seq = int(previous.get("seq", 0)) + 1
        prev_hash = str(previous.get("hash", GENESIS_HASH))
    else:
        seq = 1
        prev_hash = GENESIS_HASH

    now = time.time() if timestamp is None else float(timestamp)
    signer = signer or Signer()

    spectrum_hash = _sha256_payload(spectrum)
    feed_hash = _sha256_payload(feed)
    if spectrum_hash is not None:
        input_block = {
            "kind": "spectrum",
            "sha256": spectrum_hash,
            "spectrum_sha256": spectrum_hash,
            "n_channels": (int(spectrum.energy_ev.size)
                           if hasattr(spectrum, "energy_ev") else None),
            "live_time_s": (float(spectrum.live_time_s)
                            if hasattr(spectrum, "live_time_s") else None),
        }
    elif feed_hash is not None:
        input_block = {"kind": "feed", "sha256": feed_hash, "feed_sha256": feed_hash}
    else:
        input_block = {"kind": "report-only", "sha256": None}

    body = {
        "schema": RECEIPT_SCHEMA,
        "seq": seq,
        "t": now,
        "t_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "instrument": "xrf-sniffer",
        "provenance": payload.get("provenance", "unknown"),
        "report": payload,
        "model": {
            "name": model.get("name", "counts_to_concentration"),
            "version": model["version"],
            "calibration_id": model["calibration_id"],
            "physics": model["physics"],
            "label": model.get("label", "[MODEL]"),
            "method": model.get("method", ""),
        },
        "engine": {"name": "engine", "version": _engine_version()},
        "input": input_block,
        "prev_hash": prev_hash,
        "attestation": {
            "alg": signer.alg,
            "signer": signer.mode,
            "units": "ug_cm2",
            "one_claim": True,
            "gapless": True,
            "model_bound": True,
            "note": (
                "the signature attests to the report bytes AND to the model "
                "version / calibration id inside the signed body; it does not "
                "attest that the model describes the world"
            ),
        },
    }
    body_hash = receipt_hash(body)
    signature = signer.sign(canonical_json(body).encode("utf-8"))
    receipt = dict(body)
    receipt["hash"] = body_hash
    receipt["signature"] = signature
    receipt["public_key"] = signer.public_key_hex

    if chain_file is not None:
        _append_receipt(chain_file, receipt)
    return receipt


def _engine_version() -> str:
    try:
        import engine

        return str(getattr(engine, "__version__", "unknown"))
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
def verify_receipt(receipt: Mapping[str, Any],
                   prev_receipt: Optional[Mapping[str, Any]] = None,
                   require_model: bool = True) -> Dict[str, Any]:
    """Re-derive and re-check a receipt.  Returns a structured verdict."""
    checks: Dict[str, Any] = {}
    errors: List[str] = []

    def check(name: str, ok: bool, detail: Any = None) -> None:
        checks[name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            errors.append(name)

    for key in ("schema", "hash", "signature", "public_key", "prev_hash", "report"):
        check(f"field:{key}", key in receipt, None)
    if errors:
        return {"ok": False, "checks": checks, "errors": errors,
                "alg": None, "model": None}

    check("schema", receipt.get("schema") == RECEIPT_SCHEMA,
          receipt.get("schema"))
    model = receipt.get("model") or {}
    check("model.version", bool(model.get("version")), model.get("version"))
    check("model.calibration_id", bool(model.get("calibration_id")),
          model.get("calibration_id"))
    check("model.physics", model.get("physics") == "classical",
          model.get("physics"))
    if require_model and not (model.get("version") and model.get("calibration_id")):
        pass  # already recorded above

    # 1. body hash
    expected_hash = receipt_hash(receipt)
    check("hash", _constant_time_equals(str(receipt.get("hash", "")), expected_hash),
          {"expected": expected_hash, "stored": receipt.get("hash")})

    # 2. signature
    att = receipt.get("attestation") or {}
    alg = att.get("alg")
    if alg == "ES256":
        module = load_trust_module()
        if module is None:
            check("signature", False, "field trust root unavailable")
        else:
            try:
                ok = bool(module.verify_signature(
                    bytes.fromhex(str(receipt["public_key"])),
                    canonical_json(_body(receipt)).encode("utf-8"),
                    bytes.fromhex(str(receipt["signature"])),
                ))
            except Exception as exc:
                ok = False
                checks["signature_error"] = str(exc)
            check("signature", ok, "ECDSA P-256 / SHA-256")
    elif alg == "SHA256-CHAIN":
        expected_sig = hashlib.sha256(
            b"xrf-sha256-chain-v1\0" + canonical_json(_body(receipt)).encode("utf-8")
        ).hexdigest()
        check("signature", _constant_time_equals(
            str(receipt.get("signature", "")), expected_sig),
            "SHA-256 hash chain (not a signature)")
    else:
        check("signature", False, f"unknown attestation algorithm {alg!r}")

    # 3. chain linkage
    if prev_receipt is not None:
        check("prev_hash", receipt.get("prev_hash") == prev_receipt.get("hash"),
              {"expected": prev_receipt.get("hash"),
               "stored": receipt.get("prev_hash")})
        try:
            check("seq", int(receipt.get("seq", -1))
                  == int(prev_receipt.get("seq", -2)) + 1,
                  {"stored": receipt.get("seq"), "previous": prev_receipt.get("seq")})
        except (TypeError, ValueError):
            check("seq", False, "non-integer seq")

    # 4. provenance consistency (the seal defaults the receipt's provenance to
    #    "unknown" when the report does not declare one; the check uses the
    #    same default, so a report without the field is consistent by default)
    report = receipt.get("report") or {}
    check("provenance",
          receipt.get("provenance") == report.get("provenance", "unknown"),
          {"receipt": receipt.get("provenance"),
           "report": report.get("provenance", "unknown")})
    check("input.sha256", bool((receipt.get("input") or {}).get("sha256")
                               or (receipt.get("input") or {}).get("kind") == "report-only"),
          (receipt.get("input") or {}).get("kind"))

    return {
        "ok": all(c["ok"] for c in checks.values()),
        "checks": checks,
        "errors": errors,
        "alg": alg,
        "signer": att.get("signer"),
        "model": {
            "version": model.get("version"),
            "calibration_id": model.get("calibration_id"),
            "physics": model.get("physics"),
        },
        "hash": receipt.get("hash"),
        "prev_hash": receipt.get("prev_hash"),
        "seq": receipt.get("seq"),
        "provenance": receipt.get("provenance"),
    }


def verify_chain(receipts: Iterable[Mapping[str, Any]] | str | Path) -> Dict[str, Any]:
    """Verify a list of receipts (or a JSONL chain file) end to end."""
    if isinstance(receipts, (str, Path)):
        path = Path(receipts)
        items: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
    else:
        items = list(receipts)

    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    previous = None
    for i, receipt in enumerate(items):
        verdict = verify_receipt(receipt, prev_receipt=previous)
        results.append(verdict)
        if not verdict["ok"]:
            errors.append(f"receipt[{i}] seq={receipt.get('seq')}: "
                          + ", ".join(verdict["errors"]))
        previous = receipt
    return {
        "ok": not errors,
        "n": len(items),
        "errors": errors,
        "results": results,
        "genesis_ok": (not items) or items[0].get("prev_hash") == GENESIS_HASH,
    }


# ---------------------------------------------------------------------------
# Chain helper
# ---------------------------------------------------------------------------
@dataclass
class ReceiptChain:
    """A JSONL append-only receipt chain on disk."""

    path: str | Path
    entity_id: str = "xrf-sniffer"

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self._signer = None

    @property
    def signer(self) -> Signer:
        if self._signer is None:
            self._signer = Signer(self.entity_id)
        return self._signer

    def last(self) -> Optional[Dict[str, Any]]:
        return _read_last_receipt(self.path)

    def append(self, report: Any, spectrum: Any = None, feed: Any = None,
               timestamp: Optional[float] = None) -> Dict[str, Any]:
        return seal(report, spectrum=spectrum, feed=feed,
                    chain_file=self.path, timestamp=timestamp,
                    signer=self.signer)

    def verify(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"ok": True, "n": 0, "errors": [], "results": [],
                    "genesis_ok": True}
        return verify_chain(self.path)


def self_check() -> List[str]:
    problems: List[str] = []
    try:
        signer = Signer()
        body = canonical_json({"a": 1, "b": [2, 3]}).encode()
        sig = signer.sign(body)
        if not signer.verify(body, sig, signer.public_key_hex):
            problems.append("signer round trip failed")
    except Exception as exc:
        problems.append(f"signer failed: {exc}")
    if not GENESIS_HASH:
        problems.append("genesis hash missing")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("receipt self_check:", self_check() or "clean")
    print("trust root:", find_trust_keys())
    print("mode:", Signer().mode, Signer().alg)
