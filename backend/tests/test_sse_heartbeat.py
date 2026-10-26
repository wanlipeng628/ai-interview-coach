"""SSE 心跳包装器的测试。

覆盖：心跳启停时机、间隔、异常与返回值传播、客户端断连后的线程回收。
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from app.application.interview.interview_dto import SubmitAnswerRequest
from app.application.interview.interview_service import (
    SSE_HEARTBEAT_FRAME,
    SSE_HEARTBEAT_INTERVAL_SECONDS,
    InterviewService,
    _sse_heartbeat_wrapper,
)
from app.domain.interview.entities import InterviewSession
from app.infrastructure.agent.interview_agent import InterviewerDecision

SERVICE_MODULE = "app.application.interview.interview_service"


def _live_heartbeat_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name.startswith("sse-heartbeat-")]


def _make_session() -> InterviewSession:
    return InterviewSession(
        session_id="test-session",
        job_role="Java开发工程师",
        first_question="请自我介绍",
        user_id=1,
        current_round=1,
        duration_minutes=45,
    )


def _make_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id.return_value = _make_session()
    repo.list_messages.return_value = []
    return repo


def test_heartbeat_frame_matches_sse_comment_spec() -> None:
    """心跳必须是冒号开头的注释帧，间隔为 5 秒。"""
    assert SSE_HEARTBEAT_FRAME == ": keep-alive\n\n"
    assert SSE_HEARTBEAT_INTERVAL_SECONDS == 5.0


# === 包装器本身 ===

def test_heartbeat_frames_arrive_before_first_event() -> None:
    """首字节前的空窗期里按 interval 发注释帧。"""

    def slow_inner():
        time.sleep(0.2)
        yield "第一个事件"
        yield "第二个事件"

    events = list(_sse_heartbeat_wrapper(slow_inner(), interval_seconds=0.02))

    first_real = events.index("第一个事件")
    heartbeats_before = events[:first_real]
    assert heartbeats_before, "首字节前没有任何心跳帧"
    assert all(frame == SSE_HEARTBEAT_FRAME for frame in heartbeats_before)
    # 0.2s 空窗、20ms 间隔，大约 10 条；放宽下限只验证「确实在发」
    assert len(heartbeats_before) >= 3
    # 第一个真实事件之后不再发心跳
    assert all(item != SSE_HEARTBEAT_FRAME for item in events[first_real:])


def test_heartbeat_stops_on_first_event() -> None:
    """第一个事件后即使内层继续空转，也不再发心跳。"""

    def inner_with_gap():
        yield "delta"
        time.sleep(0.15)
        yield "done"

    events = list(_sse_heartbeat_wrapper(inner_with_gap(), interval_seconds=0.02))

    assert events.count(SSE_HEARTBEAT_FRAME) == 0


def test_inner_exception_is_propagated() -> None:
    """内层异常必须原样抛给外层，不能被队列吞掉。"""

    def failing_inner():
        yield "一部分"
        raise RuntimeError("boom")

    gen = _sse_heartbeat_wrapper(failing_inner(), interval_seconds=0.02)
    assert next(gen) == "一部分"
    with pytest.raises(RuntimeError, match="boom"):
        next(gen)
    assert not _live_heartbeat_threads()


def test_inner_return_value_is_propagated() -> None:
    """内层生成器的返回值（重试循环里的 decision）要能传出去。"""

    def returning_inner():
        yield "delta"
        return "decision-对象"

    gen = _sse_heartbeat_wrapper(returning_inner(), interval_seconds=0.02)
    assert next(gen) == "delta"
    with pytest.raises(StopIteration) as stop:
        next(gen)
    assert stop.value.value == "decision-对象"
    assert not _live_heartbeat_threads()


def test_close_stops_threads_and_closes_inner() -> None:
    """客户端断连：外层 close 后两个线程都要退出，内层生成器要被关闭。"""
    inner_closed = threading.Event()

    def endless_inner():
        try:
            while True:
                time.sleep(0.005)
                yield "tick"
        finally:
            inner_closed.set()

    gen = _sse_heartbeat_wrapper(endless_inner(), interval_seconds=0.01)
    assert next(gen) == "tick"
    # 第一个事件到达后心跳线程已经退出，生产者线程还活着
    assert _live_heartbeat_threads()

    gen.close()

    assert not _live_heartbeat_threads(), "断连后仍有心跳相关线程存活"
    assert inner_closed.is_set(), "内层生成器没有被关闭"


# === 接入 _submit_answer_stream_inner 之后 ===

def _stream_after_delay(**kwargs):
    time.sleep(0.2)
    yield {"type": "delta", "text": "那你"}
    yield {"type": "delta", "text": "怎么做的？"}
    yield {
        "type": "done",
        "decision": InterviewerDecision(
            decision="continue", question="那你怎么做的？", reason="继续"
        ),
    }


def test_service_emits_heartbeat_between_stage_and_first_delta() -> None:
    """stage 之后、第一个 delta 之前有心跳；delta 开始后没有。"""
    agent = MagicMock()
    agent.generate_next_question_stream.side_effect = _stream_after_delay
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    with patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02):
        events = list(
            service.submit_answer_stream(1, "test-session", SubmitAnswerRequest(answer="我的回答"))
        )

    stream = "".join(events)
    assert stream.index("event: stage") < stream.index(SSE_HEARTBEAT_FRAME)
    assert stream.index(SSE_HEARTBEAT_FRAME) < stream.index("event: delta")
    assert stream.rindex(SSE_HEARTBEAT_FRAME) < stream.index("event: delta")
    assert stream.count("event: delta") == 2
    assert not _live_heartbeat_threads()


def test_service_keeps_heartbeat_during_retry_backoff() -> None:
    """限流重试期间还没吐出 delta，心跳要继续保活。"""
    attempts = {"count": 0}

    def flaky_stream(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RateLimitError(message="rate limited", response=MagicMock(), body={})
        yield {
            "type": "done",
            "decision": InterviewerDecision(decision="continue", question="问题", reason="继续"),
        }

    agent = MagicMock()
    agent.generate_next_question_stream.side_effect = flaky_stream
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    real_sleep = time.sleep

    def slow_sleep(seconds: float) -> None:
        # 退避时长改短，但必须真的睡一下，否则心跳线程没有机会发帧
        real_sleep(0.12)

    with (
        patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02),
        patch(f"{SERVICE_MODULE}.time.sleep", slow_sleep),
    ):
        events = list(
            service.submit_answer_stream(1, "test-session", SubmitAnswerRequest(answer="我的回答"))
        )

    assert attempts["count"] == 2
    assert SSE_HEARTBEAT_FRAME in events, "重试退避期间心跳没有继续"
    assert "event: done" in "".join(events)
    assert not _live_heartbeat_threads()


def test_service_error_path_leaves_no_threads() -> None:
    """重试耗尽发出 error 事件后，线程全部退出。"""
    agent = MagicMock()

    def always_rate_limited(**kwargs):
        raise RateLimitError(message="rate limited", response=MagicMock(), body={})
        yield  # pragma: no cover - 让函数成为生成器

    agent.generate_next_question_stream.side_effect = always_rate_limited
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    with (
        patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02),
        patch(f"{SERVICE_MODULE}.time.sleep"),
    ):
        events = list(
            service.submit_answer_stream(1, "test-session", SubmitAnswerRequest(answer="我的回答"))
        )

    assert "event: error" in "".join(events)
    assert not _live_heartbeat_threads()


def test_service_client_disconnect_leaves_no_threads() -> None:
    """模拟客户端中途断开：close 掉响应生成器后不能残留线程。"""
    inner_closed = threading.Event()

    def endless_stream(**kwargs):
        try:
            while True:
                time.sleep(0.005)
                yield {"type": "delta", "text": "字"}
        finally:
            inner_closed.set()

    agent = MagicMock()
    agent.generate_next_question_stream.side_effect = endless_stream
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    with patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.01):
        gen = service.submit_answer_stream(
            1, "test-session", SubmitAnswerRequest(answer="我的回答")
        )
        next(gen)  # stage
        next(gen)  # 第一个 delta
        assert _live_heartbeat_threads()
        gen.close()

    assert not _live_heartbeat_threads(), "客户端断开后仍有线程存活"
    assert inner_closed.is_set(), "断开后内层 LLM 流没有被关闭"
