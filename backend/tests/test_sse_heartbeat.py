"""SSE 心跳与断连回收的测试。

覆盖：心跳时间点、首 delta 后停止、重试退避期心跳、流内 error、
内层异常/最终决策传播，以及真实 TCP 断连后 LLM 流被关闭且没有新增线程。
"""

import asyncio
import json
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import uvicorn
from fastapi import FastAPI
from openai import RateLimitError

from app.api.routes import interview as interview_routes
from app.application.interview.interview_dto import SubmitAnswerRequest
from app.application.interview.interview_service import (
    SSE_HEARTBEAT_FRAME,
    SSE_HEARTBEAT_INTERVAL_SECONDS,
    InterviewService,
)
from app.domain.interview.entities import InterviewSession
from app.infrastructure.agent.interview_agent import InterviewerAgent, InterviewerDecision
from app.infrastructure.repositories.interview_repository import get_interview_service

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


def _collect(service: InterviewService, **kwargs) -> list[str]:
    async def run() -> list[str]:
        gen = await service.submit_answer_stream(
            1, "test-session", SubmitAnswerRequest(answer="我的回答"), **kwargs
        )
        return [chunk async for chunk in gen]

    return asyncio.run(run())


def test_heartbeat_frame_matches_sse_comment_spec() -> None:
    """心跳必须是冒号开头的注释帧，间隔为 5 秒。"""
    assert SSE_HEARTBEAT_FRAME == ": keep-alive\n\n"
    assert SSE_HEARTBEAT_INTERVAL_SECONDS == 5.0


# === 心跳时间点 ===

def test_service_emits_heartbeat_between_stage_and_first_delta() -> None:
    """stage 之后、第一个 delta 之前有心跳；delta 开始后没有。"""

    async def slow_stream(**kwargs):
        await asyncio.sleep(0.2)
        yield {"type": "delta", "text": "那你"}
        yield {"type": "delta", "text": "怎么做的？"}
        yield {
            "type": "done",
            "decision": InterviewerDecision(
                decision="continue", question="那你怎么做的？", reason="继续"
            ),
        }

    agent = MagicMock()
    agent.agenerate_next_question_stream.side_effect = slow_stream
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    with patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02):
        events = _collect(service)

    stream = "".join(events)
    assert stream.index("event: stage") < stream.index(SSE_HEARTBEAT_FRAME)
    assert stream.index(SSE_HEARTBEAT_FRAME) < stream.index("event: delta")
    assert stream.rindex(SSE_HEARTBEAT_FRAME) < stream.index("event: delta")
    assert stream.count("event: delta") == 2
    assert not _live_heartbeat_threads()


def test_service_keeps_heartbeat_during_retry_backoff() -> None:
    """限流重试期间还没吐出 delta，心跳要继续保活。"""
    attempts = {"count": 0}

    async def flaky_stream(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RateLimitError(message="rate limited", response=MagicMock(), body={})
        yield {
            "type": "done",
            "decision": InterviewerDecision(decision="continue", question="问题", reason="继续"),
        }

    agent = MagicMock()
    agent.agenerate_next_question_stream.side_effect = flaky_stream
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    real_sleep = asyncio.sleep

    async def slow_sleep(seconds: float) -> None:
        # 退避时长改短，但必须真的等一会，否则外层没有机会发心跳
        await real_sleep(0.12)

    with (
        patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02),
        patch(f"{SERVICE_MODULE}.asyncio.sleep", slow_sleep),
    ):
        events = _collect(service)

    assert attempts["count"] == 2
    assert SSE_HEARTBEAT_FRAME in events, "重试退避期间心跳没有继续"
    assert "event: done" in "".join(events)
    assert not _live_heartbeat_threads()


def test_service_error_path_emits_error_and_no_threads() -> None:
    """重试耗尽后发出 error 事件，且不残留线程。"""
    agent = MagicMock()

    async def always_rate_limited(**kwargs):
        raise RateLimitError(message="rate limited", response=MagicMock(), body={})
        yield  # pragma: no cover - 让函数成为异步生成器

    agent.agenerate_next_question_stream.side_effect = always_rate_limited
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    async def no_sleep(seconds: float) -> None:
        return None

    with (
        patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02),
        patch(f"{SERVICE_MODULE}.asyncio.sleep", no_sleep),
    ):
        events = _collect(service)

    payload = "".join(events)
    assert "event: error" in payload
    assert "LLM provider error" in payload
    assert not _live_heartbeat_threads()


def test_service_inner_exception_becomes_error_event() -> None:
    """内层非可恢复异常也要作为 error 事件传出，而不是打断连接。"""
    agent = MagicMock()

    async def boom_stream(**kwargs):
        yield {"type": "delta", "text": "半句"}
        raise RuntimeError("boom")
        yield  # pragma: no cover

    agent.agenerate_next_question_stream.side_effect = boom_stream
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    with patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.02):
        events = _collect(service)

    payload = "".join(events)
    assert 'event: error\ndata: {"detail": "boom"}' in payload
    assert payload.count("event: delta") == 1


def test_service_propagates_final_decision_and_writes_messages() -> None:
    """done 事件携带最终决策，且成功后按同步路径顺序落库。"""

    async def quick_stream(**kwargs):
        yield {"type": "delta", "text": "那你怎么"}
        yield {
            "type": "done",
            "decision": InterviewerDecision(
                decision="continue", question="那你怎么做的？", reason="继续"
            ),
        }

    repo = _make_repo()
    agent = MagicMock()
    agent.agenerate_next_question_stream.side_effect = quick_stream
    service = InterviewService(repository=repo, interviewer_agent=agent)

    events = _collect(service)
    payload = "".join(events)

    assert "event: done" in payload
    done_frame = next(line for line in payload.split("\n") if line.startswith("data: ") and "next_question" in line)
    assert json.loads(done_frame.removeprefix("data: "))["next_question"] == "那你怎么做的？"
    # 用户回答 + 下一题落库，round 推进
    assert repo.append_message.call_count == 2
    repo.advance_round.assert_called_once()
    assert not _live_heartbeat_threads()


# === 真实断连（真 uvicorn + 真 socket）===

class _StallingLLMClient:
    """首次 await 处长期挂起；被取消时 finally 置位 closed，证明连接已释放。"""

    def __init__(self) -> None:
        self.closed = False
        self.started = threading.Event()

    async def achat_stream(self, messages, thinking_mode=None):
        try:
            self.started.set()
            await asyncio.sleep(3600)
            yield "永远到不了"  # pragma: no cover
        finally:
            self.closed = True


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _read_until(sock: socket.socket, marker_a: bytes, marker_b: bytes, timeout: float) -> bytes:
    received = b""
    deadline = time.monotonic() + timeout
    sock.settimeout(0.2)
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(4096)
        except TimeoutError:
            continue
        if not chunk:
            break
        received += chunk
        if marker_a in received and marker_b in received:
            break
    return received


def test_real_client_disconnect_closes_llm_stream_and_leaves_no_threads() -> None:
    """真实 TCP 断连：LLM 流被关闭，且没有任何 sse-heartbeat-* 线程。

    这里必须用真 uvicorn + 真 socket：httpx.ASGITransport 不会产生真实断连。
    """
    llm = _StallingLLMClient()
    agent = InterviewerAgent(llm_client=llm)
    service = InterviewService(repository=_make_repo(), interviewer_agent=agent)

    app = FastAPI()
    app.include_router(interview_routes.router, prefix="/interview")
    app.dependency_overrides[get_interview_service] = lambda: service

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    server_thread = threading.Thread(target=server.run, name="uvicorn-test", daemon=True)
    before = set(threading.enumerate())

    with patch(f"{SERVICE_MODULE}.SSE_HEARTBEAT_INTERVAL_SECONDS", 0.2):
        server_thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started, "uvicorn 未能在 10s 内启动"

            body = json.dumps({"answer": "我的回答"}).encode()
            request = (
                "POST /interview/test-session/answer/stream HTTP/1.1\r\n"
                "Host: 127.0.0.1\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode() + body

            sock = socket.create_connection(("127.0.0.1", port), timeout=5)
            try:
                sock.sendall(request)
                received = _read_until(
                    sock, b"event: stage", SSE_HEARTBEAT_FRAME.encode(), timeout=5
                )
            finally:
                # 真实断连：直接关掉 TCP 连接
                sock.close()

            assert b"event: stage" in received, received[:500]
            assert SSE_HEARTBEAT_FRAME.encode() in received, received[:500]

            disconnected_deadline = time.monotonic() + 3
            while not llm.closed and time.monotonic() < disconnected_deadline:
                time.sleep(0.02)

            assert llm.closed, "断连后内层 LLM 流没有被关闭"
            new_threads = [
                t
                for t in threading.enumerate()
                if t not in before and t.name.startswith("sse-heartbeat-")
            ]
            assert not new_threads, f"断连后新增了心跳线程: {[t.name for t in new_threads]}"
        finally:
            server.should_exit = True
            server_thread.join(timeout=5)
