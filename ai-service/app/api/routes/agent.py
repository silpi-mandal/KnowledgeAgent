from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_current_user

from app.models.agent import ChatRequest, ChatResponse
from app.services.citation_service import build_citations, overall_confidence
from app.services.feedback_service import record_answer
from app.services.agent_service import run_agent
from app.services.agent_service import ADMIN_ONLY_TOOLS, TOOLS
from app.services.workspace_service import (
    document_workspace,
    list_all_documents,
    WorkspaceNotFoundError,
    ensure_workspace_exists,
    list_workspace_documents,
)


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:

    user_messages = [
        message
        for message in request.messages
        if message.role == "user"
    ]

    if not user_messages:
        raise HTTPException(
            status_code=400,
            detail="No user message provided.",
        )

    question = user_messages[-1].content.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="User message cannot be empty.",
        )

    last_user_index = max(
        index
        for index, message in enumerate(request.messages)
        if message.role == "user"
    )

    history = request.messages[:last_user_index]

    document_ids = list(request.document_ids)

    if request.workspace_id:
        try:
            ensure_workspace_exists(request.workspace_id)
        except WorkspaceNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found.",
            ) from None

        if not user.can_access_workspace(request.workspace_id):
            raise HTTPException(
                status_code=404,
                detail="Workspace not found.",
            )

        workspace_document_ids = [
            document["document_id"]
            for document in list_workspace_documents(request.workspace_id)
        ]

        if document_ids:
            outside = [
                document_id
                for document_id in document_ids
                if document_id not in workspace_document_ids
            ]
            if outside:
                raise HTTPException(
                    status_code=400,
                    detail="Some documents are not in this workspace.",
                )
        else:
            document_ids = workspace_document_ids

    if not document_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one document_id is required.",
        )

    if not user.is_admin:
        workspace_by_document = {
            document["document_id"]: document_workspace(document)
            for document in list_all_documents()
        }

        for document_id in document_ids:
            workspace = workspace_by_document.get(document_id)

            if workspace is None or not user.can_access_workspace(workspace):
                raise HTTPException(
                    status_code=404,
                    detail="Document not found.",
                )

    try:
        result = await run_agent(
            question=question,
            document_ids=document_ids,
            max_steps=request.max_steps,
            history=history,
            user_role=user.role,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {exc}",
        ) from exc

    citations = build_citations(result["sources"])
    best_confidence, best_level = overall_confidence(citations)

    answer_id = record_answer(
        username=user.username,
        question=question,
        answer=result["answer"],
        workspace_id=request.workspace_id,
        document_ids=document_ids,
    )

    return ChatResponse(
        answer=result["answer"],
        traces=result["traces"],
        sources=citations,
        answer_id=answer_id,
        answer_confidence=best_confidence,
        answer_confidence_level=best_level,
    )


@router.get("/tools")
def list_tools(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, list[str]]:
    return {
        "tools": [
            tool.name
            for tool in TOOLS
            if user.is_admin or tool.name not in ADMIN_ONLY_TOOLS
        ]
    }

