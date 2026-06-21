from datetime import UTC, datetime
import re
from uuid import uuid4

from app.application.interview.interview_dto import (
    LatestActiveInterviewResponse,
    InterviewHistoryItemResponse,
    InterviewMessageResponse,
    InterviewReviewResponse,
    InterviewReviewRoundResponse,
    InterviewSessionResponse,
    FinishInterviewResponse,
    SuccessResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    StartInterviewRequest,
    StartInterviewResponse,
    UpdateInterviewValidityRequest,
)
from app.domain.interview.entities import InterviewAnswerReview, InterviewSession
from app.domain.interview.entities import InterviewSessionStatus
from app.domain.interview.repositories import InterviewRepository
from app.domain.interview.services import InterviewQuestionPolicy
from app.infrastructure.agent.interview_agent import InterviewerAgent

RESUME_CONTEXT_PREFIX = "RESUME_CONTEXT"
LEGACY_RESUME_PREFIXES = (
    "候选人简历：",
    "候选人简历:",
    "鍊欓€変汉绠€鍘嗭細",
)


class InterviewService:
    """Coordinates interview use cases."""

    def __init__(
        self,
        repository: InterviewRepository,
        interviewer_agent: InterviewerAgent | None = None,
    ) -> None:
        self._repository = repository
        self._question_policy = InterviewQuestionPolicy()
        self._interviewer_agent = interviewer_agent

    def start_interview(self, user_id: int, request: StartInterviewRequest) -> StartInterviewResponse:
        """Create a new interview session and generate the first question."""
        job_role = request.job_role.strip()
        first_question = self._question_policy.build_first_question(job_role)

        session = InterviewSession.create(
            session_id=str(uuid4()),
            job_role=job_role,
            first_question=first_question,
            user_id=user_id,
            duration_minutes=request.duration_minutes,
            direction=request.direction,
            interviewer_mode=request.interviewer_mode,
        )
        self._repository.save(session)
        self._repository.append_message(
            user_id=user_id,
            session_id=session.session_id,
            role="AI_INTERVIEWER",
            content=first_question,
            round_no=1,
        )
        resume_text = request.resume_text.strip() if request.resume_text else ""
        if resume_text:
            self._repository.append_message(
                user_id=user_id,
                session_id=session.session_id,
                role="SYSTEM",
                content=f"{RESUME_CONTEXT_PREFIX}\n{resume_text}",
                round_no=0,
            )
        if False and request.resume_text:
            self._repository.append_message(
                user_id=user_id,
                session_id=session.session_id,
                role="SYSTEM",
                content=f"候选人简历：\n{request.resume_text.strip()}",
                round_no=0,
            )

        return StartInterviewResponse(
            session_id=session.session_id,
            first_question=session.first_question,
        )

    def submit_answer(
        self,
        user_id: int,
        session_id: str,
        request: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        """Record candidate answer and generate the next question."""
        session = self._repository.get_by_id(user_id, session_id)
        if session is None:
            raise ValueError("Interview session not found")
        if session.status != InterviewSessionStatus.IN_PROGRESS:
            raise ValueError("Interview session is not in progress")

        answer = request.answer.strip()
        if not answer:
            raise ValueError("Answer cannot be empty")
        round_no = session.current_round
        self._repository.append_message(
            user_id=user_id,
            session_id=session_id,
            role="USER_CANDIDATE",
            content=answer,
            round_no=round_no,
        )

        elapsed_minutes = self._elapsed_minutes(session.created_at)
        if elapsed_minutes >= session.duration_minutes:
            self._repository.save_answer_review(
                user_id=user_id,
                session_id=session_id,
                round_no=round_no,
                review=self._build_fallback_answer_review(answer),
            )
            self._repository.finish(user_id, session_id)
            return SubmitAnswerResponse(
                session_id=session_id,
                round_no=round_no,
                next_question=None,
                is_finished=True,
                decision="end",
                reason="Reached maximum interview duration",
            )

        next_round = round_no + 1
        history = self._repository.list_messages(user_id, session_id)
        interviewer_agent = self._interviewer_agent or InterviewerAgent()
        decision = interviewer_agent.generate_next_question(
            job_role=session.job_role,
            round_no=next_round,
            duration_minutes=session.duration_minutes,
            elapsed_minutes=elapsed_minutes,
            direction=session.direction,
            interviewer_mode=session.interviewer_mode,
            resume_text=self._extract_resume_text(history),
            history=history,
        )
        self._repository.save_answer_review(
            user_id=user_id,
            session_id=session_id,
            round_no=round_no,
            review=self._to_domain_answer_review(decision.answer_review, answer),
        )
        if decision.decision == "end":
            self._repository.finish(user_id, session_id)
            return SubmitAnswerResponse(
                session_id=session_id,
                round_no=round_no,
                next_question=None,
                is_finished=True,
                decision=decision.decision,
                reason=decision.reason,
            )

        next_question = decision.question
        if not next_question:
            raise RuntimeError("LLM did not return next question")
        if self._is_repeated_question(next_question, history):
            regenerated_question = interviewer_agent.regenerate_question_avoiding_history(
                job_role=session.job_role,
                direction=session.direction,
                interviewer_mode=session.interviewer_mode,
                duplicated_question=next_question,
                history=history,
            )
            if regenerated_question and not self._is_repeated_question(regenerated_question, history):
                next_question = regenerated_question
            else:
                next_question = self._build_non_repeated_question(session.direction, history)

        self._repository.append_message(
            user_id=user_id,
            session_id=session_id,
            role="AI_INTERVIEWER",
            content=next_question,
            round_no=next_round,
        )
        self._repository.advance_round(user_id, session_id, next_round)

        return SubmitAnswerResponse(
            session_id=session_id,
            round_no=next_round,
            next_question=next_question,
            is_finished=False,
            decision=decision.decision,
            reason=decision.reason,
        )

    def finish_interview(self, user_id: int, session_id: str) -> FinishInterviewResponse:
        session = self._repository.get_by_id(user_id, session_id)
        if session is None:
            raise ValueError("Interview session not found")

        if session.status == InterviewSessionStatus.IN_PROGRESS:
            self._repository.finish(user_id, session_id)

        return FinishInterviewResponse(session_id=session_id, is_finished=True)

    def get_session(self, user_id: int, session_id: str) -> InterviewSessionResponse | None:
        session = self._repository.get_by_id(user_id, session_id)
        if session is None:
            return None

        return InterviewSessionResponse(
            session_id=session.session_id,
            job_role=session.job_role,
            direction=session.direction,
            interviewer_mode=session.interviewer_mode,
            status=session.status.value,
            current_round=session.current_round,
            duration_minutes=session.duration_minutes,
            started_at=session.created_at.isoformat(),
        )

    def list_messages(self, user_id: int, session_id: str) -> list[InterviewMessageResponse]:
        messages = self._repository.list_messages_detailed(user_id, session_id)
        return [
            InterviewMessageResponse(
                role=str(message["role"]),
                content=str(message["content"]),
                round_no=int(message["round_no"]),
                created_at=str(message["created_at"]),
            )
            for message in messages
        ]

    def list_history(self, user_id: int, include_empty: bool = False) -> list[InterviewHistoryItemResponse]:
        rows = self._repository.list_history(user_id=user_id, include_empty=include_empty)
        return [
            InterviewHistoryItemResponse(
                session_id=str(row["session_id"]),
                job_role=str(row["job_role"]),
                direction=str(row["direction"]) if row.get("direction") else None,
                interviewer_mode=str(row["interviewer_mode"]) if row.get("interviewer_mode") else None,
                status=str(row["status"]),
                current_round=int(row["current_round"]),
                message_count=int(row["message_count"]),
                answered_count=int(row["answered_count"]),
                duration_minutes=int(row["duration_minutes"]),
                started_at=str(row["started_at"]),
                ended_at=str(row["ended_at"]) if row["ended_at"] else None,
                has_report=bool(row["has_report"]),
                is_valid=bool(row["is_valid"]),
                overall_score=float(row["overall_score"]) if row["overall_score"] is not None else None,
            )
            for row in rows
        ]

    def get_latest_active(self, user_id: int) -> LatestActiveInterviewResponse:
        active = self._repository.get_latest_active(user_id)
        if active is None:
            return LatestActiveInterviewResponse(has_active=False)
        return LatestActiveInterviewResponse(
            has_active=True,
            session_id=str(active["session_id"]),
            job_role=str(active["job_role"]),
            direction=str(active["direction"]) if active.get("direction") else None,
            interviewer_mode=str(active["interviewer_mode"]) if active.get("interviewer_mode") else None,
            started_at=str(active["started_at"]),
            answered_count=int(active["answered_count"] or 0),
        )

    def delete_interview(self, user_id: int, session_id: str) -> SuccessResponse:
        self._repository.soft_delete(user_id, session_id)
        return SuccessResponse(success=True)

    def update_validity(
        self,
        user_id: int,
        session_id: str,
        request: UpdateInterviewValidityRequest,
    ) -> SuccessResponse:
        self._repository.update_validity(user_id, session_id, request.is_valid)
        return SuccessResponse(success=True)

    def get_review(self, user_id: int, session_id: str) -> InterviewReviewResponse | None:
        session = self._repository.get_by_id(user_id, session_id)
        if session is None:
            return None

        messages = self._repository.list_messages_detailed(user_id, session_id)
        history_rows = self._repository.list_history(user_id=user_id, include_empty=True)
        current_history = next(
            (item for item in history_rows if item.get("session_id") == session_id),
            None,
        )
        questions = {
            int(item["round_no"]): str(item["content"])
            for item in messages
            if item.get("role") == "AI_INTERVIEWER"
        }
        answers = [item for item in messages if item.get("role") == "USER_CANDIDATE"]
        answer_reviews = self._repository.list_answer_reviews(user_id, session_id)
        rounds: list[InterviewReviewRoundResponse] = []
        for answer in answers:
            answer_round_no = int(answer["round_no"])
            question = questions.get(answer_round_no, "")
            review = self._review_for_round(
                answer_reviews=answer_reviews,
                round_no=answer_round_no,
                answer=str(answer["content"]),
                question=question,
            )
            rounds.append(
                InterviewReviewRoundResponse(
                    round_no=answer_round_no,
                    question=question,
                    answer=str(answer["content"]),
                    evaluation=review.evaluation,
                    reference_points=review.reference_points,
                    sample_answer=review.sample_answer,
                    level=review.level,
                )
            )
        return InterviewReviewResponse(
            session_id=session.session_id,
            job_role=session.job_role,
            status=session.status.value,
            started_at=session.created_at.isoformat(),
            ended_at=str(current_history.get("ended_at")) if current_history and current_history.get("ended_at") else None,
            answered_count=len(rounds),
            has_report=bool(current_history.get("has_report")) if current_history else False,
            rounds=rounds,
        )

    def _elapsed_minutes(self, started_at: datetime) -> int:
        now = datetime.now(UTC)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        return max(0, int((now - started_at).total_seconds() // 60))

    def _extract_resume_text(self, history: list[dict[str, str]]) -> str | None:
        for item in history:
            if item.get("role") != "SYSTEM":
                continue

            content = item.get("content", "").strip()
            if not content:
                continue

            if content.startswith(RESUME_CONTEXT_PREFIX):
                return content.removeprefix(RESUME_CONTEXT_PREFIX).strip()

            for prefix in LEGACY_RESUME_PREFIXES:
                if content.startswith(prefix):
                    return content.removeprefix(prefix).strip()

            if int(item.get("round_no", -1) or -1) == 0:
                return content
        return None

        for item in history:
            if item.get("role") == "SYSTEM" and item.get("content", "").startswith("候选人简历："):
                return item["content"].removeprefix("候选人简历：").strip()
        return None

    def _estimate_answer_level(self, answer: str) -> str:
        length = len(answer.strip())
        if length >= 180:
            return "good"
        if length >= 60:
            return "normal"
        return "weak"

    def _is_repeated_question(self, question: str, history: list[dict[str, str]]) -> bool:
        normalized_question = self._normalize_question_text(question)
        if not normalized_question:
            return False

        for item in history:
            if item.get("role") != "AI_INTERVIEWER":
                continue
            previous_question = self._normalize_question_text(item.get("content", ""))
            if not previous_question:
                continue
            if normalized_question == previous_question:
                return True
            similarity = self._text_similarity(normalized_question, previous_question)
            if similarity >= 0.72:
                return True
        return False

    def _build_non_repeated_question(
        self,
        direction: str | None,
        history: list[dict[str, str]],
    ) -> str:
        candidates_by_direction = {
            "JAVA_BASIC": [
                "你能讲一下 HashMap 在 JDK 1.8 中 put 一个元素的大致过程吗？",
                "你能说一下 equals 和 hashCode 为什么通常需要一起重写吗？",
                "你能讲一下 ArrayList 扩容的大致机制吗？",
            ],
            "JVM": [
                "你能讲一下 JVM 运行时内存区域里堆和方法区分别存放什么吗？",
                "如果线上出现频繁 Full GC，你会先看哪些指标？",
            ],
            "MYSQL": [
                "你能结合一个查询场景讲一下索引为什么会失效吗？",
                "你能说明一下事务隔离级别解决了哪些典型问题吗？",
            ],
            "REDIS": [
                "你能讲一下缓存击穿通常怎么解决吗？",
                "你能说明一下 Redis 分布式锁需要注意哪些失效场景吗？",
            ],
            "CONCURRENCY": [
                "你能讲一下线程池核心参数分别控制什么吗？",
                "你能说明一下 volatile 适合解决什么问题，不适合解决什么问题吗？",
            ],
            "SPRING": [
                "你能讲一下 Spring Bean 的生命周期里几个关键阶段吗？",
                "你能说明一下 Spring 事务失效的常见原因吗？",
            ],
            "SYSTEM_DESIGN": [
                "如果让你设计一个高并发下单接口，你会先考虑哪些关键点？",
                "你能讲一下接口幂等通常有哪些实现方式吗？",
            ],
            "TROUBLESHOOTING": [
                "如果线上接口突然变慢，你会按照什么顺序排查？",
                "如果应用 CPU 突然飙高，你会怎么定位问题？",
            ],
        }
        candidates = candidates_by_direction.get(direction or "", []) + [
            "请你讲一个项目中真实遇到的技术问题，以及你当时的排查和解决过程？",
            "你能选择一个你熟悉的技术点，讲清楚它的使用场景和一个容易踩坑的地方吗？",
        ]
        for candidate in candidates:
            if not self._is_repeated_question(candidate, history):
                return candidate
        return "请你换一个项目案例，讲讲其中一个你负责解决的技术问题？"

    def _normalize_question_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", "", text.lower())
        normalized = re.sub(r"[，。！？、；：,.!?;:\"'（）()【】\[\]《》<>]", "", normalized)
        return normalized

    def _text_similarity(self, left: str, right: str) -> float:
        left_tokens = set(self._tokenize_question(left))
        right_tokens = set(self._tokenize_question(right))
        if not left_tokens or not right_tokens:
            return 0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def _tokenize_question(self, text: str) -> list[str]:
        if not text:
            return []
        return [text[index : index + 2] for index in range(max(len(text) - 1, 1))]

    def _to_domain_answer_review(
        self,
        review: object | None,
        answer: str,
    ) -> InterviewAnswerReview:
        if review is None:
            return self._build_fallback_answer_review(answer)

        fallback = self._build_fallback_answer_review(answer)
        reference_points = list(getattr(review, "reference_points", []) or [])
        return InterviewAnswerReview(
            evaluation=str(getattr(review, "evaluation", "") or "").strip()
            or fallback.evaluation,
            reference_points=reference_points or fallback.reference_points,
            sample_answer=str(getattr(review, "sample_answer", "") or "").strip()
            or fallback.sample_answer,
            level=str(getattr(review, "level", "") or fallback.level),
            raw_review_json=dict(getattr(review, "raw_review_json", {}) or {}),
        )

    def _build_fallback_answer_review(self, answer: str) -> InterviewAnswerReview:
        return InterviewAnswerReview(
            evaluation=self._build_answer_evaluation(answer),
            reference_points=["说明问题背景", "明确个人职责", "描述具体方案", "补充结果数据", "总结反思和改进"],
            sample_answer=self._build_sample_answer(""),
            level=self._estimate_answer_level(answer),
            raw_review_json={},
        )

    def _review_for_round(
        self,
        answer_reviews: dict[int, InterviewAnswerReview],
        round_no: int,
        answer: str,
        question: str = "",
    ) -> InterviewAnswerReview:
        saved_review = answer_reviews.get(round_no)
        if saved_review is not None:
            return saved_review

        return InterviewAnswerReview(
            evaluation=self._build_answer_evaluation(answer),
            reference_points=self._build_reference_points(question),
            sample_answer=self._build_sample_answer(question),
            level=self._estimate_answer_level(answer),
            raw_review_json={},
        )

    def _build_answer_evaluation(self, answer: str) -> str:
        level = self._estimate_answer_level(answer)
        if level == "good":
            return "回答内容较完整，能够展开说明背景、方案或细节。建议继续补充关键指标、异常场景和方案权衡，让表达更接近真实面试中的优秀回答。"
        if level == "normal":
            return "回答具备一定信息量，但结构和技术细节还可以继续加强。建议按照背景、方案、结果、反思的顺序展开，并补充具体数据或项目细节。"
        return "回答偏简略，暂时不足以支撑面试官判断技术深度。建议补充项目背景、个人职责、具体实现、遇到的问题和最终效果。"

    def _build_reference_points(self, question: str) -> list[str]:
        lower_question = question.lower()
        if "redis" in lower_question or "缓存" in question:
            return ["说明业务场景", "解释缓存读写流程", "补充一致性与失败补偿", "说明并发或延迟风险", "给出监控或降级方案"]
        if "mysql" in lower_question or "数据库" in question or "索引" in question:
            return ["说明表结构或查询场景", "解释索引/事务/锁相关机制", "结合执行计划或数据量分析", "给出优化方案", "说明风险和验证方式"]
        if "jvm" in lower_question or "gc" in lower_question:
            return ["说明问题现象", "解释 JVM 相关机制", "描述排查工具", "给出调优或修复方案", "说明验证结果"]
        return ["说明背景", "明确个人职责", "描述具体方案", "补充结果数据", "总结反思和改进"]

    def _build_sample_answer(self, question: str) -> str:
        lower_question = question.lower()
        if "redis" in lower_question or "缓存" in question:
            return "可以先说明业务中为什么需要缓存，再描述采用的缓存模式、更新顺序和一致性保障；最后补充删除失败重试、延迟双删、消息补偿或监控告警等生产兜底方案。"
        if "mysql" in lower_question or "数据库" in question or "索引" in question:
            return "可以结合具体查询场景说明数据量、索引设计和执行计划，再解释为什么这样优化，以及优化前后的耗时、QPS 或慢查询变化。"
        return "可以按照背景、任务、方案、结果、反思来回答：先讲业务场景和个人职责，再讲具体实现与遇到的问题，最后用数据说明效果。"
