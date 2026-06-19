from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class InterviewSessionStatus(StrEnum):
    """Lifecycle status for an interview session."""

    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"


@dataclass(slots=True)
class InterviewSession:
    """Interview session aggregate root."""

    session_id: str
    job_role: str
    first_question: str
    status: InterviewSessionStatus = InterviewSessionStatus.IN_PROGRESS
    current_round: int = 1
    max_rounds: int = 999
    duration_minutes: int = 45
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        session_id: str,
        job_role: str,
        first_question: str,
        duration_minutes: int = 45,
    ) -> "InterviewSession":
        return cls(
            session_id=session_id,
            job_role=job_role,
            first_question=first_question,
            duration_minutes=duration_minutes,
        )


@dataclass(slots=True)
class InterviewAnswerReview:
    """Internal review for a candidate answer in one interview round."""

    evaluation: str
    reference_points: list[str]
    sample_answer: str
    level: str
    raw_review_json: dict = field(default_factory=dict)
