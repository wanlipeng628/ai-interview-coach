import logging
import re
from datetime import UTC, datetime
from uuid import uuid4

from app.application.resume.resume_assistant_dto import (
    AnswerResponse,
    DraftDetailResponse,
    DraftMessageResponse,
    FinalizeResponse,
    ProgressResponse,
    StartDraftRequest,
    StartDraftResponse,
    SubmitAnswerRequest,
)
from app.application.resume.resume_dto import ResumeProfileResponse
from app.domain.resume.entities import (
    DONE_STAGE,
    MAX_FOLLOW_UPS,
    STAGE_ORDER,
    ResumeDraft,
    ResumeDraftStatus,
    empty_sections,
)
from app.domain.resume.errors import ResumeAnswerEmptyError, ResumeDraftNotFoundError
from app.infrastructure.agent.resume_agent import ResumeAgent
from app.infrastructure.repositories.resume_draft_repository import ResumeDraftRepository
from app.infrastructure.repositories.resume_repository import ResumeRepository

logger = logging.getLogger(__name__)

# 各分节的开场问题（LLM 不可用时的兜底，也用作推进到新分节时的默认问题）
STAGE_FIRST_QUESTIONS: dict[str, str] = {
    "BASIC": "先做一个简单了解：怎么称呼你？你目前的工作年限和所在城市是什么？",
    "EDUCATION": "接下来了解一下教育背景：你的学校、专业、学历和就读时间分别是什么？",
    "WORK": "聊聊你的工作经历：最近一份工作是在哪家公司、担任什么职位、在职时间是什么时候？",
    "PROJECT": "挑一个你最有代表性的项目介绍一下：这个项目是做什么的，你在里面负责哪部分？",
    "SKILL": "你目前比较熟练的技术栈有哪些？",
    "INTENT": "最后聊聊求职意向：你希望找什么方向或岗位，期望的城市是哪里？",
}

# 各分节的追问问题（用户回答过于简略时使用）
STAGE_FOLLOW_UP_QUESTIONS: dict[str, str] = {
    "BASIC": "能再具体一点吗？比如你最近一份工作的公司、职位和时间段。",
    "EDUCATION": "能补充一下具体的就读时间段和学历/学位吗？",
    "WORK": "这段经历里，你自己具体负责了哪部分？有没有可以量化的成果（比如提升了多少、覆盖多少人）？",
    "PROJECT": "这个项目里你具体做了哪些部分？有没有遇到关键难点，或者可以量化的结果？",
    "SKILL": "这些技术里你最熟练的是哪几个？分别用在什么场景、大概用了多久？",
    "INTENT": "能具体一点吗？比如目标岗位名称、期望城市，以及有没有特别要求（行业、公司规模等）？",
}

# 分节 → sections 中的键
STAGE_SECTION_KEY: dict[str, str] = {
    "BASIC": "basic",
    "EDUCATION": "education",
    "WORK": "work",
    "PROJECT": "projects",
    "SKILL": "skills",
    "INTENT": "intent",
}

# 分节中文名，用于向用户列出未完成分节
STAGE_NAMES: dict[str, str] = {
    "BASIC": "基本信息",
    "EDUCATION": "教育背景",
    "WORK": "工作经历",
    "PROJECT": "项目经历",
    "SKILL": "技能栈",
    "INTENT": "求职意向",
}

# sections 中的所有分节键（已完成的草稿做补充抽取时按此遍历）
SECTION_KEYS: tuple[str, ...] = ("basic", "education", "work", "projects", "skills", "intent")

DICT_SECTION_FIELDS: dict[str, list[str]] = {
    "basic": ["name", "target_role", "years", "city"],
    "intent": ["position", "city", "notes"],
}

LIST_SECTION_FIELDS: dict[str, tuple[str, list[str]]] = {
    "education": ("school", ["school", "major", "degree", "period"]),
    "work": ("company", ["company", "role", "period", "highlights"]),
    "projects": ("name", ["name", "background", "role", "stack", "challenge", "result"]),
}

# 用户主动结束引导的表达。判定为整句匹配：规范化后的整句必须能由这些短语（加语气词）
# 全部消耗掉才算结束指令，避免叙述句里出现「就这样 / 差不多了」被误判为结束而丢数据。
# 长短语排在前面，便于拼接短语（如「差不多了，帮我生成吧」）被完整拆分。
FINALIZE_PHRASES: tuple[str, ...] = (
    "帮我生成一份简历",
    "帮我生成简历",
    "帮我生成吧",
    "帮我生成",
    "帮忙生成",
    "生成一份简历",
    "生成简历",
    "生成吧",
    "直接生成",
    "可以生成",
    "帮我写一份简历",
    "帮我写简历",
    "帮我写吧",
    "帮我写",
    "就这样吧",
    "就这样",
    "差不多了",
    "不用问了",
    "结束吧",
    "可以了",
    "够了",
)

# 规范化后超过该长度的回答一律按叙述处理，不再判定为结束指令
FINALIZE_MAX_LENGTH = 12

# 结束短语拼接后允许残留的语气词
FINALIZE_FILLER = frozenset("吧了呢呀啊嘛哦嗯好行")

# 整句意图匹配前统一去掉空白与中英文标点，避免标点影响判断
ANSWER_NOISE_PATTERN = re.compile(r"[\s，。！？、,.!?;；:：'\"“”‘’]")

# 模型偶尔会把整份简历用 ``` 代码块围栏整体包裹（prompt 已要求不要输出围栏）。
# 落库前剥掉这层围栏，避免前端按 Markdown 渲染成一大段代码、摘要也被清空。
WRAPPING_FENCE_PATTERN = re.compile(r"^\s*```[^\n]*\n(.*?)\n?\s*```\s*$", re.DOTALL)

# 用户明确表示该节没有内容的触发词
SKIP_EXACT: frozenset[str] = frozenset(
    {
        "没有",
        "无",
        "没",
        "暂无",
        "无经验",
        "跳过",
        "不知道",
        "不清楚",
        "略过",
        "没了",
        "没有更多",
        "没有其他",
        "没有补充",
        "none",
        "skip",
        "n/a",
    }
)
SKIP_KEYWORDS: tuple[str, ...] = (
    "跳过",
    "略过",
    "不知道",
    "不清楚",
    "没有了",
    "暂无",
    "没有其他",
    "没有补充",
)
SKIP_PREFIXES: tuple[str, ...] = (
    "没有",
    "暂无",
    "跳过",
    "略过",
    "不知道",
    "不清楚",
    "没经验",
    "没做过",
    "没接触",
    "没相关",
)


class ResumeAssistantService:
    """Coordinates the conversational resume guidance use case."""

    def __init__(
        self,
        draft_repository: ResumeDraftRepository,
        resume_repository: ResumeRepository,
        resume_agent: ResumeAgent | None = None,
    ) -> None:
        self._draft_repository = draft_repository
        self._resume_repository = resume_repository
        self._resume_agent = resume_agent

    # ------------------------------------------------------------------ 用例

    def start(self, user_id: int, request: StartDraftRequest) -> StartDraftResponse:
        """Create a draft and return the opening BASIC question."""
        target_role = (request.target_role or "").strip() or None
        title = (request.title or "默认简历").strip() or "默认简历"

        sections = empty_sections()
        if target_role:
            sections["basic"]["target_role"] = target_role

        question = self._first_question("BASIC", target_role)
        draft = ResumeDraft(
            session_id=str(uuid4()),
            user_id=user_id,
            status=ResumeDraftStatus.IN_PROGRESS.value,
            stage="BASIC",
            messages=[self._build_message("assistant", question, "BASIC")],
            sections=sections,
            follow_up_count=0,
            target_role=target_role,
            title=title,
        )
        self._draft_repository.create(draft)

        return StartDraftResponse(
            draft_id=draft.session_id,
            status=draft.status,
            stage=draft.stage,
            question=question,
            progress=self._progress("BASIC"),
        )

    def submit_answer(
        self,
        user_id: int,
        draft_id: str,
        request: SubmitAnswerRequest,
    ) -> AnswerResponse:
        """Record the user's answer and decide the next guidance step."""
        draft = self._draft_repository.get(user_id, draft_id)
        if draft is None:
            raise ResumeDraftNotFoundError()

        answer = (request.answer or "").strip()
        if not answer:
            raise ResumeAnswerEmptyError()

        # 已完成的草稿：仍可继续接受补充。只把回答并入对应分节，
        # 不推进分节、不改变状态，用户后续可再次 finalize 重新生成。
        if draft.is_completed:
            draft.messages.append(self._build_message("user", answer, DONE_STAGE))
            self._merge_supplement(draft)
            self._draft_repository.save(draft)
            return AnswerResponse(
                draft_id=draft.session_id,
                status=draft.status,
                stage=DONE_STAGE,
                question=None,
                ready_to_finalize=True,
                progress=self._progress(DONE_STAGE),
            )

        current_stage = draft.stage
        draft.messages.append(self._build_message("user", answer, current_stage))

        # 1. 用户主动结束：仅当分节已全部完成（或已跳过）时才结束；
        #    仍有分节未完成时只给提示，不置 COMPLETED、不虚报进度。
        if self._is_finalize_intent(answer):
            pending = self._pending_sections(current_stage)
            if not pending:
                return self._complete_draft(draft)
            return self._prompt_pending_sections(draft, pending)

        # 2. 用户明确跳过当前分节：标记为空并推进
        if self._is_skip_answer(answer):
            self._ensure_section(draft, current_stage)
            target_stage = self._next_stage(current_stage)
            if target_stage == DONE_STAGE:
                return self._complete_draft(draft)
            return self._advance_to(
                draft,
                target_stage,
                question=self._first_question(target_stage, draft.target_role),
            )

        # 3. 常规回答：调用 Agent 抽取结构化信息并判断分节是否充分
        agent_result = self._safe_generate_next_question(draft, current_stage)
        self._merge_sections(draft.sections, current_stage, agent_result.get("merge") or {})

        section_complete = bool(agent_result.get("section_complete"))
        # 同一分节最多追问 MAX_FOLLOW_UPS 轮，超过后无论是否充分都强制推进
        should_advance = section_complete or draft.follow_up_count >= MAX_FOLLOW_UPS

        if should_advance:
            target_stage = self._next_stage(current_stage)
            if target_stage == DONE_STAGE:
                return self._complete_draft(draft)
            question = str(
                agent_result.get("next_section_question") or ""
            ).strip() or self._first_question(target_stage, draft.target_role)
            return self._advance_to(draft, target_stage, question=question)

        # 继续追问当前分节
        draft.follow_up_count += 1
        question = str(
            agent_result.get("follow_up_question") or ""
        ).strip() or self._follow_up_question(current_stage)
        draft.messages.append(self._build_message("assistant", question, current_stage))
        self._draft_repository.save(draft)
        return AnswerResponse(
            draft_id=draft.session_id,
            status=draft.status,
            stage=current_stage,
            question=question,
            ready_to_finalize=False,
            progress=self._progress(current_stage),
        )

    def finalize(self, user_id: int, draft_id: str) -> FinalizeResponse:
        """Generate the Markdown resume and persist it as the user's profile.

        反复调用会重新生成并覆盖当前用户的默认简历（可迭代语义），
        而不是直接返回上一次的结果，以便用户补充信息后再次生成。
        """
        draft = self._draft_repository.get(user_id, draft_id)
        if draft is None:
            raise ResumeDraftNotFoundError()

        content = self._safe_generate_resume(draft)
        profile = self._resume_repository.upsert_default(
            user_id=user_id,
            title=draft.title,
            content=content,
        )

        draft.profile_id = profile.id
        draft.status = ResumeDraftStatus.COMPLETED.value
        draft.stage = DONE_STAGE
        self._draft_repository.save(draft)

        return self._to_finalize_response(draft, profile)

    def get_draft(self, user_id: int, draft_id: str) -> DraftDetailResponse:
        """Fetch full draft state for refresh / resume conversation."""
        draft = self._draft_repository.get(user_id, draft_id)
        if draft is None:
            raise ResumeDraftNotFoundError()

        return DraftDetailResponse(
            draft_id=draft.session_id,
            status=draft.status,
            stage=draft.stage,
            messages=[
                DraftMessageResponse(
                    role=str(item.get("role", "")),
                    content=str(item.get("content", "")),
                    stage=str(item.get("stage", "")),
                )
                for item in draft.messages
            ],
            sections=draft.sections,
            progress=self._progress(draft.stage),
            ready_to_finalize=draft.is_completed,
        )

    # ------------------------------------------------------------- 状态流转

    def _complete_draft(self, draft: ResumeDraft) -> AnswerResponse:
        draft.status = ResumeDraftStatus.COMPLETED.value
        draft.stage = DONE_STAGE
        draft.follow_up_count = 0
        self._draft_repository.save(draft)
        return AnswerResponse(
            draft_id=draft.session_id,
            status=draft.status,
            stage=DONE_STAGE,
            question=None,
            ready_to_finalize=True,
            progress=self._progress(DONE_STAGE),
        )

    def _advance_to(
        self, draft: ResumeDraft, target_stage: str, *, question: str
    ) -> AnswerResponse:
        draft.stage = target_stage
        draft.follow_up_count = 0
        draft.messages.append(self._build_message("assistant", question, target_stage))
        self._draft_repository.save(draft)
        return AnswerResponse(
            draft_id=draft.session_id,
            status=draft.status,
            stage=target_stage,
            question=question,
            ready_to_finalize=False,
            progress=self._progress(target_stage),
        )

    def _next_stage(self, current_stage: str) -> str:
        if current_stage in STAGE_ORDER:
            index = STAGE_ORDER.index(current_stage)
            if index + 1 < len(STAGE_ORDER):
                return STAGE_ORDER[index + 1]
        return DONE_STAGE

    @staticmethod
    def _pending_sections(current_stage: str) -> list[str]:
        """返回尚未完成的分节（当前分节及其后的所有分节）。

        分节按固定顺序推进，凡已推进过去的分节都算完成（含用户主动「跳过」的），
        因此未完成分节就是当前分节及其后所有分节；DONE 表示已全部完成。
        """
        if current_stage == DONE_STAGE:
            return []
        if current_stage in STAGE_ORDER:
            return list(STAGE_ORDER[STAGE_ORDER.index(current_stage) :])
        return list(STAGE_ORDER)

    def _prompt_pending_sections(
        self, draft: ResumeDraft, pending: list[str]
    ) -> AnswerResponse:
        """命中结束短语但分节未齐：提示未完成分节，草稿保持 IN_PROGRESS。

        不推进分节、不置 COMPLETED，progress 按真实已完成分节返回；
        用户可继续补充，或对不需要的分节回复「没有 / 跳过」推进。
        """
        names = "、".join(STAGE_NAMES.get(stage, stage) for stage in pending)
        question = (
            f"还有这些分节没有完成：{names}。"
            "你可以继续补充，或者回复「没有 / 跳过」把不需要的分节略过；"
            "全部补齐（或跳过）后，再对我说「帮我生成吧」就可以了。"
        )
        draft.messages.append(self._build_message("assistant", question, draft.stage))
        self._draft_repository.save(draft)
        return AnswerResponse(
            draft_id=draft.session_id,
            status=draft.status,
            stage=draft.stage,
            question=question,
            ready_to_finalize=False,
            progress=self._progress(draft.stage),
        )

    def _progress(self, current_stage: str) -> ProgressResponse:
        if current_stage == DONE_STAGE or current_stage not in STAGE_ORDER:
            return ProgressResponse(completed=list(STAGE_ORDER), current=DONE_STAGE)
        index = STAGE_ORDER.index(current_stage)
        return ProgressResponse(completed=list(STAGE_ORDER[:index]), current=current_stage)

    # --------------------------------------------------------------- Agent 调用

    def _safe_generate_next_question(self, draft: ResumeDraft, current_stage: str) -> dict:
        """Call the LLM agent, falling back to an empty result on any failure."""
        try:
            agent = self._get_agent()
            return agent.generate_next_question(
                target_role=draft.target_role,
                current_stage=current_stage,
                sections=draft.sections,
                history=draft.messages,
                follow_up_count=draft.follow_up_count,
            )
        except Exception:
            logger.exception("resume agent failed to generate next question")
            return {}

    def _safe_generate_resume(self, draft: ResumeDraft) -> str:
        """Generate the Markdown resume, falling back to a deterministic render."""
        try:
            agent = self._get_agent()
            content = agent.generate_resume(
                sections=draft.sections,
                target_role=draft.target_role,
                history=draft.messages,
            )
            if content and content.strip():
                return self._strip_wrapping_fence(content)
            logger.warning("resume agent returned empty content, using fallback render")
        except Exception:
            logger.exception("resume agent failed to generate resume, using fallback render")
        return self._render_fallback_markdown(draft)

    def _get_agent(self) -> ResumeAgent:
        if self._resume_agent is None:
            self._resume_agent = ResumeAgent()
        return self._resume_agent

    def _first_question(self, stage: str, target_role: str | None) -> str:
        question = STAGE_FIRST_QUESTIONS.get(stage, "请继续补充你的经历。")
        if stage == "BASIC" and target_role:
            return f"先做一个简单了解：怎么称呼你？你目前的工作年限和所在城市是什么？（目标岗位：{target_role}）"
        return question

    def _follow_up_question(self, stage: str) -> str:
        return STAGE_FOLLOW_UP_QUESTIONS.get(stage, "能再具体展开说说吗？")

    # ----------------------------------------------------------- 回答意图识别

    @staticmethod
    def _normalize_answer(answer: str) -> str:
        """去空白与中英文标点并转小写，用于整句意图匹配。"""
        return ANSWER_NOISE_PATTERN.sub("", answer.lower())

    def _is_finalize_intent(self, answer: str) -> bool:
        """整句判定用户是否要求结束引导。

        只有整句都由结束短语（可带语气词）构成才算，例如「帮我生成吧」
        「差不多了，帮我生成吧」；叙述句里的「就这样」「差不多了」不会被误判。
        """
        text = self._normalize_answer(answer)
        if not text or len(text) > FINALIZE_MAX_LENGTH:
            return False
        remainder = text
        matched = False
        for phrase in FINALIZE_PHRASES:
            if phrase in remainder:
                remainder = remainder.replace(phrase, "")
                matched = True
        return matched and all(char in FINALIZE_FILLER for char in remainder)

    def _is_skip_answer(self, answer: str) -> bool:
        text = self._normalize_answer(answer)
        if not text:
            return True
        if text in SKIP_EXACT:
            return True
        if len(text) <= 12 and any(keyword in text for keyword in SKIP_KEYWORDS):
            return True
        # 短句以否定词开头，视为明确表示该节没有内容
        return len(text) <= 8 and text.startswith(SKIP_PREFIXES)

    # ------------------------------------------------------------- 结构化合并

    def _merge_sections(self, sections: dict, stage: str, merge: dict) -> None:
        key = STAGE_SECTION_KEY.get(stage)
        if key is None or not isinstance(merge, dict) or not merge:
            return
        payload = merge[key] if key in merge else merge
        self._merge_section_payload(sections, key, payload)

    def _merge_supplement(self, draft: ResumeDraft) -> None:
        """把「已完成草稿」的补充回答并入对应分节（不推进分节）。"""
        try:
            agent = self._get_agent()
            result = agent.extract_supplement(
                target_role=draft.target_role,
                sections=draft.sections,
                history=draft.messages,
            )
        except Exception:
            logger.exception("resume agent failed to extract supplement")
            return

        merge = result.get("merge") if isinstance(result, dict) else None
        if not isinstance(merge, dict) or not merge:
            return
        for key in SECTION_KEYS:
            if key in merge:
                self._merge_section_payload(draft.sections, key, merge[key])

    def _merge_section_payload(self, sections: dict, key: str, payload: object) -> None:
        if payload is None:
            return

        if key in DICT_SECTION_FIELDS:
            self._merge_dict_section(
                sections.setdefault(key, {}), payload, DICT_SECTION_FIELDS[key]
            )
        elif key in LIST_SECTION_FIELDS:
            key_field, fields = LIST_SECTION_FIELDS[key]
            self._merge_list_section(sections.setdefault(key, []), payload, key_field, fields)
        elif key == "skills":
            self._merge_skill_list(sections.setdefault(key, []), payload)

    @staticmethod
    def _merge_dict_section(target: dict, payload: object, allowed_fields: list[str]) -> None:
        if not isinstance(target, dict) or not isinstance(payload, dict):
            return
        for field in allowed_fields:
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                target[field] = value.strip()

    def _merge_list_section(
        self,
        target: list,
        payload: object,
        key_field: str,
        fields: list[str],
    ) -> None:
        if not isinstance(target, list):
            return
        if isinstance(payload, dict):
            incoming_items = [payload]
        elif isinstance(payload, list):
            incoming_items = [item for item in payload if isinstance(item, dict)]
        else:
            return

        for item in incoming_items:
            cleaned = self._clean_list_item(item, fields)
            if not cleaned:
                continue
            key_value = cleaned.get(key_field)
            if target and (not key_value or target[-1].get(key_field) == key_value):
                # 同一实体的补充信息，合并进最后一条
                for field, value in cleaned.items():
                    if field == "highlights":
                        merged = list(target[-1].get("highlights") or [])
                        for highlight in value:
                            if highlight not in merged:
                                merged.append(highlight)
                        target[-1]["highlights"] = merged
                    else:
                        target[-1][field] = value
                continue

            base = {field: ([] if field == "highlights" else "") for field in fields}
            base.update(cleaned)
            target.append(base)

    @staticmethod
    def _clean_list_item(item: dict, fields: list[str]) -> dict:
        cleaned: dict = {}
        for field in fields:
            value = item.get(field)
            if field == "highlights":
                highlights = (
                    [str(entry).strip() for entry in value] if isinstance(value, list) else []
                )
                if isinstance(value, str) and value.strip():
                    highlights = [value.strip()]
                highlights = [entry for entry in highlights if entry]
                if highlights:
                    cleaned["highlights"] = highlights
            elif isinstance(value, str) and value.strip():
                cleaned[field] = value.strip()
        return cleaned

    @staticmethod
    def _merge_skill_list(target: list, payload: object) -> None:
        if not isinstance(target, list):
            return
        if isinstance(payload, dict):
            payload = payload.get("skills", [])
        if isinstance(payload, str):
            payload = [payload]
        if not isinstance(payload, list):
            return
        for entry in payload:
            text = str(entry).strip()
            if text and text not in target:
                target.append(text)

    def _ensure_section(self, draft: ResumeDraft, stage: str) -> None:
        """Ensure the current section key exists (empty default) without wiping data."""
        key = STAGE_SECTION_KEY.get(stage)
        if key is None:
            return
        defaults = empty_sections()
        draft.sections.setdefault(key, defaults[key])

    # ------------------------------------------------------------------ 渲染

    @staticmethod
    def _strip_wrapping_fence(content: str) -> str:
        """剥掉模型整体包裹正文的 ``` 代码块围栏；没有围栏时原样返回。"""
        text = content.strip()
        match = WRAPPING_FENCE_PATTERN.match(text)
        return match.group(1).strip() if match else text

    def _render_fallback_markdown(self, draft: ResumeDraft) -> str:
        """Deterministic Markdown render used when the LLM is unavailable.

        It only reuses information explicitly present in sections, so it never
        fabricates companies, projects or skills.
        """
        sections = draft.sections or {}
        basic = sections.get("basic") or {}
        lines: list[str] = []

        name = str(basic.get("name") or "").strip() or draft.title or "我的简历"
        lines.append(f"# {name}")
        lines.append("")

        meta = []
        if basic.get("target_role"):
            meta.append(f"目标岗位：{basic['target_role']}")
        if basic.get("years"):
            meta.append(f"工作年限：{basic['years']}")
        if basic.get("city"):
            meta.append(f"所在城市：{basic['city']}")
        if meta:
            lines.append(" ｜ ".join(meta))
            lines.append("")

        education = [item for item in (sections.get("education") or []) if isinstance(item, dict)]
        if education:
            lines.append("## 教育背景")
            for item in education:
                head = "，".join(
                    part
                    for part in (item.get("school"), item.get("major"), item.get("degree"))
                    if part
                )
                period = item.get("period")
                lines.append(f"- {head}" + (f"（{period}）" if period else ""))
            lines.append("")

        work = [item for item in (sections.get("work") or []) if isinstance(item, dict)]
        if work:
            lines.append("## 工作经历")
            for item in work:
                head = " · ".join(part for part in (item.get("company"), item.get("role")) if part)
                period = item.get("period")
                lines.append(f"### {head}" + (f"（{period}）" if period else ""))
                for highlight in item.get("highlights") or []:
                    lines.append(f"- {highlight}")
            lines.append("")

        projects = [item for item in (sections.get("projects") or []) if isinstance(item, dict)]
        if projects:
            lines.append("## 项目经历")
            for item in projects:
                lines.append(f"### {item.get('name') or '项目'}")
                for label, field in (
                    ("背景", "background"),
                    ("职责", "role"),
                    ("技术栈", "stack"),
                    ("难点", "challenge"),
                    ("成果", "result"),
                ):
                    if item.get(field):
                        lines.append(f"- {label}：{item[field]}")
            lines.append("")

        skills = [
            str(skill).strip() for skill in (sections.get("skills") or []) if str(skill).strip()
        ]
        if skills:
            lines.append("## 技能栈")
            lines.append("- " + "、".join(skills))
            lines.append("")

        intent = sections.get("intent") or {}
        intent_parts = []
        if intent.get("position"):
            intent_parts.append(f"目标岗位：{intent['position']}")
        if intent.get("city"):
            intent_parts.append(f"期望城市：{intent['city']}")
        if intent.get("notes"):
            intent_parts.append(f"其他：{intent['notes']}")
        if intent_parts:
            lines.append("## 求职意向")
            lines.extend(f"- {part}" for part in intent_parts)
            lines.append("")

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------ 辅助

    def _to_finalize_response(
        self,
        draft: ResumeDraft,
        profile: ResumeProfileResponse,
    ) -> FinalizeResponse:
        return FinalizeResponse(
            draft_id=draft.session_id,
            profile_id=profile.id,
            title=profile.title,
            content=profile.content,
            summary=profile.summary or "",
        )

    @staticmethod
    def _build_message(role: str, content: str, stage: str) -> dict:
        return {
            "role": role,
            "content": content,
            "stage": stage,
            "create_time": datetime.now(UTC).isoformat(),
        }
