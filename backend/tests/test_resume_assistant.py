"""Tests for the conversational resume assistant endpoints."""

import copy
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from fastapi.testclient import TestClient

from app.api.routes.resume_assistant import get_resume_assistant_service
from app.application.resume.resume_assistant_service import ResumeAssistantService
from app.application.resume.resume_dto import ResumeProfileResponse
from app.infrastructure.agent.resume_agent import ResumeAgent
from app.main import app


class FakeDraftRepository:
    """In-memory draft repository that mimics a DB round-trip via deepcopy."""

    def __init__(self) -> None:
        self._drafts: dict[tuple[int, str], object] = {}

    def create(self, draft) -> None:
        self._drafts[(draft.user_id, draft.session_id)] = copy.deepcopy(draft)

    def get(self, user_id: int, session_id: str):
        draft = self._drafts.get((user_id, session_id))
        return copy.deepcopy(draft) if draft is not None else None

    def save(self, draft) -> None:
        self._drafts[(draft.user_id, draft.session_id)] = copy.deepcopy(draft)


class FakeResumeRepository:
    """In-memory resume profile repository."""

    def __init__(self) -> None:
        self._by_id: dict[int, ResumeProfileResponse] = {}
        self._default_by_user: dict[int, int] = {}
        self._next_id = 1

    def get_by_id(self, user_id: int, profile_id: int) -> ResumeProfileResponse | None:
        profile = self._by_id.get(profile_id)
        if profile is None:
            return None
        return profile

    def get_default(self, user_id: int) -> ResumeProfileResponse | None:
        profile_id = self._default_by_user.get(user_id)
        return self._by_id.get(profile_id) if profile_id else None

    def upsert_default(self, user_id: int, title: str, content: str) -> ResumeProfileResponse:
        profile_id = self._default_by_user.get(user_id)
        if profile_id is None:
            profile_id = self._next_id
            self._next_id += 1
            self._default_by_user[user_id] = profile_id
        profile = ResumeProfileResponse(
            id=profile_id,
            title=title,
            content=content,
            summary=(" ".join(content.split()))[:160] or None,
            is_default=True,
            update_time=datetime.now().isoformat(),
        )
        self._by_id[profile_id] = profile
        return profile


class StubResumeAgent:
    """Scripted agent: pops one scripted step per generate_next_question call."""

    def __init__(self, steps: list[dict] | None = None, resume_content: str | None = None) -> None:
        self._steps = list(steps or [])
        self._resume_content = resume_content
        self.calls = 0

    def generate_next_question(self, **kwargs) -> dict:
        if self.calls < len(self._steps):
            step = self._steps[self.calls]
            self.calls += 1
            return step
        self.calls += 1
        return {"merge": {}, "section_complete": True}

    def generate_resume(self, **kwargs) -> str:
        if self._resume_content is None:
            raise RuntimeError("llm unavailable")
        return self._resume_content


class FailingAgent:
    """Agent that always fails, exercising the deterministic fallbacks."""

    def generate_next_question(self, **kwargs) -> dict:
        raise RuntimeError("llm unavailable")

    def generate_resume(self, **kwargs) -> str:
        raise RuntimeError("llm unavailable")


@contextmanager
def make_client(agent) -> Iterator[tuple[TestClient, FakeResumeRepository]]:
    draft_repository = FakeDraftRepository()
    resume_repository = FakeResumeRepository()
    service = ResumeAssistantService(draft_repository, resume_repository, agent)
    app.dependency_overrides[get_resume_assistant_service] = lambda: service
    try:
        yield TestClient(app), resume_repository
    finally:
        app.dependency_overrides.pop(get_resume_assistant_service, None)


def _start(client: TestClient, **body) -> dict:
    response = client.post("/api/resume/assistant/start", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _answer(client: TestClient, draft_id: str, answer: str) -> dict:
    response = client.post(f"/api/resume/assistant/{draft_id}/answer", json={"answer": answer})
    assert response.status_code == 200, response.text
    return response.json()


SIX_ANSWERS = [
    "我叫张三，5 年工作经验，现在在北京",
    "清华大学，计算机科学与技术，本科，2015-2019",
    "A 公司，后端工程师，2019-2023，负责订单系统的性能优化，QPS 从 500 提升到 3000",
    "推荐系统重构，负责召回模块，用 Python 和 Redis，难点是冷启动，上线后点击率提升 12%",
    "Python、Go、Redis、PostgreSQL",
    "目标岗位 AI 应用开发工程师，期望上海",
]

SIX_MERGES = [
    {"basic": {"name": "张三", "years": "5 年", "city": "北京"}},
    {"education": {"school": "清华大学", "major": "计算机科学与技术", "degree": "本科", "period": "2015-2019"}},
    {"work": {"company": "A 公司", "role": "后端工程师", "period": "2019-2023", "highlights": ["QPS 从 500 提升到 3000"]}},
    {"projects": {"name": "推荐系统重构", "role": "召回模块负责人", "stack": "Python、Redis", "challenge": "冷启动", "result": "点击率提升 12%"}},
    {"skills": ["Python", "Go", "Redis", "PostgreSQL"]},
    {"intent": {"position": "AI 应用开发工程师", "city": "上海"}},
]


def _complete_steps() -> list[dict]:
    return [
        {"merge": merge, "section_complete": True, "next_section_question": ""}
        for merge in SIX_MERGES
    ]


class TestStart:
    def test_start_returns_basic_question(self) -> None:
        with make_client(StubResumeAgent()) as (client, _):
            body = _start(client, target_role="AI 应用开发工程师", title="我的简历")
        assert body["status"] == "IN_PROGRESS"
        assert body["stage"] == "BASIC"
        assert body["draft_id"]
        assert body["progress"] == {"completed": [], "current": "BASIC"}
        assert "AI 应用开发工程师" in body["question"]


class TestFullFlow:
    def test_six_sections_then_finalize(self) -> None:
        agent = StubResumeAgent(steps=_complete_steps())
        with make_client(agent) as (client, _):
            draft_id = _start(client)["draft_id"]

            expected_stages = ["EDUCATION", "WORK", "PROJECT", "SKILL", "INTENT", "DONE"]
            for answer, expected_stage in zip(SIX_ANSWERS, expected_stages, strict=True):
                body = _answer(client, draft_id, answer)
                assert body["stage"] == expected_stage, body

            assert body["status"] == "COMPLETED"
            assert body["ready_to_finalize"] is True
            assert body["question"] is None
            assert body["progress"]["completed"] == [
                "BASIC",
                "EDUCATION",
                "WORK",
                "PROJECT",
                "SKILL",
                "INTENT",
            ]

            finalize = client.post(f"/api/resume/assistant/{draft_id}/finalize")
            assert finalize.status_code == 200, finalize.text
            payload = finalize.json()
            assert payload["draft_id"] == draft_id
            assert payload["profile_id"] > 0
            assert "张三" in payload["content"]
            assert "A 公司" in payload["content"]
            assert "PostgreSQL" in payload["content"]

            detail = client.get(f"/api/resume/assistant/{draft_id}").json()
            assert detail["status"] == "COMPLETED"
            assert detail["stage"] == "DONE"
            assert detail["sections"]["basic"]["name"] == "张三"
            assert detail["sections"]["skills"] == ["Python", "Go", "Redis", "PostgreSQL"]
            # 最后一次回答触发了收集完成，因此末尾是用户消息
            assert detail["messages"][-1]["role"] == "user"
            assert detail["progress"]["current"] == "DONE"


class TestGuidanceBehaviour:
    def test_brief_answer_triggers_follow_up(self) -> None:
        agent = StubResumeAgent(
            steps=[
                {
                    "merge": {"basic": {"name": "张三"}},
                    "section_complete": False,
                    "follow_up_question": "你的工作年限和所在城市是什么？",
                }
            ]
        )
        with make_client(agent) as (client, _):
            draft_id = _start(client)["draft_id"]
            body = _answer(client, draft_id, "张三")

        assert body["stage"] == "BASIC"
        assert body["question"] == "你的工作年限和所在城市是什么？"
        assert body["ready_to_finalize"] is False

    def test_force_advance_after_two_follow_ups(self) -> None:
        agent = StubResumeAgent(
            steps=[
                {"merge": {}, "section_complete": False, "follow_up_question": "再具体一点？"},
                {"merge": {}, "section_complete": False, "follow_up_question": "还有吗？"},
                {"merge": {}, "section_complete": False, "follow_up_question": "再补充？"},
            ]
        )
        with make_client(agent) as (client, _):
            draft_id = _start(client)["draft_id"]
            first = _answer(client, draft_id, "做了些优化工作")
            second = _answer(client, draft_id, "主要是提升了性能")
            third = _answer(client, draft_id, "也重构了一些模块")

        assert first["stage"] == "BASIC"
        assert first["question"] == "再具体一点？"
        assert second["stage"] == "BASIC"
        assert second["question"] == "还有吗？"
        # 追问满 2 轮后，第 3 轮无论如何都推进到下一节
        assert third["stage"] == "EDUCATION"
        assert third["progress"]["completed"] == ["BASIC"]

    def test_skip_answer_advances_section_without_llm(self) -> None:
        # 明确说「没有」时无需调用 LLM，直接跳节
        with make_client(FailingAgent()) as (client, _):
            draft_id = _start(client)["draft_id"]
            body = _answer(client, draft_id, "没有")

        assert body["stage"] == "EDUCATION"
        assert body["question"]
        assert body["progress"] == {"completed": ["BASIC"], "current": "EDUCATION"}

    def test_finalize_intent_completes_draft(self) -> None:
        with make_client(FailingAgent()) as (client, _):
            draft_id = _start(client)["draft_id"]
            body = _answer(client, draft_id, "差不多了，帮我生成吧")

        assert body["status"] == "COMPLETED"
        assert body["stage"] == "DONE"
        assert body["ready_to_finalize"] is True
        assert body["question"] is None

    def test_flow_completes_without_llm_within_bound(self) -> None:
        # LLM 全程不可用时，靠追问上限仍能走完 6 个分节（6 × 3 轮回答）
        with make_client(FailingAgent()) as (client, _):
            draft_id = _start(client)["draft_id"]
            rounds = 0
            body: dict = {}
            while rounds < 30:
                body = _answer(client, draft_id, f"第{rounds + 1}轮补充说明")
                rounds += 1
                if body["ready_to_finalize"]:
                    break

        assert body["ready_to_finalize"] is True
        assert body["stage"] == "DONE"
        assert rounds == 18

    def test_answer_after_completion_returns_400(self) -> None:
        with make_client(FailingAgent()) as (client, _):
            draft_id = _start(client)["draft_id"]
            _answer(client, draft_id, "帮我生成吧")
            response = client.post(
                f"/api/resume/assistant/{draft_id}/answer",
                json={"answer": "补充一点"},
            )
        assert response.status_code == 400


class TestFinalize:
    def test_finalize_is_idempotent(self) -> None:
        agent = StubResumeAgent(steps=_complete_steps())
        with make_client(agent) as (client, _):
            draft_id = _start(client)["draft_id"]
            for answer in SIX_ANSWERS:
                _answer(client, draft_id, answer)

            first = client.post(f"/api/resume/assistant/{draft_id}/finalize").json()
            second = client.post(f"/api/resume/assistant/{draft_id}/finalize").json()

        assert first["profile_id"] == second["profile_id"]
        assert first["content"] == second["content"]

    def test_fallback_resume_does_not_fabricate(self) -> None:
        # Agent 能抽取信息但生成简历时失败 → 走确定性兜底渲染，绝不编造内容
        agent = StubResumeAgent(steps=_complete_steps(), resume_content=None)
        with make_client(agent) as (client, _):
            draft_id = _start(client)["draft_id"]
            for answer in SIX_ANSWERS:
                _answer(client, draft_id, answer)
            payload = client.post(f"/api/resume/assistant/{draft_id}/finalize").json()

        content = payload["content"]
        assert "张三" in content
        assert "A 公司" in content
        assert "清华大学" in content
        for invented in ("字节跳动", "腾讯", "阿里巴巴", "Google", "麻省理工"):
            assert invented not in content


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self._response = response

    def chat(self, messages) -> str:
        return self._response


class TestAgentJsonRobustness:
    """LLM 输出 JSON 解析失败时必须兜底，不能崩溃。"""

    def _agent(self, response: str):
        return ResumeAgent(llm_client=FakeLLMClient(response))

    def test_plain_text_response_returns_empty(self) -> None:
        agent = self._agent("抱歉，我不太确定你的意思。")
        result = agent.generate_next_question(
            target_role=None,
            current_stage="BASIC",
            sections={},
            history=[],
            follow_up_count=0,
        )
        assert result == {}

    def test_fenced_json_is_parsed(self) -> None:
        agent = self._agent(
            '```json\n{"merge": {"basic": {"name": "张三"}}, '
            '"section_complete": true, "follow_up_question": "", '
            '"next_section_question": "下一题"}\n```'
        )
        result = agent.generate_next_question(
            target_role=None,
            current_stage="BASIC",
            sections={},
            history=[],
            follow_up_count=0,
        )
        assert result["merge"] == {"basic": {"name": "张三"}}
        assert result["section_complete"] is True
        assert result["next_section_question"] == "下一题"

    def test_non_object_json_returns_empty(self) -> None:
        agent = self._agent('["not", "an", "object"]')
        result = agent.generate_next_question(
            target_role=None,
            current_stage="BASIC",
            sections={},
            history=[],
            follow_up_count=0,
        )
        assert result == {}


class TestErrorHandling:
    def test_unknown_draft_returns_404(self) -> None:
        with make_client(StubResumeAgent()) as (client, _):
            response = client.get("/api/resume/assistant/does-not-exist")
        assert response.status_code == 404

    def test_llm_failure_returns_200_with_fallback_question(self) -> None:
        with make_client(FailingAgent()) as (client, _):
            draft_id = _start(client)["draft_id"]
            body = _answer(client, draft_id, "我在 A 公司做后端开发")
        # Agent 失败不应导致 5xx，而是返回可继续的默认问题
        assert body["stage"] == "BASIC"
        assert body["question"]

    def test_whitespace_only_answer_returns_422_or_400(self) -> None:
        with make_client(FailingAgent()) as (client, _):
            draft_id = _start(client)["draft_id"]
            response = client.post(
                f"/api/resume/assistant/{draft_id}/answer",
                json={"answer": "   "},
            )
        assert response.status_code == 400
