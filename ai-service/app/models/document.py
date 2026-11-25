from pydantic import BaseModel

class DocumentResponse(BaseModel):
    document_id: str
    document_name: str
    workspace_id: str = "general"
