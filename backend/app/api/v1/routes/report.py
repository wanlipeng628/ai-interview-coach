from fastapi import APIRouter, status

router = APIRouter()


@router.get("/{interview_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_report(interview_id: int) -> dict[str, str | int]:
    """Reserved endpoint for retrieving an interview report."""
    return {"interview_id": interview_id, "message": "Report retrieval is not implemented yet."}
