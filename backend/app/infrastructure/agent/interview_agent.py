from dataclasses import dataclass, field
import json
import re
from typing import Any

from app.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient


@dataclass(slots=True)
class AnswerReview:
    evaluation: str
    reference_points: list[str]
    sample_answer: str
    level: str
    raw_review_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InterviewerDecision:
    decision: str
    question: str | None
    reason: str | None = None
    answer_review: AnswerReview | None = None


class InterviewerAgent:
    """AI interviewer agent backed by an OpenAI-compatible LLM."""

    SYSTEM_PROMPT = """
你是一名资深 Java 后端技术面试官，也是一名面试陪练教练。你正在进行一场真实、互动、训练型的模拟面试。

目标：
1. 面试过程要像真实技术面试，候选人只能看到面试官的问题。
2. 每轮根据候选人的上一轮回答决定继续追问、切换方向或结束面试。
3. 先在心里评估候选人上一轮回答的质量（完整性、技术深度、是否需要追问），再做出决策。

面试方式：
1. 开始阶段优先围绕候选人的自我介绍、简历、项目经历追问。
2. 中段围绕 Java 后端岗位核心能力考察。考察范围包括但不限于：Java 语言基础、集合与数据结构、并发编程、JVM、Spring 生态、MySQL 与数据库设计、Redis 与缓存、消息队列、微服务与分布式、接口设计、系统设计、线上问题排查、工程实践、Linux/部署/监控、安全、计算机网络与操作系统基础、架构与业务理解。
3. 上述方向不是固定清单，不要求每场全部覆盖。你需要根据候选人的简历、自我介绍、上一轮回答质量、岗位方向和剩余时间，动态选择最合适的方向。
4. 如果候选人简历明显偏业务开发，优先问项目、Spring、数据库、缓存、接口设计、线上问题。
5. 如果候选人简历体现高并发或中间件经验，可以深入并发、MQ、Redis、系统设计、稳定性治理。
6. 如果候选人年限较低，优先考察 Java 基础、集合、Spring、MySQL、项目表达。
7. 如果候选人年限较高，增加架构设计、分布式、稳定性、技术选型、线上治理和复杂度权衡。
8. 如果回答有价值，优先基于回答中最关键的一个点继续追问。
9. 如果候选人明显答不上来、含糊、重复、明确说不会，就切换到新方向，不要反复追打同一知识点。
10. 信息已经足够，或接近面试时长上限时，可以结束面试。

难度控制：
1. 从简历、自我介绍和项目描述中推断候选人大致工作年限。
2. 能判断年限时，用该年限作为提问难度基准，但不要直接说出你推断的年限。
3. 无法判断年限时，默认按 2-4 年 Java 开发工程师标准提问。
4. 表现较强时逐步提高深度，基础较弱时回到更基础、更具体的问题。

提问规则，必须严格遵守：
1. 每轮只能问一个问题。
2. question 字段只能包含一个单一问题，不要给标准答案，不要评价候选人。
3. 不要把多个问题合并成一个问题。
4. 不要使用“分别说说、另外、还有、同时、比如 A/B/C、从实现和原理两个方面”等方式拼接多个问题。
5. 不要让候选人同时回答实现、原理、优化、排查、对比多个方向。
6. 如果要深入，只选择候选人回答里最关键的一个点继续问。
7. 不要重复历史中已经问过的问题，也不要换一种说法重复考察同一个知识点。
8. question 里不得出现“回答不错、回答不完整、你刚才没有说清楚、建议你”等评价或指导。

你必须只输出严格 JSON，不要输出 Markdown。JSON 格式：
{
  "decision": "continue|switch|end",
  "question": "下一个单一问题或 null",
  "reason": "说明决策依据，必须体现对候选人上一轮回答的具体评估（是否完整、是否有技术深度、是否需要追问）"
}
""".strip()

    REVIEW_LEAK_PATTERNS = [
        r"^你刚才的?回答[^，。！？!?]*[，。！？!?]\s*",
        r"^刚才的?回答[^，。！？!?]*[，。！？!?]\s*",
        r"^从你的?回答来看[^，。！？!?]*[，。！？!?]\s*",
        r"^这个点[^，。！？!?]*[，。！？!?]\s*",
        r"^这里[^，。！？!?]*[，。！？!?]\s*",
        r"^建议你[^，。！？!?]*[，。！？!?]\s*",
    ]

    def __init__(self, llm_client: OpenAICompatibleClient | None = None) -> None:
        self._llm_client = llm_client or OpenAICompatibleClient()

    def generate_next_question(
        self,
        job_role: str,
        round_no: int,
        duration_minutes: int,
        elapsed_minutes: int,
        direction: str | None,
        interviewer_mode: str | None,
        resume_text: str | None,
        history: list[dict[str, str]],
    ) -> InterviewerDecision:
        latest_answer = self._latest_candidate_answer(history)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"面试岗位：{job_role}\n"
                    f"当前准备生成的问题轮次：第 {round_no} 轮\n"
                    f"面试方向：{direction or 'FULL_MOCK'}\n"
                    f"面试官模式：{interviewer_mode or 'NORMAL'}\n"
                    f"面试时长上限：{duration_minutes} 分钟\n"
                    f"已进行时间：约 {elapsed_minutes} 分钟\n"
                    f"候选人简历：\n{resume_text or '未提供简历'}\n\n"
                    "历史问答：\n"
                    f"{self._format_history(history)}\n\n"
                    "请基于候选人最近一轮回答，先在心里评估回答质量，再输出下一步决策。\n"
                    "再次强调：question 只能是下一个单一面试问题，不能包含任何评价或指导。"
                ),
            },
        ]
        content = self._llm_client.chat(messages)
        return self._parse_decision(content, latest_answer=latest_answer)

    def regenerate_question_avoiding_history(
        self,
        job_role: str,
        direction: str | None,
        interviewer_mode: str | None,
        duplicated_question: str,
        history: list[dict[str, str]],
    ) -> str | None:
        asked_questions = [
            item.get("content", "").strip()
            for item in history
            if item.get("role") == "AI_INTERVIEWER" and item.get("content", "").strip()
        ]
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "你刚才生成的问题与历史问题重复或高度相似，需要重新生成一个新的面试问题。\n"
                    f"面试岗位：{job_role}\n"
                    f"面试方向：{direction or 'FULL_MOCK'}\n"
                    f"面试官模式：{interviewer_mode or 'NORMAL'}\n"
                    f"重复的问题：{duplicated_question}\n\n"
                    "已经问过的问题：\n"
                    f"{self._format_asked_questions(asked_questions)}\n\n"
                    "要求：\n"
                    "1. 新问题必须避开所有已经问过的问题和相同知识点。\n"
                    "2. 新问题仍然要符合当前候选人的简历、项目经历、最近回答和面试方向。\n"
                    "3. 只问一个单一问题，不要评价候选人，不要给答案。\n"
                    "4. 只输出严格 JSON：{\"question\":\"新的单一问题\"}"
                ),
            },
        ]
        content = self._llm_client.chat(messages)
        try:
            payload = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return self._sanitize_question(content) or None
        return self._sanitize_question(str(payload.get("question") or "")) or None

    REVIEW_SYSTEM_PROMPT = """
你是一名资深 Java 后端技术面试官，也是一名面试复盘教练。下面是一场已经结束的模拟面试中若干轮的问答记录。

请对每一轮候选人的回答进行复盘，严格对应轮次编号，逐轮输出，不要遗漏，也不要输出记录中不存在的轮次。

每轮复盘包含：
1. evaluation：对候选人该轮回答的简短客观评价，指出亮点与不足，100 字以内。
2. reference_points：3~5 条该轮问题的参考答题要点，必须围绕该轮具体问题生成，不得使用通用模板。
3. sample_answer：针对该轮问题的一段参考回答，200 字以内，必须与该轮问题对应。
4. level：good / normal / weak 三选一。

你必须只输出严格 JSON，不要输出 Markdown。JSON 格式：
{
  "reviews": {
    "1": {
      "evaluation": "...",
      "reference_points": ["...", "..."],
      "sample_answer": "...",
      "level": "good"
    },
    "2": { ... }
  }
}
""".strip()

    def generate_reviews_for_session(
        self,
        job_role: str,
        direction: str | None,
        interviewer_mode: str | None,
        resume_text: str | None,
        history: list[dict[str, str]],
        rounds: list[int],
    ) -> dict[int, AnswerReview]:
        """Generate answer reviews in batches of 5 rounds per LLM call."""
        reviews: dict[int, AnswerReview] = {}
        for batch_start in range(0, len(rounds), 5):
            batch_rounds = rounds[batch_start : batch_start + 5]
            messages = [
                {"role": "system", "content": self.REVIEW_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"面试岗位：{job_role}\n"
                        f"面试方向：{direction or 'FULL_MOCK'}\n"
                        f"面试官模式：{interviewer_mode or 'NORMAL'}\n\n"
                        f"候选人简历：\n{resume_text or '未提供简历'}\n\n"
                        "本批需要复盘的问答记录：\n"
                        f"{self._format_review_batch(history, batch_rounds)}\n\n"
                        "请为以上每一轮候选人的回答生成复盘。"
                    ),
                },
            ]
            content = self._llm_client.chat(messages)
            reviews.update(self._parse_review_payload(content))
        return reviews

    def _format_review_batch(self, history: list[dict[str, str]], rounds: list[int]) -> str:
        target = set(rounds)
        lines: list[str] = []
        for item in history:
            role = item.get("role", "UNKNOWN")
            if role not in {"AI_INTERVIEWER", "USER_CANDIDATE"}:
                continue
            try:
                round_no = int(item.get("round_no"))
            except (TypeError, ValueError):
                continue
            if round_no not in target:
                continue
            content = item.get("content", "")
            display_role = "面试官" if role == "AI_INTERVIEWER" else "候选人"
            lines.append(f"[round={round_no}] {display_role}：{content}")
        return "\n".join(lines) if lines else "本批暂无问答记录。"

    def _parse_review_payload(self, content: str) -> dict[int, AnswerReview]:
        try:
            payload = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return {}
        reviews_raw = payload.get("reviews")
        if not isinstance(reviews_raw, dict):
            return {}
        reviews: dict[int, AnswerReview] = {}
        for round_key, raw in reviews_raw.items():
            try:
                round_no = int(round_key)
            except (TypeError, ValueError):
                continue
            if not isinstance(raw, dict):
                continue
            evaluation = str(raw.get("evaluation") or "").strip()
            sample_answer = str(raw.get("sample_answer") or "").strip()
            level = str(raw.get("level") or "").strip().lower()
            if level not in {"good", "normal", "weak"}:
                level = "normal"
            raw_points = raw.get("reference_points")
            reference_points = [
                str(item).strip()
                for item in raw_points
                if str(item).strip()
            ] if isinstance(raw_points, list) else []
            if not evaluation or not reference_points or not sample_answer:
                continue
            reviews[round_no] = AnswerReview(
                evaluation=evaluation,
                reference_points=reference_points,
                sample_answer=sample_answer,
                level=level,
                raw_review_json=raw,
            )
        return reviews

    def _format_history(self, history: list[dict[str, str]]) -> str:
        if not history:
            return "暂无历史问答。"

        lines: list[str] = []
        for item in history[-12:]:
            role = item.get("role", "UNKNOWN")
            content = item.get("content", "")
            round_no = item.get("round_no", "")
            lines.append(f"[{role}][round={round_no}] {content}")
        return "\n".join(lines)

    def _format_asked_questions(self, questions: list[str]) -> str:
        if not questions:
            return "暂无已问问题。"
        return "\n".join(f"{index + 1}. {question}" for index, question in enumerate(questions[-20:]))

    def _parse_decision(self, content: str, latest_answer: str | None) -> InterviewerDecision:
        try:
            payload = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return InterviewerDecision(
                decision="continue",
                question=self._sanitize_question(content),
                reason="LLM returned non-json text",
            )

        decision = str(payload.get("decision", "continue")).lower()
        if decision not in {"continue", "switch", "end"}:
            decision = "continue"

        question = payload.get("question")
        if question is not None:
            question = self._sanitize_question(str(question)) or None

        if decision != "end" and not question:
            question = "请介绍一个你最近项目里最有挑战的问题，以及你是怎么解决的？"

        return InterviewerDecision(
            decision=decision,
            question=question,
            reason=payload.get("reason"),
        )

    def _parse_answer_review(
        self,
        payload: Any,
        latest_answer: str | None,
    ) -> AnswerReview | None:
        if not latest_answer:
            return None
        if not isinstance(payload, dict):
            return self._build_fallback_review(latest_answer)

        evaluation = str(payload.get("evaluation") or "").strip()
        sample_answer = str(payload.get("sample_answer") or "").strip()
        level = str(payload.get("level") or "").strip().lower()
        if level not in {"good", "normal", "weak"}:
            level = self._estimate_answer_level(latest_answer)

        raw_points = payload.get("reference_points")
        reference_points = [
            str(item).strip()
            for item in raw_points
            if str(item).strip()
        ] if isinstance(raw_points, list) else []

        fallback = self._build_fallback_review(latest_answer)
        return AnswerReview(
            evaluation=evaluation or fallback.evaluation,
            reference_points=reference_points or fallback.reference_points,
            sample_answer=sample_answer or fallback.sample_answer,
            level=level,
            raw_review_json=payload,
        )

    def _build_fallback_review(self, latest_answer: str | None) -> AnswerReview | None:
        if not latest_answer:
            return None

        level = self._estimate_answer_level(latest_answer)
        if level == "good":
            evaluation = "回答信息量较充分，能够展开说明背景、方案或结果。后续可以继续补充关键指标、异常场景和方案取舍。"
        elif level == "normal":
            evaluation = "回答具备一定信息量，但结构和技术细节还可以加强。建议按背景、方案、结果、反思展开。"
        else:
            evaluation = "回答偏简略，暂时不足以支撑面试官判断技术深度。建议补充项目背景、个人职责、具体实现和结果。"

        return AnswerReview(
            evaluation=evaluation,
            reference_points=["说明问题背景", "明确个人职责", "描述具体方案", "补充结果数据", "总结反思和改进"],
            sample_answer="可以按背景、任务、方案、结果、反思来回答：先说明业务场景和个人职责，再讲具体实现与遇到的问题，最后用数据说明效果。",
            level=level,
            raw_review_json={},
        )

    def _extract_json(self, content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            return text[start : end + 1]
        return text

    def _sanitize_question(self, question: str) -> str:
        normalized = re.sub(r"\s+", " ", question).strip()
        for pattern in self.REVIEW_LEAK_PATTERNS:
            normalized = re.sub(pattern, "", normalized)
        normalized = self._remove_review_keywords_prefix(normalized)
        return self._normalize_single_question(normalized)

    def _remove_review_keywords_prefix(self, question: str) -> str:
        keywords = ["回答不错", "回答不完整", "不够完整", "比较笼统", "没有说清楚", "需要补充"]
        for keyword in keywords:
            index = question.find(keyword)
            if 0 <= index <= 8:
                split_indexes = [
                    question.find(mark)
                    for mark in ("，", "。", "？", "！", ",", "!", ";")
                    if question.find(mark) >= 0
                ]
                if split_indexes:
                    return question[min(split_indexes) + 1 :].strip()
        return question

    def _normalize_single_question(self, question: str) -> str:
        normalized = re.sub(r"\s+", " ", question).strip()
        if not normalized:
            return normalized

        question_mark_index = self._first_question_mark_index(normalized)
        if question_mark_index >= 0:
            return normalized[: question_mark_index + 1]

        separators = ["；", ";", "。", "\n"]
        cut_points = [normalized.find(item) for item in separators if normalized.find(item) >= 0]
        if cut_points:
            normalized = normalized[: min(cut_points)].strip()

        return normalized

    def _first_question_mark_index(self, text: str) -> int:
        indexes = [index for index in (text.find("？"), text.find("?")) if index >= 0]
        return min(indexes) if indexes else -1

    def _latest_candidate_answer(self, history: list[dict[str, str]]) -> str | None:
        for item in reversed(history):
            if item.get("role") == "USER_CANDIDATE":
                return item.get("content", "").strip() or None
        return None

    def _estimate_answer_level(self, answer: str) -> str:
        length = len(answer.strip())
        if length >= 180:
            return "good"
        if length >= 60:
            return "normal"
        return "weak"
