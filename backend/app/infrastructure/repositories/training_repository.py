from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.training.training_dto import (
    TrainingMessageResponse,
    TrainingTaskDetailResponse,
    TrainingTaskResponse,
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.db.models.training_model import (
    TrainingMessageModel,
    TrainingSessionModel,
    TrainingTaskModel,
)
from app.infrastructure.db.models.interview_model import InterviewSessionModel
from app.infrastructure.db.models.report_model import InterviewReportModel


class TrainingRepository:
    """Persistence operations for training tasks."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_tasks(self, user_id: int) -> list[TrainingTaskResponse]:
        statement = (
            select(TrainingTaskModel)
            .where(TrainingTaskModel.user_id == user_id)
            .order_by(TrainingTaskModel.create_time.desc(), TrainingTaskModel.id.desc())
        )
        rows = self.db.execute(statement).scalars().all()
        return [self._to_response(row) for row in rows]

    def get_task(self, user_id: int, task_id: int) -> TrainingTaskModel | None:
        return self.db.execute(
            select(TrainingTaskModel).where(
                TrainingTaskModel.user_id == user_id,
                TrainingTaskModel.id == task_id,
            )
        ).scalar_one_or_none()

    def get_task_detail(self, user_id: int, task_id: int) -> TrainingTaskDetailResponse | None:
        task = self.get_task(user_id, task_id)
        if task is None:
            return None
        latest_session = self.get_latest_session(user_id, task_id)
        response = self._to_detail_response(task)
        if latest_session is not None:
            response.latest_session_id = latest_session.id
            response.latest_session_status = latest_session.status
        return response

    def get_latest_session(self, user_id: int, task_id: int) -> TrainingSessionModel | None:
        return self.db.execute(
            select(TrainingSessionModel)
            .where(
                TrainingSessionModel.user_id == user_id,
                TrainingSessionModel.task_id == task_id,
            )
            .order_by(TrainingSessionModel.create_time.desc(), TrainingSessionModel.id.desc())
        ).scalar_one_or_none()

    def create_session(self, user_id: int, task_id: int) -> TrainingSessionModel:
        session = TrainingSessionModel(user_id=user_id, task_id=task_id, status="IN_PROGRESS")
        self.db.add(session)
        self.db.flush()
        self.update_status(user_id, task_id, "IN_PROGRESS", commit=False)
        self.db.commit()
        self.db.refresh(session)
        return session

    def append_message(
        self,
        user_id: int,
        session_id: int,
        role: str,
        content: str,
        round_no: int,
        feedback: str | None = None,
        reference_points: list[str] | None = None,
        sample_answer: str | None = None,
        commit: bool = True,
    ) -> TrainingMessageModel:
        message = TrainingMessageModel(
            user_id=user_id,
            training_session_id=session_id,
            role=role,
            content=content,
            round_no=round_no,
            feedback=feedback,
            reference_points=reference_points,
            sample_answer=sample_answer,
        )
        self.db.add(message)
        if commit:
            self.db.commit()
            self.db.refresh(message)
        return message

    def list_messages(self, user_id: int, session_id: int) -> list[TrainingMessageResponse]:
        rows = self.db.execute(
            select(TrainingMessageModel)
            .where(
                TrainingMessageModel.user_id == user_id,
                TrainingMessageModel.training_session_id == session_id,
            )
            .order_by(TrainingMessageModel.round_no.asc(), TrainingMessageModel.id.asc())
        ).scalars().all()
        return [self._to_message_response(row) for row in rows]

    def list_message_dicts(self, user_id: int, session_id: int) -> list[dict[str, str]]:
        return [
            {
                "role": item.role,
                "content": item.content,
                "round_no": str(item.round_no),
            }
            for item in self.db.execute(
                select(TrainingMessageModel)
                .where(
                    TrainingMessageModel.user_id == user_id,
                    TrainingMessageModel.training_session_id == session_id,
                )
                .order_by(TrainingMessageModel.round_no.asc(), TrainingMessageModel.id.asc())
            ).scalars().all()
        ]

    def get_session_with_task(
        self,
        user_id: int,
        session_id: int,
    ) -> tuple[TrainingSessionModel, TrainingTaskModel] | None:
        session = self.db.execute(
            select(TrainingSessionModel).where(
                TrainingSessionModel.user_id == user_id,
                TrainingSessionModel.id == session_id,
            )
        ).scalar_one_or_none()
        if session is None:
            return None
        task = self.get_task(user_id, session.task_id)
        if task is None:
            return None
        return session, task

    def get_latest_question(self, user_id: int, session_id: int) -> TrainingMessageModel | None:
        return self.db.execute(
            select(TrainingMessageModel)
            .where(
                TrainingMessageModel.user_id == user_id,
                TrainingMessageModel.training_session_id == session_id,
                TrainingMessageModel.role == "AI_COACH",
            )
            .order_by(TrainingMessageModel.round_no.desc(), TrainingMessageModel.id.desc())
            .limit(1)
        ).scalar_one_or_none()

    def advance_round(self, session_id: int, round_no: int, commit: bool = True) -> None:
        session = self.db.get(TrainingSessionModel, session_id)
        if session is None:
            raise ValueError("Training session not found")
        session.current_round = round_no
        if commit:
            self.db.commit()

    def finish_session(self, user_id: int, session_id: int) -> TrainingSessionModel:
        session = self.db.execute(
            select(TrainingSessionModel).where(
                TrainingSessionModel.user_id == user_id,
                TrainingSessionModel.id == session_id,
            )
        ).scalar_one_or_none()
        if session is None:
            raise ValueError("Training session not found")
        session.status = "DONE"
        session.ended_at = datetime.now(UTC).replace(tzinfo=None)
        self.update_status(user_id, session.task_id, "DONE", commit=False)
        self.db.commit()
        return session

    def upsert_from_report_items(
        self,
        user_id: int,
        source_session_id: str,
        items: list[dict],
    ) -> None:
        for item in items:
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title:
                continue

            existing = self.db.execute(
                select(TrainingTaskModel).where(
                    TrainingTaskModel.user_id == user_id,
                    TrainingTaskModel.source_session_id == source_session_id,
                    TrainingTaskModel.title == title,
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue

            task = TrainingTaskModel(
                user_id=user_id,
                source_session_id=source_session_id,
                title=title[:128],
                reason=str(item.get("description") or item.get("reason") or ""),
                severity=str(item.get("priority") or item.get("severity") or "Medium"),
                status="TODO",
            )
            self.db.add(task)
        self.db.commit()

    def update_status(self, user_id: int, task_id: int, status: str, commit: bool = True) -> None:
        task = self.db.execute(
            select(TrainingTaskModel).where(
                TrainingTaskModel.user_id == user_id,
                TrainingTaskModel.id == task_id,
            )
        ).scalar_one_or_none()
        if task is None:
            raise ValueError("Training task not found")

        task.status = status
        if commit:
            self.db.commit()

    def _to_response(self, model: TrainingTaskModel) -> TrainingTaskResponse:
        return TrainingTaskResponse(
            id=model.id,
            title=model.title,
            source_session_id=model.source_session_id,
            has_report=self._has_report(model.user_id, model.source_session_id),
            reason=model.reason,
            severity=model.severity,
            status=model.status,
            create_time=model.create_time.isoformat() if model.create_time else "",
        )

    def _to_detail_response(self, model: TrainingTaskModel) -> TrainingTaskDetailResponse:
        return TrainingTaskDetailResponse(
            id=model.id,
            title=model.title,
            source_session_id=model.source_session_id,
            has_report=self._has_report(model.user_id, model.source_session_id),
            reason=model.reason,
            severity=model.severity,
            status=model.status,
            create_time=model.create_time.isoformat() if model.create_time else "",
        )

    def _to_message_response(self, model: TrainingMessageModel) -> TrainingMessageResponse:
        return TrainingMessageResponse(
            id=model.id,
            role=model.role,
            content=model.content,
            round_no=model.round_no,
            feedback=model.feedback,
            reference_points=model.reference_points or [],
            sample_answer=model.sample_answer,
            create_time=model.create_time.isoformat() if model.create_time else "",
        )

    def _has_report(self, user_id: int, source_session_id: str | None) -> bool:
        if not source_session_id:
            return False
        statement = (
            select(InterviewReportModel.id)
            .join(InterviewSessionModel, InterviewReportModel.interview_id == InterviewSessionModel.id)
            .where(
                InterviewSessionModel.user_id == user_id,
                InterviewSessionModel.session_id == source_session_id,
                InterviewSessionModel.is_deleted.is_(False),
            )
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none() is not None


def get_training_repository(db: Session = Depends(get_db_session)) -> TrainingRepository:
    return TrainingRepository(db)
