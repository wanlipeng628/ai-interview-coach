from pydantic import BaseModel, Field


class InterviewReportListItemResponse(BaseModel):
    session_id: str
    job_role: str
    overall_score: float = Field(..., ge=0, le=100)
    report_time: str
    interview_status: str
    report_status: str = "GENERATED"


class WeaknessPointDTO(BaseModel):
    name: str
    reason: str
    severity: str = "Medium"


class TrainingItemDTO(BaseModel):
    title: str
    description: str
    priority: str = "Medium"


class ReportEvidenceItemDTO(BaseModel):
    title: str
    related_weakness: str
    question: str
    answer_summary: str
    evidence_reason: str
    impact: str = "Medium"


class InterviewReportResponse(BaseModel):
    session_id: str
    overall_score: float = Field(..., ge=0, le=100)
    technical_analysis: str
    communication_analysis: str
    project_analysis: str
    weakness_points: list[WeaknessPointDTO]
    improvement_suggestions: list[TrainingItemDTO]
    recommended_training: list[TrainingItemDTO]
    evidence_items: list[ReportEvidenceItemDTO] = []
    raw_report_json: dict
