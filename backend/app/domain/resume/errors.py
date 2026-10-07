"""Resume assistant domain errors.

每个异常自带面向用户的中文文案，避免把内部英文提示透给前端；
HTTP 状态码由接口层（api/routes）统一映射，领域层不感知 HTTP。
"""


class ResumeAssistantError(Exception):
    """Base class for resume assistant errors that map to an HTTP error."""


class ResumeDraftNotFoundError(ResumeAssistantError):
    """草稿不存在或不属于当前用户。"""

    def __init__(self, message: str = "简历草稿不存在或已过期，请重新开始引导") -> None:
        super().__init__(message)


class ResumeAnswerEmptyError(ResumeAssistantError):
    """提交的回答去除空白后为空。"""

    def __init__(self, message: str = "回答内容不能为空，请先说点什么") -> None:
        super().__init__(message)
