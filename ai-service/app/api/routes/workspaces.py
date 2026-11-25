from fastapi import APIRouter, HTTPException

from app.models.document import DocumentResponse
from app.models.workspace import WorkspaceCreate, WorkspaceResponse
from app.services import workspace_service as service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces() -> list[WorkspaceResponse]:
    return [WorkspaceResponse(**item) for item in service.list_workspaces()]


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(payload: WorkspaceCreate) -> WorkspaceResponse:
    try:
        return WorkspaceResponse(
            **service.create_workspace(payload.name, payload.description)
        )
    except service.WorkspaceExistsError:
        raise HTTPException(status_code=409, detail="Workspace already exists.") from None


@router.get("/{workspace_id}/documents", response_model=list[DocumentResponse])
def list_workspace_documents(workspace_id: str) -> list[DocumentResponse]:
    try:
        service.ensure_workspace_exists(workspace_id)
    except service.WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found.") from None

    return [
        DocumentResponse(
            **{**doc, "workspace_id": service.document_workspace(doc)}
        )
        for doc in service.list_workspace_documents(workspace_id)
    ]


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: str) -> None:
    try:
        service.delete_workspace(workspace_id)
    except service.WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
