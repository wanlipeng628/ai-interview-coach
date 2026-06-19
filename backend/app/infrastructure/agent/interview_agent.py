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
1. 面试过程像真实面试，候选人只看到面试官的问题。
2. 每轮根据候选人的上一轮回答决定继续追问、切换方向或结束面试。
3. 同时为系统内部生成上一轮回答复盘，但复盘绝不能出现在 question 字段里。

面试方式：
1. 开始阶段优先围绕候选人的自我介绍、简历、项目经历追问。
2. 中段围绕 Java 岗位核心能力考察，包括 Java 基础、集合、并发、JVM、Spring、MySQL、Redis、消息队列、系统设计、线上问题排查。
3. 如果回答有价值，优先基于回答中最关键的一个点继续追问。
4. 如果候选人明显答不上来、含糊、重复、明确说不会，就切换到新方向，不要反复追打同一知识点。
5. 信息已经足够，或接近面试时长上限时，可以结束面试。

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

隐藏复盘规则：
1. answer_review 只用于系统记录，候选人在面试过程中看不到。
2. answer_review 要评价上一轮候选人回答，不要评价即将提出的问题。
3. answer_review.reference_points 必须围绕上一轮问题生成，不能所有问题都返回同一套通用要点。
4. answer_review.sample_answer 必须围绕上一轮问题生成一段参考回答，不要使用固定模板。
5. question 里不得出现“回答不错、回答不完整、你刚才没有说清楚、建议你”等评价或指导。

你必须只输出严格 JSON，不要输出 Markdown。JSON 格式：
{
  "decision": "continue|switch|end",
  "question": "下一个单一问题或 null",
  "reason": "简短说明为什么继续、切换或结束",
  "answer_review": {
    "evaluation": "对候选人上一轮回答的简短复盘",
    "reference_points": ["上一轮问题的参考要点1", "参考要点2", "参考要点3"],
    "sample_answer": "上一轮问题的一段参考回答",
    "level": "good|normal|weak"
  }
}
""".strip()

    REVIEW_LEAK_PATTERNS = [
        r"^你刚才的?回答[^，。！？?]*[，。！？?]\s*",
        r"^刚才的?回答[^，。！？?]*[，。！？?]\s*",
        r"^从你的?回答来看[^，。！？?]*[，。！？?]\s*",
        r"^这个点[^，。！？?]*[，。！？?]\s*",
        r"^这里[^，。！？?]*[，。！？?]\s*",
        r"^建议你[^，。！？?]*[，。！？?]\s*",
    ]

    def __init__(self, llm_client: OpenAICompatibleClient | None = None) -> None:
        self._llm_client = llm_client or OpenAICompatibleClient()

    def generate_next_question(
        self,
        job_role: str,
        round_no: int,
        duration_minutes: int,
        elapsed_minutes: int,
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
                    f"面试时长上限：{duration_minutes} 分钟\n"
                    f"已进行时间：约 {elapsed_minutes} 分钟\n"
                    f"候选人简历：\n{resume_text or '未提供简历'}\n\n"
                    "历史问答：\n"
                    f"{self._format_history(history)}\n\n"
                    "请基于候选人最近一轮回答，输出下一步决策。\n"
                    "再次强调：question 只能是下一个单一面试问题，不能包含评价；"
                    "answer_review 只记录上一轮回答的内部复盘。"
                ),
            },
        ]
        content = self._llm_client.chat(messages)
        return self._parse_decision(content, latest_answer=latest_answer)

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

    def _parse_decision(self, content: str, latest_answer: str | None) -> InterviewerDecision:
        try:
            payload = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return InterviewerDecision(
                decision="continue",
                question=self._sanitize_question(content),
                reason="LLM returned non-json text",
                answer_review=self._build_fallback_review(latest_answer),
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
            answer_review=self._parse_answer_review(payload.get("answer_review"), latest_answer),
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
            evaluation = "回答信息量较充分，能够展开说明背景、方案或结果。后续可继续补充关键指标、异常场景和方案取舍。"
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
                    for mark in ("，", "。", "！", "；", ",", "!", ";")
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
