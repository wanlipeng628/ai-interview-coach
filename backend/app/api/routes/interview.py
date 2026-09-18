from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError

from app.application.interview.interview_dto import (
    LatestActiveInterviewResponse,
    InterviewHistoryItemResponse,
    InterviewMessageResponse,
    InterviewReviewResponse,
    InterviewSessionResponse,
    FinishInterviewResponse,
    SuccessResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    UpdateInterviewValidityRequest,
)
from app.application.interview.interview_service import InterviewService
from app.infrastructure.repositories.interview_repository import get_interview_service
from app.shared.constants import DEFAULT_USER_ID

router = APIRouter()


def get_current_user_id() -> int:
    return DEFAULT_USER_ID


@router.post(
    "/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_interview(
    request: StartInterviewRequest,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> StartInterviewResponse:
    """Create an interview session and return the first interviewer question."""
    return service.start_interview(user_id, request)


@router.get(
    "/latest-active",
    response_model=LatestActiveInterviewResponse,
)
async def get_latest_active_interview(
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> LatestActiveInterviewResponse:
    return service.get_latest_active(user_id)


@router.get(
    "/history",
    response_model=list[InterviewHistoryItemResponse],
)
async def list_interview_history(
    include_empty: bool = False,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> list[InterviewHistoryItemResponse]:
    return service.list_history(user_id=user_id, include_empty=include_empty)


@router.get(
    "/{session_id}/review",
    response_model=InterviewReviewResponse,
)
async def get_interview_review(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewReviewResponse:
    review = service.get_review(user_id, session_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return review


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
)
async def get_interview_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewSessionResponse:
    session = service.get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return session


@router.get(
    "/{session_id}/messages",
    response_model=list[InterviewMessageResponse],
)
async def list_interview_messages(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> list[InterviewMessageResponse]:
    try:
        return service.list_messages(user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{session_id}/answer",
    response_model=SubmitAnswerResponse,
)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> SubmitAnswerResponse:
    """Record a candidate answer and return the next interviewer question."""
    try:
        return service.submit_answer(user_id, session_id, request)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {exc}",
        ) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {exc}",
        ) from exc


@router.post(
    "/{session_id}/finish",
    response_model=FinishInterviewResponse,
)
async def finish_interview(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> FinishInterviewResponse:
    """Manually finish an interview session."""
    try:
        return service.finish_interview(user_id, session_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.post(
    "/{session_id}/reviews/regenerate",
    response_model=SuccessResponse,
)
async def regenerate_interview_reviews(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> SuccessResponse:
    """Force regenerate all answer reviews in the background."""
    try:
        return service.regenerate_reviews(user_id, session_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.delete(
    "/{session_id}",
    response_model=SuccessResponse,
)
async def delete_interview(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> SuccessResponse:
    try:
        return service.delete_interview(user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/{session_id}/validity",
    response_model=SuccessResponse,
)
async def update_interview_validity(
    session_id: str,
    request: UpdateInterviewValidityRequest,
    user_id: int = Depends(get_current_user_id),
    service: InterviewService = Depends(get_interview_service),
) -> SuccessResponse:
    try:
        return service.update_validity(user_id, session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
