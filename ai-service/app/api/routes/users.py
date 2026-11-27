from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, require_admin
from app.models.auth import (
    PasswordReset,
    UserCreate,
    UserResponse,
    WorkspaceAccessUpdate,
)
from app.services import auth_service, workspace_service

router = APIRouter(prefix="/users", tags=["users"])


def _check_workspaces(workspace_ids: list[str]) -> None:
    for workspace_id in workspace_ids:
        try:
            workspace_service.ensure_workspace_exists(workspace_id)
        except workspace_service.WorkspaceNotFoundError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown workspace: {workspace_id}",
            ) from None


@router.get("", response_model=list[UserResponse])
def list_users(_: CurrentUser = Depends(require_admin)) -> list[UserResponse]:
    return [UserResponse(**user) for user in auth_service.list_users()]


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    _: CurrentUser = Depends(require_admin),
) -> UserResponse:

    _check_workspaces(payload.workspaces)

    try:
        user = auth_service.create_user(
            payload.username,
            payload.password,
            payload.role,
            payload.workspaces,
        )
    except auth_service.InvalidUsernameError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except auth_service.UserExistsError:
        raise HTTPException(status_code=409, detail="User already exists.") from None

    return UserResponse(**user)


@router.put("/{username}/workspaces", response_model=UserResponse)
def update_workspaces(
    username: str,
    payload: WorkspaceAccessUpdate,
    _: CurrentUser = Depends(require_admin),
) -> UserResponse:

    _check_workspaces(payload.workspaces)

    try:
        user = auth_service.set_user_workspaces(username, payload.workspaces)
    except auth_service.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found.") from None

    return UserResponse(**user)


@router.put("/{username}/password", status_code=204)
def reset_password(
    username: str,
    payload: PasswordReset,
    _: CurrentUser = Depends(require_admin),
) -> None:
    """Set a new password. The user's existing sessions stop working immediately."""

    try:
        auth_service.reset_password(username, payload.password)
    except auth_service.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found.") from None


@router.delete("/{username}", status_code=204)
def delete_user(
    username: str,
    admin: CurrentUser = Depends(require_admin),
) -> None:

    target = auth_service.get_user(username)

    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")

    if target["username"] == admin.username:
        raise HTTPException(status_code=400, detail="You cannot delete yourself.")

    if target["role"] == "admin" and auth_service.count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin.")

    auth_service.delete_user(username)
