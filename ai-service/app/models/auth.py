from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["admin", "employee"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "employee"
    workspaces: list[str] = Field(default_factory=list)


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class WorkspaceAccessUpdate(BaseModel):
    workspaces: list[str]


class UserResponse(BaseModel):
    username: str
    role: Role
    workspaces: list[str] = Field(default_factory=list)
