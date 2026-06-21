from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import BaseModel


class ResumeProfileModel(BaseModel):
    """User resume profile used as interview context."""

    __tablename__ = "resume_profiles"
    __table_args__ = (
        Index("idx_resume_profiles_user_id", "user_id"),
        Index("idx_resume_profiles_default", "user_id", "is_default"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="用户ID",
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="简历标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="简历正文")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简历摘要")
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否默认简历",
    )

    user = relationship("UserModel", back_populates="resumes")
