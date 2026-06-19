import json
import re

from app.domain.report.entities import InterviewReport
from app.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient


class ReportAgent:
    """Generate final interview reports with an OpenAI-compatible LLM."""

    SYSTEM_PROMPT = """
你是一名资深 Java 技术面试官、面试评估专家和训练教练。
请基于完整面试记录生成最终面试报告。

评估目标：
1. 这是一个 AI 面试陪练产品，不是淘汰型面试系统。
2. 报告要真实指出问题，但语气要建设性、可训练、可改进。
3. 不要因为某几个知识点答不上来就过度压低总分。
4. 不要编造候选人没有提到的项目、经历或能力。
5. 所有判断必须来自面试记录。

候选人级别判断：
1. 先从简历、自我介绍、项目描述和历史回答中推定大致工作年限。
2. 如果能判断出年限，请按该年限对应的 Java 开发工程师水平评估。
3. 如果无法明确判断年限，默认按 2-4 年 Java 开发工程师标准评估。
4. 报告中可以自然提及“从当前面试表现看，更接近初级/中级/高级水平”，但不要武断断言真实工作年限。

评分机制：
1. 技术基础 30%
2. 项目经验 25%
3. 问题分析 20%
4. 表达能力 15%
5. 岗位匹配 10%

请从完整面试记录中提取 3-5 条关键问答证据 evidence_items。
每条证据必须来自真实问答，不要编造。
证据应优先对应薄弱点、评分依据或重要项目能力判断。
不要输出完整长回答，只输出回答摘要。

你必须只输出严格 JSON，不要输出 Markdown。
JSON 字段：
{
  "overall_score": 0-100,
  "technical_analysis": "技术能力分析",
  "communication_analysis": "表达能力分析",
  "project_analysis": "项目经验分析",
  "weakness_points": [
    {"name": "薄弱点名称", "reason": "原因", "severity": "High|Medium|Low"}
  ],
  "improvement_suggestions": [
    {"title": "建议标题", "description": "具体建议", "priority": "High|Medium|Low"}
  ],
  "recommended_training": [
    {"title": "训练方向", "description": "训练内容", "priority": "High|Medium|Low"}
  ],
  "evidence_items": [
    {
      "title": "证据标题",
      "related_weakness": "对应薄弱点或评分依据",
      "question": "真实面试问题",
      "answer_summary": "候选人回答摘要",
      "evidence_reason": "为什么该问答能支撑报告结论",
      "impact": "High|Medium|Low"
    }
  ]
}
""".strip()

    def __init__(self, llm_client: OpenAICompatibleClient | None = None) -> None:
        self._llm_client = llm_client or OpenAICompatibleClient()

    def generate(
        self,
        session_id: str,
        job_role: str,
        messages: list[dict[str, str]],
    ) -> InterviewReport:
        content = self._llm_client.chat(
            [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"面试岗位：{job_role}\n"
                        "完整面试记录：\n"
                        f"{self._format_messages(messages)}\n\n"
                        "请生成结构化面试报告。"
                    ),
                },
            ]
        )
        payload = self._parse_json(content)
        return InterviewReport(
            session_id=session_id,
            overall_score=self._clamp_score(payload.get("overall_score", 0)),
            technical_analysis=str(payload.get("technical_analysis", "")),
            communication_analysis=str(payload.get("communication_analysis", "")),
            project_analysis=str(payload.get("project_analysis", "")),
            weakness_points=self._as_list(payload.get("weakness_points")),
            improvement_suggestions=self._as_list(payload.get("improvement_suggestions")),
            recommended_training=self._as_list(payload.get("recommended_training")),
            raw_report_json=payload,
        )

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        lines = []
        for item in messages:
            role = item.get("role", "UNKNOWN")
            round_no = item.get("round_no", "")
            content = item.get("content", "")
            lines.append(f"[{role}][round={round_no}] {content}")
        return "\n".join(lines)

    def _parse_json(self, content: str) -> dict:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Report LLM returned invalid JSON") from exc

    def _clamp_score(self, value: object) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0
        return min(100, max(0, score))

    def _as_list(self, value: object) -> list[dict]:
        return value if isinstance(value, list) else []
