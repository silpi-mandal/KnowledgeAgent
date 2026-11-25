from dataclasses import dataclass, field

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    username: str
    role: str
    workspaces: list[str] = field(default_factory=list)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can_access_workspace(self, workspace_id: str) -> bool:
        return self.is_admin or workspace_id in self.workspaces


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:

    if not get_settings().auth_enabled:
        # Local development only: AUTH_ENABLED=false turns access control off.
        return CurrentUser(username="anonymous", role="admin")

    if credentials is None:
        raise _unauthorized()

    try:
        username = auth_service.decode_token(credentials.credentials)
    except auth_service.AuthNotConfiguredError:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on the server.",
        ) from None

    record = auth_service.get_user(username) if username else None

    if record is None:
        raise _unauthorized()

    return CurrentUser(
        username=record["username"],
        role=record["role"],
        workspaces=list(record.get("workspaces", [])),
    )


def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    return user
