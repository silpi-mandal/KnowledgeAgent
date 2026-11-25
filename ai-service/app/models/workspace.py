from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=300)


class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    description: str = ""
    document_count: int = 0
