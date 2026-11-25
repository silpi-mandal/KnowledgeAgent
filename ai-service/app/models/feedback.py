from typing import Literal

from pydantic import BaseModel, Field

Rating = Literal["up", "down"]


class FeedbackCreate(BaseModel):
    answer_id: str = Field(min_length=1, max_length=64)
    rating: Rating
    comment: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    answer_id: str
    username: str
    rating: Rating
    comment: str = ""
    created_at: str
    updated_at: str


class FeedbackDetail(FeedbackResponse):
    """Admin view: includes the question and answer that were rated."""

    workspace_id: str | None = None
    question: str = ""
    answer: str = ""


class FeedbackSummary(BaseModel):
    total: int
    up: int
    down: int
    satisfaction: float | None = None  # up / total, None when there is no feedback
    by_workspace: dict[str, dict[str, int]] = Field(default_factory=dict)
