from pathlib import Path

from mcp.server.mcpserver import MCPServer

from app.core.config import get_settings
from documind_mcp import enterprise_tools
from app.services.document_metadata_service import load_document_metadata
from app.services.vector_store_service import (
    load_vector_store,
    search_vector_store,
)


settings = get_settings()

VECTOR_STORES_DIR = (
    Path(settings.storage_dir)
    / "vector_stores"
)


mcp = MCPServer("KnowledgeAgent")


@mcp.tool()
def search_document(
    document_id: str,
    query: str,
    k: int = 3,
) -> list[dict]:
    """Search an uploaded document using FAISS similarity search."""

    vector_store_path = VECTOR_STORES_DIR / document_id

    if not vector_store_path.exists():
        return [
            {
                "error": "Document vector store not found.",
                "document_id": document_id,
            }
        ]

    metadata = load_document_metadata(
        vector_store_path
    )

    vector_store = load_vector_store(
        str(vector_store_path)
    )

    results = search_vector_store(
        vector_store,
        query,
        k=k,
    )

    for result in results:
        result["document_name"] = metadata.get(
            "document_name"
        )

    return results


@mcp.tool()
def get_document_info(
    document_id: str,
) -> dict:
    """Get metadata information about an uploaded document."""

    vector_store_path = VECTOR_STORES_DIR / document_id

    if not vector_store_path.exists():
        return {
            "error": "Document vector store not found.",
            "document_id": document_id,
        }

    metadata = load_document_metadata(
        vector_store_path
    )

    return metadata


@mcp.tool()
def list_documents() -> list[dict]:
    """List all uploaded documents."""

    if not VECTOR_STORES_DIR.exists():
        return []

    documents = []

    for document_path in VECTOR_STORES_DIR.iterdir():

        if not document_path.is_dir():
            continue

        metadata = load_document_metadata(
            document_path
        )

        if not metadata:
            continue

        documents.append(metadata)

    return documents


@mcp.tool()
def lookup_ticket(ticket_id: str) -> dict:
    """Get one support ticket by id, e.g. IT-1001, HR-2001 or FIN-3001."""

    return enterprise_tools.lookup_ticket(ticket_id)


@mcp.tool()
def search_tickets(
    status: str | None = None,
    assignee: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search support tickets. status: open, in_progress, resolved or closed."""

    return enterprise_tools.search_tickets(status, assignee, keyword, limit)


@mcp.tool()
def find_employee(
    query: str,
    department: str | None = None,
) -> list[dict]:
    """Find employees in the company directory by name, title or email."""

    return enterprise_tools.find_employee(query, department)


@mcp.tool()
def send_notification(
    recipient_email: str,
    subject: str,
    message: str,
) -> dict:
    """Queue a notification to an employee (mock outbox, no real email)."""

    return enterprise_tools.send_notification(
        recipient_email,
        subject,
        message,
        Path(settings.storage_dir) / "outbox.jsonl",
    )


if __name__ == "__main__":
    mcp.run()
