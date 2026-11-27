import logging

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    ToolMessage,
)

from app.models.agent import ChatMessage
from app.services.citation_service import make_snippet
from app.services.llm_service import create_llm
from app.services.mcp_tools import (
    find_employee_tool,
    lookup_ticket_tool,
    search_tickets_tool,
    send_notification_tool,
    get_document_info_tool,
    list_documents_tool,
    search_document_tool,
)
from app.services.query_rewrite_service import (
    create_standalone_query,
)


logger = logging.getLogger("documind.ai")


TOOLS = [
    search_document_tool,
    get_document_info_tool,
    list_documents_tool,
    lookup_ticket_tool,
    search_tickets_tool,
    find_employee_tool,
    send_notification_tool,
]

# Tools only admins may use (employees never see or run them).
ADMIN_ONLY_TOOLS = {"send_notification_tool"}

# Tools that return tickets; employees only see their own departments' tickets.
TICKET_TOOLS = {"lookup_ticket_tool", "search_tickets_tool"}

TOOLS_BY_NAME = {
    tool.name: tool
    for tool in TOOLS
}


def add_source(
    sources: list[dict],
    item: dict,
) -> None:

    source = {
        "document_id": item["document_id"],
        "document_name": item.get("document_name"),
        "page": item["page_number"],
        "score": item.get("score"),
        "snippet": make_snippet(item.get("text")),
    }

    for existing in sources:

        if (
            existing["document_id"] == source["document_id"]
            and existing["page"] == source["page"]
        ):
            # Same page found again: keep the closest match (lowest distance).
            old, new = existing["score"], source["score"]

            if new is not None and (old is None or new < old):
                existing.update(source)

            return

    sources.append(source)


def extract_error(
    result: object,
) -> str | None:

    if isinstance(result, dict) and "error" in result:
        return str(result["error"])

    if isinstance(result, list):

        for item in result:

            if isinstance(item, dict) and "error" in item:
                return str(item["error"])

    return None


def scope_ticket_result(
    tool_name: str,
    tool_args: dict,
    result: object,
    user_role: str,
    allowed_workspaces: list[str] | None,
) -> object:
    """Employees only see tickets whose department matches one of their workspaces.

    Departments are matched to workspace ids ("IT" ticket <-> "it" workspace).
    A forbidden ticket looks exactly like a missing one. The employee directory
    stays company-wide on purpose: you need it to find who to contact.
    """
    if user_role == "admin" or tool_name not in TICKET_TOOLS:
        return result

    allowed = {workspace.lower() for workspace in allowed_workspaces or []}

    def visible(ticket: object) -> bool:
        return (
            isinstance(ticket, dict)
            and str(ticket.get("department", "")).lower() in allowed
        )

    if tool_name == "lookup_ticket_tool":
        if isinstance(result, dict) and "error" not in result and not visible(result):
            return {
                "error": "Ticket not found.",
                "ticket_id": tool_args.get("ticket_id"),
            }
        return result

    if isinstance(result, list):
        return [ticket for ticket in result if visible(ticket)]

    return result


def history_to_messages(
    history: list[ChatMessage] | None,
) -> list[AnyMessage]:

    messages: list[AnyMessage] = []

    for entry in history or []:

        if not entry.content.strip():
            continue

        if entry.role == "user":
            messages.append(
                HumanMessage(
                    content=entry.content
                )
            )

        elif entry.role == "assistant":
            messages.append(
                AIMessage(
                    content=entry.content
                )
            )

    return messages


async def run_agent(
    question: str,
    document_ids: list[str],
    max_steps: int = 5,
    history: list[ChatMessage] | None = None,
    user_role: str = "employee",
    allowed_workspaces: list[str] | None = None,
) -> dict:

    llm = create_llm()

    available_tools = [
        tool
        for tool in TOOLS
        if user_role == "admin" or tool.name not in ADMIN_ONLY_TOOLS
    ]
    llm_with_tools = llm.bind_tools(available_tools)

    history_messages = history_to_messages(
        history
    )

    messages: list[AnyMessage] = list(history_messages)

    messages.append(
        HumanMessage(
            content=question
        )
    )

    traces = []
    sources = []

    # Always search all selected documents first.
    if document_ids:

        retrieval_query = await create_standalone_query(
            question,
            history_messages,
        )

        retrieved_contexts = []

        for document_id in document_ids:

            search_args = {
                "document_id": document_id,
                "query": retrieval_query,
                "k": 3,
            }

            try:
                result = await search_document_tool.ainvoke(
                    search_args
                )

            except Exception as exc:
                logger.exception(
                    "search_document_tool failed for document %s",
                    document_id,
                )
                result = {"error": str(exc)}

            error = extract_error(result)

            if isinstance(result, list):

                for item in result:

                    if (
                        isinstance(item, dict)
                        and "document_id" in item
                        and "page_number" in item
                    ):
                        add_source(sources, item)

            traces.append(
                {
                    "tool": "search_document_tool",
                    "arguments": search_args,
                    "result_summary": str(result)[:500],
                    "ok": error is None,
                }
            )

            retrieved_contexts.append(
                f"Document ID: {document_id}\n"
                f"Retrieved context:\n{result}"
            )

        messages.append(
            HumanMessage(
                content=(
                    "Use the following retrieved document contexts "
                    "to answer the question. Consider information from "
                    "all selected documents. Do not use your general "
                    "knowledge when the answer is not present in these "
                    "contexts.\n\n"
                    + "\n\n---\n\n".join(retrieved_contexts)
                )
            )
        )

    for _ in range(max_steps):

        response = await llm_with_tools.ainvoke(messages)

        messages.append(response)

        if not response.tool_calls:
            return {
                "answer": str(response.content),
                "traces": traces,
                "sources": sources,
            }

        for tool_call in response.tool_calls:

            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if (
                tool_name == "search_document_tool"
                and not tool_args.get("document_id")
            ):
                if not document_ids:
                    raise ValueError(
                        "No document_id available for document search."
                    )

                tool_args["document_id"] = document_ids[0]

            tool = TOOLS_BY_NAME.get(tool_name)
            error: str | None = None

            requested_document = tool_args.get("document_id")

            if (
                tool_name in ADMIN_ONLY_TOOLS
                and user_role != "admin"
            ):
                error = (
                    "Access denied: this tool requires admin access."
                )
                result = error

            elif (
                requested_document
                and requested_document not in document_ids
            ):
                error = (
                    "Access denied: document is not part of the "
                    "selected documents."
                )
                result = error

            elif tool is None:
                error = f"Unknown tool: {tool_name}"
                result = error

            else:
                try:
                    result = await tool.ainvoke(tool_args)

                except Exception as exc:
                    logger.exception(
                        "Tool %s failed",
                        tool_name,
                    )
                    error = str(exc)
                    result = f"Tool call failed: {exc}"

            if (
                error is None
                and tool_name == "list_documents_tool"
                and isinstance(result, list)
            ):
                result = [
                    item
                    for item in result
                    if isinstance(item, dict)
                    and item.get("document_id") in document_ids
                ]

            if error is None:
                result = scope_ticket_result(
                    tool_name,
                    tool_args,
                    result,
                    user_role,
                    allowed_workspaces,
                )
                error = extract_error(result)

            if tool_name == "search_document_tool":

                if isinstance(result, list):

                    for item in result:

                        if (
                            isinstance(item, dict)
                            and "document_id" in item
                            and "page_number" in item
                        ):
                            add_source(sources, item)

            traces.append(
                {
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result_summary": str(result)[:500],
                    "ok": error is None,
                }
            )

            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )

    traces.append(
        {
            "tool": "agent_loop",
            "arguments": {"max_steps": max_steps},
            "result_summary": (
                "Agent reached max_steps before producing a "
                "final answer."
            ),
            "ok": False,
        }
    )

    return {
        "answer": (
            "I could not finish answering within the allowed "
            "number of steps. Please try again or ask a more "
            "specific question."
        ),
        "traces": traces,
        "sources": sources,
    }