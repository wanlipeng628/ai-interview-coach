from dataclasses import dataclass


@dataclass(slots=True)
class InterviewReport:
    session_id: str
    overall_score: float
    technical_analysis: str
    communication_analysis: str
    project_analysis: str
    weakness_points: list[dict]
    improvement_suggestions: list[dict]
    recommended_training: list[dict]
    raw_report_json: dict


@dataclass(slots=True)
class InterviewReportListItem:
    session_id: str
    job_role: str
    overall_score: float
    report_time: str
    interview_status: str
    report_status: str = "GENERATED"
