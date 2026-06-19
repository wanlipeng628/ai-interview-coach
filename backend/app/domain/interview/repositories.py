from typing import Protocol

from app.domain.interview.entities import InterviewAnswerReview, InterviewSession


class InterviewRepository(Protocol):
    """Persistence contract for interviews."""

    def save(self, session: InterviewSession) -> None:
        """Persist an interview session."""
        ...

    def get_by_id(self, session_id: str) -> InterviewSession | None:
        """Find an interview session by id."""
        ...

    def list_messages_detailed(self, session_id: str) -> list[dict[str, str | int]]:
        """List detailed interview messages for UI recovery."""
        ...

    def list_history(self, include_empty: bool = False) -> list[dict[str, object]]:
        """List interview sessions for history page."""
        ...

    def save_answer_review(
        self,
        session_id: str,
        round_no: int,
        review: InterviewAnswerReview,
    ) -> None:
        """Persist hidden answer review for one interview round."""
        ...

    def list_answer_reviews(self, session_id: str) -> dict[int, InterviewAnswerReview]:
        """List hidden answer reviews by round number."""
        ...

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        round_no: int,
    ) -> None:
        """Persist one interview message."""
        ...

    def advance_round(self, session_id: str, current_round: int) -> None:
        """Update interview current round."""
        ...

    def finish(self, session_id: str) -> None:
        """Mark interview as finished."""
        ...

    def list_messages(self, session_id: str) -> list[dict[str, str]]:
        """List interview messages for LLM context."""
        ...
