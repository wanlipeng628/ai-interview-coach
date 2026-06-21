from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.application.interview.interview_service import InterviewService
from app.domain.interview.entities import (
    InterviewAnswerReview,
    InterviewSession,
    InterviewSessionStatus,
)
from app.domain.interview.repositories import InterviewRepository
from app.infrastructure.db.database import get_db_session
from app.infrastructure.db.models.interview_model import (
    InterviewAnswerReviewModel,
    InterviewMessageModel,
    InterviewSessionModel,
)
from app.infrastructure.db.models.report_model import InterviewReportModel


class SqlAlchemyInterviewRepository:
    """SQLAlchemy implementation for interview persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, session: InterviewSession) -> None:
        model = InterviewSessionModel(
            session_id=session.session_id,
            user_id=session.user_id,
            job_role=session.job_role,
            direction=session.direction,
            interviewer_mode=session.interviewer_mode,
            status=session.status.value,
            current_round=session.current_round,
            duration_minutes=session.duration_minutes,
            max_rounds=session.max_rounds,
            started_at=session.created_at.replace(tzinfo=None),
            is_deleted=session.is_deleted,
            is_valid=session.is_valid,
        )
        self.db.add(model)
        self.db.commit()

    def get_by_id(self, user_id: int, session_id: str) -> InterviewSession | None:
        model = self._get_model_by_session_id(user_id, session_id)
        if model is None:
            return None
        return self._to_entity(model)

    def get_latest_active(self, user_id: int) -> dict[str, object] | None:
        answered_count = func.sum(
            case((InterviewMessageModel.role == "USER_CANDIDATE", 1), else_=0)
        ).label("answered_count")

        statement = (
            select(InterviewSessionModel, answered_count)
            .outerjoin(
                InterviewMessageModel,
                InterviewMessageModel.interview_id == InterviewSessionModel.id,
            )
            .where(
                InterviewSessionModel.user_id == user_id,
                InterviewSessionModel.status == InterviewSessionStatus.IN_PROGRESS.value,
                InterviewSessionModel.is_deleted.is_(False),
            )
            .group_by(InterviewSessionModel.id)
            .order_by(InterviewSessionModel.create_time.desc())
            .limit(1)
        )
        row = self.db.execute(statement).first()
        if row is None:
            return None

        model = row[0]
        return {
            "session_id": model.session_id,
            "job_role": model.job_role,
            "direction": model.direction,
            "interviewer_mode": model.interviewer_mode,
            "started_at": model.create_time.isoformat() if model.create_time else "",
            "answered_count": int(row.answered_count or 0),
        }

    def append_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        round_no: int,
    ) -> None:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        message = InterviewMessageModel(
            interview_id=interview.id,
            role=role,
            content=content,
            round_no=round_no,
        )
        self.db.add(message)
        self.db.commit()

    def advance_round(self, user_id: int, session_id: str, current_round: int) -> None:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        interview.current_round = current_round
        self.db.commit()

    def finish(self, user_id: int, session_id: str) -> None:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        interview.status = InterviewSessionStatus.FINISHED.value
        interview.ended_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()

    def soft_delete(self, user_id: int, session_id: str) -> None:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        interview.is_deleted = True
        self.db.commit()

    def update_validity(self, user_id: int, session_id: str, is_valid: bool) -> None:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        interview.is_valid = is_valid
        self.db.commit()

    def list_messages(self, user_id: int, session_id: str) -> list[dict[str, str]]:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        statement = (
            select(InterviewMessageModel)
            .where(InterviewMessageModel.interview_id == interview.id)
            .order_by(InterviewMessageModel.round_no.asc(), InterviewMessageModel.id.asc())
        )
        messages = self.db.execute(statement).scalars().all()
        return [
            {
                "role": message.role,
                "round_no": str(message.round_no),
                "content": message.content,
            }
            for message in messages
        ]

    def list_messages_detailed(
        self,
        user_id: int,
        session_id: str,
    ) -> list[dict[str, str | int]]:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        statement = (
            select(InterviewMessageModel)
            .where(InterviewMessageModel.interview_id == interview.id)
            .order_by(InterviewMessageModel.round_no.asc(), InterviewMessageModel.id.asc())
        )
        messages = self.db.execute(statement).scalars().all()
        return [
            {
                "role": message.role,
                "round_no": message.round_no,
                "content": message.content,
                "created_at": message.create_time.isoformat() if message.create_time else "",
            }
            for message in messages
        ]

    def list_history(self, user_id: int, include_empty: bool = False) -> list[dict[str, object]]:
        message_count = func.count(InterviewMessageModel.id).label("message_count")
        answered_count = func.sum(
            case((InterviewMessageModel.role == "USER_CANDIDATE", 1), else_=0)
        ).label("answered_count")

        statement = (
            select(
                InterviewSessionModel.session_id,
                InterviewSessionModel.job_role,
                InterviewSessionModel.direction,
                InterviewSessionModel.interviewer_mode,
                InterviewSessionModel.status,
                InterviewSessionModel.current_round,
                InterviewSessionModel.duration_minutes,
                InterviewSessionModel.create_time,
                InterviewSessionModel.ended_at,
                InterviewSessionModel.is_valid,
                message_count,
                answered_count,
                InterviewReportModel.id.label("report_id"),
                InterviewReportModel.overall_score,
            )
            .outerjoin(
                InterviewMessageModel,
                InterviewMessageModel.interview_id == InterviewSessionModel.id,
            )
            .outerjoin(
                InterviewReportModel,
                InterviewReportModel.interview_id == InterviewSessionModel.id,
            )
            .where(
                InterviewSessionModel.user_id == user_id,
                InterviewSessionModel.is_deleted.is_(False),
            )
            .group_by(InterviewSessionModel.id, InterviewReportModel.id)
            .order_by(InterviewSessionModel.create_time.desc())
        )
        if not include_empty:
            statement = statement.having(answered_count > 0)

        rows = self.db.execute(statement).all()
        return [
            {
                "session_id": row.session_id,
                "job_role": row.job_role,
                "direction": row.direction,
                "interviewer_mode": row.interviewer_mode,
                "status": row.status,
                "current_round": row.current_round,
                "duration_minutes": row.duration_minutes,
                "started_at": row.create_time.isoformat() if row.create_time else "",
                "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                "message_count": int(row.message_count or 0),
                "answered_count": int(row.answered_count or 0),
                "has_report": row.report_id is not None,
                "is_valid": bool(row.is_valid),
                "overall_score": float(row.overall_score) if row.overall_score is not None else None,
            }
            for row in rows
        ]

    def save_answer_review(
        self,
        user_id: int,
        session_id: str,
        round_no: int,
        review: InterviewAnswerReview,
    ) -> None:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        statement = select(InterviewAnswerReviewModel).where(
            InterviewAnswerReviewModel.interview_id == interview.id,
            InterviewAnswerReviewModel.round_no == round_no,
        )
        model = self.db.execute(statement).scalar_one_or_none()
        if model is None:
            model = InterviewAnswerReviewModel(
                interview_id=interview.id,
                round_no=round_no,
                evaluation=review.evaluation,
                reference_points=review.reference_points,
                sample_answer=review.sample_answer,
                level=review.level,
                raw_review_json=review.raw_review_json,
            )
            self.db.add(model)
        else:
            model.evaluation = review.evaluation
            model.reference_points = review.reference_points
            model.sample_answer = review.sample_answer
            model.level = review.level
            model.raw_review_json = review.raw_review_json
        self.db.commit()

    def list_answer_reviews(
        self,
        user_id: int,
        session_id: str,
    ) -> dict[int, InterviewAnswerReview]:
        interview = self._get_model_by_session_id(user_id, session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        statement = (
            select(InterviewAnswerReviewModel)
            .where(InterviewAnswerReviewModel.interview_id == interview.id)
            .order_by(InterviewAnswerReviewModel.round_no.asc())
        )
        rows = self.db.execute(statement).scalars().all()
        return {
            row.round_no: InterviewAnswerReview(
                evaluation=row.evaluation,
                reference_points=list(row.reference_points or []),
                sample_answer=row.sample_answer,
                level=row.level,
                raw_review_json=dict(row.raw_review_json or {}),
            )
            for row in rows
        }

    def _get_model_by_session_id(
        self,
        user_id: int,
        session_id: str,
    ) -> InterviewSessionModel | None:
        statement = select(InterviewSessionModel).where(
            InterviewSessionModel.user_id == user_id,
            InterviewSessionModel.session_id == session_id,
            InterviewSessionModel.is_deleted.is_(False),
        )
        return self.db.execute(statement).scalar_one_or_none()

    def _to_entity(self, model: InterviewSessionModel) -> InterviewSession:
        return InterviewSession(
            session_id=model.session_id,
            job_role=model.job_role,
            first_question="",
            user_id=model.user_id,
            status=InterviewSessionStatus(model.status),
            current_round=model.current_round,
            max_rounds=model.max_rounds,
            duration_minutes=model.duration_minutes,
            direction=model.direction,
            interviewer_mode=model.interviewer_mode,
            is_deleted=model.is_deleted,
            is_valid=model.is_valid,
            created_at=model.create_time.replace(tzinfo=UTC),
        )


def get_interview_repository(
    db: Session = Depends(get_db_session),
) -> InterviewRepository:
    return SqlAlchemyInterviewRepository(db)


def get_interview_service(
    repository: InterviewRepository = Depends(get_interview_repository),
) -> InterviewService:
    return InterviewService(repository=repository)
