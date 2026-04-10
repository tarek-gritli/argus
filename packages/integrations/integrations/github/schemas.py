from pydantic import BaseModel


class PullRequestPayload(BaseModel):
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    installation_id: int
    action: str
