from app.application.resume.resume_dto import (
    ResumeProfileResponse,
    SaveResumeProfileRequest,
    SuccessResponse,
)
from app.infrastructure.repositories.resume_repository import ResumeRepository


class ResumeService:
    """Coordinates resume profile use cases."""

    def __init__(self, repository: ResumeRepository) -> None:
        self._repository = repository

    def get_profile(self, user_id: int) -> ResumeProfileResponse | None:
        return self._repository.get_default(user_id)

    def save_profile(self, user_id: int, request: SaveResumeProfileRequest) -> SuccessResponse:
        self._repository.upsert_default(
            user_id=user_id,
            title=request.title.strip(),
            content=request.content.strip(),
        )
        return SuccessResponse(success=True)
