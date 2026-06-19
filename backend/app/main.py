from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.api.v1.router import api_v1_router
from app.shared.config import settings
from app.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hook."""
    configure_logging()
    logger.info("application_starting", extra={"app_name": settings.app_name})
    yield
    logger.info("application_stopping", extra={"app_name": settings.app_name})


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "ok"}

    return app


app = create_app()
