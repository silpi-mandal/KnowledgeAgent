from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services import login_throttle

client = TestClient(app)

ADMIN_PASSWORD = "admin-test-pass-1"
ALICE_PASSWORD = "alice-test-pass-1"


@pytest.fixture
def secured(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "s" * 40)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()

    def login(user, password):
        return client.post("/auth/login", json={"username": user, "password": password})

    def headers(user, password):
        return {"Authorization": f"Bearer {login(user, password).json()['access_token']}"}

    admin = headers("admin", ADMIN_PASSWORD)
    client.post("/workspaces", json={"name": "HR"}, headers=admin)
    client.post(
        "/users",
        json={"username": "alice", "password": ALICE_PASSWORD, "workspaces": ["hr"]},
        headers=admin,
    )
    return SimpleNamespace(login=login, headers=headers, admin=admin)


# ---------- login throttling ----------

def test_lockout_after_repeated_failures_even_for_correct_password(secured):
    for _ in range(login_throttle.MAX_FAILURES):
        assert secured.login("alice", "wrong-password").status_code == 401

    locked = secured.login("alice", ALICE_PASSWORD)  # correct, but locked
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0

    # other accounts are unaffected
    assert secured.login("admin", ADMIN_PASSWORD).status_code == 200


def test_successful_login_resets_the_failure_count(secured):
    for _ in range(login_throttle.MAX_FAILURES - 1):
        secured.login("alice", "wrong-password")

    assert secured.login("alice", ALICE_PASSWORD).status_code == 200

    for _ in range(login_throttle.MAX_FAILURES - 1):
        assert secured.login("alice", "wrong-password").status_code == 401
    assert secured.login("alice", ALICE_PASSWORD).status_code == 200


def test_unknown_usernames_are_throttled_the_same_way(secured):
    for _ in range(login_throttle.MAX_FAILURES):
        assert secured.login("ghost", "whatever-123").status_code == 401
    assert secured.login("ghost", "whatever-123").status_code == 429


def test_username_case_does_not_bypass_the_lock(secured):
    for _ in range(login_throttle.MAX_FAILURES):
        secured.login("ALICE", "wrong-password")
    assert secured.login("alice", ALICE_PASSWORD).status_code == 429


def test_lock_expires(secured, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(login_throttle, "_clock", lambda: now[0])

    for _ in range(login_throttle.MAX_FAILURES):
        secured.login("alice", "wrong-password")
    assert secured.login("alice", ALICE_PASSWORD).status_code == 429

    now[0] += login_throttle.LOCK_SECONDS + 1
    assert secured.login("alice", ALICE_PASSWORD).status_code == 200


def test_old_failures_age_out_of_the_window(secured, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(login_throttle, "_clock", lambda: now[0])

    for _ in range(login_throttle.MAX_FAILURES - 1):
        secured.login("alice", "wrong-password")

    now[0] += login_throttle.WINDOW_SECONDS + 1
    assert secured.login("alice", "wrong-password").status_code == 401  # count restarts
    assert secured.login("alice", ALICE_PASSWORD).status_code == 200


def test_throttle_memory_is_bounded(monkeypatch):
    monkeypatch.setattr(login_throttle, "MAX_TRACKED", 50)
    for i in range(500):
        login_throttle.record_failure(f"user{i}")
    assert len(login_throttle._state) == 50


# ---------- password reset and token revocation ----------

def test_admin_reset_changes_password_and_revokes_old_tokens(secured):
    old_headers = secured.headers("alice", ALICE_PASSWORD)
    assert client.get("/auth/me", headers=old_headers).status_code == 200

    reset = client.put(
        "/users/alice/password", json={"password": "brand-new-pass-1"}, headers=secured.admin
    )
    assert reset.status_code == 204

    assert client.get("/auth/me", headers=old_headers).status_code == 401  # revoked
    assert secured.login("alice", ALICE_PASSWORD).status_code == 401  # old password dead
    new_headers = secured.headers("alice", "brand-new-pass-1")
    assert client.get("/auth/me", headers=new_headers).status_code == 200


def test_reset_does_not_affect_other_users_sessions(secured):
    admin_still_valid = client.get("/auth/me", headers=secured.admin)
    client.put("/users/alice/password", json={"password": "brand-new-pass-1"}, headers=secured.admin)
    assert admin_still_valid.status_code == 200
    assert client.get("/auth/me", headers=secured.admin).status_code == 200


def test_reset_validation_and_permissions(secured):
    alice = secured.headers("alice", ALICE_PASSWORD)

    assert client.put("/users/alice/password", json={"password": "x" * 12}, headers=alice).status_code == 403
    assert client.put("/users/alice/password", json={"password": "short"}, headers=secured.admin).status_code == 422
    assert client.put("/users/ghost/password", json={"password": "long-enough-1"}, headers=secured.admin).status_code == 404
    assert client.put("/users/alice/password", json={"password": "long-enough-1"}).status_code == 401


def test_token_without_version_claim_is_rejected(secured):
    import jwt
    from datetime import datetime, timedelta, timezone

    legacy = jwt.encode(
        {"sub": "alice", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "s" * 40,
        algorithm="HS256",
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {legacy}"})
    assert response.status_code == 401
