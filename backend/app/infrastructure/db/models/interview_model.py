from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import BaseModel


class InterviewSessionModel(BaseModel):
    """Interview session aggregate persistence model."""

    __tablename__ = "interview_sessions"
    __table_args__ = (
        Index("idx_interview_sessions_status", "status"),
        Index("idx_interview_sessions_position_id", "position_id"),
        Index("idx_interview_sessions_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="面试会话业务ID",
    )
    position_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("positions.id"),
        nullable=True,
        comment="岗位ID，MVP可为空并仅使用job_role",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        default=1,
        comment="用户ID",
    )
    job_role: Mapped[str] = mapped_column(String(128), nullable=False, comment="面试岗位")
    direction: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="面试方向")
    interviewer_mode: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="面试官模式",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="IN_PROGRESS",
        comment="状态：IN_PROGRESS/FINISHED/REPORTED/CANCELLED",
    )
    current_round: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="当前轮次",
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=45,
        comment="面试时长上限，单位分钟",
    )
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=8, comment="最大轮次")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        comment="开始时间",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        comment="结束时间",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否软删除",
    )
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否作为有效训练记录",
    )

    user = relationship("UserModel", back_populates="interviews")
    position = relationship("PositionModel", back_populates="interviews")
    messages = relationship(
        "InterviewMessageModel",
        back_populates="interview",
        cascade="all, delete-orphan",
    )
    answer_reviews = relationship(
        "InterviewAnswerReviewModel",
        back_populates="interview",
        cascade="all, delete-orphan",
    )
    report = relationship(
        "InterviewReportModel",
        back_populates="interview",
        uselist=False,
        cascade="all, delete-orphan",
    )


class InterviewMessageModel(BaseModel):
    """Full interview conversation message."""

    __tablename__ = "interview_messages"
    __table_args__ = (
        Index("idx_interview_messages_interview_id", "interview_id"),
        Index("idx_interview_messages_round", "interview_id", "round_no"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interview_sessions.id"),
        nullable=False,
        comment="面试会话表ID",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="消息角色：AI_INTERVIEWER/USER_CANDIDATE/SYSTEM",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    round_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="面试轮次")
    interview = relationship("InterviewSessionModel", back_populates="messages")


class InterviewAnswerReviewModel(BaseModel):
    """Hidden per-answer review generated during the interview."""

    __tablename__ = "interview_answer_reviews"
    __table_args__ = (
        UniqueConstraint("interview_id", "round_no", name="uk_interview_answer_reviews_round"),
        Index("idx_interview_answer_reviews_interview_id", "interview_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interview_sessions.id"),
        nullable=False,
        comment="面试会话表ID",
    )
    round_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="面试轮次")
    evaluation: Mapped[str] = mapped_column(Text, nullable=False, comment="本轮回答评价")
    reference_points: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        comment="参考答题要点",
    )
    sample_answer: Mapped[str] = mapped_column(Text, nullable=False, comment="参考回答")
    level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="回答水平：good/normal/weak",
    )
    raw_review_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="模型原始复盘结构",
    )

    interview = relationship("InterviewSessionModel", back_populates="answer_reviews")
