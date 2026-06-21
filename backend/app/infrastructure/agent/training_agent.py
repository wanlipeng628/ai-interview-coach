from dataclasses import dataclass, field
import json
import re
from typing import Any

from app.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient


@dataclass(slots=True)
class TrainingTurn:
    feedback: str
    reference_points: list[str]
    sample_answer: str
    next_question: str | None
    is_finished: bool = False
    raw_json: dict[str, Any] = field(default_factory=dict)


class TrainingAgent:
    """AI coach for focused training tasks."""

    SYSTEM_PROMPT = """
你是一名资深 Java 后端面试训练教练。你正在进行专项训练，不是正式模拟面试。

训练类型判断：
1. 如果训练任务与表达、逻辑、沟通、结构化表达、项目讲述、自我介绍、STAR、讲不清楚相关，这是表达能力训练。
2. 如果训练任务与项目经历、项目亮点、职责描述、项目难点、方案表达相关，这是项目表达训练。
3. 如果训练任务与 Java、JVM、并发、MySQL、Redis、Spring、消息队列、系统设计、线上排查等技术点相关，这是技术知识训练。

训练目标：
1. 围绕训练任务标题和薄弱原因进行针对性练习。
2. 每次只提出一个训练问题。
3. 候选人回答后，必须给出即时反馈、参考要点、参考回答。
4. 表达能力训练要重点反馈结构、顺序、重点突出、因果关系、结果量化和语言简洁度。
5. 项目表达训练要重点反馈背景、目标、个人职责、关键动作、技术方案、结果和复盘。
6. 技术知识训练要重点反馈概念准确性、机制完整性、场景理解、边界条件和项目落地。
7. 如果候选人已经能较好覆盖核心要点，可以继续给一个更深入的问题；如果已经连续多轮表现较好，可以结束训练。
8. 反馈要具体，不要只说“回答不错”。

下一题规则：
1. 下一题必须继续围绕当前训练任务，不要随意切换到无关技术。
2. 表达类训练的下一题应让候选人继续练习表达，而不是问“你对表达逻辑性的理解是什么”。
3. 技术类训练的下一题可以继续追问原理、场景、排查或项目使用。
4. 每次只输出一个单一问题。

输出要求：
你必须只输出严格 JSON，不要输出 Markdown。
JSON 格式：
{
  "feedback": "对本轮回答的具体反馈",
  "reference_points": ["本题参考要点1", "本题参考要点2", "本题参考要点3"],
  "sample_answer": "一段可参考的回答",
  "next_question": "下一道单一训练问题或 null",
  "is_finished": false
}
""".strip()

    EXPRESSION_KEYWORDS = (
        "表达",
        "逻辑",
        "沟通",
        "结构",
        "条理",
        "讲不清",
        "说不清",
        "自我介绍",
        "语言",
        "总结",
    )
    PROJECT_EXPRESSION_KEYWORDS = (
        "项目表达",
        "项目描述",
        "项目经历",
        "项目亮点",
        "职责",
        "难点描述",
        "方案表达",
    )

    def __init__(self, llm_client: OpenAICompatibleClient | None = None) -> None:
        self._llm_client = llm_client or OpenAICompatibleClient()

    def build_first_question(self, title: str, reason: str | None) -> str:
        topic = title.strip()
        context = f"{title} {reason or ''}"
        if self._is_project_expression_training(context):
            return (
                f"我们围绕「{topic}」做专项训练。请你选择一个最近参与的项目，"
                "用「项目背景、业务目标、你的职责、关键技术方案、最终结果」这五步介绍一遍。"
            )
        if self._is_expression_training(context):
            return (
                f"我们围绕「{topic}」做专项训练。请你选择一个项目中的技术问题，"
                "用「问题背景、分析过程、解决方案、最终结果」四步讲清楚。"
            )
        if reason:
            return (
                f"我们围绕「{topic}」做专项训练。你先说一下这个知识点的核心概念、"
                "典型使用场景，以及它在项目里通常解决什么问题？"
            )
        return f"我们围绕「{topic}」做专项训练。你先说一下你对这个知识点的核心理解？"

    def review_answer(
        self,
        task_title: str,
        task_reason: str | None,
        question: str,
        answer: str,
        history: list[dict[str, str]],
    ) -> TrainingTurn:
        training_type = self._training_type(task_title, task_reason)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"训练任务：{task_title}\n"
                    f"薄弱原因：{task_reason or '未提供'}\n"
                    f"训练类型：{training_type}\n"
                    f"本轮问题：{question}\n"
                    f"候选人回答：{answer}\n\n"
                    f"历史训练记录：\n{self._format_history(history)}\n\n"
                    "请生成本轮反馈、参考要点、参考回答，并决定是否继续下一题。"
                ),
            },
        ]
        content = self._llm_client.chat(messages)
        return self._parse_turn(content, question=question, answer=answer, training_type=training_type)

    def _parse_turn(self, content: str, question: str, answer: str, training_type: str) -> TrainingTurn:
        try:
            payload = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return self._fallback_turn(question, answer, training_type)

        points = payload.get("reference_points")
        reference_points = [
            str(item).strip()
            for item in points
            if str(item).strip()
        ] if isinstance(points, list) else []

        fallback = self._fallback_turn(question, answer, training_type)
        next_question = payload.get("next_question")
        if next_question is not None:
            next_question = self._sanitize_question(str(next_question)) or None

        return TrainingTurn(
            feedback=str(payload.get("feedback") or "").strip() or fallback.feedback,
            reference_points=reference_points or fallback.reference_points,
            sample_answer=str(payload.get("sample_answer") or "").strip() or fallback.sample_answer,
            next_question=next_question,
            is_finished=bool(payload.get("is_finished", False)),
            raw_json=payload,
        )

    def _fallback_turn(self, question: str, answer: str, training_type: str) -> TrainingTurn:
        if training_type in {"expression", "project_expression"}:
            if len(answer.strip()) >= 120:
                feedback = "你的回答已经有一定信息量，下一步要加强结构顺序、重点突出和结果量化，让面试官更容易抓住你的贡献。"
            else:
                feedback = "当前回答偏简略，建议按照固定结构展开，并补充个人职责、关键动作和结果。"
            return TrainingTurn(
                feedback=feedback,
                reference_points=["先交代背景", "明确个人职责", "讲清关键动作", "补充结果数据", "最后总结复盘"],
                sample_answer=(
                    "可以按这样的结构回答：这个问题发生在什么业务背景下，我负责哪一部分，"
                    "我先做了哪些分析，然后采取了什么方案，最后带来了哪些可验证的结果。"
                ),
                next_question="请你再用 1 分钟重述一遍，重点突出你的个人职责和最终结果。",
                is_finished=False,
            )

        if len(answer.strip()) >= 120:
            feedback = "你的回答已经有一定信息量，建议继续补充关键机制、适用场景和边界条件，让表达更接近真实面试中的高质量回答。"
        else:
            feedback = "当前回答偏简略，建议补充定义、核心流程、典型场景和容易踩坑的边界条件。"
        return TrainingTurn(
            feedback=feedback,
            reference_points=["说明核心概念", "讲清关键流程", "补充适用场景", "说明常见问题或边界条件"],
            sample_answer=f"可以先直接回答「{question}」的核心定义，再按流程、场景、风险点展开，并结合一个项目例子说明。",
            next_question="你能结合一个实际项目场景，说明这个知识点在什么情况下会产生问题吗？",
            is_finished=False,
        )

    def _training_type(self, title: str, reason: str | None) -> str:
        context = f"{title} {reason or ''}"
        if self._is_project_expression_training(context):
            return "project_expression"
        if self._is_expression_training(context):
            return "expression"
        return "technical"

    def _is_expression_training(self, context: str) -> bool:
        return any(keyword in context for keyword in self.EXPRESSION_KEYWORDS)

    def _is_project_expression_training(self, context: str) -> bool:
        return any(keyword in context for keyword in self.PROJECT_EXPRESSION_KEYWORDS)

    def _format_history(self, history: list[dict[str, str]]) -> str:
        if not history:
            return "暂无历史训练记录。"
        return "\n".join(
            f"[{item.get('role')}][round={item.get('round_no')}] {item.get('content')}"
            for item in history[-10:]
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
        indexes = [index for index in (normalized.find("？"), normalized.find("?")) if index >= 0]
        if indexes:
            return normalized[: min(indexes) + 1]
        return normalized
