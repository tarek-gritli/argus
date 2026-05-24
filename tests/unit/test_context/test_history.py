from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from context.history import get_rejected_finding_keys, suppress_duplicate_findings
from shared.schemas import FindingSchema


def _finding(title: str = "SQL Injection", file: str = "app.py") -> FindingSchema:
    return FindingSchema(
        agent="security",
        severity="high",
        file=file,
        line_start=1,
        line_end=5,
        title=title,
        description="desc",
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_get_rejected_keys_queries_db():
    mock_result = MagicMock()
    mock_result.all.return_value = [MagicMock(file="app.py", title="SQL Injection")]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("context.history.fresh_session_context", return_value=mock_cm):
        keys = await get_rejected_finding_keys(org_id="org_1", repo_id="repo_abc", lookback_days=30)

    assert ("app.py", "SQL Injection") in keys


@pytest.mark.asyncio
async def test_get_rejected_keys_scoped_by_repo():
    """Rejected findings from a different repo must not bleed into another repo's suppression set."""
    mock_result = MagicMock()
    mock_result.all.return_value = []  # repo_xyz has no rejections

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("context.history.fresh_session_context", return_value=mock_cm):
        keys = await get_rejected_finding_keys(org_id="org_1", repo_id="repo_xyz", lookback_days=30)

    assert ("app.py", "SQL Injection") not in keys
    assert keys == set()


def test_suppress_duplicate_findings_removes_rejected():
    findings = [_finding("SQL Injection", "app.py"), _finding("XSS", "views.py")]
    rejected = {("app.py", "SQL Injection")}

    result = suppress_duplicate_findings(findings, rejected)

    assert len(result) == 1
    assert result[0].title == "XSS"


def test_suppress_duplicate_findings_keeps_all_if_no_rejected():
    findings = [_finding("SQL Injection"), _finding("XSS")]
    result = suppress_duplicate_findings(findings, set())
    assert len(result) == 2
