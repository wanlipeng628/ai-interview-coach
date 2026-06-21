from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError

from app.application.report.report_dto import InterviewReportListItemResponse, InterviewReportResponse
from app.application.report.report_service import ReportService
from app.infrastructure.repositories.interview_repository import get_interview_repository
from app.infrastructure.repositories.report_repository import get_report_repository
from app.infrastructure.repositories.training_repository import get_training_repository
from app.shared.constants import DEFAULT_USER_ID

router = APIRouter()


def get_current_user_id() -> int:
    return DEFAULT_USER_ID


def get_report_service(
    report_repository=Depends(get_report_repository),
    interview_repository=Depends(get_interview_repository),
    training_repository=Depends(get_training_repository),
) -> ReportService:
    return ReportService(
        report_repository=report_repository,
        interview_repository=interview_repository,
        training_repository=training_repository,
    )


@router.get("/reports", response_model=list[InterviewReportListItemResponse])
async def list_reports(
    user_id: int = Depends(get_current_user_id),
    service: ReportService = Depends(get_report_service),
) -> list[InterviewReportListItemResponse]:
    return service.list_reports(user_id)


@router.get("/{session_id}/report", response_model=InterviewReportResponse)
async def get_report(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: ReportService = Depends(get_report_service),
) -> InterviewReportResponse:
    report = service.get_report(user_id, session_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.post("/{session_id}/report/generate", response_model=InterviewReportResponse)
async def generate_report(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    service: ReportService = Depends(get_report_service),
) -> InterviewReportResponse:
    try:
        return service.generate_report(user_id, session_id)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except OpenAIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
