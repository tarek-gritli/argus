import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from context.bundle import ContextBundle
from shared.schemas import FindingSchema


def _patch_run_async():
    """Patch run_async so tests don't need a live event loop."""
    return patch("orchestrator.coordinator.run_async", side_effect=lambda coro: asyncio.run(coro))


VALID_PAYLOAD = {
    "action": "opened",
    "repo_full_name": "owner/repo",
    "pr_number": 123,
    "head_sha": "abc123",
    "base_sha": "base456",
    "installation_id": 42,
}

SAMPLE_FINDING = FindingSchema(
    agent="security",
    severity="high",
    file="src/auth.py",
    line_start=10,
    line_end=15,
    title="SQL Injection",
    description="User input not sanitized.",
    suggestion="Use parameterized queries.",
    confidence=0.95,
)


def _vcs(files=None, diff="+ some diff", platform="github"):
    """Patch the coordinator's provider factory with a fake provider; returns (patcher, provider)."""
    from orchestrator.vcs import UnifiedPayload

    provider = MagicMock()
    provider.title = "title"
    provider.body = "body"
    provider.url = "https://example.test/pr/1"
    provider.get_files.return_value = _make_mock_files() if files is None else files
    provider.get_diff.return_value = diff
    provider.get_file_content.return_value = "code"

    def factory(payload):
        unified = UnifiedPayload(
            platform=platform,
            repo_id=payload.get("repo_full_name") or payload.get("project_path", ""),
            pr_id=payload.get("pr_number") or payload.get("mr_iid", 0),
            head_sha=payload["head_sha"],
            base_sha=payload["base_sha"],
            org_id=payload.get("org_id", ""),
            installation_id=payload.get("installation_id", 0),
        )
        return provider, unified

    return patch("orchestrator.coordinator.get_vcs_provider", side_effect=factory), provider


def _pipeline(**overrides):
    """The patches every full-run test needs, as a list for ExitStack."""
    patches = {
        "orchestrator.coordinator._already_reviewed": AsyncMock(return_value=False),
        "orchestrator.coordinator._check_quota": AsyncMock(return_value=(True, "pro")),
        "orchestrator.coordinator._get_repo_id_for_run": AsyncMock(return_value="repo_abc"),
        "orchestrator.coordinator._fetch_context": AsyncMock(return_value=ContextBundle.empty()),
        "orchestrator.coordinator.get_rejected_finding_keys": AsyncMock(return_value=set()),
        "orchestrator.coordinator.run_review": MagicMock(return_value=[SAMPLE_FINDING]),
        "orchestrator.coordinator.run_fix_pipeline": MagicMock(return_value=[SAMPLE_FINDING]),
        "orchestrator.coordinator._persist": AsyncMock(),
        "orchestrator.coordinator._notify": AsyncMock(),
    }
    patches.update(overrides)
    return patches


def _run(payload, vcs_patch, **overrides):
    """Run the coordinator with the standard patches; returns the dict of mocks used."""
    from contextlib import ExitStack

    mocks = _pipeline(**overrides)
    with ExitStack() as stack:
        stack.enter_context(_patch_run_async())
        stack.enter_context(vcs_patch)
        for target, mock in mocks.items():
            stack.enter_context(patch(target, new=mock))
        from orchestrator.coordinator import run

        run(payload)
    return mocks


def _make_mock_files(n: int = 2):
    files = []
    for i in range(n):
        f = MagicMock()
        f.filename = f"src/file{i}.py"
        f.patch = f"@@ -1 +1 @@ +code{i}"
        files.append(f)
    return files


def test_run_happy_path_posts_findings():
    """Coordinator fetches files, runs analysis, posts comment."""
    vcs, provider = _vcs()
    _run(VALID_PAYLOAD, vcs)

    provider.post_issue_comment.assert_called_once()
    body = provider.post_issue_comment.call_args[0][0]
    assert "SQL Injection" in body
    assert "HIGH" in body or "high" in body.lower()


def test_run_no_files_posts_warning():
    """Empty file list posts a warning comment and skips analysis."""
    vcs, provider = _vcs(files=[])
    mocks = _run(VALID_PAYLOAD, vcs)

    mocks["orchestrator.coordinator.run_review"].assert_not_called()
    provider.post_issue_comment.assert_called_once()
    assert "No changes detected" in provider.post_issue_comment.call_args[0][0]


def test_run_no_findings_posts_clean_message():
    """No findings from analysis posts a clean bill of health."""
    vcs, provider = _vcs(diff="")
    _run(
        VALID_PAYLOAD,
        vcs,
        **{
            "orchestrator.coordinator.run_review": MagicMock(return_value=[]),
            "orchestrator.coordinator.run_fix_pipeline": MagicMock(return_value=[]),
        },
    )

    assert "no issues" in provider.post_issue_comment.call_args[0][0]


def test_run_raises_when_provider_cannot_be_built():
    """If the provider can't be resolved (e.g. GitHub API down), the exception propagates."""
    with patch("orchestrator.coordinator.get_vcs_provider", side_effect=Exception("GitHub API down")):
        from orchestrator.coordinator import run

        with pytest.raises(Exception, match="GitHub API down"):
            run(VALID_PAYLOAD)


def test_format_findings_groups_by_severity():
    """_format_findings groups and orders findings correctly."""
    findings = [
        FindingSchema(
            agent="security",
            severity="low",
            file="a.py",
            line_start=1,
            line_end=2,
            title="Minor issue",
            description="Low severity.",
            confidence=0.5,
        ),
        FindingSchema(
            agent="security",
            severity="critical",
            file="b.py",
            line_start=5,
            line_end=10,
            title="Critical bug",
            description="Very bad.",
            confidence=0.99,
        ),
    ]

    from orchestrator.formatter import format_findings

    result = format_findings(findings)

    assert result.index("CRITICAL") < result.index("LOW")
    assert "Critical bug" in result
    assert "Minor issue" in result


def test_format_findings_includes_suggestion():
    """_format_findings includes suggestion when present."""
    finding = FindingSchema(
        agent="security",
        severity="high",
        file="c.py",
        line_start=1,
        line_end=1,
        title="XSS",
        description="Unescaped output.",
        suggestion="Escape HTML.",
        confidence=0.8,
    )

    from orchestrator.formatter import format_findings

    result = format_findings([finding])

    assert "Escape HTML." in result


def test_format_findings_empty_returns_clean():
    """Empty findings list returns clean message."""
    from orchestrator.formatter import format_findings

    result = format_findings([])
    assert "no issues" in result


def test_run_persists_review_and_findings_when_org_id_present():
    """When org_id is in payload, coordinator should persist Review + Findings to DB."""
    vcs, _ = _vcs()
    mocks = _run({**VALID_PAYLOAD, "org_id": "org-123"}, vcs)

    mocks["orchestrator.coordinator._persist"].assert_called_once()
    assert mocks["orchestrator.coordinator.run_review"].call_args.kwargs["plan"] == "pro"


def test_quota_exceeded_posts_comment_and_returns():
    vcs, provider = _vcs()
    mocks = _run(
        {**VALID_PAYLOAD, "org_id": "o1"},
        vcs,
        **{"orchestrator.coordinator._check_quota": AsyncMock(return_value=(False, "free"))},
    )

    mocks["orchestrator.coordinator.run_review"].assert_not_called()
    provider.post_issue_comment.assert_called_once()
    assert "quota" in provider.post_issue_comment.call_args[0][0].lower()


def test_run_skips_review_when_head_sha_already_reviewed():
    """Coordinator skips analysis entirely if head_sha was already reviewed."""
    vcs, provider = _vcs()
    mocks = _run(
        {**VALID_PAYLOAD, "org_id": "org-1"},
        vcs,
        **{"orchestrator.coordinator._already_reviewed": AsyncMock(return_value=True)},
    )

    mocks["orchestrator.coordinator.run_review"].assert_not_called()
    provider.post_issue_comment.assert_not_called()


def test_run_proceeds_when_head_sha_not_yet_reviewed():
    """Coordinator runs full review when head_sha has no completed review."""
    vcs, provider = _vcs()
    _run({**VALID_PAYLOAD, "org_id": "org-1"}, vcs)

    provider.post_issue_comment.assert_called_once()


def test_notify_called_for_team_plan_not_pro():
    """_notify is invoked for team plan but not for pro."""
    vcs, _ = _vcs()
    team = _run(
        {**VALID_PAYLOAD, "org_id": "org-1"},
        vcs,
        **{"orchestrator.coordinator._check_quota": AsyncMock(return_value=(True, "team"))},
    )
    team["orchestrator.coordinator._notify"].assert_called_once()

    vcs, _ = _vcs()
    pro = _run({**VALID_PAYLOAD, "org_id": "org-1"}, vcs)
    pro["orchestrator.coordinator._notify"].assert_not_called()


def test_run_skips_persist_when_no_org_id():
    """When org_id is absent, coordinator skips DB writes."""
    vcs, _ = _vcs()
    with patch("orchestrator.coordinator.get_session_factory") as mock_sf:
        _run(VALID_PAYLOAD, vcs)

    mock_sf.assert_not_called()


def test_run_posts_summary_even_if_inline_review_fails():
    """The summary comment should still be posted if inline review creation fails."""
    vcs, provider = _vcs()
    provider.post_findings_as_review.side_effect = RuntimeError("review failed")
    _run({**VALID_PAYLOAD, "org_id": "org-1"}, vcs)

    assert provider.post_issue_comment.call_count == 1


def test_run_updates_description_when_generated():
    vcs, provider = _vcs()
    _run(VALID_PAYLOAD, vcs)
    with patch("orchestrator.coordinator.generate_pr_description", return_value="new body"):
        vcs, provider = _vcs()
        _run(VALID_PAYLOAD, vcs)
    provider.update_description.assert_called_once_with("new body")


GITLAB_PAYLOAD = {
    "platform": "gitlab",
    "project_id": 7,
    "project_path": "group/proj",
    "mr_iid": 3,
    "head_sha": "abc123",
    "base_sha": "base456",
    "action": "opened",
    "org_id": "org-gl",
    "integration_id": "int-1",
}


def test_run_gitlab_mr_uses_same_pipeline_and_notifies_with_provider_url():
    vcs, provider = _vcs(platform="gitlab")
    mocks = _run(
        GITLAB_PAYLOAD,
        vcs,
        **{"orchestrator.coordinator._check_quota": AsyncMock(return_value=(True, "team"))},
    )

    provider.post_issue_comment.assert_called_once()
    persisted = mocks["orchestrator.coordinator._persist"].call_args.kwargs["pr_payload"]
    assert (persisted.platform, persisted.repo_id, persisted.pr_id) == ("gitlab", "group/proj", 3)
    assert mocks["orchestrator.coordinator._notify"].call_args.kwargs["provider"] is provider


def test_repo_query_keys_github_by_installation_and_gitlab_by_org():
    from orchestrator.coordinator import _repo_query
    from orchestrator.vcs import UnifiedPayload

    gh = str(_repo_query(UnifiedPayload("github", "o/r", 1, "h", "b", org_id="o1", installation_id=42)).whereclause)
    gl = str(_repo_query(UnifiedPayload("gitlab", "g/p", 1, "h", "b", org_id="o1")).whereclause)

    assert "installation_id" in gh and "provider" not in gh
    assert "repos.org_id" in gl and "repos.provider" in gl and "installation_id" not in gl
