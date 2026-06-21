from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import BaseModel


class TrainingTaskModel(BaseModel):
    """Training task generated from reports and answer reviews."""

    __tablename__ = "training_tasks"
    __table_args__ = (
        Index("idx_training_tasks_user_id", "user_id"),
        Index("idx_training_tasks_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="用户ID",
    )
    source_session_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="来源面试会话业务ID",
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="训练任务标题")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="生成原因")
    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="Medium",
        comment="严重程度：High/Medium/Low",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="TODO",
        comment="状态：TODO/IN_PROGRESS/DONE",
    )

    user = relationship("UserModel", back_populates="training_tasks")
    sessions = relationship("TrainingSessionModel", back_populates="task")


class TrainingSessionModel(BaseModel):
    """Interactive training session for a single training task."""

    __tablename__ = "training_sessions"
    __table_args__ = (
        Index("idx_training_sessions_user_id", "user_id"),
        Index("idx_training_sessions_task_id", "task_id"),
        Index("idx_training_sessions_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("training_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="IN_PROGRESS")
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    task = relationship("TrainingTaskModel", back_populates="sessions")
    messages = relationship(
        "TrainingMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class TrainingMessageModel(BaseModel):
    """Training question, answer and feedback message."""

    __tablename__ = "training_messages"
    __table_args__ = (
        Index("idx_training_messages_session_id", "training_session_id"),
        Index("idx_training_messages_round", "training_session_id", "round_no"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    training_session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_points: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    sample_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("TrainingSessionModel", back_populates="messages")
