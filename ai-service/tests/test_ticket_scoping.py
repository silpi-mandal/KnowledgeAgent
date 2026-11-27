import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import AIMessage, ToolMessage

from app.services.agent_service import run_agent, scope_ticket_result
from documind_mcp import enterprise_tools

ALL_TICKETS = enterprise_tools.search_tickets(limit=20)


def scoped(tool, args, result, role="employee", workspaces=("hr",)):
    return scope_ticket_result(tool, args, result, role, list(workspaces))


# ---------- pure filtering ----------

def test_employee_search_only_returns_own_departments():
    result = scoped("search_tickets_tool", {}, ALL_TICKETS, workspaces=("hr",))
    assert {t["department"] for t in result} == {"HR"}
    assert {t["ticket_id"] for t in result} == {"HR-2001", "HR-2002"}


def test_employee_with_several_workspaces_sees_each_department():
    result = scoped("search_tickets_tool", {}, ALL_TICKETS, workspaces=("hr", "IT"))
    assert {t["department"] for t in result} == {"HR", "IT"}


def test_employee_with_no_workspace_sees_no_tickets():
    assert scoped("search_tickets_tool", {}, ALL_TICKETS, workspaces=()) == []
    assert scope_ticket_result("search_tickets_tool", {}, ALL_TICKETS, "employee", None) == []


def test_forbidden_lookup_looks_exactly_like_a_missing_ticket():
    forbidden = scoped("lookup_ticket_tool", {"ticket_id": "IT-1001"}, enterprise_tools.lookup_ticket("IT-1001"))
    missing = enterprise_tools.lookup_ticket("IT-9999")

    assert forbidden["error"] == missing["error"] == "Ticket not found."
    assert "title" not in forbidden and "assignee" not in forbidden


def test_allowed_lookup_passes_through_unchanged():
    ticket = enterprise_tools.lookup_ticket("HR-2001")
    assert scoped("lookup_ticket_tool", {"ticket_id": "HR-2001"}, ticket) == ticket


def test_admin_sees_everything():
    result = scoped("search_tickets_tool", {}, ALL_TICKETS, role="admin", workspaces=())
    assert result == ALL_TICKETS


def test_other_tools_are_not_touched():
    people = enterprise_tools.find_employee("")
    assert scoped("find_employee_tool", {}, people) == people


def test_error_results_and_odd_shapes_do_not_crash():
    assert scoped("search_tickets_tool", {}, "Tool call failed: boom") == "Tool call failed: boom"
    assert scoped("lookup_ticket_tool", {}, {"error": "Ticket not found."}) == {"error": "Ticket not found."}
    assert scoped("search_tickets_tool", {}, [None, "x", {"department": "HR"}]) == [{"department": "HR"}]


# ---------- through the real agent loop ----------

def run_with_ticket_call(tool_name, args, tool_result, role, workspaces):
    call = AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": "c1", "type": "tool_call"}],
    )
    replies = iter([call, AIMessage(content="done")])
    seen = []

    async def ainvoke(messages):
        seen.append(list(messages))
        return next(replies)

    bound = Mock()
    bound.ainvoke = ainvoke
    llm = Mock()
    llm.bind_tools = Mock(return_value=bound)
    tool = SimpleNamespace(ainvoke=AsyncMock(return_value=tool_result))

    with patch("app.services.agent_service.create_llm", return_value=llm), patch(
        "app.services.agent_service.TOOLS_BY_NAME", {tool_name: tool}
    ):
        result = asyncio.run(
            run_agent(
                question="q",
                document_ids=["d1"],
                user_role=role,
                allowed_workspaces=workspaces,
            )
        )

    tool_message = [m for m in seen[-1] if isinstance(m, ToolMessage)][0]
    return result, tool_message.content


def test_employee_asking_for_another_departments_ticket_gets_not_found():
    result, what_the_model_saw = run_with_ticket_call(
        "lookup_ticket_tool",
        {"ticket_id": "IT-1001"},
        enterprise_tools.lookup_ticket("IT-1001"),
        "employee",
        ["hr"],
    )

    assert "VPN" not in what_the_model_saw and "Priya" not in what_the_model_saw
    assert "Ticket not found" in what_the_model_saw
    assert "VPN" not in result["traces"][-1]["result_summary"]


def test_employee_search_is_filtered_before_the_model_sees_it():
    _, what_the_model_saw = run_with_ticket_call(
        "search_tickets_tool", {"status": "open"}, enterprise_tools.search_tickets(status="open"),
        "employee", ["hr"],
    )
    assert "HR-2001" in what_the_model_saw
    assert "IT-1001" not in what_the_model_saw


def test_admin_agent_sees_all_tickets():
    _, what_the_model_saw = run_with_ticket_call(
        "search_tickets_tool", {"status": "open"}, enterprise_tools.search_tickets(status="open"),
        "admin", [],
    )
    assert "HR-2001" in what_the_model_saw and "IT-1001" in what_the_model_saw
