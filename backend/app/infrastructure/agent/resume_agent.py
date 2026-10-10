import json
import re

from app.domain.resume.entities import STAGE_ORDER
from app.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient

STAGE_LABELS: dict[str, str] = {
    "BASIC": "基本信息",
    "EDUCATION": "教育背景",
    "WORK": "工作经历",
    "PROJECT": "项目经历",
    "SKILL": "技能栈",
    "INTENT": "求职意向",
    "DONE": "结束",
}

# 各分节允许的结构化字段，供模型抽取时对齐
SECTION_FIELDS: dict[str, list[str]] = {
    "BASIC": ["name", "target_role", "years", "city"],
    "EDUCATION": ["school", "major", "degree", "period"],
    "WORK": ["company", "role", "period", "highlights"],
    "PROJECT": ["name", "background", "role", "stack", "challenge", "result"],
    "INTENT": ["position", "city", "notes"],
}


class ResumeAgent:
    """Conversational resume assistant backed by an OpenAI-compatible LLM."""

    SYSTEM_PROMPT = """
你是一名资深的简历顾问，正在通过多轮对话引导用户梳理经历，最终生成一份结构化简历。

引导分节固定按以下顺序推进：
BASIC（基本信息）→ EDUCATION（教育背景）→ WORK（工作经历）→ PROJECT（项目经历）→ SKILL（技能栈）→ INTENT（求职意向）

引导原则（必须严格遵守）：
1. 核心是「引导」而不是「收集」：用户回答过于简略时，要追问具体化，例如「这个优化有数据支撑吗？提升多少？」「这块是你负责还是团队？你具体做了哪部分？」
2. 每次只问一个问题。唯一的例外是 BASIC 节，可以一次性问清称呼、工作年限、所在城市。
3. 用户明确表示「没有 / 跳过 / 不知道」时，不要再纠缠该点，视为该节信息已确定。
4. 用户卡住时，可以给一句示例引导，例如「可以这样写：负责 XX 模块，用 XX 方案把 XX 从 A 优化到 B」。
5. 绝对不要编造用户没有提供的信息。merge 里只允许出现用户原话中确实提到的内容；可以润色措辞，但不能新增事实。
6. 技能与经历以用户原话为准，不要替用户补充未提及的公司、项目或技术。
7. 不要输出 Markdown，不要输出解释，只输出严格 JSON。

输出 JSON 格式：
{
  "merge": {
    // 从用户最新回答中抽取的、属于「当前分节」的结构化字段；没有就不给该字段
    // BASIC:    {"name": "", "target_role": "", "years": "", "city": ""}
    // EDUCATION:{"school": "", "major": "", "degree": "", "period": ""}
    // WORK:     {"company": "", "role": "", "period": "", "highlights": ["..."]}
    // PROJECT:  {"name": "", "background": "", "role": "", "stack": "", "challenge": "", "result": ""}
    // SKILL:    {"skills": ["..."]}
    // INTENT:   {"position": "", "city": "", "notes": ""}
  },
  "section_complete": false,   // 当前分节信息是否已经足够，可以推进到下一分节
  "follow_up_question": "",    // 若仍需继续追问当前分节，问这个单一问题
  "next_section_question": ""  // 若推进到下一分节，用这个问题作为下一节的开场问题
}
""".strip()

    RESUME_SYSTEM_PROMPT = """
你是一名简历撰写助手。任务是把用户**已经提供**的信息整理成一份 Markdown 简历。

最重要的一条：**只允许使用用户已经提供的信息，严禁新增任何用户未提供的事实。**
简历是要拿去投递、面试会被逐个追问的，任何一个用户没说过的细节都会让用户当场穿帮。

你唯一被允许做的三件事：
1. 重新组织用户已提供信息的顺序与层次；
2. 改写句式、润色表达，使其更书面、更简洁；
3. 合并重复的表述。

以下是**严格禁止新增**的内容类别（用户原话里没出现的，一个字都不许写）：
1. 量化结果与指标：任何提升幅度、百分比、QPS、并发量、延时（P99/P95/平均）、准确率、用户量、订单量、覆盖人数等数字；
2. 技术手段与中间件：异步化、缓存、读写分离、分库分表、消息队列、限流、熔断、向量召回、热度降权等实现方案，以及任何具体中间件/框架/库名称（Redis、Kafka、Pandas、Scikit-learn 等）；
3. 架构方案：微服务、DDD、事件驱动、领域拆分等；
4. 版本号：v1.0、v2.3、第几代等；
5. 荣誉与致谢：获奖、榜单、Maintainer 致谢/认可、被某方采用等；
6. 业务规模：日均百万级、千万用户、GMV、峰值等；
7. 团队规模：带几人团队、跨部门协作人数等。

信息不足时的处理：**宁可留白、写短，也不要补全。** 缺失的信息整句省略，
不要用「待补充」「N/A」等占位内容填充，也不要为了句式完整而脑补细节。
用户明确说「没有 / 跳过」的分节，直接省略该分节，不要输出「无」「暂无」之类的空节标题。

输出前必须自检（逐句执行）：
逐条检查你写下的每一句事实性表述，尤其是数字、技术名词、版本号、荣誉、规模，
逐条自问「这在用户提供的回答或信息里能找到出处吗？」
- 找不到出处的：删掉该表述，或改写成不包含该事实的版本。
- 拿不准的：按「用户没说过」处理，删掉。

结构要求：
1. 使用标准简历结构：一级标题为姓名（或简历标题），随后按「教育背景 / 工作经历 / 项目经历 / 技能栈 / 求职意向」分节，只输出有内容的分节。
2. 工作经历与项目经历用有条理的 bullet 表达，突出用户明确说过的个人职责与结果。
3. 直接输出 Markdown 正文，不要输出任何解释、说明或代码块围栏。
""".strip()

    def __init__(self, llm_client: OpenAICompatibleClient | None = None) -> None:
        self._llm_client = llm_client or OpenAICompatibleClient()

    def generate_next_question(
        self,
        *,
        target_role: str | None,
        current_stage: str,
        sections: dict,
        history: list[dict],
        follow_up_count: int,
    ) -> dict:
        """Ask the LLM for the next guidance step.

        Returns a dict with keys: merge, section_complete, follow_up_question,
        next_section_question. On non-JSON output, returns an empty dict so the
        caller can fall back to deterministic questions.
        """
        next_stage = self._next_stage(current_stage)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户目标岗位：{target_role or '未提供'}\n"
                    f"当前分节：{current_stage}（{STAGE_LABELS.get(current_stage, current_stage)}）\n"
                    f"下一分节：{next_stage}（{STAGE_LABELS.get(next_stage, next_stage)}）\n"
                    f"当前分节已追问次数：{follow_up_count}\n"
                    f"当前已收集的结构化信息：\n{json.dumps(sections, ensure_ascii=False)}\n\n"
                    "本会话对话历史：\n"
                    f"{self._format_history(history)}\n\n"
                    f"请先抽取用户最新回答中属于「{current_stage}」的结构化字段填入 merge，"
                    "再判断该分节信息是否已经足够（section_complete）。\n"
                    "如果还需要继续追问当前分节，请在 follow_up_question 给出一个具体的单一追问；"
                    f"如果可以推进到下一分节，请在 next_section_question 给出「{next_stage}」的开场问题。\n"
                    "记住：只输出严格 JSON。"
                ),
            },
        ]
        content = self._llm_client.chat(messages)
        return self._parse_payload(content)

    SUPPLEMENT_SYSTEM_PROMPT = """
你是一名资深的简历顾问。用户已经完成了一轮完整的简历信息收集并生成过简历，现在想继续补充内容。

请从用户的最新回答中抽取结构化字段，按所属分节归入 merge。

硬性要求：
1. 绝对不要编造用户没有提供的信息；merge 里只允许出现用户原话中确实提到的内容。
2. 只抽取用户最新回答中新增的信息，不要重复已经收集过的内容。
3. 不要输出 Markdown，不要输出解释，只输出严格 JSON。

输出 JSON 格式：
{
  "merge": {
    // 只给出用户最新回答确实涉及的分节；没有涉及的直接省略该分节
    // "basic":    {"name": "", "target_role": "", "years": "", "city": ""}
    // "education":{"school": "", "major": "", "degree": "", "period": ""}
    // "work":     {"company": "", "role": "", "period": "", "highlights": ["..."]}
    // "projects": {"name": "", "background": "", "role": "", "stack": "", "challenge": "", "result": ""}
    // "skills":   ["..."]
    // "intent":   {"position": "", "city": "", "notes": ""}
  }
}
""".strip()

    def extract_supplement(
        self,
        *,
        target_role: str | None,
        sections: dict,
        history: list[dict],
    ) -> dict:
        """抽取「已完成草稿」补充回答中的结构化字段。

        与 generate_next_question 不同，这里不区分当前分节：模型自行判断补充内容
        属于哪个分节，返回值形如 {"merge": {"work": {...}, "skills": [...]}}。
        输出非 JSON 时返回 {"merge": {}}，由调用方决定是否兜底。
        """
        messages = [
            {"role": "system", "content": self.SUPPLEMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户目标岗位：{target_role or '未提供'}\n"
                    f"当前已收集的结构化信息：\n{json.dumps(sections, ensure_ascii=False)}\n\n"
                    "本会话对话历史：\n"
                    f"{self._format_history(history)}\n\n"
                    "请抽取用户最新回答中新增的结构化字段，按分节归入 merge。"
                    "记住：只输出严格 JSON。"
                ),
            },
        ]
        content = self._llm_client.chat(messages)
        return {"merge": self._parse_payload(content).get("merge") or {}}

    def generate_resume(
        self,
        *,
        sections: dict,
        target_role: str | None,
        history: list[dict] | None = None,
    ) -> str:
        """Generate the final Markdown resume from collected sections.

        history 只取用户侧发言，作为「每句事实是否有出处」的核对依据；
        助手侧的引导问题（含示例句式）不参与，避免把示例误当成用户提供的事实。
        """
        messages = [
            {"role": "system", "content": self.RESUME_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户目标岗位：{target_role or '未提供'}\n\n"
                    f"已收集的结构化信息（唯一可用素材）：\n"
                    f"{json.dumps(sections, ensure_ascii=False)}\n\n"
                    f"用户在对话中的原始回答（唯一可用素材，用于核对每句是否有出处）：\n"
                    f"{self._format_user_answers(history or [])}\n\n"
                    "请生成完整的 Markdown 简历。再次强调：只允许使用以上素材中出现过的信息，"
                    "任何未出现在素材中的数字、技术手段、版本号、荣誉、规模都不得写入。"
                ),
            },
        ]
        return self._llm_client.chat(messages)

    def _parse_payload(self, content: str) -> dict:
        try:
            payload = json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}

        merge = payload.get("merge")
        return {
            "merge": merge if isinstance(merge, dict) else {},
            "section_complete": bool(payload.get("section_complete")),
            "follow_up_question": str(payload.get("follow_up_question") or "").strip(),
            "next_section_question": str(payload.get("next_section_question") or "").strip(),
        }

    @staticmethod
    def _next_stage(current_stage: str) -> str:
        if current_stage in STAGE_ORDER:
            index = STAGE_ORDER.index(current_stage)
            if index + 1 < len(STAGE_ORDER):
                return STAGE_ORDER[index + 1]
        return "DONE"

    @staticmethod
    def _format_user_answers(history: list[dict]) -> str:
        answers = [
            str(item.get("content", "")).strip()
            for item in history
            if item.get("role") == "user" and str(item.get("content", "")).strip()
        ]
        if not answers:
            return "（用户未留下文字回答）"
        return "\n".join(f"- {answer}" for answer in answers)

    def _format_history(self, history: list[dict]) -> str:
        if not history:
            return "暂无历史对话。"
        lines: list[str] = []
        for item in history[-12:]:
            role = "顾问" if item.get("role") == "assistant" else "用户"
            stage = item.get("stage", "")
            lines.append(f"[{stage}] {role}：{item.get('content', '')}")
        return "\n".join(lines)

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
