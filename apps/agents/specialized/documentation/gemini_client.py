"""Shared Gemini client with automatic retry on per-minute rate limits."""

from __future__ import annotations

import logging
import re
import time

from google import genai
from google.genai.errors import ClientError
from shared.config import get_settings

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.0-flash"
_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY = 15  # seconds — used when response doesn't include retryDelay


def _status_code(exc: ClientError) -> int:
    """ClientError(status_code, response_json, response) — status is args[0]."""
    try:
        return int(exc.args[0])
    except Exception:
        return 0


def _response_body(exc: ClientError) -> dict:
    """ClientError(status_code, response_json, response) — body dict is args[1]."""
    try:
        body = exc.args[1]
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


def _extract_retry_delay(exc: ClientError) -> float | None:
    """Pull the retryDelay seconds from the 429 error details, if present."""
    try:
        body = _response_body(exc)
        for item in body.get("error", {}).get("details", []):
            if item.get("@type", "").endswith("RetryInfo"):
                delay_str = item.get("retryDelay", "")
                m = re.match(r"([\d.]+)", delay_str)
                if m:
                    return float(m.group(1)) + 1  # +1s buffer
    except Exception:
        pass
    return None


def _is_daily_quota_exhausted(exc: ClientError) -> bool:
    """Return True if the per-day quota is exhausted (retry won't help today)."""
    try:
        body = _response_body(exc)
        for item in body.get("error", {}).get("details", []):
            for v in item.get("violations", []):
                if "PerDay" in v.get("quotaId", ""):
                    return True
    except Exception:
        pass
    return False


def call_gemini(system: str, user: str, fallback: str = "[]") -> str:
    """Call Gemini with automatic retry on transient per-minute rate limits.

    Returns `fallback` when:
    - GEMINI_API_KEY is not configured
    - Daily quota is exhausted (retrying won't help)
    - All retries are consumed
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — skipping Gemini call.")
        return fallback

    contents = f"{system}\n\n{user}"

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(model=_MODEL, contents=contents)
            return response.text or fallback
        except ClientError as exc:
            if _status_code(exc) != 429:
                logger.warning("Gemini ClientError (non-rate-limit): %s", exc)
                return fallback

            if _is_daily_quota_exhausted(exc):
                logger.warning("Gemini daily quota exhausted — get a new API key at aistudio.google.com")
                return fallback

            delay = _extract_retry_delay(exc) or _DEFAULT_RETRY_DELAY
            if attempt < _MAX_RETRIES:
                logger.info(
                    "Gemini rate limited (attempt %d/%d) — retrying in %.0fs",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.warning("Gemini rate limited — all retries consumed, skipping.")
                return fallback
        except Exception as exc:
            logger.warning("Gemini call failed: %s", exc)
            return fallback

    return fallback
