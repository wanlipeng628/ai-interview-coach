from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.resume.resume_assistant_dto import (
    AnswerResponse,
    DraftDetailResponse,
    FinalizeResponse,
    StartDraftRequest,
    StartDraftResponse,
    SubmitAnswerRequest,
)
from app.application.resume.resume_assistant_service import ResumeAssistantService
from app.domain.resume.errors import ResumeAssistantError, ResumeDraftNotFoundError
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

# 领域异常 → HTTP 状态码；未登记的领域异常一律按 400 处理。
# 异常自带中文文案，因此不会把内部英文提示透给用户。
_ERROR_STATUS: dict[type[ResumeAssistantError], int] = {
    ResumeDraftNotFoundError: status.HTTP_404_NOT_FOUND,
}


def get_current_user_id() -> int:
    return DEFAULT_USER_ID


def get_resume_assistant_service(
    draft_repository: ResumeDraftRepository = Depends(get_resume_draft_repository),
    resume_repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeAssistantService:
    return ResumeAssistantService(draft_repository, resume_repository)


def _raise_draft_error(exc: ResumeAssistantError) -> NoReturn:
    code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    raise HTTPException(status_code=code, detail=str(exc)) from exc


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
    except ResumeAssistantError as exc:
        _raise_draft_error(exc)


@router.post("/{draft_id}/finalize", response_model=FinalizeResponse)
async def finalize_draft(
    draft_id: str,
    user_id: int = Depends(get_current_user_id),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> FinalizeResponse:
    """Generate the Markdown resume and persist it as the user's profile."""
    try:
        return service.finalize(user_id, draft_id)
    except ResumeAssistantError as exc:
        _raise_draft_error(exc)


@router.get("/{draft_id}", response_model=DraftDetailResponse)
async def get_draft(
    draft_id: str,
    user_id: int = Depends(get_current_user_id),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> DraftDetailResponse:
    """Fetch the full draft state for refresh / resume conversation."""
    try:
        return service.get_draft(user_id, draft_id)
    except ResumeAssistantError as exc:
        _raise_draft_error(exc)
