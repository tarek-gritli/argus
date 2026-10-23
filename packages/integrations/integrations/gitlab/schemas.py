from pydantic import BaseModel


class MergeRequestPayload(BaseModel):
    project_id: int
    project_path: str
    mr_iid: int
    head_sha: str
    base_sha: str
    action: str
    org_id: str = ""
    integration_id: str = ""
