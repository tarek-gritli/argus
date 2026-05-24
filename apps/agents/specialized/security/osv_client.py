"""
OSV (Open Source Vulnerabilities) API client with local disk cache.

Queries https://api.osv.dev/v1/querybatch for package vulnerability data.
Results are cached to disk for 7 days to avoid repeated API calls on every PR.

Supported ecosystems mapped automatically from manifest filename:
    requirements.txt / pyproject.toml / setup.cfg  →  PyPI
    package.json / yarn.lock                        →  npm
    Gemfile / Gemfile.lock                          →  RubyGems
    go.mod / go.sum                                 →  Go
"""

from __future__ import annotations

import json
import logging
import math
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .schemas import DependencyHit, Severity

logger = logging.getLogger(__name__)

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_REQUEST_TIMEOUT = 8  # seconds — covers one round trip comfortably
_CACHE_TTL_DAYS = 7  # re-query OSV after this many days
_CACHE_SCHEMA = "2"

# Manifest filename → OSV ecosystem name
ECOSYSTEM_MAP: dict[str, str] = {
    "requirements.txt": "PyPI",
    "pyproject.toml": "PyPI",
    "setup.cfg": "PyPI",
    "package.json": "npm",
    "yarn.lock": "npm",
    "Gemfile": "RubyGems",
    "Gemfile.lock": "RubyGems",
    "go.mod": "Go",
    "go.sum": "Go",
}

# ---------------------------------------------------------------------------
# CVSS 3.x metric weight tables (FIRST_TIME: 2.x formula differs — skip for now)
# ---------------------------------------------------------------------------
_AV_W = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_AC_W = {"L": 0.77, "H": 0.44}
_PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}  # Scope = Unchanged
_PR_C = {"N": 0.85, "L": 0.68, "H": 0.50}  # Scope = Changed
_UI_W = {"N": 0.85, "R": 0.62}
_CIA_W = {"N": 0.00, "L": 0.22, "H": 0.56}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def query(
    deps: list[tuple[str, str, str]],
    cache_file: Path,
) -> dict[str, list[DependencyHit]]:
    """Query OSV for a batch of (package, version, ecosystem) tuples.

    Returns a dict keyed by "package@version@ecosystem" → list of DependencyHit.
    Cache entries that are still fresh are served without hitting the network.
    """
    cache = _load_cache(cache_file)
    results: dict[str, list[DependencyHit]] = {}
    uncached: list[tuple[str, str, str]] = []

    for package, version, ecosystem in deps:
        key = _cache_key(package, version, ecosystem)
        entry = cache.get("entries", {}).get(key)
        if entry and _is_fresh(entry):
            results[key] = [_hit_from_dict(h) for h in entry.get("hits", [])]
        else:
            uncached.append((package, version, ecosystem))

    if uncached:
        try:
            raw = _batch_api_call(uncached)
        except Exception as exc:
            logger.warning("OSV API unreachable (%s) — static CVE database used as fallback.", exc)
            raw = []

        entries = cache.setdefault("entries", {})
        for (package, version, ecosystem), vulns in zip(uncached, raw):
            key = _cache_key(package, version, ecosystem)
            hits = _parse_vulns(vulns, package, version)
            results[key] = hits
            entries[key] = {
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "hits": [_hit_to_dict(h) for h in hits],
            }

        _save_cache(cache_file, cache)

    return results


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------


def _batch_api_call(deps: list[tuple[str, str, str]]) -> list[list[dict]]:
    """POST to OSV querybatch; return a parallel list of vulnerability lists."""
    queries = [{"package": {"name": pkg, "ecosystem": eco}, "version": ver} for pkg, ver, eco in deps]
    payload = json.dumps({"queries": queries}).encode()

    req = urllib.request.Request(
        _OSV_BATCH_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "argus-security-agent/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read())

    # Response shape: {"results": [{"vulns": [...]}, {"vulns": []}, ...]}
    return [r.get("vulns", []) for r in data.get("results", [])]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_vulns(vulns: list[dict], package: str, version: str) -> list[DependencyHit]:
    hits = []
    for v in vulns:
        hit = _parse_vuln(v, package, version)
        if hit:
            hits.append(hit)
    return hits


def _parse_vuln(vuln: dict, package: str, version: str) -> DependencyHit | None:
    cve_id = _extract_cve_id(vuln)
    if not cve_id:
        return None

    fix_version = _extract_fix_version(vuln)
    severity, cvss_score = _extract_severity(vuln)

    return DependencyHit(
        package=package,
        version=version,
        cve_id=cve_id,
        cvss_score=cvss_score,
        fix_version=fix_version,
        severity_hint=severity,
    )


def _extract_cve_id(vuln: dict) -> str:
    """Prefer a CVE-YYYY-NNNNN ID from id or aliases; fall back to OSV/GHSA ID."""
    candidates = [vuln.get("id", "")] + list(vuln.get("aliases", []))
    for c in candidates:
        if c.startswith("CVE-"):
            return c
    return candidates[0] if candidates else ""


def _extract_fix_version(vuln: dict) -> str | None:
    """Return the first 'fixed' version found in ECOSYSTEM-type ranges."""
    for affected in vuln.get("affected", []):
        for rng in affected.get("ranges", []):
            if rng.get("type") == "ECOSYSTEM":
                for event in rng.get("events", []):
                    if "fixed" in event:
                        return event["fixed"]
    return None


def _extract_severity(vuln: dict) -> tuple[Severity, float]:
    """Extract severity level and an approximate CVSS score."""
    # 1. CVSS vector in severity array (most accurate)
    for sev in vuln.get("severity", []):
        if sev.get("type") in ("CVSS_V3", "CVSS_V3_1"):
            score = _cvss3_score(sev.get("score", ""))
            if score is not None:
                return _cvss_to_severity(score), score

    db = vuln.get("database_specific", {})

    # 2. Numeric CVSS score in database_specific (some advisories include it directly)
    raw_score = db.get("cvss_v3") or db.get("cvss_score")
    if raw_score is not None:
        try:
            score = float(raw_score)
            return _cvss_to_severity(score), score
        except (ValueError, TypeError):
            pass

    # 3. String severity level in database_specific
    level_str = str(db.get("severity", "")).upper()
    level_to_score = {
        "CRITICAL": (Severity.CRITICAL, 9.5),
        "HIGH": (Severity.HIGH, 7.5),
        "MODERATE": (Severity.MEDIUM, 5.5),
        "MEDIUM": (Severity.MEDIUM, 5.5),
        "LOW": (Severity.LOW, 2.5),
    }
    if level_str in level_to_score:
        return level_to_score[level_str]

    # 4. Conservative default — assume HIGH rather than silently under-reporting
    return Severity.HIGH, 7.5


def _cvss3_score(vector: str) -> float | None:
    """Compute a CVSS 3.x base score from a vector string.

    Implements the official CVSS 3.1 base score formula exactly.
    Returns None if the vector cannot be parsed.
    """
    try:
        # Strip 'CVSS:3.x/' prefix if present
        body = vector.split("/", 1)[1] if "/" in vector else vector
        metrics = dict(part.split(":", 1) for part in body.split("/"))

        scope = metrics.get("S", "U")
        pr_w = _PR_C if scope == "C" else _PR_U

        av = _AV_W[metrics["AV"]]
        ac = _AC_W[metrics["AC"]]
        pr = pr_w[metrics["PR"]]
        ui = _UI_W[metrics["UI"]]
        c = _CIA_W[metrics["C"]]
        i = _CIA_W[metrics["I"]]
        a = _CIA_W[metrics["A"]]
    except (KeyError, ValueError):
        return None

    isc_base = 1.0 - (1.0 - c) * (1.0 - i) * (1.0 - a)
    if isc_base == 0.0:
        return 0.0

    exploitability = 8.22 * av * ac * pr * ui

    if scope == "U":
        isc = 6.42 * isc_base
        raw = min(exploitability + isc, 10.0)
    else:  # Scope Changed
        isc = 7.52 * (isc_base - 0.029) - 3.25 * ((isc_base - 0.02) ** 15)
        raw = min(1.08 * (exploitability + isc), 10.0)

    # CVSS Roundup: ceil to one decimal place (per CVSS spec)
    return math.ceil(raw * 10) / 10


def _cvss_to_severity(score: float) -> Severity:
    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    return Severity.LOW


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_key(package: str, version: str, ecosystem: str) -> str:
    return f"{package}@{version}@{ecosystem}"


def _is_fresh(entry: dict) -> bool:
    try:
        cached_at = datetime.fromisoformat(entry["cached_at"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - cached_at).days < _CACHE_TTL_DAYS
    except (KeyError, ValueError):
        return False


def _load_cache(cache_file: Path) -> dict:
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if data.get("schema_version") == _CACHE_SCHEMA:
                return data
        except Exception:
            pass
    return {"schema_version": _CACHE_SCHEMA, "entries": {}}


def _save_cache(cache_file: Path, cache: dict) -> None:
    try:
        cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not write OSV cache to %s: %s", cache_file, exc)


def _hit_to_dict(hit: DependencyHit) -> dict:
    return hit.model_dump(mode="json")


def _hit_from_dict(data: dict) -> DependencyHit:
    return DependencyHit(**data)
