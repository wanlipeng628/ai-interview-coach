from typing import Protocol

from app.domain.interview.entities import InterviewAnswerReview, InterviewSession


class InterviewRepository(Protocol):
    """Persistence contract for interviews."""

    def save(self, session: InterviewSession) -> None:
        """Persist an interview session."""
        ...

    def get_by_id(self, user_id: int, session_id: str) -> InterviewSession | None:
        """Find an interview session by id."""
        ...

    def get_latest_active(self, user_id: int) -> dict[str, object] | None:
        """Find latest active interview for current user."""
        ...

    def list_messages_detailed(self, user_id: int, session_id: str) -> list[dict[str, str | int]]:
        """List detailed interview messages for UI recovery."""
        ...

    def list_history(self, user_id: int, include_empty: bool = False) -> list[dict[str, object]]:
        """List interview sessions for history page."""
        ...

    def soft_delete(self, user_id: int, session_id: str) -> None:
        """Soft delete one interview session."""
        ...

    def update_validity(self, user_id: int, session_id: str, is_valid: bool) -> None:
        """Update whether an interview should be counted as valid training data."""
        ...

    def save_answer_review(
        self,
        user_id: int,
        session_id: str,
        round_no: int,
        review: InterviewAnswerReview,
    ) -> None:
        """Persist hidden answer review for one interview round."""
        ...

    def list_answer_reviews(self, user_id: int, session_id: str) -> dict[int, InterviewAnswerReview]:
        """List hidden answer reviews by round number."""
        ...

    def append_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        round_no: int,
    ) -> None:
        """Persist one interview message."""
        ...

    def advance_round(self, user_id: int, session_id: str, current_round: int) -> None:
        """Update interview current round."""
        ...

    def finish(self, user_id: int, session_id: str) -> None:
        """Mark interview as finished."""
        ...

    def list_messages(self, user_id: int, session_id: str) -> list[dict[str, str]]:
        """List interview messages for LLM context."""
        ...
