"""Starts the real MCP server over stdio and calls the enterprise tools."""

import asyncio

from app.services.mcp_client_service import call_mcp_tool, list_mcp_tools

ENTERPRISE_TOOLS = {
    "lookup_ticket",
    "search_tickets",
    "find_employee",
    "send_notification",
}


def test_server_exposes_enterprise_tools():
    names = {tool.name for tool in asyncio.run(list_mcp_tools())}
    assert ENTERPRISE_TOOLS <= names
    assert {"search_document", "get_document_info", "list_documents"} <= names


def test_lookup_ticket_through_mcp():
    result = asyncio.run(call_mcp_tool("lookup_ticket", {"ticket_id": "HR-2001"}))
    assert result["assignee"] == "Asha Verma"


def test_search_and_directory_through_mcp():
    tickets = asyncio.run(call_mcp_tool("search_tickets", {"status": "open"}))
    assert {t["ticket_id"] for t in tickets} == {"IT-1001", "HR-2001"}

    people = asyncio.run(call_mcp_tool("find_employee", {"query": "priya"}))
    assert people[0]["email"] == "priya.nair@example.com"


def test_send_notification_through_mcp_rejects_unknown_recipient():
    result = asyncio.run(
        call_mcp_tool(
            "send_notification",
            {"recipient_email": "nobody@evil.com", "subject": "s", "message": "m"},
        )
    )
    assert "error" in result
