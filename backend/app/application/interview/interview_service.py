from datetime import UTC, datetime
from uuid import uuid4

from app.application.interview.interview_dto import (
    InterviewHistoryItemResponse,
    InterviewMessageResponse,
    InterviewReviewResponse,
    InterviewReviewRoundResponse,
    InterviewSessionResponse,
    FinishInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    StartInterviewRequest,
    StartInterviewResponse,
)
from app.domain.interview.entities import InterviewAnswerReview, InterviewSession
from app.domain.interview.entities import InterviewSessionStatus
from app.domain.interview.repositories import InterviewRepository
from app.domain.interview.services import InterviewQuestionPolicy
from app.infrastructure.agent.interview_agent import InterviewerAgent


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

    def start_interview(self, request: StartInterviewRequest) -> StartInterviewResponse:
        """Create a new interview session and generate the first question."""
        job_role = request.job_role.strip()
        first_question = self._question_policy.build_first_question(job_role)

        session = InterviewSession.create(
            session_id=str(uuid4()),
            job_role=job_role,
            first_question=first_question,
            duration_minutes=request.duration_minutes,
        )
        self._repository.save(session)
        self._repository.append_message(
            session_id=session.session_id,
            role="AI_INTERVIEWER",
            content=first_question,
            round_no=1,
        )
        if request.resume_text:
            self._repository.append_message(
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
        session_id: str,
        request: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        """Record candidate answer and generate the next question."""
        session = self._repository.get_by_id(session_id)
        if session is None:
            raise ValueError("Interview session not found")
        if session.status != InterviewSessionStatus.IN_PROGRESS:
            raise ValueError("Interview session is not in progress")

        answer = request.answer.strip()
        if not answer:
            raise ValueError("Answer cannot be empty")
        round_no = session.current_round
        self._repository.append_message(
            session_id=session_id,
            role="USER_CANDIDATE",
            content=answer,
            round_no=round_no,
        )

        elapsed_minutes = self._elapsed_minutes(session.created_at)
        if elapsed_minutes >= session.duration_minutes:
            self._repository.save_answer_review(
                session_id=session_id,
                round_no=round_no,
                review=self._build_fallback_answer_review(answer),
            )
            self._repository.finish(session_id)
            return SubmitAnswerResponse(
                session_id=session_id,
                round_no=round_no,
                next_question=None,
                is_finished=True,
                decision="end",
                reason="Reached maximum interview duration",
            )

        next_round = round_no + 1
        history = self._repository.list_messages(session_id)
        interviewer_agent = self._interviewer_agent or InterviewerAgent()
        decision = interviewer_agent.generate_next_question(
            job_role=session.job_role,
            round_no=next_round,
            duration_minutes=session.duration_minutes,
            elapsed_minutes=elapsed_minutes,
            resume_text=self._extract_resume_text(history),
            history=history,
        )
        self._repository.save_answer_review(
            session_id=session_id,
            round_no=round_no,
            review=self._to_domain_answer_review(decision.answer_review, answer),
        )
        if decision.decision == "end":
            self._repository.finish(session_id)
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

        self._repository.append_message(
            session_id=session_id,
            role="AI_INTERVIEWER",
            content=next_question,
            round_no=next_round,
        )
        self._repository.advance_round(session_id, next_round)

        return SubmitAnswerResponse(
            session_id=session_id,
            round_no=next_round,
            next_question=next_question,
            is_finished=False,
            decision=decision.decision,
            reason=decision.reason,
        )

    def finish_interview(self, session_id: str) -> FinishInterviewResponse:
        session = self._repository.get_by_id(session_id)
        if session is None:
            raise ValueError("Interview session not found")

        if session.status == InterviewSessionStatus.IN_PROGRESS:
            self._repository.finish(session_id)

        return FinishInterviewResponse(session_id=session_id, is_finished=True)

    def get_session(self, session_id: str) -> InterviewSessionResponse | None:
        session = self._repository.get_by_id(session_id)
        if session is None:
            return None

        return InterviewSessionResponse(
            session_id=session.session_id,
            job_role=session.job_role,
            status=session.status.value,
            current_round=session.current_round,
            duration_minutes=session.duration_minutes,
            started_at=session.created_at.isoformat(),
        )

    def list_messages(self, session_id: str) -> list[InterviewMessageResponse]:
        messages = self._repository.list_messages_detailed(session_id)
        return [
            InterviewMessageResponse(
                role=str(message["role"]),
                content=str(message["content"]),
                round_no=int(message["round_no"]),
                created_at=str(message["created_at"]),
            )
            for message in messages
        ]

    def list_history(self, include_empty: bool = False) -> list[InterviewHistoryItemResponse]:
        rows = self._repository.list_history(include_empty=include_empty)
        return [
            InterviewHistoryItemResponse(
                session_id=str(row["session_id"]),
                job_role=str(row["job_role"]),
                status=str(row["status"]),
                current_round=int(row["current_round"]),
                message_count=int(row["message_count"]),
                answered_count=int(row["answered_count"]),
                duration_minutes=int(row["duration_minutes"]),
                started_at=str(row["started_at"]),
                ended_at=str(row["ended_at"]) if row["ended_at"] else None,
                has_report=bool(row["has_report"]),
                overall_score=float(row["overall_score"]) if row["overall_score"] is not None else None,
            )
            for row in rows
        ]

    def get_review(self, session_id: str) -> InterviewReviewResponse | None:
        session = self._repository.get_by_id(session_id)
        if session is None:
            return None

        messages = self._repository.list_messages_detailed(session_id)
        history_rows = self._repository.list_history(include_empty=True)
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
        answer_reviews = self._repository.list_answer_reviews(session_id)
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
