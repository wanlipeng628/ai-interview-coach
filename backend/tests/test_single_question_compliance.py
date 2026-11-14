"""D4 单题合规回归测试（AIC-83）。

背景：关思考时模型爱用「，以及……怎么/如何」把两问连成一句，句末只有一个问号，
`_normalize_single_question()` 按问号截断碰不到。修复分三层：
1. prompt 硬约束（一次只问一个问题、开场题不叠加要求）；
2. normalizer 识别第二疑问分句，记 `multi_question_detected`；
3. 命中时按 `regenerate_question_avoiding_history()` 语义重生成一次，不循环。
"""

import asyncio

import pytest

from app.application.interview.interview_dto import SubmitAnswerRequest
from app.application.interview.interview_service import InterviewService
from app.domain.interview.entities import InterviewSession, InterviewSessionStatus
from app.infrastructure.agent.interview_agent import (
    InterviewerAgent,
    InterviewerDecision,
    detect_multi_question,
)

# AIC-80 报告里点名的结构：两问连成一句，句末只有一个问号
TWO_QUESTIONS_IN_ONE = (
    "请讲一下消息表从写入到补偿完成的完整流程，"
    "以及消费端如何保证消息不被重复消费导致订单状态出错？"
)

# 正常单一问题：不能被误判，否则会白烧一次重生成、拉高出题延迟
SINGLE_QUESTIONS = [
    "如果线上出现频繁 Full GC，你会先看哪些指标？",
    "你能说明一下 volatile 适合解决什么问题，不适合解决什么问题吗？",
    "请介绍一个你最近项目里最有挑战的问题，说说你当时是怎么解决的？",
    "如果迁移期间源库还在写入，同时你的分批任务也在跑，你怎么保证不漏数据？",
    (
        "你用 SELECT ... FOR UPDATE 锁的是假期配置表里该员工的那行锚点记录，"
        "如果这个员工在配置表里还没有对应行，这条 SELECT 会锁住什么？"
    ),
    "你在导入服务里用的什么垃圾收集器，为什么没选 G1？",
]


class FakeInterviewRepository:
    """内存版 repository，只覆盖出题链路需要的方法。"""

    def __init__(self, session: InterviewSession) -> None:
        self._session = session
        self.messages: list[dict] = []
        self.finished = False

    def get_by_id(self, user_id: int, session_id: str) -> InterviewSession | None:
        return self._session

    def append_message(
        self, user_id: int, session_id: str, role: str, content: str, round_no: int
    ) -> None:
        self.messages.append({"role": role, "content": content, "round_no": round_no})

    def list_messages(self, user_id: int, session_id: str) -> list[dict[str, str]]:
        return [
            {"role": item["role"], "round_no": str(item["round_no"]), "content": item["content"]}
            for item in self.messages
        ]

    def advance_round(self, user_id: int, session_id: str, current_round: int) -> None:
        self._session.current_round = current_round

    def finish(self, user_id: int, session_id: str) -> None:
        self.finished = True
        self._session.status = InterviewSessionStatus.FINISHED


class ScriptedAgent:
    """按脚本返回出题结果，并记录重生成调用。"""

    def __init__(
        self,
        *,
        first_question: str,
        regenerated_question: str | None,
        multi_question_detected: bool = False,
    ) -> None:
        self._first_question = first_question
        self._regenerated_question = regenerated_question
        self._multi_question_detected = multi_question_detected
        self.regenerate_calls: list[dict] = []

    def generate_next_question(self, **kwargs) -> InterviewerDecision:
        return InterviewerDecision(
            decision="continue",
            question=self._first_question,
            reason="继续考察",
            multi_question_detected=self._multi_question_detected,
        )

    def regenerate_question_avoiding_history(self, **kwargs) -> str | None:
        self.regenerate_calls.append(kwargs)
        return self._regenerated_question

    async def agenerate_next_question_stream(self, **kwargs):
        decision = self.generate_next_question(**kwargs)
        yield {"type": "delta", "text": decision.question or ""}
        yield {"type": "done", "decision": decision}


def _make_session() -> InterviewSession:
    return InterviewSession(
        session_id="test-session",
        job_role="Java开发工程师",
        first_question="请做一下自我介绍",
        user_id=1,
        current_round=1,
        duration_minutes=45,
    )


def _service_with(agent: ScriptedAgent) -> tuple[InterviewService, InterviewSession]:
    session = _make_session()
    repository = FakeInterviewRepository(session)
    repository.append_message(1, session.session_id, "AI_INTERVIEWER", "请做一下自我介绍", 1)
    return InterviewService(repository=repository, interviewer_agent=agent), session


# === 识别层 ===

@pytest.mark.parametrize("question", SINGLE_QUESTIONS)
def test_single_question_is_not_flagged(question: str) -> None:
    assert detect_multi_question(question) is False


def test_connector_second_question_is_detected() -> None:
    assert detect_multi_question(TWO_QUESTIONS_IN_ONE) is True


def test_single_question_is_normalized_unchanged() -> None:
    agent = InterviewerAgent.__new__(InterviewerAgent)
    question = "你能讲一下 HashMap 在 JDK 1.8 中 put 一个元素的大致过程吗？"

    assert agent._sanitize_question(question) == question


def test_two_question_marks_are_truncated_but_still_flagged() -> None:
    agent = InterviewerAgent.__new__(InterviewerAgent)
    raw = (
        "Redis setnx 占位成功但后续业务处理失败时，这个占位怎么处理？"
        "如果直接丢弃消息，会不会导致消息实际没被正确处理却再也不会重试？"
    )

    sanitized = agent._sanitize_question_with_flags(raw)

    assert sanitized.question == "Redis setnx 占位成功但后续业务处理失败时，这个占位怎么处理？"
    # 截断是兜底，但「模型输出含多问」这个事实必须记下来（AIC-80 口径）
    assert sanitized.multi_question_detected is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # 开场题没有问号时，模型会先打招呼再提要求；不能把问题切掉只剩问候
        ("你好，我是今天的面试官。请先做一个自我介绍。", "请先做一个自我介绍"),
        ("你好，我是本次面试官。请先做一个简短的自我介绍。", "请先做一个简短的自我介绍"),
        (
            "周晴你好，很高兴今天能和你聊聊。请先做一个简单的自我介绍吧。",
            "请先做一个简单的自我介绍吧",
        ),
        # 没有问候前缀时行为不变
        ("请先做一个自我介绍。", "请先做一个自我介绍"),
        # 含请求标志的寒暄句不能整句丢掉
        ("你好，我们聊聊你最近做的项目。", "你好，我们聊聊你最近做的项目"),
    ],
)
def test_greeting_prefix_keeps_the_real_question(raw: str, expected: str) -> None:
    agent = InterviewerAgent.__new__(InterviewerAgent)

    assert agent._sanitize_question(raw) == expected


def test_parse_decision_reports_multi_question_flag() -> None:
    agent = InterviewerAgent.__new__(InterviewerAgent)
    raw = (
        '{"decision": "continue", "question": "'
        + TWO_QUESTIONS_IN_ONE
        + '", "reason": "继续追问"}'
    )

    decision = agent._parse_decision(raw, latest_answer="上一轮回答")

    assert decision.question == TWO_QUESTIONS_IN_ONE
    assert decision.multi_question_detected is True


# === prompt 层 ===

def test_prompt_forbids_connector_second_question() -> None:
    assert "禁止用「以及 / 同时 / 另外 / 顺便 / 还有 / 并且」" in InterviewerAgent.SYSTEM_PROMPT
    assert "句末只能有一个问号" in InterviewerAgent.SYSTEM_PROMPT


def test_opening_prompt_does_not_stack_project_requirements() -> None:
    agent = InterviewerAgent.__new__(InterviewerAgent)

    messages = agent._build_next_question_messages(
        job_role="Java 后端",
        round_no=1,
        duration_minutes=45,
        elapsed_minutes=0,
        direction="FULL_MOCK",
        interviewer_mode="NORMAL",
        resume_text="三年 Java 后端",
        history=[],
    )

    assert "本轮是开场题" in messages[1]["content"]
    assert "不要在同一题里再要求讲项目" in messages[1]["content"]


def test_opening_hint_disappears_after_first_round() -> None:
    agent = InterviewerAgent.__new__(InterviewerAgent)
    history = [
        {"role": "AI_INTERVIEWER", "round_no": "1", "content": "请做一下自我介绍"},
        {"role": "USER_CANDIDATE", "round_no": "1", "content": "我是做 Java 后端的"},
    ]

    messages = agent._build_next_question_messages(
        job_role="Java 后端",
        round_no=2,
        duration_minutes=45,
        elapsed_minutes=5,
        direction="FULL_MOCK",
        interviewer_mode="NORMAL",
        resume_text="三年 Java 后端",
        history=history,
    )

    assert "本轮是开场题" not in messages[1]["content"]


# === 重生成一层 ===

def test_multi_question_triggers_single_regeneration() -> None:
    agent = ScriptedAgent(
        first_question=TWO_QUESTIONS_IN_ONE,
        regenerated_question="请讲一下消息表从写入到补偿完成的完整流程？",
        multi_question_detected=True,
    )
    service, _ = _service_with(agent)

    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert result.next_question == "请讲一下消息表从写入到补偿完成的完整流程？"
    assert len(agent.regenerate_calls) == 1
    assert agent.regenerate_calls[0]["reason"] == InterviewerAgent.REGENERATE_REASON_MULTI_QUESTION


def test_multi_question_regeneration_failure_keeps_original_without_retry() -> None:
    """重生成后仍是多问：保留原题，只重试一次，不阻塞用户。"""
    agent = ScriptedAgent(
        first_question=TWO_QUESTIONS_IN_ONE,
        regenerated_question="你把消息表方案再展开一下，以及消费端怎么保证幂等？",
        multi_question_detected=True,
    )
    service, _ = _service_with(agent)

    result = service.submit_answer(1, "test-session", SubmitAnswerRequest(answer="我的回答"))

    assert result.next_question == TWO_QUESTIONS_IN_ONE
    assert len(agent.regenerate_calls) == 1


def test_streaming_path_also_regenerates_once() -> None:
    agent = ScriptedAgent(
        first_question=TWO_QUESTIONS_IN_ONE,
        regenerated_question="请讲一下消息表从写入到补偿完成的完整流程？",
        multi_question_detected=True,
    )
    service, _ = _service_with(agent)

    async def collect_done() -> str:
        stream = await service.submit_answer_stream(
            1, "test-session", SubmitAnswerRequest(answer="我的回答")
        )
        events = [event async for event in stream]
        return [event for event in events if event.startswith("event: done")][0]

    done_event = asyncio.run(collect_done())

    assert "请讲一下消息表从写入到补偿完成的完整流程？" in done_event
    assert len(agent.regenerate_calls) == 1
