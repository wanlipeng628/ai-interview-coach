from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.report.entities import InterviewReport, InterviewReportListItem
from app.domain.report.repositories import ReportRepository
from app.infrastructure.db.database import get_db_session
from app.infrastructure.db.models.interview_model import InterviewSessionModel
from app.infrastructure.db.models.report_model import InterviewReportModel


class SqlAlchemyReportRepository:
    """SQLAlchemy report repository."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_id(self, session_id: str) -> InterviewReport | None:
        report_model = self._get_report_model(session_id)
        if report_model is None:
            return None
        return self._to_entity(report_model)

    def list_reports(self, limit: int = 20) -> list[InterviewReportListItem]:
        statement = (
            select(InterviewReportModel)
            .join(InterviewSessionModel, InterviewReportModel.interview_id == InterviewSessionModel.id)
            .order_by(InterviewReportModel.create_time.desc(), InterviewReportModel.id.desc())
            .limit(limit)
        )
        reports = self.db.execute(statement).scalars().all()
        return [self._to_list_item(report) for report in reports]

    def save(self, report: InterviewReport) -> InterviewReport:
        interview = self._get_interview_model(report.session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        existing = self._get_report_model(report.session_id)
        if existing is not None:
            return self._to_entity(existing)

        model = InterviewReportModel(
            interview_id=interview.id,
            overall_score=report.overall_score,
            technical_analysis=report.technical_analysis,
            communication_analysis=report.communication_analysis,
            weakness_points=report.weakness_points,
            improvement_suggestions=report.improvement_suggestions,
            recommended_training=report.recommended_training,
            raw_report_json=report.raw_report_json,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_entity(model)

    def _get_interview_model(self, session_id: str) -> InterviewSessionModel | None:
        statement = select(InterviewSessionModel).where(
            InterviewSessionModel.session_id == session_id
        )
        return self.db.execute(statement).scalar_one_or_none()

    def _get_report_model(self, session_id: str) -> InterviewReportModel | None:
        interview = self._get_interview_model(session_id)
        if interview is None:
            return None
        statement = select(InterviewReportModel).where(
            InterviewReportModel.interview_id == interview.id
        )
        return self.db.execute(statement).scalar_one_or_none()

    def _to_entity(self, model: InterviewReportModel) -> InterviewReport:
        session_id = model.interview.session_id
        raw = model.raw_report_json or {}
        return InterviewReport(
            session_id=session_id,
            overall_score=float(model.overall_score or 0),
            technical_analysis=model.technical_analysis or "",
            communication_analysis=model.communication_analysis or "",
            project_analysis=str(raw.get("project_analysis", "")),
            weakness_points=model.weakness_points or [],
            improvement_suggestions=model.improvement_suggestions or [],
            recommended_training=model.recommended_training or [],
            raw_report_json=raw,
        )

    def _to_list_item(self, model: InterviewReportModel) -> InterviewReportListItem:
        interview = model.interview
        return InterviewReportListItem(
            session_id=interview.session_id,
            job_role=interview.job_role,
            overall_score=float(model.overall_score or 0),
            report_time=model.create_time.isoformat() if model.create_time else "",
            interview_status=interview.status,
        )


def get_report_repository(db: Session = Depends(get_db_session)) -> ReportRepository:
    return SqlAlchemyReportRepository(db)
