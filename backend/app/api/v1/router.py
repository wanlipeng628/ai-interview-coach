from fastapi import APIRouter

from app.api.v1.routes import health, interview, report, user

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, prefix="/health", tags=["Health"])
api_v1_router.include_router(user.router, prefix="/users", tags=["Users"])
api_v1_router.include_router(interview.router, prefix="/interviews", tags=["Interviews"])
api_v1_router.include_router(report.router, prefix="/reports", tags=["Reports"])
