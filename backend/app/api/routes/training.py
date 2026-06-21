from fastapi import APIRouter, Depends, HTTPException, status

from app.application.training.training_dto import (
    FinishTrainingResponse,
    StartTrainingResponse,
    SuccessResponse,
    SubmitTrainingAnswerRequest,
    SubmitTrainingAnswerResponse,
    TrainingTaskDetailResponse,
    TrainingTaskResponse,
    UpdateTrainingTaskStatusRequest,
)
from app.application.training.training_service import TrainingService
from app.infrastructure.repositories.training_repository import (
    TrainingRepository,
    get_training_repository,
)
from app.shared.constants import DEFAULT_USER_ID

router = APIRouter()


def get_current_user_id() -> int:
    return DEFAULT_USER_ID


def get_training_service(
    repository: TrainingRepository = Depends(get_training_repository),
) -> TrainingService:
    return TrainingService(repository)


@router.get("/tasks", response_model=list[TrainingTaskResponse])
async def list_training_tasks(
    user_id: int = Depends(get_current_user_id),
    service: TrainingService = Depends(get_training_service),
) -> list[TrainingTaskResponse]:
    return service.list_tasks(user_id)


@router.get("/tasks/{task_id}", response_model=TrainingTaskDetailResponse)
async def get_training_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    service: TrainingService = Depends(get_training_service),
) -> TrainingTaskDetailResponse:
    try:
        return service.get_task_detail(user_id, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/start", response_model=StartTrainingResponse)
async def start_training(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    service: TrainingService = Depends(get_training_service),
) -> StartTrainingResponse:
    try:
        return service.start_training(user_id, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/tasks/{task_id}/status", response_model=SuccessResponse)
async def update_training_task_status(
    task_id: int,
    request: UpdateTrainingTaskStatusRequest,
    user_id: int = Depends(get_current_user_id),
    service: TrainingService = Depends(get_training_service),
) -> SuccessResponse:
    try:
        return service.update_status(user_id, task_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/sessions/{session_id}/answer", response_model=SubmitTrainingAnswerResponse)
async def submit_training_answer(
    session_id: int,
    request: SubmitTrainingAnswerRequest,
    user_id: int = Depends(get_current_user_id),
    service: TrainingService = Depends(get_training_service),
) -> SubmitTrainingAnswerResponse:
    try:
        return service.submit_answer(user_id, session_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/sessions/{session_id}/finish", response_model=FinishTrainingResponse)
async def finish_training(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    service: TrainingService = Depends(get_training_service),
) -> FinishTrainingResponse:
    try:
        return service.finish_training(user_id, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
