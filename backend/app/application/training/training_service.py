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
from app.infrastructure.agent.training_agent import TrainingAgent
from app.infrastructure.repositories.training_repository import TrainingRepository


class TrainingService:
    """Coordinates training task use cases."""

    VALID_STATUS = {"TODO", "IN_PROGRESS", "DONE"}

    def __init__(
        self,
        repository: TrainingRepository,
        training_agent: TrainingAgent | None = None,
    ) -> None:
        self._repository = repository
        self._training_agent = training_agent

    def list_tasks(self, user_id: int) -> list[TrainingTaskResponse]:
        return self._repository.list_tasks(user_id)

    def get_task_detail(self, user_id: int, task_id: int) -> TrainingTaskDetailResponse:
        task = self._repository.get_task_detail(user_id, task_id)
        if task is None:
            raise ValueError("Training task not found")
        return task

    def start_training(self, user_id: int, task_id: int) -> StartTrainingResponse:
        task = self._repository.get_task(user_id, task_id)
        if task is None:
            raise ValueError("Training task not found")

        latest_session = self._repository.get_latest_session(user_id, task_id)
        if latest_session is not None and latest_session.status == "IN_PROGRESS":
            messages = self._repository.list_messages(user_id, latest_session.id)
            first_question = next(
                (message.content for message in messages if message.role == "AI_COACH"),
                "",
            )
            return StartTrainingResponse(
                session_id=latest_session.id,
                task=self.get_task_detail(user_id, task_id),
                first_question=first_question,
                messages=messages,
            )

        session = self._repository.create_session(user_id, task_id)
        agent = self._training_agent or TrainingAgent()
        first_question = agent.build_first_question(task.title, task.reason)
        self._repository.append_message(
            user_id=user_id,
            session_id=session.id,
            role="AI_COACH",
            content=first_question,
            round_no=1,
        )
        return StartTrainingResponse(
            session_id=session.id,
            task=self.get_task_detail(user_id, task_id),
            first_question=first_question,
            messages=self._repository.list_messages(user_id, session.id),
        )

    def submit_answer(
        self,
        user_id: int,
        session_id: int,
        request: SubmitTrainingAnswerRequest,
    ) -> SubmitTrainingAnswerResponse:
        data = self._repository.get_session_with_task(user_id, session_id)
        if data is None:
            raise ValueError("Training session not found")
        session, task = data
        if session.status != "IN_PROGRESS":
            raise ValueError("Training session is not in progress")

        answer = request.answer.strip()
        if not answer:
            raise ValueError("Answer cannot be empty")

        question = self._repository.get_latest_question(user_id, session_id)
        if question is None:
            raise ValueError("Training question not found")

        self._repository.append_message(
            user_id=user_id,
            session_id=session_id,
            role="USER",
            content=answer,
            round_no=question.round_no,
        )

        agent = self._training_agent or TrainingAgent()
        turn = agent.review_answer(
            task_title=task.title,
            task_reason=task.reason,
            question=question.content,
            answer=answer,
            history=self._repository.list_message_dicts(user_id, session_id),
        )
        next_round = question.round_no + 1
        if turn.next_question and not turn.is_finished:
            self._repository.append_message(
                user_id=user_id,
                session_id=session_id,
                role="AI_COACH",
                content=turn.next_question,
                round_no=next_round,
                feedback=turn.feedback,
                reference_points=turn.reference_points,
                sample_answer=turn.sample_answer,
            )
            self._repository.advance_round(session_id, next_round)
        else:
            self._repository.append_message(
                user_id=user_id,
                session_id=session_id,
                role="AI_COACH",
                content="本次专项训练已经完成，你可以回到训练列表继续处理其他薄弱点。",
                round_no=next_round,
                feedback=turn.feedback,
                reference_points=turn.reference_points,
                sample_answer=turn.sample_answer,
            )
            self._repository.finish_session(user_id, session_id)

        return SubmitTrainingAnswerResponse(
            session_id=session_id,
            round_no=question.round_no,
            feedback=turn.feedback,
            reference_points=turn.reference_points,
            sample_answer=turn.sample_answer,
            next_question=turn.next_question,
            is_finished=turn.is_finished or not turn.next_question,
            messages=self._repository.list_messages(user_id, session_id),
        )

    def finish_training(self, user_id: int, session_id: int) -> FinishTrainingResponse:
        self._repository.finish_session(user_id, session_id)
        return FinishTrainingResponse(session_id=session_id)

    def update_status(
        self,
        user_id: int,
        task_id: int,
        request: UpdateTrainingTaskStatusRequest,
    ) -> SuccessResponse:
        status = request.status.upper()
        if status not in self.VALID_STATUS:
            raise ValueError("Invalid training task status")
        self._repository.update_status(user_id, task_id, status)
        return SuccessResponse(success=True)
