"""出题链路 thinking 模式开关的单元测试。

覆盖三层：
1. OpenAICompatibleClient.chat / chat_stream 对 thinking_mode 的透传与省略；
2. 出题链路（同步 / 流式 / 去重重生成）带上配置值；
3. 复盘链路始终不传 thinking_mode，保持思考开启。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.agent.interview_agent import InterviewerAgent
from app.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient
from app.shared.config import settings


class FakeStream:
    """最小可迭代流对象，模拟 openai SDK 的 stream 响应。"""

    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self.closed = False

    def __iter__(self):
        for text in self._texts:
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=text))]
            )

    def close(self) -> None:
        self.closed = True


def _chat_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture
def mock_openai() -> MagicMock:
    """替换模块内的 OpenAI 客户端，避免真实网络请求与 API Key 依赖。"""
    with patch(
        "app.infrastructure.llm.openai_compatible_client.OpenAI"
    ) as openai_cls, patch.object(settings, "llm_api_key", "test-key"):
        yield openai_cls


def _create_kwargs(openai_cls: MagicMock) -> dict:
    return openai_cls.return_value.chat.completions.create.call_args.kwargs


@pytest.mark.parametrize(
    ("thinking_mode", "expected"),
    [
        ("disabled", {"thinking": {"type": "disabled"}}),
        ("enabled", {"thinking": {"type": "enabled"}}),
    ],
)
def test_chat_passes_thinking_extra_body(mock_openai, thinking_mode, expected):
    mock_openai.return_value.chat.completions.create.return_value = _chat_response(
        " 问题内容 "
    )
    client = OpenAICompatibleClient()

    result = client.chat([{"role": "user", "content": "hi"}], thinking_mode=thinking_mode)
    assert result == "问题内容"

    kwargs = _create_kwargs(mock_openai)
    assert kwargs["extra_body"] == expected
    assert "stream" not in kwargs


def test_chat_omits_extra_body_when_thinking_mode_is_none(mock_openai):
    mock_openai.return_value.chat.completions.create.return_value = _chat_response("ok")
    client = OpenAICompatibleClient()

    client.chat([{"role": "user", "content": "hi"}])

    assert "extra_body" not in _create_kwargs(mock_openai)


@pytest.mark.parametrize(
    ("thinking_mode", "expected"),
    [
        ("disabled", {"thinking": {"type": "disabled"}}),
        ("enabled", {"thinking": {"type": "enabled"}}),
    ],
)
def test_chat_stream_passes_thinking_extra_body(mock_openai, thinking_mode, expected):
    stream = FakeStream(["a", "b"])
    mock_openai.return_value.chat.completions.create.return_value = stream
    client = OpenAICompatibleClient()

    chunks = list(
        client.chat_stream([{"role": "user", "content": "hi"}], thinking_mode=thinking_mode)
    )

    assert chunks == ["a", "b"]
    kwargs = _create_kwargs(mock_openai)
    assert kwargs["extra_body"] == expected
    assert kwargs["stream"] is True
    assert stream.closed is True


def test_chat_stream_omits_extra_body_when_thinking_mode_is_none(mock_openai):
    mock_openai.return_value.chat.completions.create.return_value = FakeStream([])
    client = OpenAICompatibleClient()

    list(client.chat_stream([{"role": "user", "content": "hi"}]))

    assert "extra_body" not in _create_kwargs(mock_openai)


class RecordingLLMClient:
    """记录每次调用携带的 thinking_mode，用于验证 agent 层接线。"""

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[tuple[str, str | None]] = []

    def chat(self, messages, thinking_mode=None):
        self.calls.append(("chat", thinking_mode))
        return self.content

    def chat_stream(self, messages, thinking_mode=None):
        self.calls.append(("chat_stream", thinking_mode))
        yield self.content


def _question_kwargs() -> dict:
    return {
        "job_role": "后端工程师",
        "round_no": 1,
        "duration_minutes": 30,
        "elapsed_minutes": 0,
        "direction": "BACKEND",
        "interviewer_mode": "NORMAL",
        "resume_text": "简历",
        "history": [],
    }


def test_generate_next_question_uses_configured_thinking():
    fake = RecordingLLMClient('{"decision": "continue", "question": "请自我介绍？"}')
    agent = InterviewerAgent(llm_client=fake)

    with patch.object(settings, "llm_question_thinking", "enabled"):
        agent.generate_next_question(**_question_kwargs())

    assert fake.calls == [("chat", "enabled")]


def test_generate_next_question_stream_uses_configured_thinking():
    fake = RecordingLLMClient('{"decision": "continue", "question": "请自我介绍？"}')
    agent = InterviewerAgent(llm_client=fake)

    with patch.object(settings, "llm_question_thinking", "disabled"):
        list(agent.generate_next_question_stream(**_question_kwargs()))

    assert fake.calls == [("chat_stream", "disabled")]


def test_regenerate_question_uses_configured_thinking():
    fake = RecordingLLMClient('{"question": "换个问题？"}')
    agent = InterviewerAgent(llm_client=fake)

    with patch.object(settings, "llm_question_thinking", "disabled"):
        agent.regenerate_question_avoiding_history(
            job_role="后端工程师",
            direction="BACKEND",
            interviewer_mode="NORMAL",
            duplicated_question="重复的问题？",
            history=[],
        )

    assert fake.calls == [("chat", "disabled")]


def test_generate_reviews_never_passes_thinking_mode():
    fake = RecordingLLMClient('{"reviews": {}}')
    agent = InterviewerAgent(llm_client=fake)

    agent.generate_reviews_for_session(
        job_role="后端工程师",
        direction="BACKEND",
        interviewer_mode="NORMAL",
        resume_text="简历",
        history=[{"role": "AI_INTERVIEWER", "round_no": "1", "content": "问题？"}],
        rounds=[1],
    )

    assert fake.calls == [("chat", None)]
