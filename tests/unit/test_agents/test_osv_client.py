"""
Unit tests for osv_client pure functions — no network calls, no I/O.
"""

from specialized.security import osv_client as osv
from specialized.security.schemas import Severity

# ---------------------------------------------------------------------------
# _cvss3_score
# ---------------------------------------------------------------------------


def test_cvss3_critical_score():
    # CVE-2021-44228 Log4Shell vector
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
    score = osv._cvss3_score(vector)
    assert score == 10.0


def test_cvss3_high_score():
    # HIGH — network, low complexity, low privileges required, C:H/I:H/A:N → 8.1
    vector = "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N"
    score = osv._cvss3_score(vector)
    assert score is not None
    assert 7.0 <= score < 9.0


def test_cvss3_medium_score():
    # Medium — requires user interaction, low impact
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N"
    score = osv._cvss3_score(vector)
    assert score is not None
    assert 4.0 <= score < 7.0


def test_cvss3_zero_impact():
    # All impacts None → score 0
    vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N"
    score = osv._cvss3_score(vector)
    assert score == 0.0


def test_cvss3_invalid_vector_returns_none():
    assert osv._cvss3_score("not-a-vector") is None
    assert osv._cvss3_score("") is None
    assert osv._cvss3_score("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") is None


# ---------------------------------------------------------------------------
# _cvss_to_severity
# ---------------------------------------------------------------------------


def test_cvss_to_severity_bands():
    assert osv._cvss_to_severity(9.8) == Severity.CRITICAL
    assert osv._cvss_to_severity(9.0) == Severity.CRITICAL
    assert osv._cvss_to_severity(8.9) == Severity.HIGH
    assert osv._cvss_to_severity(7.0) == Severity.HIGH
    assert osv._cvss_to_severity(6.9) == Severity.MEDIUM
    assert osv._cvss_to_severity(4.0) == Severity.MEDIUM
    assert osv._cvss_to_severity(3.9) == Severity.LOW
    assert osv._cvss_to_severity(0.0) == Severity.LOW


# ---------------------------------------------------------------------------
# _extract_cve_id
# ---------------------------------------------------------------------------


def test_extract_cve_id_from_id_field():
    vuln = {"id": "CVE-2019-10906", "aliases": []}
    assert osv._extract_cve_id(vuln) == "CVE-2019-10906"


def test_extract_cve_id_from_aliases():
    vuln = {"id": "GHSA-abc-def-1234", "aliases": ["CVE-2020-8203"]}
    assert osv._extract_cve_id(vuln) == "CVE-2020-8203"


def test_extract_cve_id_falls_back_to_ghsa():
    vuln = {"id": "GHSA-abc-def-1234", "aliases": []}
    assert osv._extract_cve_id(vuln) == "GHSA-abc-def-1234"


# ---------------------------------------------------------------------------
# _extract_fix_version
# ---------------------------------------------------------------------------


def test_extract_fix_version_ecosystem_range():
    vuln = {
        "affected": [
            {
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "0"}, {"fixed": "2.10.1"}],
                    }
                ]
            }
        ]
    }
    assert osv._extract_fix_version(vuln) == "2.10.1"


def test_extract_fix_version_no_ranges():
    vuln = {"affected": [{"ranges": []}]}
    assert osv._extract_fix_version(vuln) is None


def test_extract_fix_version_git_range_skipped():
    # GIT-type ranges should not be returned (we only want ECOSYSTEM)
    vuln = {
        "affected": [
            {
                "ranges": [
                    {
                        "type": "GIT",
                        "events": [{"introduced": "abc123"}, {"fixed": "def456"}],
                    }
                ]
            }
        ]
    }
    assert osv._extract_fix_version(vuln) is None


# ---------------------------------------------------------------------------
# _extract_severity
# ---------------------------------------------------------------------------


def test_extract_severity_from_cvss_vector():
    vuln = {"severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"}]}
    severity, score = osv._extract_severity(vuln)
    assert severity == Severity.CRITICAL
    assert score == 10.0


def test_extract_severity_from_database_specific_level():
    vuln = {"severity": [], "database_specific": {"severity": "HIGH"}}
    severity, score = osv._extract_severity(vuln)
    assert severity == Severity.HIGH
    assert score == 7.5


def test_extract_severity_moderate_maps_to_medium():
    vuln = {"severity": [], "database_specific": {"severity": "MODERATE"}}
    severity, score = osv._extract_severity(vuln)
    assert severity == Severity.MEDIUM


def test_extract_severity_default_when_missing():
    vuln = {}
    severity, score = osv._extract_severity(vuln)
    assert severity == Severity.HIGH  # conservative default
    assert score == 7.5


# ---------------------------------------------------------------------------
# _is_fresh / _cache_key
# ---------------------------------------------------------------------------


def test_cache_key_format():
    assert osv._cache_key("jinja2", "2.10", "PyPI") == "jinja2@2.10@PyPI"


def test_is_fresh_recent_entry():
    from datetime import datetime, timezone

    entry = {"cached_at": datetime.now(timezone.utc).isoformat()}
    assert osv._is_fresh(entry) is True


def test_is_fresh_old_entry():
    entry = {"cached_at": "2020-01-01T00:00:00+00:00"}
    assert osv._is_fresh(entry) is False


def test_is_fresh_missing_key():
    assert osv._is_fresh({}) is False
