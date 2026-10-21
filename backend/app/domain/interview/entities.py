from dataclasses import dataclass, field
from datetime import datetime
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
    user_id: int = 1
    status: InterviewSessionStatus = InterviewSessionStatus.IN_PROGRESS
    current_round: int = 1
    max_rounds: int = 999
    duration_minutes: int = 45
    direction: str | None = None
    interviewer_mode: str | None = None
    is_deleted: bool = False
    is_valid: bool = True
    # 全站时间统一用服务器本地时间（naive），不存 UTC：
    # 数据库 create_time 的 server_default=now() 也是本地，两边一致才不会差 8 小时。
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        session_id: str,
        job_role: str,
        first_question: str,
        user_id: int = 1,
        duration_minutes: int = 45,
        direction: str | None = None,
        interviewer_mode: str | None = None,
    ) -> "InterviewSession":
        return cls(
            session_id=session_id,
            job_role=job_role,
            first_question=first_question,
            user_id=user_id,
            duration_minutes=duration_minutes,
            direction=direction,
            interviewer_mode=interviewer_mode,
        )


@dataclass(slots=True)
class InterviewAnswerReview:
    """Internal review for a candidate answer in one interview round."""

    evaluation: str
    reference_points: list[str]
    sample_answer: str
    level: str
    raw_review_json: dict = field(default_factory=dict)
