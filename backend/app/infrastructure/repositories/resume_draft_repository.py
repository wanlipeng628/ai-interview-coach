import copy

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.resume.entities import ResumeDraft
from app.infrastructure.db.database import get_db_session
from app.infrastructure.db.models.resume_draft_model import ResumeDraftModel


class ResumeDraftRepository:
    """Persistence operations for conversational resume drafts."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, draft: ResumeDraft) -> None:
        model = ResumeDraftModel(
            user_id=draft.user_id,
            session_id=draft.session_id,
            status=draft.status,
            stage=draft.stage,
            messages=copy.deepcopy(draft.messages),
            sections=copy.deepcopy(draft.sections),
            follow_up_count=draft.follow_up_count,
            target_role=draft.target_role,
            title=draft.title,
            profile_id=draft.profile_id,
        )
        self.db.add(model)
        self.db.commit()

    def get(self, user_id: int, session_id: str) -> ResumeDraft | None:
        model = self.db.execute(
            select(ResumeDraftModel).where(
                ResumeDraftModel.user_id == user_id,
                ResumeDraftModel.session_id == session_id,
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    def save(self, draft: ResumeDraft) -> None:
        model = self.db.execute(
            select(ResumeDraftModel).where(
                ResumeDraftModel.user_id == draft.user_id,
                ResumeDraftModel.session_id == draft.session_id,
            )
        ).scalar_one_or_none()
        if model is None:
            raise ValueError("Resume draft not found")

        # JSONB 字段整体重新赋值，确保变更被 SQLAlchemy 识别并落库
        model.status = draft.status
        model.stage = draft.stage
        model.messages = copy.deepcopy(draft.messages)
        model.sections = copy.deepcopy(draft.sections)
        model.follow_up_count = draft.follow_up_count
        model.target_role = draft.target_role
        model.title = draft.title
        model.profile_id = draft.profile_id
        self.db.commit()

    @staticmethod
    def _to_entity(model: ResumeDraftModel) -> ResumeDraft:
        return ResumeDraft(
            session_id=model.session_id,
            user_id=model.user_id,
            status=model.status,
            stage=model.stage,
            messages=list(model.messages or []),
            sections=dict(model.sections or {}),
            follow_up_count=model.follow_up_count,
            target_role=model.target_role,
            title=model.title,
            profile_id=model.profile_id,
        )


def get_resume_draft_repository(db: Session = Depends(get_db_session)) -> ResumeDraftRepository:
    return ResumeDraftRepository(db)
