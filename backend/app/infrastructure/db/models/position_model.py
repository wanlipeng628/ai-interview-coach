from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import BaseModel


class PositionModel(BaseModel):
    """Interview position definition, such as Java developer."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="岗位名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="岗位描述")
    difficulty_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="middle",
        comment="岗位难度：junior/middle/senior",
    )
    skill_tags: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="岗位技能标签",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用",
    )

    interviews = relationship("InterviewSessionModel", back_populates="position")
