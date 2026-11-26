from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes import agent as agent_route
from app.core.config import get_settings
from app.main import app
from app.services import document_metadata_service, feedback_service

client = TestClient(app)

RESULT = {
    "answer": "Employees get 20 days of leave.",
    "traces": [],
    "sources": [
        {"document_id": "d1", "document_name": "leave.pdf", "page": 3,
         "score": 0.5, "snippet": "Employees receive 20 days..."},
        {"document_id": "d1", "document_name": "leave.pdf", "page": 7,
         "score": 1.5, "snippet": "Unrelated clause"},
    ],
}


def ask(headers=None, **extra):
    body = {"messages": [{"role": "user", "content": "How much leave?"}], "document_ids": ["d1"], **extra}
    with patch.object(agent_route, "run_agent", AsyncMock(return_value=RESULT)):
        return client.post("/agent/chat", json=body, headers=headers or {})


# ---------- chat response: citations + confidence ----------

def test_chat_returns_citations_with_confidence_and_answer_id():
    data = ask().json()

    first, second = data["sources"]
    assert (first["page"], first["confidence"], first["confidence_level"]) == (3, 0.75, "high")
    assert first["snippet"].startswith("Employees receive")
    assert (second["page"], second["confidence"], second["confidence_level"]) == (7, 0.25, "low")

    assert data["answer_confidence"] == 0.75
    assert data["answer_confidence_level"] == "high"
    assert data["answer_id"]


def test_answer_without_sources_has_no_confidence():
    empty = {"answer": "I don't know.", "traces": [], "sources": []}
    with patch.object(agent_route, "run_agent", AsyncMock(return_value=empty)):
        data = client.post(
            "/agent/chat",
            json={"messages": [{"role": "user", "content": "?"}], "document_ids": ["d1"]},
        ).json()

    assert data["sources"] == []
    assert data["answer_confidence"] is None
    assert data["answer_confidence_level"] is None


def test_chat_still_works_if_answer_cannot_be_stored():
    with patch.object(agent_route, "record_answer", return_value=None):
        response = ask()
    assert response.status_code == 200
    assert response.json()["answer_id"] is None


# ---------- feedback ----------

def test_thumbs_up_and_re_rating_replaces_previous():
    answer_id = ask().json()["answer_id"]

    first = client.post("/feedback", json={"answer_id": answer_id, "rating": "up"})
    assert first.status_code == 200
    assert first.json()["rating"] == "up"

    second = client.post(
        "/feedback",
        json={"answer_id": answer_id, "rating": "down", "comment": "  wrong page  "},
    )
    assert second.json()["rating"] == "down"
    assert second.json()["comment"] == "wrong page"
    assert second.json()["created_at"] == first.json()["created_at"]

    summary = client.get("/feedback/summary").json()
    assert (summary["total"], summary["up"], summary["down"]) == (1, 0, 1)
    assert summary["satisfaction"] == 0.0


def test_feedback_validation():
    answer_id = ask().json()["answer_id"]

    assert client.post("/feedback", json={"answer_id": answer_id, "rating": "meh"}).status_code == 422
    too_long = {"answer_id": answer_id, "rating": "up", "comment": "x" * 1001}
    assert client.post("/feedback", json=too_long).status_code == 422


@pytest.mark.parametrize(
    "bad_id",
    ["nope", "../../etc/passwd", "..\\..\\x", "00000000-0000-0000-0000-000000000000", "a" * 64],
)
def test_unknown_or_malicious_answer_ids_are_404(bad_id):
    response = client.post("/feedback", json={"answer_id": bad_id, "rating": "up"})
    assert response.status_code == 404


def test_summary_and_list_with_filters():
    for rating in ("up", "up", "down"):
        answer_id = ask(workspace_id=None).json()["answer_id"]
        client.post("/feedback", json={"answer_id": answer_id, "rating": rating, "comment": rating})

    summary = client.get("/feedback/summary").json()
    assert (summary["total"], summary["up"], summary["down"]) == (3, 2, 1)
    assert summary["satisfaction"] == 0.667

    downs = client.get("/feedback", params={"rating": "down"}).json()
    assert len(downs) == 1
    assert downs[0]["question"] == "How much leave?"
    assert downs[0]["answer"].startswith("Employees get")

    assert len(client.get("/feedback", params={"limit": 2}).json()) == 2
    assert client.get("/feedback", params={"limit": 0}).status_code == 422
    assert client.get("/feedback", params={"rating": "bad"}).status_code == 422


def test_empty_feedback_summary():
    assert client.get("/feedback/summary").json() == {
        "total": 0, "up": 0, "down": 0, "satisfaction": None, "by_workspace": {},
    }
    assert client.get("/feedback").json() == []


# ---------- access control with login ----------

@pytest.fixture
def secured(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "k" * 40)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-test-pass-1")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()

    def login(user, password):
        token = client.post("/auth/login", json={"username": user, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    admin = login("admin", "admin-test-pass-1")
    client.post("/workspaces", json={"name": "HR"}, headers=admin)
    for name in ("alice", "bob"):
        client.post(
            "/users",
            json={"username": name, "password": "employee-pass-1", "workspaces": ["hr"]},
            headers=admin,
        )
        path = tmp_path / "storage" / "vector_stores" / "d1"
    path.mkdir(parents=True)
    document_metadata_service.save_document_metadata(path, "d1", "leave.pdf", "pdf", "hr")

    return SimpleNamespace(
        admin=admin, alice=login("alice", "employee-pass-1"), bob=login("bob", "employee-pass-1")
    )


def test_feedback_requires_login(secured):
    assert client.post("/feedback", json={"answer_id": "x", "rating": "up"}).status_code == 401


def test_only_the_asker_can_rate_an_answer(secured):
    answer_id = ask(secured.alice, workspace_id="hr", document_ids=[]).json()["answer_id"]

    assert client.post("/feedback", json={"answer_id": answer_id, "rating": "up"}, headers=secured.bob).status_code == 404
    assert client.post("/feedback", json={"answer_id": answer_id, "rating": "up"}, headers=secured.admin).status_code == 404
    assert client.post("/feedback", json={"answer_id": answer_id, "rating": "up"}, headers=secured.alice).status_code == 200


def test_only_admin_can_read_feedback(secured):
    answer_id = ask(secured.alice, workspace_id="hr", document_ids=[]).json()["answer_id"]
    client.post("/feedback", json={"answer_id": answer_id, "rating": "down"}, headers=secured.alice)

    assert client.get("/feedback", headers=secured.alice).status_code == 403
    assert client.get("/feedback/summary", headers=secured.alice).status_code == 403

    entries = client.get("/feedback", headers=secured.admin).json()
    assert entries[0]["username"] == "alice"
    assert entries[0]["workspace_id"] == "hr"

    summary = client.get("/feedback/summary", headers=secured.admin).json()
    assert summary["by_workspace"] == {"hr": {"up": 0, "down": 1}}
