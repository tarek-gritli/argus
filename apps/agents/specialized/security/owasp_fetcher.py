"""
OWASP Top 10 update checker and fetcher.

Scrapes https://owasp.org/Top10/{year}/ to detect new releases and updates
owasp_top10.json in place. Also migrates owasp ID references in all SAST rule
files when a new version is applied.

Usage:
    python -m apps.agents.specialized.security.owasp_fetcher          # check only
    python -m apps.agents.specialized.security.owasp_fetcher --update # fetch & apply latest

Exit codes:
    0 - up to date or update applied successfully
    1 - new version detected but --update not passed
    2 - network or parse error
"""

from __future__ import annotations

import json
import logging
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_RULES_DIR = Path(__file__).resolve().parent / "rules"
_OWASP_FILE = _RULES_DIR / "owasp_top10.json"
_SAST_DIR = _RULES_DIR / "sast"

# Probe this many future years before giving up.
_YEAR_LOOKAHEAD = 3


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_owasp_rules(rules_dir: Path = _RULES_DIR, max_age_days: int = 30) -> dict:
    """Load OWASP rules, triggering a background staleness check if the file is old."""
    owasp_file = rules_dir / "owasp_top10.json"
    if not owasp_file.exists():
        logger.warning("OWASP rules file not found at %s", owasp_file)
        return {}

    data = json.loads(owasp_file.read_text(encoding="utf-8"))

    fetched_at_str = data.get("meta", {}).get("fetched_at")
    if fetched_at_str:
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - fetched_at).days
            if age_days > max_age_days:
                logger.info("OWASP rules are %d days old — checking for updates.", age_days)
                _try_refresh(owasp_file, data)
        except (ValueError, TypeError):
            pass

    return data


def check_for_new_version(current_version: str) -> str | None:
    """Probe OWASP website for a newer Top 10 version.

    Tries each year from current+1 up to current+_YEAR_LOOKAHEAD.
    Returns the first year whose OWASP Top 10 page exists, or None.
    """
    try:
        current_year = int(current_version)
    except ValueError:
        return None

    for year in range(current_year + 1, current_year + _YEAR_LOOKAHEAD + 1):
        url = f"https://owasp.org/Top10/{year}/"
        if _url_exists(url):
            logger.info("Found new OWASP Top 10 version: %s", year)
            return str(year)

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _try_refresh(owasp_file: Path, data: dict) -> None:
    current_version = data.get("meta", {}).get("version", "2025")
    try:
        new_version = check_for_new_version(current_version)
    except Exception as exc:
        logger.warning("Could not check for OWASP updates: %s", exc)
        return

    if new_version:
        logger.warning(
            "New OWASP Top 10 version %s is available (current: %s). Run `python -m apps.agents.specialized.security.owasp_fetcher --update` to apply.",
            new_version,
            current_version,
        )
        return

    # Up to date — bump fetched_at so the check doesn't run again for another cycle.
    data.setdefault("meta", {})["fetched_at"] = datetime.now(timezone.utc).isoformat()
    owasp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("OWASP rules are up to date (version %s).", current_version)


def _fetch_and_apply_update(new_version: str, owasp_file: Path, sast_dir: Path) -> None:
    """Scrape categories for new_version from owasp.org and overwrite owasp_top10.json.

    Also rewrites SAST rule owasp IDs from old_version to new_version using
    the category ordering extracted from the new page.
    """
    url = f"https://owasp.org/Top10/{new_version}/"
    logger.info("Fetching OWASP Top 10 %s from %s", new_version, url)

    html = _http_get_text(url)
    categories = _parse_categories_from_html(html, new_version)

    if not categories:
        logger.warning(
            "Could not auto-parse OWASP %s categories from %s. Update rules/owasp_top10.json manually.",
            new_version,
            url,
        )

    existing = json.loads(owasp_file.read_text(encoding="utf-8")) if owasp_file.exists() else {}
    old_version = existing.get("meta", {}).get("version", "")
    existing_cats = {k: v for k, v in existing.items() if k != "meta"}
    merged = {**existing_cats, **categories}

    updated: dict = {
        "meta": {
            "version": new_version,
            "title": f"OWASP Top 10:{new_version}",
            "source_url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0",
        },
        **merged,
    }

    owasp_file.write_text(json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("owasp_top10.json updated to version %s.", new_version)

    if old_version and old_version != new_version and categories:
        id_map = _build_id_migration_map(existing_cats, categories, old_version, new_version)
        if id_map:
            _migrate_sast_owasp_refs(sast_dir, id_map, old_version, new_version)


def _parse_categories_from_html(html: str, version: str) -> dict:
    """Extract OWASP category IDs and names from the Top 10 page HTML."""
    categories: dict = {}

    # Match patterns like: A01:2025 - Broken Access Control
    pattern = re.compile(
        rf"(A\d{{2}}:{re.escape(version)})\s*[-–—:]\s*([A-Z][A-Za-z ,&/()]+?)(?:<|\"|\n|$)",
        re.MULTILINE,
    )
    for match in pattern.finditer(html):
        cat_id = match.group(1)
        name = match.group(2).strip().rstrip(" -–—,")
        if cat_id not in categories and len(name) > 2:
            categories[cat_id] = {
                "name": name,
                "severity_range": "HIGH-CRITICAL",
                "description": f"OWASP {cat_id}: {name}",
                "examples": [],
            }

    return categories


def _build_id_migration_map(
    old_cats: dict,
    new_cats: dict,
    old_version: str,
    new_version: str,
) -> dict[str, str]:
    """Build a mapping from old OWASP IDs to new ones by matching category names."""
    old_name_to_id = {v.get("name", "").lower(): k for k, v in old_cats.items()}
    id_map: dict[str, str] = {}

    for new_id, new_data in new_cats.items():
        name = new_data.get("name", "").lower()
        old_id = old_name_to_id.get(name)
        if old_id and old_id != new_id:
            id_map[old_id] = new_id

    return id_map


def _migrate_sast_owasp_refs(
    sast_dir: Path,
    id_map: dict[str, str],
    old_version: str,
    new_version: str,
) -> None:
    """Rewrite owasp fields in all SAST JSON files according to id_map."""
    if not sast_dir.exists():
        return

    for path in sorted(sast_dir.glob("sast_rules_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for rule in data.get("rules", []):
            old_id = rule.get("owasp", "")
            if old_id in id_map:
                rule["owasp"] = id_map[old_id]
                changed += 1
        if changed:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            logger.info(
                "%s: migrated %d OWASP ID(s) from %s to %s",
                path.name,
                changed,
                old_version,
                new_version,
            )


def _url_exists(url: str) -> bool:
    """Return True if url responds with 2xx, False on 404/other error."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "argus-security-agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status < 400
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        logger.debug("HTTP %s checking %s", exc.code, url)
        return False
    except urllib.error.URLError:
        return False


def _http_get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "argus-security-agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error fetching {url}: {exc.reason}") from exc


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = argv if argv is not None else sys.argv[1:]
    do_update = "--update" in args

    if not _OWASP_FILE.exists():
        logger.error("owasp_top10.json not found at %s", _OWASP_FILE)
        return 2

    data = json.loads(_OWASP_FILE.read_text(encoding="utf-8"))
    current_version = data.get("meta", {}).get("version", "2025")

    logger.info("Checking for OWASP updates (current: %s) ...", current_version)
    try:
        new_version = check_for_new_version(current_version)
    except Exception as exc:
        logger.error("Failed to reach owasp.org: %s", exc)
        return 2

    if new_version is None:
        data.setdefault("meta", {})["fetched_at"] = datetime.now(timezone.utc).isoformat()
        _OWASP_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("owasp_top10.json is already at the latest version (%s).", current_version)
        return 0

    logger.warning("New OWASP Top 10 version available: %s.", new_version)

    if not do_update:
        logger.info("Run with --update to apply the update to owasp_top10.json.")
        return 1

    try:
        _fetch_and_apply_update(new_version, _OWASP_FILE, _SAST_DIR)
        return 0
    except Exception as exc:
        logger.error("Failed to apply OWASP update: %s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
