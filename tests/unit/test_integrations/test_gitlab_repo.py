from unittest.mock import MagicMock

from gitlab.exceptions import GitlabGetError
from integrations.gitlab import get_repo_files


def _gl(tree, blobs):
    gl = MagicMock()
    project = gl.projects.get.return_value
    project.repository_tree.return_value = iter(tree)
    project.repository_raw_blob.side_effect = lambda sha: blobs[sha]
    return gl, project


def test_returns_decoded_code_files_only():
    tree = [
        {"id": "a", "type": "blob", "path": "src/app.py"},
        {"id": "b", "type": "blob", "path": "README.md"},
        {"id": "c", "type": "tree", "path": "src"},
        {"id": "d", "type": "blob", "path": "web/index.ts"},
        {"id": "e", "type": "blob", "path": "Makefile"},
    ]
    gl, project = _gl(tree, {"a": b"print(1)\n", "d": b"export {}\n"})

    files = get_repo_files(gl, 7, "main")

    assert files == [
        {"filename": "src/app.py", "content": "print(1)\n"},
        {"filename": "web/index.ts", "content": "export {}\n"},
    ]
    gl.projects.get.assert_called_once_with(7)
    project.repository_tree.assert_called_once_with(ref="main", recursive=True, iterator=True)


def test_skips_blobs_that_fail_to_download_and_tolerates_bad_bytes():
    tree = [{"id": "a", "type": "blob", "path": "a.py"}, {"id": "b", "type": "blob", "path": "b.py"}]
    gl, project = _gl(tree, {"b": b"ok \xff"})
    project.repository_raw_blob.side_effect = lambda sha: (_ for _ in ()).throw(GitlabGetError("gone", 404)) if sha == "a" else b"ok \xff"

    files = get_repo_files(gl, 1, "main")

    assert [f["filename"] for f in files] == ["b.py"]
    assert files[0]["content"].startswith("ok ")
