"""THE AIR READER: filter-based PM loading and real public air-quality feeds.

HONESTY
-------
Two paths, two different kinds of number.

``air_from_spectrum``
    **[REAL XRF ANALYSIS + EXACT UNIT ARITHMETIC]**.  A filter sample's element
    areal densities come from the sniffer's XRF inversion.  The conversion
    areal density (ug/cm2) -> mass concentration (ug/m3) is the exact identity
    ``c = m / (Q t)`` with ``m = areal * filter_area``.  What is a model is the
    inlet/collection efficiency (default 1.0) and the assumption that the
    deposit is uniform.  The *visible* element mass sums the elements with
    transported capture in this configure — it stays a floor while the windowed
    analog heads are used, and the Law-2396 register block of the report
    carries every element of the table besides it (line channels plus the
    phi-ground floor channel for H/He).  The estimated total uses the mineral
    unmix (which includes O by stoichiometry; raw NNLS — no prior pull by
    default) and inherits whatever mineral split is in force.

``air_from_feed``
    **[REAL PUBLIC DATA + A MODEL FOR COMPOSITION]**.  The PM mass is read from
    a public air-quality network (Open-Meteo's air-quality API is the keyless
    source used here; AirNow and OpenAQ v3 are supported when their API keys
    are set).  Those feeds do **not** provide elemental composition, so the
    element -> mineral conversion uses the engine's normative endmember model.
    The reading says ``provenance="feed"`` and lists the assumptions.  If the
    network is down, the reader uses a TTL cache; if there is no cache it
    returns a blank reading and says so.  It never invents a PM value.

Every reading carries ``location`` and ``timestamp``.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from engine import air as eng_air
from engine import elements as eng_elements
from engine import minerals as eng_minerals

from .sniffer import Report, sniff
from .spectrum import Spectrum, canonical_json, _json_safe

DEFAULT_FLOW_LPM = 16.7
DEFAULT_DURATION_MIN = 24 * 60
DEFAULT_FILTER_AREA_CM2 = 11.3       # 47 mm filter, 38 mm deposit
DEFAULT_CACHE_TTL_S = 6 * 3600
DEFAULT_TIMEOUT_S = 12.0
OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
AIRNOW_URL = "https://www.airnowapi.org/aq/observation/latLong/current/"
OPENAQ_URL = "https://api.openaq.org/v3"


@dataclass
class AirReading:
    """A location- and time-stamped air/mineral reading."""

    schema: str
    mode: str                       # "filter_spectrum" | "feed"
    location: Dict[str, Any]
    timestamp: str
    provenance: str
    source: str
    status: str
    pm2_5_ug_m3: Optional[float] = None
    pm10_ug_m3: Optional[float] = None
    dust_ug_m3: Optional[float] = None
    visible_element_mass_ug_m3: Optional[float] = None
    estimated_total_pm_ug_m3: Optional[float] = None
    elements_ug_m3: Dict[str, float] = field(default_factory=dict)
    minerals_ug_m3: Dict[str, float] = field(default_factory=dict)
    mineral_mass_fractions: Dict[str, float] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    cached: bool = False
    stale: bool = False
    feed: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        payload = {
            "schema": self.schema,
            "mode": self.mode,
            "location": self.location,
            "timestamp": self.timestamp,
            "provenance": self.provenance,
            "source": self.source,
            "status": self.status,
            "pm2_5_ug_m3": self.pm2_5_ug_m3,
            "pm10_ug_m3": self.pm10_ug_m3,
            "dust_ug_m3": self.dust_ug_m3,
            "visible_element_mass_ug_m3": self.visible_element_mass_ug_m3,
            "estimated_total_pm_ug_m3": self.estimated_total_pm_ug_m3,
            "elements_ug_m3": self.elements_ug_m3,
            "minerals_ug_m3": self.minerals_ug_m3,
            "mineral_mass_fractions": self.mineral_mass_fractions,
            "assumptions": self.assumptions,
            "notes": self.notes,
            "cached": self.cached,
            "stale": self.stale,
            "feed": self.feed,
        }
        if self.report is not None:
            payload["report"] = self.report
        return _json_safe(payload)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_or_none(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# ---------------------------------------------------------------------------
# Filter-based path
# ---------------------------------------------------------------------------
def _stoichiometric_minerals(detected: Mapping[str, float]
                             ) -> Dict[str, float]:
    """**[MODEL]** Mineral mass (ug/cm2) from apportioned element mass.

    ``apportion`` distributes each element over its candidate minerals.  For
    each mineral, the element with the largest attributed mass is used with the
    mineral's exact formula fraction to reconstruct the mineral mass:

        m_mineral = m_element_dominant / fraction(element_dominant, mineral)

    This includes O (and any other unmeasured element) by stoichiometry, so it
    is a better total-PM estimate than the raw element mass.  It is **not** a
    gravimetric measurement and it inherits the engine's normative prior.  The
    dominant-element rule avoids double counting when a mineral receives more
    than one measured element.
    """
    contributions: Dict[str, Dict[str, float]] = {}
    for symbol, mass in detected.items():
        priors = eng_minerals.ELEMENT_MINERAL_PRIOR.get(symbol, ())
        wsum = sum(w for _, w in priors) or 1.0
        for name, weight in priors:
            contributions.setdefault(name, {})[symbol] = mass * weight / wsum

    mineral_mass: Dict[str, float] = {}
    for name, by_element in contributions.items():
        mineral = eng_minerals.MINERALS.get(name)
        if mineral is None or not by_element:
            continue
        dominant = max(by_element, key=by_element.get)
        z = eng_elements.element(dominant).z
        fraction = mineral.fractions.get(z, 0.0)
        if fraction > 0:
            mineral_mass[name] = by_element[dominant] / fraction

    unapportioned = sum(mass for symbol, mass in detected.items()
                        if symbol not in eng_minerals.ELEMENT_MINERAL_PRIOR)
    if unapportioned > 0:
        mineral_mass["unapportioned"] = unapportioned
    return mineral_mass


def air_from_spectrum(spectrum: Any,
                      flow_lpm: Optional[float] = None,
                      duration_min: Optional[float] = None,
                      filter_area_cm2: Optional[float] = None,
                      detector_preset: Optional[str] = None,
                      calibration_id: Optional[str] = None,
                      air_path_cm: Optional[float] = None,
                      location: Optional[Mapping[str, Any]] = None,
                      timestamp: Optional[str] = None,
                      **sniff_kwargs) -> AirReading:
    """Sniff a filter spectrum, then convert the deposit to air loading.

    The chain is the standard PM speciation method:

        filter deposit -> element areal density (ug/cm2)   [XRF inversion]
        -> element mass (ug) = areal * filter area          [exact]
        -> mass concentration (ug/m3) = mass / (flow * time) [exact]
        -> mineral loading (ug/m3)                          [mineral model]

    ``flow_lpm``, ``duration_min`` and ``filter_area_cm2`` may be supplied
    explicitly or carried on the spectrum.  If neither is available, the
    function raises: it will not invent a sampled volume.
    """
    spec = spectrum if isinstance(spectrum, Spectrum) else Spectrum.from_engine(spectrum)
    flow = flow_lpm if flow_lpm is not None else spec.flow_lpm
    duration = duration_min if duration_min is not None else spec.duration_min
    area = filter_area_cm2 if filter_area_cm2 is not None else spec.filter_area_cm2
    missing = [name for name, value in (
        ("flow_lpm", flow), ("duration_min", duration), ("filter_area_cm2", area)
    ) if value is None]
    if missing:
        raise ValueError(
            "air_from_spectrum needs " + ", ".join(missing)
            + " (pass it explicitly or put it on the Spectrum); "
              "without a sampled volume the ug/m3 number would be invented"
        )
    flow = float(flow)
    duration = float(duration)
    area = float(area)
    if flow <= 0 or duration <= 0 or area <= 0:
        raise ValueError("flow_lpm, duration_min and filter_area_cm2 must all be > 0")

    report = sniff(spec, detector_preset=detector_preset,
                   calibration_id=calibration_id, air_path_cm=air_path_cm,
                   **sniff_kwargs)

    detected = {row["symbol"]: float(row["areal_ug_cm2"])
                for row in report.elements
                if row["detection_flag"] == "detected" and row["areal_ug_cm2"] > 0}
    visible_areal = float(sum(detected.values()))
    visible_pm = eng_air.pm_mass_from_areal(visible_areal, flow, duration, area)

    elements_ug_m3 = {
        symbol: eng_air.pm_mass_from_areal(areal, flow, duration, area)
        for symbol, areal in detected.items()
    }

    minerals_block = report.minerals
    mineral_mass_areal = _stoichiometric_minerals(detected)
    minerals_ug_m3: Dict[str, float] = {
        name: eng_air.pm_mass_from_areal(mass, flow, duration, area)
        for name, mass in mineral_mass_areal.items() if mass > 0
    }
    estimated_total_areal = float(sum(mineral_mass_areal.values()))
    estimated_total = (eng_air.pm_mass_from_areal(
        estimated_total_areal, flow, duration, area)
        if estimated_total_areal > 0 else None)
    total_ug_m3 = sum(minerals_ug_m3.values())
    mineral_fractions = ({k: v / total_ug_m3 for k, v in minerals_ug_m3.items()}
                         if total_ug_m3 > 0 else {})

    assumptions = [
        "filter deposit is uniform over the filter area [MODEL]",
        "inlet and collection efficiency are 1.0 unless the caller supplies them [MODEL]",
        "the XRF-visible element mass excludes O, C, N and H; visible_element_mass_ug_m3 "
        "is a lower bound on total PM",
        "mineral masses are reconstructed from the apportioned element mass and the "
        "mineral formula, using the dominant measured element of each mineral "
        "[MODEL/NORMATIVE]; estimated_total_pm_ug_m3 is not a gravimetric measurement",
        "the PM size cut is the inlet's; this filter path does not by itself separate "
        "PM2.5 from PM10",
    ]
    notes = list(report.warnings)
    if estimated_total is None:
        notes.append(
            "no detected element has a mineral prior; estimated_total_pm_ug_m3 is null. "
            "Use visible_element_mass_ug_m3 as the measured lower bound."
        )
    if estimated_total is not None and estimated_total + 1e-9 < visible_pm:
        notes.append(
            "the stoichiometric mineral estimate is below the visible element mass; "
            "this should not happen and suggests an apportionment problem"
        )

    status = "ok" if detected else "no_detections"
    if not report.gate.get("valid", False):
        status = "gated"

    return AirReading(
        schema="xrf-sniffer/air-v1",
        mode="filter_spectrum",
        location=dict(location or {}),
        timestamp=timestamp or report.timestamp,
        provenance=report.provenance,
        source=report.source,
        status=status,
        pm2_5_ug_m3=None,
        pm10_ug_m3=estimated_total,
        dust_ug_m3=None,
        visible_element_mass_ug_m3=visible_pm,
        estimated_total_pm_ug_m3=estimated_total,
        elements_ug_m3=elements_ug_m3,
        minerals_ug_m3=minerals_ug_m3,
        mineral_mass_fractions=mineral_fractions,
        assumptions=assumptions,
        notes=notes,
        report=report.as_dict(),
    )


# ---------------------------------------------------------------------------
# Feed path
# ---------------------------------------------------------------------------
def _cache_key(lat: float, lon: float, source: str) -> str:
    text = f"{source}:{lat:.3f}:{lon:.3f}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24] + ".json"


def _cache_path(cache_dir: str | Path, lat: float, lon: float, source: str) -> Path:
    return Path(cache_dir) / _cache_key(lat, lon, source)


def _read_cache(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True),
                   encoding="utf-8")
    os.replace(tmp, path)        # atomic on the same volume


def _http_json(url: str, timeout_s: float, headers: Optional[Mapping[str, str]] = None):
    request = urllib.request.Request(url, headers={
        "User-Agent": "xrf-sniffer/1.0 (offline-first air reader)",
        "Accept": "application/json",
        **(dict(headers or {})),
    })
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        body = response.read()
    return json.loads(body.decode("utf-8"))


def _fetch_open_meteo(lat: float, lon: float, timeout_s: float) -> Dict[str, Any]:
    """Keyless public air-quality feed (Open-Meteo).  Real PM mass data."""
    query = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "pm10,pm2_5,dust,us_aqi",
        "timezone": "UTC",
    })
    blob = _http_json(f"{OPEN_METEO_URL}?{query}", timeout_s)
    current = blob.get("current") or {}
    return {
        "source": "open-meteo",
        "source_url": OPEN_METEO_URL,
        "time": current.get("time"),
        "pm10_ug_m3": _finite_or_none(current.get("pm10")),
        "pm2_5_ug_m3": _finite_or_none(current.get("pm2_5")),
        "dust_ug_m3": _finite_or_none(current.get("dust")),
        "us_aqi": _finite_or_none(current.get("us_aqi")),
        "units": blob.get("current_units", {}),
        "raw": blob,
    }


def _fetch_airnow(lat: float, lon: float, timeout_s: float) -> Dict[str, Any]:
    """AirNow (US) — requires ``AIRNOW_API_KEY``."""
    key = os.environ.get("AIRNOW_API_KEY")
    if not key:
        raise RuntimeError("AIRNOW_API_KEY is not set")
    query = urllib.parse.urlencode({
        "format": "application/json", "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}", "distance": 25, "API_KEY": key,
    })
    blob = _http_json(f"{AIRNOW_URL}?{query}", timeout_s)
    pm25 = pm10 = None
    for row in blob if isinstance(blob, list) else []:
        name = str(row.get("ParameterName", "")).upper()
        value = _finite_or_none(row.get("Value"))
        if "PM2.5" in name or "PM2" in name:
            pm25 = value if pm25 is None else min(pm25, value)
        elif "PM10" in name:
            pm10 = value if pm10 is None else min(pm10, value)
    return {
        "source": "airnow",
        "source_url": AIRNOW_URL,
        "time": (blob[0].get("DateObserved") if isinstance(blob, list) and blob else None),
        "pm10_ug_m3": pm10,
        "pm2_5_ug_m3": pm25,
        "dust_ug_m3": None,
        "raw": blob,
    }


def _fetch_openaq(lat: float, lon: float, timeout_s: float) -> Dict[str, Any]:
    """OpenAQ v3 — requires ``OPENAQ_API_KEY``.

    OpenAQ v2 is retired (HTTP 410 as of this build); v3 needs a key.  This
    function is a best-effort adapter and is not the default source.
    """
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise RuntimeError("OPENAQ_API_KEY is not set")
    headers = {"X-API-Key": key}
    loc_q = urllib.parse.urlencode({
        "coordinates": f"{lat:.4f},{lon:.4f}", "radius": 25000, "limit": 1,
    })
    loc_blob = _http_json(f"{OPENAQ_URL}/locations?{loc_q}", timeout_s, headers)
    results = loc_blob.get("results") or []
    if not results:
        raise RuntimeError("OpenAQ returned no locations")
    location_id = results[0].get("id")
    latest = _http_json(f"{OPENAQ_URL}/locations/{location_id}/latest", timeout_s, headers)
    pm25 = pm10 = None
    for row in latest.get("results") or []:
        name = str(row.get("parameter", {}).get("name", "")).lower()
        value = _finite_or_none((row.get("value") or None))
        if name == "pm25":
            pm25 = value
        elif name == "pm10":
            pm10 = value
    return {
        "source": "openaq",
        "source_url": OPENAQ_URL,
        "time": (latest.get("results") or [{}])[0].get("datetime", {}).get("utc")
        if latest.get("results") else None,
        "pm10_ug_m3": pm10,
        "pm2_5_ug_m3": pm25,
        "dust_ug_m3": None,
        "raw": latest,
    }


def _default_fetch(lat: float, lon: float, timeout_s: float,
                   source: str = "auto") -> Dict[str, Any]:
    """Try the keyless source first, then keyed sources if configured."""
    errors: List[str] = []
    order: List[Callable] = []
    if source in ("auto", "open-meteo", "open_meteo"):
        order.append(_fetch_open_meteo)
    if source in ("auto", "airnow"):
        order.append(_fetch_airnow)
    if source in ("auto", "openaq"):
        order.append(_fetch_openaq)
    for fetcher in order:
        try:
            payload = fetcher(lat, lon, timeout_s)
            if payload.get("pm10_ug_m3") is not None or payload.get("pm2_5_ug_m3") is not None:
                return payload
            errors.append(f"{fetcher.__name__}: no PM value")
        except Exception as exc:
            errors.append(f"{fetcher.__name__}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors) if errors else "no feed source available")


def _feed_to_minerals(pm10: Optional[float], pm2_5: Optional[float],
                      dust: Optional[float],
                      composition: Optional[Mapping[str, float]] = None
                      ) -> Tuple[Dict[str, float], Dict[str, float], List[str]]:
    """Convert feed PM mass (+ optional composition) to element/mineral loading.

    With a measured element composition, the engine's ``unmix`` is used for the
    mineral mass.  Without one, the engine's normative endmember model supplies
    a stated composition.  The returned units are ug/m3.
    """
    assumptions: List[str] = []
    if composition:
        elements = {str(k): float(v) for k, v in composition.items() if float(v) > 0}
        unmix = eng_minerals.unmix(elements)
        minerals = {k: float(v) for k, v in (unmix.get("minerals") or {}).items()}
        assumptions.append(
            "element composition was supplied by the feed; mineral mass is the "
            "engine's unmix of that composition [MODEL]"
        )
        return elements, minerals, assumptions

    total = pm10 if pm10 is not None else pm2_5
    if total is None or total <= 0:
        assumptions.append("the feed supplied no positive PM mass; no mineral loading computed")
        return {}, {}, assumptions

    coarse = 0.0
    if pm10 is not None and pm2_5 is not None and pm10 > 0:
        coarse = max(0.0, (float(pm10) - float(pm2_5)) / float(pm10))
    if dust is not None and dust > 0:
        dust_frac = max(0.05, min(0.60, float(dust) / float(total)))
    else:
        # Open-Meteo's dust field is often 0 at low concentrations; it does not
        # mean "no dust".  Use the coarse fraction as a proxy with a floor.
        dust_frac = max(0.10, min(0.60, coarse))
        assumptions.append(
            "dust mass was zero or not reported; mineral_dust fraction is the "
            "coarse-mode proxy with a 0.10 floor [MODEL/NORMATIVE]"
        )
    sulfate = 0.30
    sea_salt = 0.05 if coarse < 0.20 else 0.15
    soot = max(0.0, 1.0 - dust_frac - sulfate - sea_salt)
    mix = {
        "mineral_dust": dust_frac,
        "sulfate": sulfate,
        "sea_salt": sea_salt,
        "soot": soot,
    }
    norm = sum(mix.values()) or 1.0
    mix = {k: v / norm for k, v in mix.items()}
    assumptions.append(
        "element composition was not in the feed; the endmember mix is "
        + ", ".join(f"{k}={v:.2f}" for k, v in mix.items())
        + " [MODEL/NORMATIVE]. 'soot' is the engine's carbonaceous endmember and "
          "stands in for unmeasured organic carbon."
    )

    minerals: Dict[str, float] = {}
    elements: Dict[str, float] = {}
    for endmember, frac in mix.items():
        if frac <= 0:
            continue
        for mineral_name, mineral_frac in eng_air.AEROSOL_ENDMEMBERS[endmember].items():
            minerals[mineral_name] = minerals.get(mineral_name, 0.0) + total * frac * mineral_frac
        for z, element_frac in eng_air.endmember_fractions(endmember).items():
            symbol = eng_elements.BY_Z[z].symbol
            elements[symbol] = elements.get(symbol, 0.0) + total * frac * element_frac
    return elements, minerals, assumptions


def air_from_feed(lat: float, lon: float,
                  cache_only: bool = False,
                  cache_dir: Optional[str | Path] = None,
                  ttl_s: float = DEFAULT_CACHE_TTL_S,
                  timeout_s: float = DEFAULT_TIMEOUT_S,
                  source: str = "auto",
                  fetcher: Optional[Callable[[float, float, float], Dict[str, Any]]] = None,
                  composition: Optional[Mapping[str, float]] = None,
                  timestamp: Optional[str] = None) -> AirReading:
    """Read real PM mass from a public air-quality feed, with cache + fallback.

    ``cache_only=True`` never touches the network: it returns the cached
    reading if present (stale or not), otherwise a blank offline reading.
    ``fetcher`` is injectable for tests; it must return the same dict shape as
    ``_fetch_open_meteo``.  The function never raises on a network failure.
    """
    lat = float(lat)
    lon = float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("latitude must be in [-90, 90] and longitude in [-180, 180]")
    cache_dir = Path(cache_dir or os.environ.get(
        "XRF_SNIFFER_CACHE", Path.home() / ".cache" / "xrf_sniffer"))
    path = _cache_path(cache_dir, lat, lon, source)
    cached = _read_cache(path)
    now = time.time()
    age = (now - float(cached.get("fetched_at", 0))) if cached else None
    # TTL <= 0 means "never treat the cache as fresh" (used by the stale-path
    # test and by callers who want a network-first policy).
    fresh = bool(cached and ttl_s > 0 and age is not None and age <= ttl_s)

    payload: Optional[Dict[str, Any]] = None
    used_cache = False
    stale = False
    status = "ok"
    notes: List[str] = []

    if cache_only:
        if cached:
            payload = cached.get("data")
            used_cache = True
            stale = not fresh
            status = "cached" if fresh else "stale_cache"
            notes.append(
                f"cache_only=True; using cache from {cached.get('fetched_at_iso', 'unknown')}"
                + (" (stale)" if stale else "")
            )
        else:
            status = "offline_no_cache"
            notes.append("cache_only=True and no cache entry; returning a blank reading")
    elif fresh:
        payload = cached.get("data")
        used_cache = True
        status = "cached"
        notes.append(
            f"cache is fresh (age {age/60:.1f} min <= TTL {ttl_s/60:.1f} min); "
            "no network call made"
        )
    else:
        try:
            payload = (fetcher or (lambda a, b, c: _default_fetch(a, b, c, source)))(lat, lon, timeout_s)
            status = "ok"
            _write_cache(path, {
                "fetched_at": now,
                "fetched_at_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                "lat": lat, "lon": lon, "source": source, "data": payload,
            })
        except Exception as exc:
            if cached:
                payload = cached.get("data")
                used_cache = True
                stale = True
                status = "stale_cache"
                notes.append(
                    f"network fetch failed ({type(exc).__name__}: {exc}); "
                    f"using stale cache from {cached.get('fetched_at_iso', 'unknown')}"
                )
            else:
                status = "offline_no_cache"
                notes.append(
                    f"network fetch failed ({type(exc).__name__}: {exc}) and no cache "
                    "entry exists; returning a blank reading rather than inventing a value"
                )

    if payload is None:
        return AirReading(
            schema="xrf-sniffer/air-v1", mode="feed",
            location={"latitude": lat, "longitude": lon},
            timestamp=timestamp or _now_iso(),
            provenance="feed", source=source, status=status,
            assumptions=[
                "offline: no feed response and no cache; PM and mineral fields are null/empty"
            ],
            notes=notes, cached=used_cache, stale=stale,
        )

    pm10 = _finite_or_none(payload.get("pm10_ug_m3"))
    pm25 = _finite_or_none(payload.get("pm2_5_ug_m3"))
    dust = _finite_or_none(payload.get("dust_ug_m3"))
    elements, minerals, assumptions = _feed_to_minerals(pm10, pm25, dust, composition)
    total_minerals = sum(minerals.values())
    fractions = ({k: v / total_minerals for k, v in minerals.items()}
                 if total_minerals > 0 else {})
    feed_time = payload.get("time") or timestamp or _now_iso()

    return AirReading(
        schema="xrf-sniffer/air-v1",
        mode="feed",
        location={"latitude": lat, "longitude": lon},
        timestamp=str(feed_time),
        provenance="feed",
        source=str(payload.get("source", source)),
        status=status,
        pm2_5_ug_m3=pm25,
        pm10_ug_m3=pm10,
        dust_ug_m3=dust,
        visible_element_mass_ug_m3=None,
        estimated_total_pm_ug_m3=pm10 if pm10 is not None else pm25,
        elements_ug_m3=elements,
        minerals_ug_m3=minerals,
        mineral_mass_fractions=fractions,
        assumptions=assumptions,
        notes=notes,
        cached=used_cache,
        stale=stale,
        feed={k: v for k, v in payload.items() if k != "raw"},
    )


def self_check() -> List[str]:
    problems: List[str] = []
    if abs(eng_air.pm_mass_from_areal(10.0, 16.7, 1440, 11.3)
           - (10.0 * 11.3) / (16.7 * 1440 / 1000.0)) > 1e-9:
        problems.append("pm_mass_from_areal inverse check failed")
    return problems


if __name__ == "__main__":  # pragma: no cover
    print("air self_check:", self_check() or "clean")
