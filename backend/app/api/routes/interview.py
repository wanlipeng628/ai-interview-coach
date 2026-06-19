from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError

from app.application.interview.interview_dto import (
    InterviewHistoryItemResponse,
    InterviewMessageResponse,
    InterviewReviewResponse,
    InterviewSessionResponse,
    FinishInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    StartInterviewRequest,
    StartInterviewResponse,
)
from app.application.interview.interview_service import InterviewService
from app.infrastructure.repositories.interview_repository import get_interview_service

router = APIRouter()


@router.post(
    "/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_interview(
    request: StartInterviewRequest,
    service: InterviewService = Depends(get_interview_service),
) -> StartInterviewResponse:
    """Create an interview session and return the first interviewer question."""
    return service.start_interview(request)


@router.get(
    "/history",
    response_model=list[InterviewHistoryItemResponse],
)
async def list_interview_history(
    include_empty: bool = False,
    service: InterviewService = Depends(get_interview_service),
) -> list[InterviewHistoryItemResponse]:
    return service.list_history(include_empty=include_empty)


@router.get(
    "/{session_id}/review",
    response_model=InterviewReviewResponse,
)
async def get_interview_review(
    session_id: str,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewReviewResponse:
    review = service.get_review(session_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return review


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
)
async def get_interview_session(
    session_id: str,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewSessionResponse:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return session


@router.get(
    "/{session_id}/messages",
    response_model=list[InterviewMessageResponse],
)
async def list_interview_messages(
    session_id: str,
    service: InterviewService = Depends(get_interview_service),
) -> list[InterviewMessageResponse]:
    try:
        return service.list_messages(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{session_id}/answer",
    response_model=SubmitAnswerResponse,
)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    service: InterviewService = Depends(get_interview_service),
) -> SubmitAnswerResponse:
    """Record a candidate answer and return the next interviewer question."""
    try:
        return service.submit_answer(session_id, request)
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
    service: InterviewService = Depends(get_interview_service),
) -> FinishInterviewResponse:
    """Manually finish an interview session."""
    try:
        return service.finish_interview(session_id)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
