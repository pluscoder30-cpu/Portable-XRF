"""The spectrum container and its I/O.

HONESTY
-------
This module is **real code doing real data handling**.  It does not create
X-rays and it does not detect them — the computer IS the instrument: the code
antenna and the code sniffer are its body, and the forward response is the
instrument's own declared transduction of the sample.  It holds a measured
(an external instrument's export), instrument-forward (the instrument's own
forward response), or feed-derived XRF spectrum, and refuses malformed input
instead of guessing.

A spectrum is an array of energy channels (eV) and counts, plus the acquisition
metadata that makes the numbers meaningful: live time, real time, tube current,
air flow, filter area, sample id and provenance.  Every quantity that the
instrument needs is carried explicitly; nothing is inferred from a default
that could be mistaken for an external measurement.

Provenance is one of ``measured`` / ``instrument`` / ``feed`` / ``unknown``.
``instrument`` is the instrument's own forward response (the code antenna's
declared transduction, seed-logged); the legacy value ``simulated`` is still
accepted on older receipts.  The sniffer never upgrades an instrument-forward
or feed spectrum to ``measured``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

#: Provenance classes.  ``instrument`` (the instrument's own forward
#: response) is the current value; ``simulated`` is the legacy spelling and
#: remains valid on receipts sealed before the 2026-11-09 rename.
PROVENANCE_VALUES = ("measured", "instrument", "simulated", "feed", "unknown")

#: Metadata keys that are first-class fields of :class:`Spectrum`.
_FIELD_KEYS = {
    "live_time_s", "real_time_s", "current_ua", "flow_lpm", "duration_min",
    "filter_area_cm2", "sample_id", "source", "provenance",
}


class SpectrumValidationError(ValueError):
    """Raised when a spectrum is not physically or structurally valid."""


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    n_channels: int = 0

    def raise_if_bad(self) -> None:
        if not self.ok:
            raise SpectrumValidationError("; ".join(self.errors))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "n_channels": self.n_channels,
        }


def _json_safe(value: Any) -> Any:
    """Convert numpy scalars/arrays and non-finite floats to JSON-safe values."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8 safe."""
    return json.dumps(_json_safe(obj), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


@dataclass
class Spectrum:
    """An XRF spectrum plus the acquisition metadata that makes it meaningful."""

    energy_ev: np.ndarray
    counts: np.ndarray
    live_time_s: float = 1.0
    real_time_s: Optional[float] = None
    current_ua: Optional[float] = None
    flow_lpm: Optional[float] = None
    duration_min: Optional[float] = None
    filter_area_cm2: Optional[float] = None
    sample_id: str = ""
    source: str = ""
    provenance: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.energy_ev = np.asarray(self.energy_ev, dtype=float).ravel()
        self.counts = np.asarray(self.counts, dtype=float).ravel()
        self.metadata = dict(self.metadata or {})
        if self.provenance not in PROVENANCE_VALUES:
            self.provenance = "unknown"

    # -- construction -----------------------------------------------------
    @classmethod
    def from_engine(cls, spec, provenance: Optional[str] = None, **kw) -> "Spectrum":
        """Wrap ``engine.forward.Spectrum`` without copying its physics."""
        meta = dict(getattr(spec, "meta", {}) or {})
        if provenance is None:
            if meta.get("model") == "forward-v1" or "poisson_seed" in meta:
                provenance = "instrument"
            else:
                provenance = "unknown"
        return cls(
            energy_ev=np.asarray(spec.energy_ev, dtype=float),
            counts=np.asarray(spec.counts, dtype=float),
            live_time_s=float(getattr(spec, "live_time_s", 1.0)),
            sample_id=str(getattr(spec, "label", "") or kw.pop("sample_id", "")),
            provenance=provenance,
            metadata=meta,
            **kw,
        )

    def to_engine(self):
        """Return the engine's spectrum type (the physics engine's input)."""
        from engine.forward import Spectrum as EngineSpectrum

        meta = dict(self.metadata)
        meta.update({
            "live_time_s": self.live_time_s,
            "real_time_s": self.real_time_s,
            "current_ua": self.current_ua,
            "flow_lpm": self.flow_lpm,
            "duration_min": self.duration_min,
            "filter_area_cm2": self.filter_area_cm2,
            "sample_id": self.sample_id,
            "source": self.source,
            "provenance": self.provenance,
        })
        return EngineSpectrum(self.energy_ev, self.counts, self.live_time_s,
                              self.sample_id, meta)

    # -- validation -------------------------------------------------------
    def validate(self, strict: bool = True) -> ValidationResult:
        """Strict structural validation.

        Refuses, rather than repairs:
          * mismatched array lengths,
          * fewer than 3 channels,
          * non-finite energies or counts,
          * non-monotone (or duplicate) energies,
          * negative counts,
          * a non-positive live time,
          * real time shorter than live time,
          * non-positive flow / area / current / duration when supplied.
        """
        errors: List[str] = []
        warnings: List[str] = []
        e = np.asarray(self.energy_ev, dtype=float)
        c = np.asarray(self.counts, dtype=float)

        if e.ndim != 1 or c.ndim != 1:
            errors.append("energy_ev and counts must be one-dimensional")
        if e.size != c.size:
            errors.append(f"energy/counts length mismatch: {e.size} != {c.size}")
        if e.size < 3:
            errors.append(f"need at least 3 channels, got {e.size}")
        if e.size and not np.all(np.isfinite(e)):
            errors.append("energy_ev contains NaN or infinity")
        if c.size and not np.all(np.isfinite(c)):
            errors.append("counts contains NaN or infinity")
        if c.size and np.any(c < 0):
            errors.append("counts contains negative values")
        if e.size >= 2 and np.all(np.isfinite(e)):
            d = np.diff(e)
            if np.any(d <= 0):
                bad = int(np.argmax(d <= 0))
                errors.append(
                    f"energy_ev is not strictly increasing at index {bad} "
                    f"({e[bad]:.6g} -> {e[bad + 1]:.6g})"
                )
        if not (isinstance(self.live_time_s, (int, float))
                and math.isfinite(float(self.live_time_s))
                and float(self.live_time_s) > 0):
            errors.append(f"live_time_s must be finite and > 0, got {self.live_time_s!r}")
        if self.real_time_s is not None:
            if not (math.isfinite(float(self.real_time_s)) and float(self.real_time_s) > 0):
                errors.append(f"real_time_s must be finite and > 0, got {self.real_time_s!r}")
            elif float(self.real_time_s) + 1e-12 < float(self.live_time_s):
                errors.append(
                    f"real_time_s ({self.real_time_s}) is shorter than "
                    f"live_time_s ({self.live_time_s})"
                )
        for name in ("current_ua", "flow_lpm", "duration_min", "filter_area_cm2"):
            value = getattr(self, name)
            if value is not None:
                if not (isinstance(value, (int, float)) and math.isfinite(float(value))
                        and float(value) > 0):
                    errors.append(f"{name} must be finite and > 0 when supplied, got {value!r}")

        if not errors:
            if float(np.sum(c)) <= 0:
                warnings.append("spectrum has zero total counts (no signal)")
            if float(np.max(e)) < 2500.0:
                warnings.append("maximum energy is below 2.5 keV; most K lines are out of range")
            if float(self.live_time_s) < 1.0:
                warnings.append("live time is below 1 s; Poisson noise will dominate")
            if self.provenance == "unknown":
                warnings.append("provenance is 'unknown'; the report will say so")
            if self.flow_lpm is not None and self.filter_area_cm2 is None:
                warnings.append("flow_lpm supplied without filter_area_cm2; air loading cannot be computed")

        result = ValidationResult(not errors, errors, warnings, int(e.size))
        if strict:
            result.raise_if_bad()
        return result

    # -- identity ---------------------------------------------------------
    def sha256(self) -> str:
        """Deterministic SHA-256 of the arrays and metadata (no ``hash()``)."""
        h = hashlib.sha256()
        h.update(b"xrf-spectrum-v1\0")
        h.update(np.asarray(self.energy_ev, dtype="<f8").tobytes())
        h.update(np.asarray(self.counts, dtype="<f8").tobytes())
        meta = {
            "live_time_s": self.live_time_s,
            "real_time_s": self.real_time_s,
            "current_ua": self.current_ua,
            "flow_lpm": self.flow_lpm,
            "duration_min": self.duration_min,
            "filter_area_cm2": self.filter_area_cm2,
            "sample_id": self.sample_id,
            "source": self.source,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }
        h.update(canonical_json(meta).encode("utf-8"))
        return h.hexdigest()

    # -- summary ----------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        return {
            "n_channels": int(self.energy_ev.size),
            "energy_min_ev": float(self.energy_ev.min()) if self.energy_ev.size else None,
            "energy_max_ev": float(self.energy_ev.max()) if self.energy_ev.size else None,
            "total_counts": float(self.counts.sum()) if self.counts.size else 0.0,
            "live_time_s": float(self.live_time_s),
            "real_time_s": self.real_time_s,
            "sample_id": self.sample_id,
            "provenance": self.provenance,
            "source": self.source,
            "sha256": self.sha256(),
        }

    # -- serialisation ----------------------------------------------------
    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema": "xrf-spectrum-v1",
            "energy_ev": [float(x) for x in self.energy_ev],
            "counts": [float(x) for x in self.counts],
            "live_time_s": float(self.live_time_s),
            "real_time_s": self.real_time_s,
            "current_ua": self.current_ua,
            "flow_lpm": self.flow_lpm,
            "duration_min": self.duration_min,
            "filter_area_cm2": self.filter_area_cm2,
            "sample_id": self.sample_id,
            "source": self.source,
            "provenance": self.provenance,
            "metadata": _json_safe(self.metadata),
        }

    def save(self, path: str | Path, fmt: Optional[str] = None) -> Path:
        p = Path(path)
        fmt = (fmt or p.suffix.lstrip(".") or "json").lower()
        p.parent.mkdir(parents=True, exist_ok=True)
        if fmt in ("json", "jsonl"):
            if fmt == "json":
                p.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True,
                                        ensure_ascii=False), encoding="utf-8")
            else:
                with p.open("w", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "schema": "xrf-spectrum-jsonl-v1",
                        "header": {
                            "live_time_s": self.live_time_s,
                            "real_time_s": self.real_time_s,
                            "current_ua": self.current_ua,
                            "flow_lpm": self.flow_lpm,
                            "duration_min": self.duration_min,
                            "filter_area_cm2": self.filter_area_cm2,
                            "sample_id": self.sample_id,
                            "source": self.source,
                            "provenance": self.provenance,
                            "metadata": _json_safe(self.metadata),
                        },
                    }, ensure_ascii=False) + "\n")
                    for e, c in zip(self.energy_ev, self.counts):
                        fh.write(json.dumps({"energy_ev": float(e), "counts": float(c)}) + "\n")
        elif fmt in ("csv", "tsv"):
            delim = "," if fmt == "csv" else "\t"
            with p.open("w", encoding="utf-8", newline="") as fh:
                fh.write(f"# live_time_s={self.live_time_s}\n")
                fh.write(f"# real_time_s={self.real_time_s}\n")
                fh.write(f"# provenance={self.provenance}\n")
                fh.write(f"# sample_id={self.sample_id}\n")
                w = csv.writer(fh, delimiter=delim)
                w.writerow(["energy_ev", "counts"])
                for e, c in zip(self.energy_ev, self.counts):
                    w.writerow([f"{float(e):.10g}", f"{float(c):.10g}"])
        else:
            raise ValueError(f"unsupported spectrum format {fmt!r}; use json/jsonl/csv/tsv")
        return p


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _coerce_spectrum(raw: Dict[str, Any], path: Optional[Path] = None) -> Spectrum:
    """Build a Spectrum from a dict, accepting several common shapes."""
    blob = dict(raw)
    meta = dict(blob.pop("metadata", {}) or {})
    header = dict(blob.pop("header", {}) or {})
    meta.update(header)

    # arrays can be top-level, under "channels", or under "spectrum"
    energy = None
    counts = None
    if "energy_ev" in blob and "counts" in blob:
        energy, counts = blob.pop("energy_ev"), blob.pop("counts")
    elif "energy_keV" in blob and "counts" in blob:
        energy = [float(x) * 1000.0 for x in blob.pop("energy_keV")]
        counts = blob.pop("counts")
    elif "channels" in blob:
        ch = blob.pop("channels")
        if isinstance(ch, list) and ch and isinstance(ch[0], dict):
            if "energy_keV" in ch[0]:
                energy = [float(r["energy_keV"]) * 1000.0 for r in ch]
            else:
                energy = [float(r["energy_ev"]) for r in ch]
            counts = [float(r["counts"]) for r in ch]
    elif "spectrum" in blob and isinstance(blob["spectrum"], dict):
        return _coerce_spectrum(blob["spectrum"], path)

    if energy is None or counts is None:
        raise SpectrumValidationError(
            f"{path or 'input'} has no recognisable energy/counts arrays"
        )

    known = {
        "live_time_s", "real_time_s", "current_ua", "flow_lpm", "duration_min",
        "filter_area_cm2", "sample_id", "source", "provenance",
    }
    fields = {k: blob[k] for k in list(blob) if k in known}
    for k in list(fields):
        blob.pop(k, None)
    meta.update({k: v for k, v in blob.items()
                 if k not in ("schema", "energy_ev", "counts", "energy_keV")})
    fields.setdefault("provenance", "unknown")
    if fields["provenance"] not in PROVENANCE_VALUES:
        fields["provenance"] = "unknown"
    return Spectrum(energy_ev=np.asarray(energy, dtype=float),
                    counts=np.asarray(counts, dtype=float),
                    metadata=meta, **fields)


def _parse_comment_meta(line: str) -> Tuple[str, Any] | None:
    body = line.lstrip("#").strip()
    if "=" not in body:
        return None
    key, value = body.split("=", 1)
    key, value = key.strip(), value.strip()
    if value.lower() in ("none", "null", ""):
        return key, None
    if value.lower() in ("true", "false"):
        return key, value.lower() == "true"
    try:
        if any(ch in value for ch in ".eE"):
            return key, float(value)
        return key, int(value)
    except ValueError:
        return key, value


def _load_delimited(path: Path, delim: str) -> Spectrum:
    meta: Dict[str, Any] = {}
    rows: List[Tuple[float, float]] = []
    header_seen = False
    with path.open("r", encoding="utf-8", newline="") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                parsed = _parse_comment_meta(line)
                if parsed:
                    meta[parsed[0]] = parsed[1]
                continue
            parts = [p.strip() for p in line.split(delim)]
            if not header_seen and parts and not _is_number(parts[0]):
                header_seen = True
                continue
            header_seen = True
            if len(parts) < 2:
                raise SpectrumValidationError(f"{path}: row has {len(parts)} columns: {line!r}")
            try:
                e, c = float(parts[0]), float(parts[1])
            except ValueError as exc:
                raise SpectrumValidationError(f"{path}: non-numeric row {line!r}") from exc
            if "kev" in str(meta.get("_header", "")).lower():
                e *= 1000.0
            rows.append((e, c))
    if not rows:
        raise SpectrumValidationError(f"{path}: no data rows")
    energy = np.array([r[0] for r in rows], dtype=float)
    counts = np.array([r[1] for r in rows], dtype=float)
    fields = {k: meta.pop(k) for k in list(meta) if k in _FIELD_KEYS}
    fields.setdefault("provenance", "unknown")
    return Spectrum(energy, counts, metadata=meta, **fields)


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def _load_jsonl(path: Path) -> Spectrum:
    header: Dict[str, Any] = {}
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SpectrumValidationError(f"{path}: invalid JSONL line: {line[:80]!r}") from exc
            if isinstance(obj, dict) and ("energy_ev" in obj or "energy_keV" in obj) and "counts" in obj:
                rows.append(obj)
            elif isinstance(obj, dict):
                header.update(obj.get("header", obj))
    if not rows:
        raise SpectrumValidationError(f"{path}: no channel records in JSONL")
    energy = [float(r["energy_keV"]) * 1000.0 if "energy_keV" in r else float(r["energy_ev"])
              for r in rows]
    counts = [float(r["counts"]) for r in rows]
    meta = dict(header.pop("metadata", {}) or {})
    fields = {k: header.pop(k) for k in list(header) if k in _FIELD_KEYS}
    fields.setdefault("provenance", "unknown")
    meta.update(header)
    return Spectrum(energy, counts, metadata=meta, **fields)


def load_spectrum(path: str | Path, fmt: Optional[str] = None,
                  strict: bool = True) -> Spectrum:
    """Load a spectrum from CSV, TSV, JSON or JSONL and validate it."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    fmt = (fmt or p.suffix.lstrip(".") or "json").lower()
    if fmt == "csv":
        spec = _load_delimited(p, ",")
    elif fmt == "tsv":
        spec = _load_delimited(p, "\t")
    elif fmt == "jsonl":
        spec = _load_jsonl(p)
    elif fmt == "json":
        try:
            blob = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SpectrumValidationError(f"{p}: invalid JSON") from exc
        spec = _coerce_spectrum(blob, p)
    else:
        raise ValueError(f"unsupported spectrum format {fmt!r}")
    spec.source = spec.source or str(p)
    spec.validate(strict=strict)
    return spec


def save_spectrum(spec: Spectrum, path: str | Path, fmt: Optional[str] = None) -> Path:
    return spec.save(path, fmt)


def self_check() -> List[str]:
    problems: List[str] = []
    e = np.arange(0.0, 20000.0, 10.0)
    c = 100.0 * np.exp(-e / 5000.0)
    s = Spectrum(e, c, live_time_s=100.0, provenance="instrument")
    if not s.validate(strict=False).ok:
        problems.append("valid forward-response spectrum failed validation")
    bad = Spectrum(e, c, live_time_s=0.0)
    if bad.validate(strict=False).ok:
        problems.append("zero live time was accepted")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("spectrum self_check:", self_check() or "clean")
