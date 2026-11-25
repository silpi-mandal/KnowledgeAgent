from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentUser, get_current_user, require_admin
from app.models.feedback import (
    FeedbackCreate,
    FeedbackDetail,
    FeedbackResponse,
    FeedbackSummary,
    Rating,
)
from app.services import feedback_service as service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackCreate,
    user: CurrentUser = Depends(get_current_user),
) -> FeedbackResponse:
    """Thumbs up/down on an answer you received. Sending it again replaces your rating."""

    try:
        record = service.submit_feedback(
            payload.answer_id,
            user.username,
            payload.rating,
            payload.comment,
        )
    except service.AnswerNotFoundError:
        # also returned for other people's answers, so ids cannot be probed
        raise HTTPException(status_code=404, detail="Answer not found.") from None

    return FeedbackResponse(**record)


@router.get("/summary", response_model=FeedbackSummary)
def feedback_summary(_: CurrentUser = Depends(require_admin)) -> FeedbackSummary:
    return FeedbackSummary(**service.summarize_feedback())


@router.get("", response_model=list[FeedbackDetail])
def list_feedback(
    rating: Rating | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    _: CurrentUser = Depends(require_admin),
) -> list[FeedbackDetail]:
    return [FeedbackDetail(**item) for item in service.list_feedback(rating, limit)]
