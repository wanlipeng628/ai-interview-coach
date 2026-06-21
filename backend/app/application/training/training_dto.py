from pydantic import BaseModel


class TrainingTaskResponse(BaseModel):
    id: int
    title: str
    source_session_id: str | None = None
    has_report: bool = False
    reason: str | None = None
    severity: str
    status: str
    create_time: str


class TrainingTaskDetailResponse(TrainingTaskResponse):
    latest_session_id: int | None = None
    latest_session_status: str | None = None


class TrainingMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    round_no: int
    feedback: str | None = None
    reference_points: list[str] = []
    sample_answer: str | None = None
    create_time: str


class StartTrainingResponse(BaseModel):
    session_id: int
    task: TrainingTaskDetailResponse
    first_question: str
    messages: list[TrainingMessageResponse]


class SubmitTrainingAnswerRequest(BaseModel):
    answer: str


class SubmitTrainingAnswerResponse(BaseModel):
    session_id: int
    round_no: int
    feedback: str
    reference_points: list[str]
    sample_answer: str
    next_question: str | None = None
    is_finished: bool = False
    messages: list[TrainingMessageResponse]


class FinishTrainingResponse(BaseModel):
    session_id: int
    is_finished: bool = True


class UpdateTrainingTaskStatusRequest(BaseModel):
    status: str


class SuccessResponse(BaseModel):
    success: bool = True
