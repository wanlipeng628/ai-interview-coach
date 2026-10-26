"""Tests for submit_answer retry logic and failure rollback.

验证两件事：
1. _generate_next_question_with_retry 对可恢复错误重试、对不可恢复错误不重试。
2. LLM 失败时不留半成品：数据库里不会出现"有用户回答但没有下一题"的状态。
"""

from unittest.mock import MagicMock, patch

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.application.interview.interview_dto import SubmitAnswerRequest
from app.application.interview.interview_service import InterviewService
from app.domain.interview.entities import InterviewSession, InterviewSessionStatus
from app.infrastructure.agent.interview_agent import InterviewerDecision

RETRY_SLEEP_TARGET = "app.application.interview.interview_service.time.sleep"


class FakeInterviewRepository:
    """内存版 repository，用于验证消息是否被写入。"""

    def __init__(self, session: InterviewSession) -> None:
        self._session = session
        self.messages: list[dict] = []
        self.finished = False
        self.advanced_to: int | None = None

    def get_by_id(self, user_id: int, session_id: str) -> InterviewSession | None:
        return self._session

    def append_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        round_no: int,
    ) -> None:
        self.messages.append(
            {"user_id": user_id, "session_id": session_id, "role": role, "content": content, "round_no": round_no}
        )

    def list_messages(self, user_id: int, session_id: str) -> list[dict[str, str]]:
        return [
            {"role": m["role"], "round_no": str(m["round_no"]), "content": m["content"]}
            for m in self.messages
        ]

    def advance_round(self, user_id: int, session_id: str, current_round: int) -> None:
        self.advanced_to = current_round
        self._session.current_round = current_round

    def finish(self, user_id: int, session_id: str) -> None:
        self.finished = True
        self._session.status = InterviewSessionStatus.FINISHED

    def list_messages_detailed(self, user_id: int, session_id: str) -> list[dict]:
        return []

    def list_history(self, user_id: int, include_empty: bool = False) -> list[dict]:
        return []

    def list_answer_reviews(self, user_id: int, session_id: str) -> dict:
        return {}

    def save_answer_review(self, *args, **kwargs) -> None:  # noqa: D401
        pass

    def get_latest_active(self, user_id: int) -> dict | None:
        return None

    def soft_delete(self, user_id: int, session_id: str) -> None:
        pass

    def update_validity(self, user_id: int, session_id: str, is_valid: bool) -> None:
        pass


def _make_session() -> InterviewSession:
    return InterviewSession(
        session_id="test-session",
        job_role="Java开发工程师",
        first_question="请自我介绍",
        user_id=1,
        current_round=1,
        duration_minutes=45,
    )


def _make_agent_that_always_succeeds() -> MagicMock:
    agent = MagicMock()
    agent.generate_next_question.return_value = InterviewerDecision(
        decision="continue",
        question="下一个问题",
        reason="继续考察",
    )
    agent.regenerate_question_avoiding_history.return_value = None
    return agent


# === 重试行为 ===

@patch(RETRY_SLEEP_TARGET)
def test_retry_on_rate_limit_error_then_succeeds(mock_sleep: MagicMock) -> None:
    """RateLimitError 应该触发重试，第三次成功。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    # 先写一条初始问题，模拟已有的历史
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.side_effect = [
        RateLimitError(message="rate limited", response=MagicMock(), body={}),
        RateLimitError(message="rate limited", response=MagicMock(), body={}),
        InterviewerDecision(decision="continue", question="下一个问题", reason="继续"),
    ]
    agent.regenerate_question_avoiding_history.return_value = None

    service = InterviewService(repository=repo, interviewer_agent=agent)
    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert agent.generate_next_question.call_count == 3
    # 退避 3s、10s：两次重试前分别 sleep 3s 和 10s
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0][0][0] == 3.0
    assert mock_sleep.call_args_list[1][0][0] == 10.0
    assert result.next_question == "下一个问题"
    assert result.is_finished is False


@patch(RETRY_SLEEP_TARGET)
def test_retry_on_api_timeout_error(mock_sleep: MagicMock) -> None:
    """APITimeoutError 也应该触发重试。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.side_effect = [
        APITimeoutError(request=MagicMock()),
        InterviewerDecision(decision="continue", question="下一个问题", reason="继续"),
    ]
    agent.regenerate_question_avoiding_history.return_value = None

    service = InterviewService(repository=repo, interviewer_agent=agent)
    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert agent.generate_next_question.call_count == 2
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args[0][0] == 3.0
    assert result.next_question == "下一个问题"


@patch(RETRY_SLEEP_TARGET)
def test_retry_on_api_connection_error(mock_sleep: MagicMock) -> None:
    """APIConnectionError 也应该触发重试。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.side_effect = [
        APIConnectionError(message="connection refused", request=MagicMock()),
        InterviewerDecision(decision="continue", question="下一个问题", reason="继续"),
    ]
    agent.regenerate_question_avoiding_history.return_value = None

    service = InterviewService(repository=repo, interviewer_agent=agent)
    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert agent.generate_next_question.call_count == 2
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args[0][0] == 3.0
    assert result.next_question == "下一个问题"


def test_no_retry_on_runtime_error() -> None:
    """RuntimeError（不可恢复错误）不应该重试，直接抛出。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.side_effect = RuntimeError("LLM did not return next question")

    service = InterviewService(repository=repo, interviewer_agent=agent)

    with pytest.raises(RuntimeError, match="LLM did not return next question"):
        service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert agent.generate_next_question.call_count == 1


def test_no_retry_on_value_error() -> None:
    """ValueError 也不应该重试。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.side_effect = ValueError("bad input")

    service = InterviewService(repository=repo, interviewer_agent=agent)

    with pytest.raises(ValueError, match="bad input"):
        service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert agent.generate_next_question.call_count == 1


@patch(RETRY_SLEEP_TARGET)
def test_all_retries_exhausted_raises_last_error(mock_sleep: MagicMock) -> None:
    """三次都失败后，原样抛出最后一次异常。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.side_effect = [
        RateLimitError(message="rate limited 1", response=MagicMock(), body={}),
        RateLimitError(message="rate limited 2", response=MagicMock(), body={}),
        RateLimitError(message="rate limited 3", response=MagicMock(), body={}),
    ]

    service = InterviewService(repository=repo, interviewer_agent=agent)

    with pytest.raises(RateLimitError, match="rate limited 3"):
        service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert agent.generate_next_question.call_count == 3
    # 两次重试前都 sleep 了：3s 和 10s
    assert mock_sleep.call_count == 2


# === 失败不留半成品 ===

@patch(RETRY_SLEEP_TARGET)
def test_llm_failure_leaves_no_user_message(mock_sleep: MagicMock) -> None:
    """LLM 失败后，interview_messages 里不应该有该轮的用户回答。

    核心验收：模拟 LLM 抛错后，消息列表里没有该轮 USER_CANDIDATE。
    之前的实现是先写用户回答再调 LLM，失败后用户回答已经入库，
    造成"界面说失败，刷新页面答案又冒出来"的半成品状态。
    """
    session = _make_session()
    repo = FakeInterviewRepository(session)
    # 模拟已有的历史消息（第一轮问题）
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    message_count_before = len(repo.messages)

    agent = MagicMock()
    agent.generate_next_question.side_effect = RateLimitError(
        message="rate limited", response=MagicMock(), body={}
    )

    service = InterviewService(repository=repo, interviewer_agent=agent)

    with pytest.raises(RateLimitError):
        service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    # 失败后不应该有新增消息（用户回答没有被写入）
    assert len(repo.messages) == message_count_before
    user_messages_in_round_1 = [
        m for m in repo.messages if m["role"] == "USER_CANDIDATE" and m["round_no"] == 1
    ]
    assert len(user_messages_in_round_1) == 0


@patch(RETRY_SLEEP_TARGET)
def test_llm_failure_does_not_advance_round(mock_sleep: MagicMock) -> None:
    """LLM 失败后，current_round 不应该被推进。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    round_before = session.current_round

    agent = MagicMock()
    agent.generate_next_question.side_effect = RateLimitError(
        message="rate limited", response=MagicMock(), body={}
    )

    service = InterviewService(repository=repo, interviewer_agent=agent)

    with pytest.raises(RateLimitError):
        service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert session.current_round == round_before
    assert repo.advanced_to is None


def test_success_path_writes_both_messages() -> None:
    """成功路径：用户回答和下一题都被写入，顺序正确，round 被推进。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = _make_agent_that_always_succeeds()

    service = InterviewService(repository=repo, interviewer_agent=agent)
    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    # 成功后应该有 3 条消息：初始问题 + 用户回答 + 下一题
    assert len(repo.messages) == 3
    assert repo.messages[1]["role"] == "USER_CANDIDATE"
    assert repo.messages[1]["round_no"] == 1
    assert repo.messages[2]["role"] == "AI_INTERVIEWER"
    assert repo.messages[2]["round_no"] == 2
    assert repo.advanced_to == 2
    assert result.round_no == 2
    assert result.next_question == "下一个问题"


def test_success_path_history_includes_user_answer_for_llm() -> None:
    """LLM 收到的 history 必须包含当前轮的用户回答。

    推迟落库方案的关键验证：我们不先写 DB，但传给 LLM 的 history
    里必须有用户的回答，否则 LLM 不知道候选人刚说了什么。
    """
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = _make_agent_that_always_succeeds()

    service = InterviewService(repository=repo, interviewer_agent=agent)
    service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    call_args = agent.generate_next_question.call_args
    history = call_args.kwargs["history"]
    user_messages = [m for m in history if m["role"] == "USER_CANDIDATE"]
    assert len(user_messages) == 1
    assert user_messages[0]["content"] == "我的回答"
    assert user_messages[0]["round_no"] == "1"


def test_end_decision_still_writes_user_answer() -> None:
    """LLM 决定结束面试时，用户回答仍然要落库（保证复盘数据完整）。"""
    session = _make_session()
    repo = FakeInterviewRepository(session)
    repo.append_message(1, "test-session", "AI_INTERVIEWER", "请自我介绍", 1)
    agent = MagicMock()
    agent.generate_next_question.return_value = InterviewerDecision(
        decision="end",
        question=None,
        reason="考察完毕",
    )

    service = InterviewService(repository=repo, interviewer_agent=agent)
    # 禁掉后台线程，避免测试退出时还在跑
    service._schedule_backfill_reviews = MagicMock()  # type: ignore[method-assign]
    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert result.is_finished is True
    # 结束时也要有用户回答
    user_messages = [m for m in repo.messages if m["role"] == "USER_CANDIDATE"]
    assert len(user_messages) == 1
    assert repo.finished is True


# === _generate_reviews_with_retry 保持原样 ===

def test_generate_reviews_with_retry_is_unchanged() -> None:
    """确认复盘那条链路的重试参数没有被误改。

    复盘是后台任务，可以等更久（15s 线性退避），与实时提问的
    3s/10s 退避是两套独立的参数。这里通过签名检查确保没被复用。
    """
    service = InterviewService(repository=MagicMock())
    # 复盘方法的默认参数：max_attempts=3, base_wait_seconds=15.0
    import inspect

    sig = inspect.signature(service._generate_reviews_with_retry)
    assert sig.parameters["max_attempts"].default == 3
    assert sig.parameters["base_wait_seconds"].default == 15.0


# === 流式重试：吐过内容就不再重试 ===

def _stream_delta_then_rate_limit(**kwargs):
    yield {"type": "delta", "text": "那你"}
    raise RateLimitError(message="rate limited", response=MagicMock(), body={})


def test_stream_retry_stops_once_delta_emitted() -> None:
    """已经吐出 delta 之后再限流，不能重试。

    重试会让前端把同一道题重新拼一遍，用户会看到「那你那你…」。
    """
    service = InterviewService(repository=MagicMock())
    agent = MagicMock()
    agent.generate_next_question_stream.side_effect = _stream_delta_then_rate_limit

    gen = service._generate_next_question_stream_with_retry(
        agent,
        job_role="Java开发工程师",
        round_no=2,
        duration_minutes=45,
        elapsed_minutes=5,
        direction=None,
        interviewer_mode=None,
        resume_text=None,
        history=[],
    )

    assert next(gen) == "那你"
    with pytest.raises(RateLimitError):
        next(gen)
    assert agent.generate_next_question_stream.call_count == 1


# === SSE 帧完整性：裸文本不能漏进流 ===

def _stream_two_deltas_then_done(**kwargs):
    yield {"type": "delta", "text": "那你"}
    yield {"type": "delta", "text": "怎么做的？"}
    yield {
        "type": "done",
        "decision": InterviewerDecision(decision="continue", question="那你怎么做的？", reason="继续"),
    }


def test_stream_output_is_properly_framed() -> None:
    """每个非空行必须是 event: 或 data: 开头的 SSE 帧。

    这条守住一个真实踩过的坑：内层生成器 yield 的是裸文本，用 yield from 会把它
    直接漏进 HTTP 流，前端收到的就是「题目文本 + event: done」混在一起的东西。
    """
    repo = MagicMock()
    repo.get_by_id.return_value = _make_session()
    repo.list_messages.return_value = []

    agent = MagicMock()
    agent.generate_next_question_stream.side_effect = _stream_two_deltas_then_done

    service = InterviewService(repository=repo, interviewer_agent=agent)
    events = list(
        service.submit_answer_stream(1, "test-session", SubmitAnswerRequest(answer="我的回答"))
    )
    payload = "".join(events)

    for line in payload.split("\n"):
        if not line.strip():
            continue
        # 心跳注释帧（以冒号开头）也是合法 SSE，除此之外必须是事件帧
        assert (
            line.startswith("event: ")
            or line.startswith("data: ")
            or line.startswith(": ")
        ), f"裸文本漏进了 SSE 流: {line!r}"

    assert payload.count("event: delta") == 2
    assert "event: done" in payload
    assert "event: stage" in payload
