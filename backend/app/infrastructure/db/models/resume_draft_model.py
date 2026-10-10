from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import BaseModel


class ResumeDraftModel(BaseModel):
    """Conversational resume draft aggregate persistence model."""

    __tablename__ = "resume_drafts"
    __table_args__ = (
        Index("idx_resume_drafts_user_id", "user_id"),
        Index("idx_resume_drafts_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="用户ID",
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="对外暴露的草稿ID",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="IN_PROGRESS",
        comment="状态：IN_PROGRESS/COMPLETED",
    )
    stage: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="BASIC",
        comment="当前分节：BASIC/EDUCATION/WORK/PROJECT/SKILL/INTENT/DONE",
    )
    messages: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="对话历史：[{role, content, stage, create_time}]",
    )
    sections: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="结构化收集结果",
    )
    follow_up_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="当前分节已追问次数",
    )
    target_role: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="用户目标岗位",
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="默认简历",
        comment="简历标题",
    )
    profile_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="finalize 后关联的 resume_profiles.id",
    )
