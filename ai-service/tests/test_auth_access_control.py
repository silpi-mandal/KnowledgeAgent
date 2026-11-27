import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.api.routes import agent as agent_route
from app.core.config import get_settings
from app.main import app
from app.services import auth_service, document_metadata_service
from app.services.agent_service import run_agent

client = TestClient(app)

SECRET = "t" * 40
ADMIN_PASSWORD = "admin-test-pass-1"
EMPLOYEE_PASSWORD = "employee-test-pass-1"


@pytest.fixture
def secured(tmp_path: Path, monkeypatch) -> Path:
    """Auth switched on, isolated storage, bootstrap admin configured."""
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", SECRET)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    return tmp_path / "storage"


def login(username: str, password: str):
    return client.post("/auth/login", json={"username": username, "password": password})


def headers_for(username: str, password: str) -> dict:
    token = login(username, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_document(storage: Path, document_id: str, workspace: str):
    path = storage / "vector_stores" / document_id
    path.mkdir(parents=True)
    document_metadata_service.save_document_metadata(
        path, document_id, f"{document_id}.pdf", file_type="pdf", workspace_id=workspace
    )


@pytest.fixture
def org(secured):
    """Admin + two workspaces (hr, it) + employee who can only see hr."""
    admin = headers_for("admin", ADMIN_PASSWORD)
    client.post("/workspaces", json={"name": "HR"}, headers=admin)
    client.post("/workspaces", json={"name": "IT"}, headers=admin)
    created = client.post(
        "/users",
        json={
            "username": "Alice",
            "password": EMPLOYEE_PASSWORD,
            "role": "employee",
            "workspaces": ["hr"],
        },
        headers=admin,
    )
    assert created.status_code == 201
    add_document(secured, "d-hr", "hr")
    add_document(secured, "d-it", "it")
    return SimpleNamespace(
        admin=admin,
        alice=headers_for("alice", EMPLOYEE_PASSWORD),
        storage=secured,
    )


# ---------- login & tokens ----------

def test_login_success_and_wrong_credentials_look_identical(secured):
    assert login("admin", ADMIN_PASSWORD).status_code == 200

    wrong_password = login("admin", "nope-nope-nope")
    unknown_user = login("ghost", "nope-nope-nope")

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_passwords_are_stored_hashed(secured):
    login("admin", ADMIN_PASSWORD)
    stored = (secured / "users.json").read_text()
    assert ADMIN_PASSWORD not in stored
    assert "scrypt$" in stored


def test_endpoints_require_a_token(secured):
    assert client.get("/health").status_code == 200
    for method, url in [
        ("get", "/workspaces"),
        ("get", "/documents"),
        ("get", "/agent/tools"),
        ("get", "/users"),
        ("get", "/auth/me"),
    ]:
        assert getattr(client, method)(url).status_code == 401, url

    chat = client.post(
        "/agent/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "workspace_id": "hr"},
    )
    assert chat.status_code == 401


def test_garbage_tampered_and_expired_tokens_are_rejected(secured):
    login("admin", ADMIN_PASSWORD)  # creates admin

    def call(token):
        return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert call("not-a-token").status_code == 401

    wrong_key = jwt.encode(
        {"sub": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "x" * 40,
        algorithm="HS256",
    )
    assert call(wrong_key).status_code == 401

    expired = jwt.encode(
        {"sub": "admin", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET,
        algorithm="HS256",
    )
    assert call(expired).status_code == 401

    unsigned = jwt.encode({"sub": "admin"}, SECRET, algorithm="HS256")  # no exp
    assert call(unsigned).status_code == 401


def test_deleted_user_token_stops_working(org):
    client.delete("/users/alice", headers=org.admin)
    assert client.get("/auth/me", headers=org.alice).status_code == 401


def test_login_reports_503_when_secret_not_configured(secured, monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "short")
    get_settings.cache_clear()
    assert login("admin", ADMIN_PASSWORD).status_code == 503


# ---------- user management ----------

def test_only_admin_can_manage_users(org):
    body = {"username": "bob", "password": EMPLOYEE_PASSWORD}
    assert client.get("/users", headers=org.alice).status_code == 403
    assert client.post("/users", json=body, headers=org.alice).status_code == 403
    assert client.post("/users", json=body, headers=org.admin).status_code == 201


def test_user_creation_validation(org):
    weak = client.post(
        "/users", json={"username": "bob", "password": "short"}, headers=org.admin
    )
    assert weak.status_code == 422

    bad_name = client.post(
        "/users",
        json={"username": "bad name!", "password": EMPLOYEE_PASSWORD},
        headers=org.admin,
    )
    assert bad_name.status_code == 422

    duplicate = client.post(
        "/users",
        json={"username": "ALICE", "password": EMPLOYEE_PASSWORD},
        headers=org.admin,
    )
    assert duplicate.status_code == 409

    unknown_workspace = client.post(
        "/users",
        json={"username": "bob", "password": EMPLOYEE_PASSWORD, "workspaces": ["nope"]},
        headers=org.admin,
    )
    assert unknown_workspace.status_code == 400


def test_admin_cannot_delete_self_or_last_admin(org):
    assert client.delete("/users/admin", headers=org.admin).status_code == 400


def test_grant_workspace_access(org):
    before = client.get("/workspaces", headers=org.alice).json()
    assert [w["workspace_id"] for w in before] == ["hr"]

    client.put("/users/alice/workspaces", json={"workspaces": ["hr", "it"]}, headers=org.admin)

    after = client.get("/workspaces", headers=org.alice).json()
    assert {w["workspace_id"] for w in after} == {"hr", "it"}


# ---------- workspace & document isolation ----------

def test_employee_only_sees_assigned_workspaces_and_documents(org):
    workspaces = client.get("/workspaces", headers=org.alice).json()
    assert [w["workspace_id"] for w in workspaces] == ["hr"]

    docs = client.get("/documents", headers=org.alice).json()
    assert [d["document_id"] for d in docs] == ["d-hr"]

    assert client.get("/workspaces/hr/documents", headers=org.alice).status_code == 200
    assert client.get("/workspaces/it/documents", headers=org.alice).status_code == 404
    # filtering by someone else's workspace returns nothing, not their documents
    assert client.get("/documents?workspace_id=it", headers=org.alice).json() == []

    admin_docs = client.get("/documents", headers=org.admin).json()
    assert {d["document_id"] for d in admin_docs} == {"d-hr", "d-it"}


def test_employee_cannot_change_content(org):
    assert client.post("/workspaces", json={"name": "X"}, headers=org.alice).status_code == 403
    assert client.delete("/workspaces/hr", headers=org.alice).status_code == 403

    with Path("tests/fixtures/sample.pdf").open("rb") as file:
        upload = client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", file, "application/pdf")},
            data={"workspace_id": "hr"},
            headers=org.alice,
        )
    assert upload.status_code == 403


# ---------- chat access ----------

def chat(headers, **extra):
    body = {"messages": [{"role": "user", "content": "question"}], **extra}
    fake = AsyncMock(return_value={"answer": "ok", "traces": [], "sources": []})
    with patch.object(agent_route, "run_agent", fake):
        response = client.post("/agent/chat", json=body, headers=headers)
    return response, fake


def test_employee_chat_limited_to_allowed_workspaces(org):
    ok, fake = chat(org.alice, workspace_id="hr")
    assert ok.status_code == 200
    assert fake.call_args.kwargs["document_ids"] == ["d-hr"]
    assert fake.call_args.kwargs["user_role"] == "employee"
    assert fake.call_args.kwargs["allowed_workspaces"] == ["hr"]

    assert chat(org.alice, workspace_id="it")[0].status_code == 404
    assert chat(org.alice, document_ids=["d-it"])[0].status_code == 404
    assert chat(org.alice, document_ids=["d-hr", "d-it"])[0].status_code == 404
    assert chat(org.alice, document_ids=["does-not-exist"])[0].status_code == 404
    assert chat(org.alice, document_ids=["d-hr"])[0].status_code == 200


def test_admin_chat_reaches_every_workspace(org):
    response, fake = chat(org.admin, workspace_id="it")
    assert response.status_code == 200
    assert fake.call_args.kwargs["user_role"] == "admin"


# ---------- tool restrictions ----------

def test_tools_endpoint_hides_notifications_from_employees(org):
    employee_tools = client.get("/agent/tools", headers=org.alice).json()["tools"]
    admin_tools = client.get("/agent/tools", headers=org.admin).json()["tools"]

    assert "send_notification_tool" not in employee_tools
    assert "send_notification_tool" in admin_tools
    assert "search_document_tool" in employee_tools


def _agent_with_notification_call(role):
    call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "send_notification_tool",
                "args": {
                    "recipient_email": "asha.verma@example.com",
                    "subject": "s",
                    "message": "m",
                },
                "id": "c1",
                "type": "tool_call",
            }
        ],
    )
    final = AIMessage(content="done")
    state = {"n": 0}
    bound = Mock()

    async def ainvoke(messages):
        state["n"] += 1
        return call if state["n"] == 1 else final

    bound.ainvoke = ainvoke
    llm = Mock()
    llm.bind_tools = Mock(return_value=bound)

    notify = SimpleNamespace(ainvoke=AsyncMock(return_value={"status": "queued"}))
    search = SimpleNamespace(ainvoke=AsyncMock(return_value=[]))

    with patch("app.services.agent_service.create_llm", return_value=llm), patch(
        "app.services.agent_service.TOOLS_BY_NAME", {"send_notification_tool": notify}
    ), patch("app.services.agent_service.search_document_tool", search):
        result = asyncio.run(
            run_agent(question="notify", document_ids=["d1"], user_role=role)
        )

    return result, notify, llm


def test_employee_agent_cannot_run_or_see_notification_tool():
    result, notify, llm = _agent_with_notification_call("employee")

    notify.ainvoke.assert_not_called()
    assert "Access denied" in result["traces"][-1]["result_summary"]
    offered = {tool.name for tool in llm.bind_tools.call_args.args[0]}
    assert "send_notification_tool" not in offered


def test_admin_agent_can_run_notification_tool():
    result, notify, llm = _agent_with_notification_call("admin")

    notify.ainvoke.assert_awaited_once()
    offered = {tool.name for tool in llm.bind_tools.call_args.args[0]}
    assert "send_notification_tool" in offered


def test_default_role_for_run_agent_is_least_privilege():
    result, notify, _ = _agent_with_notification_call("employee")
    import inspect

    assert inspect.signature(run_agent).parameters["user_role"].default == "employee"


def test_hash_verify_roundtrip_and_malformed_hash():
    stored = auth_service.hash_password("correct horse battery")
    assert auth_service.verify_password("correct horse battery", stored)
    assert not auth_service.verify_password("wrong", stored)
    assert not auth_service.verify_password("x", "garbage")
    assert not auth_service.verify_password("x", "md5$1$2$3$4$5")
