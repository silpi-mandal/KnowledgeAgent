from langchain_core.tools import tool

from app.services.mcp_client_service import (
    call_mcp_tool,
    get_document_info,
    list_documents,
    search_document,
)


@tool
async def search_document_tool(
    document_id: str,
    query: str,
    k: int = 3,
) -> list[dict]:
    """Search an uploaded document for information relevant to a question."""

    return await search_document(
        document_id,
        query,
        k,
    )


@tool
async def get_document_info_tool(
    document_id: str,
) -> dict:
    """Get information about an uploaded document."""

    return await get_document_info(
        document_id,
    )


@tool
async def list_documents_tool() -> list[dict]:
    """List all uploaded documents."""

    return await list_documents()


@tool
async def lookup_ticket_tool(ticket_id: str) -> dict:
    """Get one support ticket by id (e.g. IT-1001, HR-2001, FIN-3001)."""

    return await call_mcp_tool("lookup_ticket", {"ticket_id": ticket_id})


@tool
async def search_tickets_tool(
    status: str | None = None,
    assignee: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search support tickets by status (open, in_progress, resolved, closed), assignee name or keyword."""

    return await call_mcp_tool(
        "search_tickets",
        {
            "status": status,
            "assignee": assignee,
            "keyword": keyword,
            "limit": limit,
        },
    )


@tool
async def find_employee_tool(
    query: str,
    department: str | None = None,
) -> list[dict]:
    """Find employees in the company directory by name, title or email, optionally within a department."""

    return await call_mcp_tool(
        "find_employee",
        {"query": query, "department": department},
    )


@tool
async def send_notification_tool(
    recipient_email: str,
    subject: str,
    message: str,
) -> dict:
    """Queue a notification to an employee. Use ONLY when the user explicitly asks to notify someone. Mock outbox, no real email is sent."""

    return await call_mcp_tool(
        "send_notification",
        {
            "recipient_email": recipient_email,
            "subject": subject,
            "message": message,
        },
    )
