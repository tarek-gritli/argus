from unittest.mock import AsyncMock, patch


def test_index_repo_task_calls_embed():
    files = [
        {"filename": "app/auth.py", "content": "import os\ndef login(): pass\n"},
        {"filename": "app/models.py", "content": "class User: pass\n"},
    ]

    with (
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock) as mock_embed,
        patch("workers.index_task.get_repo_files", return_value=files),
    ):
        from workers.index_task import index_repo_task

        index_repo_task(
            repo_id="repo_abc",
            installation_id=123,
            repo_full_name="acme/api",
            ref="main",
        )

    assert mock_embed.call_count == 1


def test_index_repo_task_skips_non_code_files():
    files = [
        {"filename": "README.md", "content": "# docs\n"},
        {"filename": "app/auth.py", "content": "def login(): pass\n"},
    ]

    with (
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock) as mock_embed,
        patch("workers.index_task.get_repo_files", return_value=files),
    ):
        from workers.index_task import index_repo_task

        index_repo_task(
            repo_id="repo_abc",
            installation_id=123,
            repo_full_name="acme/api",
            ref="main",
        )

    calls = mock_embed.call_args_list
    all_chunk_filepaths = [c.filepath for call in calls for c in call[0][1]]
    assert "README.md" not in all_chunk_filepaths


def test_index_repo_task_is_resilient_to_partial_failure():
    files = [{"filename": "app/auth.py", "content": "import os\n"}]

    with (
        patch("workers.index_task.embed_chunks", new_callable=AsyncMock, side_effect=Exception("Qdrant down")),
        patch("workers.index_task.get_repo_files", return_value=files),
    ):
        from workers.index_task import index_repo_task

        # Must not raise — indexing failure is non-fatal
        index_repo_task(
            repo_id="repo_abc",
            installation_id=123,
            repo_full_name="acme/api",
            ref="main",
        )
