from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError

from app.application.resume.resume_assistant_dto import (
    AnswerResponse,
    DraftDetailResponse,
    FinalizeResponse,
    StartDraftRequest,
    StartDraftResponse,
    SubmitAnswerRequest,
)
from app.application.resume.resume_assistant_service import ResumeAssistantService
from app.infrastructure.repositories.resume_draft_repository import (
    ResumeDraftRepository,
    get_resume_draft_repository,
)
from app.infrastructure.repositories.resume_repository import (
    ResumeRepository,
    get_resume_repository,
)
from app.shared.constants import DEFAULT_USER_ID

router = APIRouter()


def get_current_user_id() -> int:
    return DEFAULT_USER_ID


def get_resume_assistant_service(
    draft_repository: ResumeDraftRepository = Depends(get_resume_draft_repository),
    resume_repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeAssistantService:
    return ResumeAssistantService(draft_repository, resume_repository)


def _raise_draft_error(exc: ValueError) -> None:
    message = str(exc)
    if "not found" in message.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.post("/start", response_model=StartDraftResponse, status_code=status.HTTP_201_CREATED)
async def start_draft(
    request: StartDraftRequest,
    user_id: int = Depends(get_current_user_id),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> StartDraftResponse:
    """Start a conversational resume draft and return the opening question."""
    return service.start(user_id, request)


@router.post("/{draft_id}/answer", response_model=AnswerResponse)
async def submit_draft_answer(
    draft_id: str,
    request: SubmitAnswerRequest,
    user_id: int = Depends(get_current_user_id),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> AnswerResponse:
    """Record the user's answer and return the next guidance question."""
    try:
        return service.submit_answer(user_id, draft_id, request)
    except ValueError as exc:
        _raise_draft_error(exc)
    except (RuntimeError, OpenAIError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {exc}",
        ) from exc
    raise RuntimeError("unreachable")


@router.post("/{draft_id}/finalize", response_model=FinalizeResponse)
async def finalize_draft(
    draft_id: str,
    user_id: int = Depends(get_current_user_id),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> FinalizeResponse:
    """Generate the Markdown resume and persist it as the user's profile."""
    try:
        return service.finalize(user_id, draft_id)
    except ValueError as exc:
        _raise_draft_error(exc)
    except (RuntimeError, OpenAIError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {exc}",
        ) from exc
    raise RuntimeError("unreachable")


@router.get("/{draft_id}", response_model=DraftDetailResponse)
async def get_draft(
    draft_id: str,
    user_id: int = Depends(get_current_user_id),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> DraftDetailResponse:
    """Fetch the full draft state for refresh / resume conversation."""
    try:
        return service.get_draft(user_id, draft_id)
    except ValueError as exc:
        _raise_draft_error(exc)
    raise RuntimeError("unreachable")
