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
    # 不设 min_length：空白回答交由服务层校验，返回统一的中文错误提示，
    # 避免 Pydantic 直接抛出英文校验信息给用户。
    answer: str = Field(default="", max_length=5000)


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
    # 与前端契约保持一致：始终返回字符串（无摘要时为空串），前端按非空 string 使用
    summary: str = ""


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
