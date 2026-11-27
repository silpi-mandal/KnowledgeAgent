"""Users, password hashing and access tokens (stdlib + PyJWT).

Users live in ``<storage_dir>/users.json``. Passwords are stored as salted
scrypt hashes, never in plain text. Tokens only carry the username and an
expiry; the role and workspace access are re-read from the user store on
every request, so demoting or deleting a user takes effect immediately.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
MIN_SECRET_LENGTH = 32
USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,32}$")
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


class AuthNotConfiguredError(Exception):
    pass


class UserExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InvalidUsernameError(Exception):
    pass


# ---------- password hashing ----------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode(), salt=salt, n=int(n), r=int(r), p=int(p)
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(actual, expected)


# A throwaway hash so unknown usernames take as long to reject as wrong passwords.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# ---------- user store ----------

def _users_file() -> Path:
    return Path(get_settings().storage_dir) / "users.json"


def _load() -> dict[str, dict]:
    path = _users_file()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _save(users: dict[str, dict]) -> None:
    path = _users_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(users, file, indent=2)
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def public_user(record: dict) -> dict:
    return {
        "username": record["username"],
        "role": record["role"],
        "workspaces": list(record.get("workspaces", [])),
    }


def normalize_username(username: str) -> str:
    cleaned = username.strip().lower()
    if not USERNAME_PATTERN.match(cleaned):
        raise InvalidUsernameError(
            "Username must be 3-32 characters: letters, digits, '.', '_' or '-'."
        )
    return cleaned


def get_user(username: str) -> dict | None:
    return _load().get(username.strip().lower())


def list_users() -> list[dict]:
    return [public_user(record) for record in _load().values()]


def create_user(
    username: str,
    password: str,
    role: str = "employee",
    workspaces: list[str] | None = None,
) -> dict:
    name = normalize_username(username)
    users = _load()

    if name in users:
        raise UserExistsError(name)

    users[name] = {
        "username": name,
        "password_hash": hash_password(password),
        "role": role,
        "workspaces": sorted(set(workspaces or [])),
    }
    _save(users)
    return public_user(users[name])


def set_user_workspaces(username: str, workspaces: list[str]) -> dict:
    users = _load()
    name = username.strip().lower()
    if name not in users:
        raise UserNotFoundError(name)

    users[name]["workspaces"] = sorted(set(workspaces))
    _save(users)
    return public_user(users[name])


def delete_user(username: str) -> None:
    users = _load()
    name = username.strip().lower()
    if name not in users:
        raise UserNotFoundError(name)

    del users[name]
    _save(users)


def reset_password(username: str, new_password: str) -> None:
    """Set a new password and invalidate every token issued before now."""
    users = _load()
    name = username.strip().lower()
    if name not in users:
        raise UserNotFoundError(name)

    users[name]["password_hash"] = hash_password(new_password)
    users[name]["token_version"] = users[name].get("token_version", 0) + 1
    _save(users)


def count_admins() -> int:
    return sum(1 for record in _load().values() if record["role"] == "admin")


def bootstrap_admin_if_needed() -> None:
    """Create the first admin from ADMIN_USERNAME / ADMIN_PASSWORD, only if no users exist."""
    settings = get_settings()
    password = settings.admin_password.get_secret_value()

    if _load() or not settings.admin_username or len(password) < 8:
        return

    create_user(settings.admin_username, password, role="admin")


def authenticate(username: str, password: str) -> dict | None:
    bootstrap_admin_if_needed()
    record = get_user(username)

    if record is None:
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, record["password_hash"]):
        return None

    return record


# ---------- tokens ----------

def _secret() -> str:
    secret = get_settings().auth_secret_key.get_secret_value()
    if len(secret) < MIN_SECRET_LENGTH:
        raise AuthNotConfiguredError(
            f"AUTH_SECRET_KEY must be set to at least {MIN_SECRET_LENGTH} characters."
        )
    return secret


def create_access_token(username: str, token_version: int = 0) -> tuple[str, int]:
    minutes = get_settings().token_expire_minutes
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    token = jwt.encode(
        {"sub": username, "ver": token_version, "exp": expires},
        _secret(),
        algorithm=ALGORITHM,
    )
    return token, minutes * 60


def decode_token(token: str) -> tuple[str, int] | None:
    """Return (username, token_version), or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "ver"]},
        )
    except jwt.PyJWTError:
        return None

    subject, version = payload.get("sub"), payload.get("ver")

    if not isinstance(subject, str) or not isinstance(version, int):
        return None

    return subject, version
