from fastapi import APIRouter, Depends, HTTPException, status

from app.application.resume.resume_dto import (
    ResumeProfileResponse,
    SaveResumeProfileRequest,
    SuccessResponse,
)
from app.application.resume.resume_service import ResumeService
from app.infrastructure.repositories.resume_repository import (
    ResumeRepository,
    get_resume_repository,
)
from app.shared.constants import DEFAULT_USER_ID

router = APIRouter()


def get_current_user_id() -> int:
    return DEFAULT_USER_ID


def get_resume_service(
    repository: ResumeRepository = Depends(get_resume_repository),
) -> ResumeService:
    return ResumeService(repository)


@router.get("/profile", response_model=ResumeProfileResponse)
async def get_resume_profile(
    user_id: int = Depends(get_current_user_id),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeProfileResponse:
    profile = service.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume profile not found")
    return profile


@router.put("/profile", response_model=SuccessResponse)
async def save_resume_profile(
    request: SaveResumeProfileRequest,
    user_id: int = Depends(get_current_user_id),
    service: ResumeService = Depends(get_resume_service),
) -> SuccessResponse:
    return service.save_profile(user_id, request)
