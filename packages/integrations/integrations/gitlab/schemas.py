from pydantic import BaseModel


class MergeRequestPayload(BaseModel):
    project_id: int
    mr_iid: int
    head_sha: str
    base_sha: str
    action: str
