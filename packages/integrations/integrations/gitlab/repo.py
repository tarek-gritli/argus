import gitlab

from integrations.code_extensions import CODE_EXTENSIONS


def get_repo_files(gl: gitlab.Gitlab, project_id: int, ref: str = "main") -> list[dict]:
    """Fetch all indexable source files from a GitLab project at a given ref."""
    project = gl.projects.get(project_id)
    files = []
    for item in project.repository_tree(ref=ref, recursive=True, iterator=True):
        path: str = item["path"]
        if item["type"] != "blob" or ("." + path.rsplit(".", 1)[-1] if "." in path else "") not in CODE_EXTENSIONS:
            continue
        try:
            raw = project.repository_raw_blob(item["id"])
        except gitlab.exceptions.GitlabError:
            continue
        files.append({"filename": path, "content": raw.decode("utf-8", errors="replace")})
    return files
