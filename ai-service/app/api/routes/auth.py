from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_current_user
from app.models.auth import LoginRequest, TokenResponse, UserResponse
from app.services import auth_service, login_throttle

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:

    try:
        login_throttle.check(payload.username)
    except login_throttle.LoginLockedError as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many failed sign-in attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from None

    try:
        record = auth_service.authenticate(payload.username, payload.password)

        if record is None:
            login_throttle.record_failure(payload.username)
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password.",
            )

        token, expires_in = auth_service.create_access_token(
            record["username"],
            record.get("token_version", 0),
        )
        login_throttle.record_success(payload.username)

    except auth_service.AuthNotConfiguredError:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on the server.",
        ) from None

    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        username=user.username,
        role=user.role,
        workspaces=user.workspaces,
    )
