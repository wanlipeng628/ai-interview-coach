import re

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.resume.resume_dto import ResumeProfileResponse
from app.infrastructure.db.database import get_db_session
from app.infrastructure.db.models.resume_model import ResumeProfileModel

# 摘要要输出纯文本：剥离 Markdown 标记与多余符号，避免调用方以纯文本渲染时
# 直接显示 #、**、--- 等标记（结果层 / 简历页都按纯文本展示 summary）。
_FENCE_LINE_PATTERN = re.compile(r"^\s*```[^\n]*$", re.MULTILINE)
_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HR_PATTERN = re.compile(
    r"^\s*(?:\*\s*){3,}$|^\s*(?:-\s*){3,}$|^\s*(?:_\s*){3,}$", re.MULTILINE
)
_HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s*", re.MULTILINE)
_LIST_MARKER_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_BLOCKQUOTE_PATTERN = re.compile(r"^\s*>\s?", re.MULTILINE)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_ASCII_TABLE_PIPE_PATTERN = re.compile(r"\s*\|\s*")
_EMPHASIS_PATTERN = re.compile(r"\*\*|__|`|\*")


class ResumeRepository:
    """Persistence operations for resume profiles."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_default(self, user_id: int) -> ResumeProfileResponse | None:
        statement = (
            select(ResumeProfileModel)
            .where(
                ResumeProfileModel.user_id == user_id,
                ResumeProfileModel.is_default.is_(True),
            )
            .order_by(ResumeProfileModel.update_time.desc(), ResumeProfileModel.id.desc())
            .limit(1)
        )
        model = self.db.execute(statement).scalar_one_or_none()
        return self._to_response(model) if model else None

    def upsert_default(
        self,
        user_id: int,
        title: str,
        content: str,
    ) -> ResumeProfileResponse:
        model = self.db.execute(
            select(ResumeProfileModel).where(
                ResumeProfileModel.user_id == user_id,
                ResumeProfileModel.is_default.is_(True),
            )
        ).scalar_one_or_none()

        summary = self._build_summary(content)
        if model is None:
            model = ResumeProfileModel(
                user_id=user_id,
                title=title,
                content=content,
                summary=summary,
                is_default=True,
            )
            self.db.add(model)
        else:
            model.title = title
            model.content = content
            model.summary = summary

        self.db.commit()
        self.db.refresh(model)
        return self._to_response(model)

    def _to_response(self, model: ResumeProfileModel) -> ResumeProfileResponse:
        return ResumeProfileResponse(
            id=model.id,
            title=model.title,
            content=model.content,
            summary=model.summary,
            is_default=model.is_default,
            update_time=model.update_time.isoformat() if model.update_time else "",
        )

    @staticmethod
    def _build_summary(content: str) -> str:
        """把 Markdown 简历压成一句纯文本摘要。

        先剥离 Markdown 标记（标题 #、强调 **、列表符号、分隔线 ---、链接、代码围栏
        与行内代码、表格竖线等），再折叠空白取前 160 字，保证纯文本渲染下无标记符号。
        这里只去掉围栏标记行、保留围栏内文本，避免模型整体用 ``` 包裹正文时摘要被清空。
        """
        text = content or ""
        text = _FENCE_LINE_PATTERN.sub(" ", text)
        text = _IMAGE_PATTERN.sub(r"\1", text)
        text = _LINK_PATTERN.sub(r"\1", text)
        text = _HR_PATTERN.sub(" ", text)
        text = _BLOCKQUOTE_PATTERN.sub("", text)
        text = _HEADING_PATTERN.sub("", text)
        text = _LIST_MARKER_PATTERN.sub("", text)
        text = _ASCII_TABLE_PIPE_PATTERN.sub(" ", text)
        text = _HTML_TAG_PATTERN.sub(" ", text)
        text = _EMPHASIS_PATTERN.sub("", text)
        text = " ".join(text.split())
        return text[:160]


def get_resume_repository(db: Session = Depends(get_db_session)) -> ResumeRepository:
    return ResumeRepository(db)
