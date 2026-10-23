from unittest.mock import AsyncMock, MagicMock, patch


def _make_redis(latest_ref: str = "main") -> MagicMock:
    r = MagicMock()
    r.get.return_value = latest_ref
    return r


def _redis_patch(latest_ref: str = "main"):
    r = _make_redis(latest_ref)
    return patch("workers.index_task.redis_client", r), r


def test_index_repo_task_calls_embed():
    files = [
        {"filename": "app/auth.py", "content": "import os\ndef login(): pass\n"},
        {"filename": "app/models.py", "content": "class User: pass\n"},
    ]
    redis_ctx, _ = _redis_patch()

    with (
        redis_ctx,
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock) as mock_embed,
        patch("workers.index_task.get_repo_files", return_value=files),
    ):
        from workers.index_task import index_repo_task

        index_repo_task(repo_id="repo_abc", installation_id=123, repo_full_name="acme/api")

    assert mock_embed.call_count == 1


def test_index_repo_task_skips_non_code_files():
    files = [
        {"filename": "README.md", "content": "# docs\n"},
        {"filename": "app/auth.py", "content": "def login(): pass\n"},
    ]
    redis_ctx, _ = _redis_patch()

    with (
        redis_ctx,
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock) as mock_embed,
        patch("workers.index_task.get_repo_files", return_value=files),
    ):
        from workers.index_task import index_repo_task

        index_repo_task(repo_id="repo_abc", installation_id=123, repo_full_name="acme/api")

    calls = mock_embed.call_args_list
    all_chunk_filepaths = [c.filepath for call in calls for c in call[0][1]]
    assert "README.md" not in all_chunk_filepaths


def test_index_repo_task_is_resilient_to_partial_failure():
    files = [{"filename": "app/auth.py", "content": "import os\n"}]
    redis_ctx, _ = _redis_patch()

    with (
        redis_ctx,
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock, side_effect=Exception("Qdrant down")),
        patch("workers.index_task.get_repo_files", return_value=files),
    ):
        from workers.index_task import index_repo_task

        index_repo_task(repo_id="repo_abc", installation_id=123, repo_full_name="acme/api")


def test_uses_latest_ref_from_redis():
    """Task reads index:latest from Redis — indexes the newest commit, not the one it was scheduled with."""
    files = [{"filename": "app/auth.py", "content": "def f(): pass\n"}]
    redis_ctx, _ = _redis_patch(latest_ref="sha-CCC")

    with (
        redis_ctx,
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock),
        patch("workers.index_task.get_repo_files", return_value=files) as mock_files,
    ):
        from workers.index_task import index_repo_task

        index_repo_task(repo_id="repo_abc", installation_id=123, repo_full_name="acme/api")

    mock_files.assert_called_once_with("acme/api", 123, "sha-CCC")


def test_falls_back_to_ref_when_latest_key_missing():
    """If index:latest has expired, falls back to the ref passed to the task."""
    files = [{"filename": "app/auth.py", "content": "def f(): pass\n"}]
    r = MagicMock()
    r.get.return_value = None  # key expired

    with (
        patch("workers.index_task.redis_client", r),
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock),
        patch("workers.index_task.get_repo_files", return_value=files) as mock_files,
    ):
        from workers.index_task import index_repo_task

        index_repo_task(repo_id="repo_abc", installation_id=123, repo_full_name="acme/api", ref="sha-fallback")

    mock_files.assert_called_once_with("acme/api", 123, "sha-fallback")


# Connection lifecycle tests


def test_init_connections_creates_redis_client():
    mock_redis = MagicMock()
    with patch("workers.connections.redis_lib.Redis.from_url", return_value=mock_redis) as mock_from_url:
        import workers.connections as conns

        conns.redis_client = None
        conns.init_connections()

    mock_from_url.assert_called_once()
    assert conns.redis_client is mock_redis


def test_close_connections_closes_and_clears_client():
    mock_redis = MagicMock()

    import workers.connections as conns

    conns.redis_client = mock_redis
    conns.close_connections()

    mock_redis.close.assert_called_once()
    assert conns.redis_client is None


def test_worker_init_bootstraps_connections():
    with patch("workers.connections.init_connections") as mock_init:
        from workers.celery_app import on_worker_init

        on_worker_init()

    mock_init.assert_called_once()


def test_index_repo_task_reads_gitlab_project_with_org_credentials():
    r_patch, _ = _redis_patch()
    files = [{"filename": "app/main.py", "content": "def f():\n    return 1\n"}]
    gl = MagicMock()

    with (
        r_patch,
        patch("workers.index_task.run_async", side_effect=lambda coro: ("https://git.corp.io", "glpat")) as run_async,
        patch("workers.index_task.load_gitlab_credentials", new=MagicMock(return_value=None)) as load_creds,
        patch("workers.index_task.get_gitlab_client", return_value=gl) as get_client,
        patch("workers.index_task.get_gitlab_repo_files", return_value=files) as gl_files,
        patch("workers.index_task.get_repo_files") as gh_files,
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock) as mock_embed,
    ):
        from workers.index_task import index_repo_task

        index_repo_task(repo_id="repo_gl", repo_full_name="group/proj", ref="main", integration_id="int-1", org_id="org-1", project_id=7)

    run_async.assert_called_once()
    load_creds.assert_called_once_with("org-1", "int-1")
    get_client.assert_called_once_with("https://git.corp.io", "glpat")
    gl_files.assert_called_once_with(gl, 7, "main")
    gh_files.assert_not_called()
    mock_embed.assert_awaited_once()
