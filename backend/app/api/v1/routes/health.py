from fastapi import APIRouter

from app.shared.config import settings

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    """Return basic application health without touching external services."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }
