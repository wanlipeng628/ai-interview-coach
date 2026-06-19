from fastapi import APIRouter, status

router = APIRouter()


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_interview() -> dict[str, str]:
    """Reserved endpoint for starting an interview."""
    return {"message": "Interview creation is not implemented yet."}


@router.post("/{interview_id}/answers", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def submit_answer(interview_id: int) -> dict[str, str | int]:
    """Reserved endpoint for submitting a candidate answer."""
    return {"interview_id": interview_id, "message": "Answer submission is not implemented yet."}


@router.post("/{interview_id}/finish", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def finish_interview(interview_id: int) -> dict[str, str | int]:
    """Reserved endpoint for finishing an interview."""
    return {"interview_id": interview_id, "message": "Interview finishing is not implemented yet."}
