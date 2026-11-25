from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    role: Role
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None


class SourceRef(BaseModel):
    document_id: str
    document_name: str | None = None
    page: int | None = None
    score: float | None = None  # raw FAISS distance (lower = closer)
    snippet: str | None = None  # start of the retrieved passage
    confidence: float | None = None  # retrieval relevance 0-1 (higher = closer match)
    confidence_level: str | None = None  # high / medium / low


class ToolCallTrace(BaseModel):
    tool: str
    arguments: dict = Field(default_factory=dict)
    result_summary: str = ""
    ok: bool = True


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    document_ids: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    conversation_id: str | None = None
    max_steps: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str = ""
    traces: list[ToolCallTrace] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    answer_id: str | None = None  # use with POST /feedback
    answer_confidence: float | None = None  # best source relevance, None if no sources
    answer_confidence_level: str | None = None
