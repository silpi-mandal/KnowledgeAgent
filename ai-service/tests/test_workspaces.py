from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.routes import agent as agent_route
from app.api.routes import documents as documents_route
from app.main import app
from app.services import (
    document_metadata_service,
    document_storage_service,
    workspace_service,
)

client = TestClient(app)


@pytest.fixture
def storage(tmp_path: Path, monkeypatch) -> Path:
    settings = SimpleNamespace(storage_dir=str(tmp_path / "storage"))
    for module in (workspace_service, documents_route, document_storage_service):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    return tmp_path / "storage"


def add_document(storage: Path, document_id: str, name: str, workspace: str | None):
    path = storage / "vector_stores" / document_id
    path.mkdir(parents=True)
    document_metadata_service.save_document_metadata(
        path,
        document_id,
        name,
        file_type="pdf",
        **({"workspace_id": workspace} if workspace else {}),
    )


def test_default_workspace_always_exists(storage) -> None:
    response = client.get("/workspaces")
    assert response.status_code == 200
    assert [w["workspace_id"] for w in response.json()] == ["general"]


def test_create_list_and_duplicate_workspace(storage) -> None:
    created = client.post("/workspaces", json={"name": "HR Policies"})
    assert created.status_code == 201
    assert created.json()["workspace_id"] == "hr-policies"

    assert client.post("/workspaces", json={"name": "hr policies"}).status_code == 409

    ids = {w["workspace_id"] for w in client.get("/workspaces").json()}
    assert ids == {"general", "hr-policies"}


def test_blank_workspace_name_is_rejected(storage) -> None:
    assert client.post("/workspaces", json={"name": ""}).status_code == 422


def test_documents_are_grouped_by_workspace(storage) -> None:
    client.post("/workspaces", json={"name": "HR"})
    add_document(storage, "d-hr", "leave.pdf", "hr")
    add_document(storage, "d-old", "legacy.pdf", None)

    hr_docs = client.get("/workspaces/hr/documents").json()
    assert [d["document_id"] for d in hr_docs] == ["d-hr"]

    # documents saved before workspaces existed fall back to "general"
    general = client.get("/documents", params={"workspace_id": "general"}).json()
    assert [d["document_id"] for d in general] == ["d-old"]

    counts = {w["workspace_id"]: w["document_count"] for w in client.get("/workspaces").json()}
    assert counts == {"general": 1, "hr": 1}


def test_upload_into_unknown_workspace_is_404(storage) -> None:
    with Path("tests/fixtures/sample.pdf").open("rb") as file:
        response = client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", file, "application/pdf")},
            data={"workspace_id": "nope"},
        )
    assert response.status_code == 404


def test_upload_records_workspace(storage, monkeypatch) -> None:
    client.post("/workspaces", json={"name": "IT"})
    seen = {}

    def fake_ingest(document_id, file_path, document_name, workspace_id="general"):
        seen["workspace_id"] = workspace_id

    monkeypatch.setattr(documents_route, "ingest_document", fake_ingest)

    with Path("tests/fixtures/sample.pdf").open("rb") as file:
        response = client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", file, "application/pdf")},
            data={"workspace_id": "it"},
        )

    assert response.status_code == 200
    assert response.json()["workspace_id"] == "it"
    assert seen["workspace_id"] == "it"


def test_delete_workspace_rules(storage) -> None:
    client.post("/workspaces", json={"name": "Temp"})
    add_document(storage, "d1", "a.pdf", "temp")

    assert client.delete("/workspaces/general").status_code == 400
    assert client.delete("/workspaces/temp").status_code == 400  # not empty
    assert client.delete("/workspaces/ghost").status_code == 404

    client.post("/workspaces", json={"name": "Empty"})
    assert client.delete("/workspaces/empty").status_code == 204


def test_chat_uses_only_documents_from_the_workspace(storage) -> None:
    client.post("/workspaces", json={"name": "HR"})
    add_document(storage, "d-hr", "leave.pdf", "hr")
    add_document(storage, "d-other", "finance.pdf", "general")

    fake = AsyncMock(return_value={"answer": "ok", "traces": [], "sources": []})
    with patch.object(agent_route, "run_agent", fake):
        response = client.post(
            "/agent/chat",
            json={
                "messages": [{"role": "user", "content": "leave policy?"}],
                "workspace_id": "hr",
            },
        )

    assert response.status_code == 200
    assert fake.call_args.kwargs["document_ids"] == ["d-hr"]


def test_chat_rejects_documents_outside_the_workspace(storage) -> None:
    client.post("/workspaces", json={"name": "HR"})
    add_document(storage, "d-hr", "leave.pdf", "hr")
    add_document(storage, "d-other", "finance.pdf", "general")

    response = client.post(
        "/agent/chat",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "workspace_id": "hr",
            "document_ids": ["d-other"],
        },
    )
    assert response.status_code == 400


def test_chat_unknown_or_empty_workspace(storage) -> None:
    body = {"messages": [{"role": "user", "content": "hi"}]}

    assert client.post("/agent/chat", json={**body, "workspace_id": "ghost"}).status_code == 404

    client.post("/workspaces", json={"name": "Empty"})
    assert client.post("/agent/chat", json={**body, "workspace_id": "empty"}).status_code == 400
