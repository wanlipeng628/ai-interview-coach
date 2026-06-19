from fastapi import APIRouter, status

router = APIRouter()


@router.get("/me", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_current_user() -> dict[str, str]:
    """Reserved endpoint for current user profile."""
    return {"message": "User profile is not implemented yet."}
