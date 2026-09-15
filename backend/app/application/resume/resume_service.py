from pathlib import Path

from app.application.resume.file_parser import parse_resume_file
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

    def upload_resume(
        self,
        user_id: int,
        filename: str,
        file_bytes: bytes,
    ) -> ResumeProfileResponse:
        """Parse an uploaded resume file and save it as the user's default resume.

        Returns the saved resume profile.
        Raises ValueError on unsupported file types or empty content.
        """
        content = parse_resume_file(filename, file_bytes)
        if not content.strip():
            raise ValueError("Resume file contains no extractable text")

        # 用文件名（去扩展名）作为简历标题
        title = Path(filename).stem or "上传简历"
        if len(title) > 128:
            title = title[:128]

        return self._repository.upsert_default(
            user_id=user_id,
            title=title.strip(),
            content=content.strip(),
        )
