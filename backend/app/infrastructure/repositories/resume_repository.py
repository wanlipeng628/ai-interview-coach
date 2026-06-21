from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.resume.resume_dto import ResumeProfileResponse
from app.infrastructure.db.database import get_db_session
from app.infrastructure.db.models.resume_model import ResumeProfileModel


class ResumeRepository:
    """Persistence operations for resume profiles."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_default(self, user_id: int) -> ResumeProfileResponse | None:
        statement = (
            select(ResumeProfileModel)
            .where(
                ResumeProfileModel.user_id == user_id,
                ResumeProfileModel.is_default.is_(True),
            )
            .order_by(ResumeProfileModel.update_time.desc(), ResumeProfileModel.id.desc())
            .limit(1)
        )
        model = self.db.execute(statement).scalar_one_or_none()
        return self._to_response(model) if model else None

    def upsert_default(
        self,
        user_id: int,
        title: str,
        content: str,
    ) -> ResumeProfileResponse:
        model = self.db.execute(
            select(ResumeProfileModel).where(
                ResumeProfileModel.user_id == user_id,
                ResumeProfileModel.is_default.is_(True),
            )
        ).scalar_one_or_none()

        summary = self._build_summary(content)
        if model is None:
            model = ResumeProfileModel(
                user_id=user_id,
                title=title,
                content=content,
                summary=summary,
                is_default=True,
            )
            self.db.add(model)
        else:
            model.title = title
            model.content = content
            model.summary = summary

        self.db.commit()
        self.db.refresh(model)
        return self._to_response(model)

    def _to_response(self, model: ResumeProfileModel) -> ResumeProfileResponse:
        return ResumeProfileResponse(
            id=model.id,
            title=model.title,
            content=model.content,
            summary=model.summary,
            is_default=model.is_default,
            update_time=model.update_time.isoformat() if model.update_time else "",
        )

    def _build_summary(self, content: str) -> str:
        text = " ".join(content.split())
        return text[:160]


def get_resume_repository(db: Session = Depends(get_db_session)) -> ResumeRepository:
    return ResumeRepository(db)
