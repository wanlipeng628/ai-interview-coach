from fastapi import APIRouter

from app.api.routes import interview, report

api_router = APIRouter()

api_router.include_router(report.router, prefix="/interview", tags=["Interview Report"])
api_router.include_router(interview.router, prefix="/interview", tags=["Interview"])
