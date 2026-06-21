from pydantic import BaseModel, Field


class ResumeProfileResponse(BaseModel):
    id: int
    title: str
    content: str
    summary: str | None = None
    is_default: bool
    update_time: str


class SaveResumeProfileRequest(BaseModel):
    title: str = Field("默认简历", min_length=1, max_length=128)
    content: str = Field(..., min_length=1)


class SuccessResponse(BaseModel):
    success: bool = True
