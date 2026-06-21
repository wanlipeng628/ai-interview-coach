from typing import Protocol

from app.domain.report.entities import InterviewReport, InterviewReportListItem


class ReportRepository(Protocol):
    """Persistence contract for interview reports."""

    def get_by_session_id(self, user_id: int, session_id: str) -> InterviewReport | None:
        """Get report by interview session id."""
        ...

    def list_reports(self, user_id: int, limit: int = 20) -> list[InterviewReportListItem]:
        """List generated reports ordered by report time descending."""
        ...

    def save(self, user_id: int, report: InterviewReport) -> InterviewReport:
        """Persist report."""
        ...
