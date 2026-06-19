from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import BaseModel


class InterviewReportModel(BaseModel):
    """Final analysis report generated after an interview finishes."""

    __tablename__ = "interview_reports"
    __table_args__ = (Index("idx_interview_reports_interview_id", "interview_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interview_sessions.id"),
        nullable=False,
        unique=True,
        comment="面试会话表ID",
    )
    overall_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="总体评分",
    )
    technical_analysis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="技术能力分析",
    )
    communication_analysis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="表达能力分析",
    )
    weakness_points: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="薄弱知识点",
    )
    improvement_suggestions: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="改进建议",
    )
    recommended_training: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="推荐训练方向",
    )
    raw_report_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Agent原始结构化报告",
    )

    interview = relationship("InterviewSessionModel", back_populates="report")
