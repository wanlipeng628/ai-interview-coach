from dataclasses import dataclass, field
from enum import StrEnum


class ResumeDraftStatus(StrEnum):
    """Lifecycle status for a conversational resume draft."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# 引导分节，按固定顺序推进；DONE 表示收集结束、可生成简历
STAGE_ORDER: tuple[str, ...] = (
    "BASIC",
    "EDUCATION",
    "WORK",
    "PROJECT",
    "SKILL",
    "INTENT",
)
DONE_STAGE = "DONE"

# 同一分节最多追问轮数，超过后强制推进下一节
MAX_FOLLOW_UPS = 2


def empty_sections() -> dict:
    """Build an empty sections structure matching the API contract."""
    return {
        "basic": {"name": "", "target_role": "", "years": "", "city": ""},
        "education": [],
        "work": [],
        "projects": [],
        "skills": [],
        "intent": {"position": "", "city": "", "notes": ""},
    }


@dataclass
class ResumeDraft:
    """Conversational resume draft aggregate root."""

    session_id: str
    user_id: int
    status: str = ResumeDraftStatus.IN_PROGRESS.value
    stage: str = "BASIC"
    messages: list[dict] = field(default_factory=list)
    sections: dict = field(default_factory=empty_sections)
    follow_up_count: int = 0
    target_role: str | None = None
    title: str = "默认简历"
    profile_id: int | None = None

    @property
    def is_completed(self) -> bool:
        return self.status == ResumeDraftStatus.COMPLETED.value
