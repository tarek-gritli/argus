from unittest.mock import MagicMock, patch


def _make_finding(agent: str) -> dict:
    return {
        "agent": agent,
        "severity": "high",
        "file": "src/auth.py",
        "line_start": 1,
        "line_end": 5,
        "title": f"{agent} issue",
        "description": "desc",
        "suggestion": "fix it",
        "confidence": 0.9,
        "fix": None,
    }


def test_review_local_publishes_findings_per_agent():
    from workers.local_review_task import run_local_review

    mock_redis = MagicMock()
    security_finding = _make_finding("security")
    quality_finding = _make_finding("quality")

    with (
        patch("workers.local_review_task._get_redis", return_value=mock_redis),
        patch("workers.local_review_task.security_analyze", return_value=[MagicMock(model_dump=lambda: security_finding)]),
        patch("workers.local_review_task.quality_analyze", return_value=[MagicMock(model_dump=lambda: quality_finding)]),
        patch("workers.local_review_task.testing_analyze", return_value=[]),
    ):
        run_local_review(job_id="job123", diff="+ code", files=None)

    published_calls = mock_redis.publish.call_args_list
    channels = [c[0][0] for c in published_calls]
    assert all(ch == "local_review:job123" for ch in channels)

    import json

    payloads = [json.loads(c[0][1]) for c in published_calls]
    event_types = [p["event"] for p in payloads]
    assert "finding" in event_types
    assert "done" in event_types


def test_review_local_publishes_done_on_empty_findings():
    from workers.local_review_task import run_local_review

    mock_redis = MagicMock()

    with (
        patch("workers.local_review_task._get_redis", return_value=mock_redis),
        patch("workers.local_review_task.security_analyze", return_value=[]),
        patch("workers.local_review_task.quality_analyze", return_value=[]),
        patch("workers.local_review_task.testing_analyze", return_value=[]),
    ):
        run_local_review(job_id="job456", diff="+ code", files=None)

    import json

    payloads = [json.loads(c[0][1]) for c in mock_redis.publish.call_args_list]
    assert payloads[-1]["event"] == "done"


def test_review_local_one_agent_exception_still_publishes_done():
    """A single agent failure is logged and skipped; review still completes."""
    from workers.local_review_task import run_local_review

    mock_redis = MagicMock()

    with (
        patch("workers.local_review_task._get_redis", return_value=mock_redis),
        patch("workers.local_review_task.security_analyze", side_effect=RuntimeError("boom")),
        patch("workers.local_review_task.quality_analyze", return_value=[]),
        patch("workers.local_review_task.testing_analyze", return_value=[]),
    ):
        run_local_review(job_id="job789", diff="+ code", files=None)

    import json

    payloads = [json.loads(c[0][1]) for c in mock_redis.publish.call_args_list]
    assert payloads[-1]["event"] == "done"


def test_review_local_publishes_error_on_outer_exception():
    """A failure outside the agent loop (e.g. first Redis setex) publishes error."""
    from workers.local_review_task import run_local_review

    mock_redis = MagicMock()
    # First setex (result key) raises; second setex (status key in error handler) succeeds
    mock_redis.setex.side_effect = [RuntimeError("redis down"), None]

    with (
        patch("workers.local_review_task._get_redis", return_value=mock_redis),
        patch("workers.local_review_task.security_analyze", return_value=[]),
        patch("workers.local_review_task.quality_analyze", return_value=[]),
        patch("workers.local_review_task.testing_analyze", return_value=[]),
    ):
        run_local_review(job_id="job999", diff="+ code", files=None)

    import json

    payloads = [json.loads(c[0][1]) for c in mock_redis.publish.call_args_list]
    assert any(p["event"] == "error" for p in payloads)
