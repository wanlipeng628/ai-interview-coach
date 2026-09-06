from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.application.resume.file_parser import UnsupportedFileTypeError
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


@router.post("/upload", response_model=ResumeProfileResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    service: ResumeService = Depends(get_resume_service),
) -> ResumeProfileResponse:
    """Upload a resume file, extract text, and save as the user's default resume."""
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required",
        )

    file_bytes = await file.read()
    try:
        return service.upload_resume(
            user_id=user_id,
            filename=file.filename,
            file_bytes=file_bytes,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
