from app.application.report.report_dto import InterviewReportListItemResponse, InterviewReportResponse
from app.domain.interview.repositories import InterviewRepository
from app.domain.report.entities import InterviewReport
from app.domain.report.repositories import ReportRepository
from app.infrastructure.agent.report_agent import ReportAgent


class ReportService:
    """Coordinates report generation and retrieval use cases."""

    def __init__(
        self,
        report_repository: ReportRepository,
        interview_repository: InterviewRepository,
        report_agent: ReportAgent | None = None,
    ) -> None:
        self._report_repository = report_repository
        self._interview_repository = interview_repository
        self._report_agent = report_agent

    def get_report(self, session_id: str) -> InterviewReportResponse | None:
        report = self._report_repository.get_by_session_id(session_id)
        return self._to_response(report) if report else None

    def list_reports(self, limit: int = 20) -> list[InterviewReportListItemResponse]:
        reports = self._report_repository.list_reports(limit=limit)
        return [
            InterviewReportListItemResponse(
                session_id=report.session_id,
                job_role=report.job_role,
                overall_score=report.overall_score,
                report_time=report.report_time,
                interview_status=report.interview_status,
                report_status=report.report_status,
            )
            for report in reports
        ]

    def generate_report(self, session_id: str) -> InterviewReportResponse:
        existing = self._report_repository.get_by_session_id(session_id)
        if existing is not None:
            return self._to_response(existing)

        interview = self._interview_repository.get_by_id(session_id)
        if interview is None:
            raise ValueError("Interview session not found")

        messages = self._interview_repository.list_messages(session_id)
        if len(messages) < 2:
            raise ValueError("Not enough interview messages to generate report")

        agent = self._report_agent or ReportAgent()
        report = agent.generate(
            session_id=session_id,
            job_role=interview.job_role,
            messages=messages,
        )
        saved_report = self._report_repository.save(report)
        return self._to_response(saved_report)

    def _to_response(self, report: InterviewReport) -> InterviewReportResponse:
        return InterviewReportResponse(
            session_id=report.session_id,
            overall_score=report.overall_score,
            technical_analysis=report.technical_analysis,
            communication_analysis=report.communication_analysis,
            project_analysis=report.project_analysis,
            weakness_points=report.weakness_points,
            improvement_suggestions=report.improvement_suggestions,
            recommended_training=report.recommended_training,
            evidence_items=report.raw_report_json.get("evidence_items", []),
            raw_report_json=report.raw_report_json,
        )
