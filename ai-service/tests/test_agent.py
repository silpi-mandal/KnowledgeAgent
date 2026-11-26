from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_requires_a_document_or_workspace() -> None:
    response = client.post(
        "/agent/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 400
    assert "document_id" in response.json()["detail"]


def test_chat_rejects_empty_messages() -> None:
    response = client.post("/agent/chat", json={"messages": []})
    assert response.status_code == 422


def test_chat_rejects_unknown_role() -> None:
    response = client.post(
        "/agent/chat",
        json={"messages": [{"role": "wizard", "content": "hi"}]},
    )
    assert response.status_code == 422


def test_chat_schema_exposes_request_and_response_models() -> None:
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    assert "ChatRequest" in schema
    assert "ChatResponse" in schema
    assert "workspace_id" in schema["ChatRequest"]["properties"]
    assert set(schema["ChatResponse"]["properties"]) == {
        "answer",
        "traces",
        "sources",
        "answer_id",
        "answer_confidence",
        "answer_confidence_level",
    }


def test_list_tools_returns_registered_tools() -> None:
    response = client.get("/agent/tools")
    assert response.status_code == 200
    assert response.json() == {
        "tools": [
            "search_document_tool",
            "get_document_info_tool",
            "list_documents_tool",
            "lookup_ticket_tool",
            "search_tickets_tool",
            "find_employee_tool",
            "send_notification_tool",
        ]
    }
