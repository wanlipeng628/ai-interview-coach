from fastapi import APIRouter

from app.api.routes import interview, report, resume, resume_assistant, training

api_router = APIRouter()

api_router.include_router(report.router, prefix="/interview", tags=["Interview Report"])
api_router.include_router(interview.router, prefix="/interview", tags=["Interview"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume"])
api_router.include_router(
    resume_assistant.router,
    prefix="/resume/assistant",
    tags=["Resume Assistant"],
)
api_router.include_router(training.router, prefix="/training", tags=["Training"])
