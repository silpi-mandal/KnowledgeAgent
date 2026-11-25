from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_current_user, require_admin

from app.models.document import DocumentResponse
from app.models.workspace import WorkspaceCreate, WorkspaceResponse
from app.services import workspace_service as service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    user: CurrentUser = Depends(get_current_user),
) -> list[WorkspaceResponse]:
    return [
        WorkspaceResponse(**item)
        for item in service.list_workspaces()
        if user.can_access_workspace(item["workspace_id"])
    ]


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(
    payload: WorkspaceCreate,
    _: CurrentUser = Depends(require_admin),
) -> WorkspaceResponse:
    try:
        return WorkspaceResponse(
            **service.create_workspace(payload.name, payload.description)
        )
    except service.WorkspaceExistsError:
        raise HTTPException(status_code=409, detail="Workspace already exists.") from None


@router.get("/{workspace_id}/documents", response_model=list[DocumentResponse])
def list_workspace_documents(
    workspace_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> list[DocumentResponse]:
    try:
        service.ensure_workspace_exists(workspace_id)
    except service.WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found.") from None

    if not user.can_access_workspace(workspace_id):
        # same answer as "missing" so workspace names cannot be probed
        raise HTTPException(status_code=404, detail="Workspace not found.")

    return [
        DocumentResponse(
            **{**doc, "workspace_id": service.document_workspace(doc)}
        )
        for doc in service.list_workspace_documents(workspace_id)
    ]


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: str,
    _: CurrentUser = Depends(require_admin),
) -> None:
    try:
        service.delete_workspace(workspace_id)
    except service.WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
