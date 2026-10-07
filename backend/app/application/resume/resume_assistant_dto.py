from pydantic import BaseModel, Field


class StartDraftRequest(BaseModel):
    """Optional inputs when starting a conversational resume draft."""

    target_role: str | None = Field(None, max_length=128)
    title: str | None = Field(None, min_length=1, max_length=128)


class ProgressResponse(BaseModel):
    """Section progress derived from the current stage."""

    completed: list[str]
    current: str


class StartDraftResponse(BaseModel):
    draft_id: str
    status: str
    stage: str
    question: str
    progress: ProgressResponse


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)


class AnswerResponse(BaseModel):
    draft_id: str
    status: str
    stage: str
    question: str | None = None
    ready_to_finalize: bool = False
    progress: ProgressResponse


class FinalizeResponse(BaseModel):
    draft_id: str
    profile_id: int
    title: str
    content: str
    summary: str | None = None


class DraftMessageResponse(BaseModel):
    role: str
    content: str
    stage: str


class DraftDetailResponse(BaseModel):
    draft_id: str
    status: str
    stage: str
    messages: list[DraftMessageResponse]
    sections: dict
    progress: ProgressResponse
    ready_to_finalize: bool = False
