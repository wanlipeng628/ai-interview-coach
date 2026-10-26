#!/usr/bin/env python3
"""AIC-80 关思考 / 开思考出题质量对比样本跑批（一次性脚本）。

只做三件事：按固定输入包调用生产出题链路、按输入包第 7 节导出 JSONL、生成 README。
不碰数据库、不碰 HTTP 服务、不改任何业务代码。

为什么不需要起 backend 容器：
  本脚本直接实例化生产用的 ``InterviewerAgent`` / ``OpenAICompatibleClient``，
  thinking 开关与生产完全同源（``settings.llm_question_thinking`` 每次调用时读取，
  序列化为 ``extra_body={"thinking": {"type": ...}}``）。去重 / 重生成 / 静态兜底
  直接调用 ``InterviewService`` 里的同名方法，不重写逻辑。因此没有「测试实例」需要重建，
  也就不存在动到线上容器的可能。

用法见 ./README.md 或 ``--help``。校验脚本本身用 ``--mock``，不要用 mock 结果做质量结论。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parents[1]
REPO_DIR = SCRIPT_DIR.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.application.interview.interview_service import InterviewService  # noqa: E402
from app.infrastructure.agent.interview_agent import InterviewerAgent  # noqa: E402
from app.infrastructure.llm.openai_compatible_client import OpenAICompatibleClient  # noqa: E402
from app.shared.config import settings  # noqa: E402

# 输入包 7.1 的字段顺序，导出时按此顺序写，方便人工核对。
SAMPLE_FIELDS = [
    "sample_id",
    "session_id",
    "scene_id",
    "group",
    "batch_id",
    "job_role",
    "resume_id",
    "direction",
    "mode",
    "duration_minutes",
    "round_no",
    "is_first_of_session",
    "scored",
    "history",
    "decision",
    "reason",
    "raw_output",
    "question",
    "sanitize_truncated",
    "regen_triggered",
    "regen_success",
    "fallback_hit",
    "parse_failed",
    "retried",
    "first_token_ms",
    "total_ms",
    "model",
    "prompt_version",
    "created_at",
    # 额外字段：标准 §6.1 要求样本带简历全文，输入包 7.1 的示例里没有，单独补上。
    "resume_text",
]

EMPTY_QUESTION_DEFAULT = "请介绍一个你最近项目里最有挑战的问题，以及你是怎么解决的？"

# README 里写死的生产模型。与当前 env 不一致时脚本会拦下，避免悄悄产出不可外推的样本。
PRODUCTION_MODEL = "deepseek-flash"

DIRECTION_LABELS = {
    "FULL_MOCK": "完整模拟",
    "PROJECT_DEEP_DIVE": "项目深挖",
    "JAVA_BASIC": "Java 基础",
    "CONCURRENCY": "并发编程",
    "JVM": "JVM",
    "MYSQL": "MySQL",
    "REDIS": "Redis",
    "SPRING": "Spring",
    "SYSTEM_DESIGN": "系统设计",
    "TROUBLESHOOTING": "线上问题排查",
}

MODE_LABELS = {
    "GENTLE": "温和",
    "NORMAL": "正常",
    "STRICT": "严格",
    "BIG_TECH_FIRST_ROUND": "大厂一面",
}


# --------------------------------------------------------------------------- #
# 基础设施
# --------------------------------------------------------------------------- #
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(moment: datetime | None = None) -> str:
    moment = moment or utc_now()
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def local_tz_label() -> str:
    offset = datetime.now().astimezone().utcoffset() or timezone.utc.utcoffset(None)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def git_short_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - 取不到就标 unknown，不阻断跑批
        return "unknown"


def prompt_version() -> str:
    sha = hashlib.sha256(InterviewerAgent.SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]
    return f"git:{git_short_sha()};interviewer_prompt:sha256-{sha}"


def simulator_prompt_version(text: str) -> str:
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"simulator_prompt:sha256-{sha}"


def default_out_dir() -> Path:
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    return SCRIPT_DIR / "out" / f"aic80-{stamp}"


# --------------------------------------------------------------------------- #
# LLM 调用层
# --------------------------------------------------------------------------- #
@dataclass
class CallRecord:
    thinking_mode: str | None
    first_token_ms: float
    total_ms: float
    raw_output: str


class RecordingClient:
    """包住生产 LLM client，记录原始输出与首 token / 总耗时。"""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.last: CallRecord | None = None

    def reset(self) -> None:
        self.last = None

    def chat(self, messages: list[dict[str, str]], thinking_mode: str | None = None) -> str:
        start = time.perf_counter()
        text = self._inner.chat(messages, thinking_mode=thinking_mode)
        total_ms = (time.perf_counter() - start) * 1000
        self.last = CallRecord(thinking_mode, total_ms, total_ms, text)
        return text

    def chat_stream(
        self, messages: list[dict[str, str]], thinking_mode: str | None = None
    ) -> Iterator[str]:
        start = time.perf_counter()
        first_token_ms: float | None = None
        parts: list[str] = []
        for chunk in self._inner.chat_stream(messages, thinking_mode=thinking_mode):
            if first_token_ms is None:
                first_token_ms = (time.perf_counter() - start) * 1000
            parts.append(chunk)
            yield chunk
        total_ms = (time.perf_counter() - start) * 1000
        self.last = CallRecord(
            thinking_mode,
            total_ms if first_token_ms is None else first_token_ms,
            total_ms,
            "".join(parts),
        )


class MockInterviewerClient:
    """只用于校验脚本本身。产出确定性的假 JSON，不是任何真实样本。"""

    # 互不相似的题面池，保证去重逻辑不会被自己的 mock 误触发
    _QUESTIONS = [
        "请讲一下 JVM 分代回收里对象什么时候会进入老年代？",
        "你在项目里是怎么做接口幂等控制的？",
        "MySQL 索引失效你遇到过哪些具体场景？",
        "线程池队列满了之后会发生什么？",
        "缓存和数据库不一致时你会怎么兜底？",
        "说说你对 Spring Bean 生命周期的理解？",
        "服务拆分后跨服务事务你是怎么处理的？",
        "如果线上接口 P99 突然涨到 3 秒，你的排查顺序是什么？",
        "Redis 分布式锁续期失败会导致什么问题？",
        "你怎么评估一个 RAG 检索链路的召回质量？",
        "Agent 工具调用失败后如何做重规划？",
        "简历里的秒杀链路，你怎么压测和定位瓶颈的？",
    ]

    def __init__(self) -> None:
        self.calls = 0
        self._index = 0

    def _payload(self) -> str:
        from openai import APITimeoutError
        import httpx

        self.calls += 1
        index = self.calls
        if index % 23 == 0:
            # 制造一次可恢复错误，验证重试与 retried 标记
            raise APITimeoutError(request=httpx.Request("POST", "https://mock.invalid/chat"))
        if index % 17 == 0:
            # 非 JSON，验证 parse_failed / 原文兜底
            return f"好的，我们继续聊下一个点（mock 非 JSON 输出 #{index}）"
        question = self._QUESTIONS[self._index % len(self._QUESTIONS)]
        self._index += 1
        if index % 11 == 0:
            # 故意重复上一题，验证去重 → 重生成分支
            question = self._QUESTIONS[(self._index - 2) % len(self._QUESTIONS)]
        decision = "end" if index % 53 == 0 else "continue"
        return json.dumps(
            {"decision": decision, "question": None if decision == "end" else question,
             "reason": f"mock reason #{index}"},
            ensure_ascii=False,
        )

    def chat(self, messages: list[dict[str, str]], thinking_mode: str | None = None) -> str:
        return self._payload()

    def chat_stream(
        self, messages: list[dict[str, str]], thinking_mode: str | None = None
    ) -> Iterator[str]:
        text = self._payload()
        step = max(1, len(text) // 3)
        for start in range(0, len(text), step):
            time.sleep(0.001)
            yield text[start : start + step]


class CandidateSimulator:
    """输入包 5.2 的候选人模拟器。两组共用同一实例与同一参数。"""

    def __init__(
        self,
        template: str,
        call: Callable[[list[dict[str, str]]], str],
    ) -> None:
        self._template = template
        self._call = call

    def answer(
        self,
        *,
        resume_text: str,
        job_role: str,
        direction: str,
        question: str,
        history: list[dict[str, str]],
    ) -> str:
        system = self._template.format(
            resume_text=resume_text, job_role=job_role, direction=direction
        )
        lines: list[str] = []
        for item in history:
            if item.get("role") == "AI_INTERVIEWER":
                lines.append(f"[面试官] {item.get('content', '')}")
            elif item.get("role") == "USER_CANDIDATE":
                lines.append(f"[候选人] {item.get('content', '')}")
        transcript = "\n".join(lines) if lines else "（暂无）"
        user = (
            "面试进行到这里的完整问答记录：\n"
            f"{transcript}\n\n"
            f"面试官当前的问题：\n{question}\n\n"
            "请以候选人身份，直接给出你这一轮的回答正文。"
        )
        return self._call(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        ).strip()


class MockSimulator:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        question = messages[-1]["content"].rsplit("\n", 3)[-3] if messages else ""
        filler = "这块我实际做过，主要是在项目里按部就班落地，遇到问题再针对性调整。" * 2
        return f"（mock 候选人回答 #{self.calls}）{filler} 关于「{question[:24]}」我大概是这样理解的。"


# --------------------------------------------------------------------------- #
# 单轮生成
# --------------------------------------------------------------------------- #
@dataclass
class Turn:
    decision: str
    question: str | None
    reason: str | None
    raw_output: str
    first_token_ms: int
    total_ms: int
    retried: bool
    parse_failed: bool
    sanitize_truncated: bool | None
    regen_triggered: bool = False
    regen_success: bool | None = None
    fallback_hit: bool = False


def detect_truncation(agent: InterviewerAgent, raw_question: str | None, sanitized: str) -> bool | None:
    """复现 _sanitize_question 的清洗前两步，判断 _normalize_single_question 是否切掉了尾部。"""
    if raw_question is None or not sanitized:
        return None
    pre = re.sub(r"\s+", " ", raw_question).strip()
    for pattern in agent.REVIEW_LEAK_PATTERNS:
        pre = re.sub(pattern, "", pre)
    pre = agent._remove_review_keywords_prefix(pre).strip()  # noqa: SLF001 - 刻意复用生产逻辑
    if not pre:
        return None
    return pre != sanitized


def raw_question_field(agent: InterviewerAgent, raw_output: str) -> str | None:
    try:
        payload = json.loads(agent._extract_json(raw_output))  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return None
    if isinstance(payload, dict) and payload.get("question") is not None:
        return str(payload["question"])
    return None


def generate_turn(
    *,
    agent: InterviewerAgent,
    service: InterviewService,
    client: RecordingClient,
    scene: dict[str, Any],
    history: list[dict[str, str]],
    round_no: int,
    elapsed_minutes: int,
    duration_minutes: int,
    retry_backoff: tuple[float, ...] = (3.0, 10.0),
) -> Turn:
    from openai import APIConnectionError, APITimeoutError, RateLimitError

    retryable = (RateLimitError, APITimeoutError, APIConnectionError)
    attempts = 0
    decision = None
    last_error: Exception | None = None

    for attempt in range(len(retry_backoff) + 1):
        attempts = attempt + 1
        client.reset()
        emitted = False
        try:
            stream = agent.generate_next_question_stream(
                job_role=scene["job_role"],
                round_no=round_no,
                duration_minutes=duration_minutes,
                elapsed_minutes=elapsed_minutes,
                direction=scene["direction"],
                interviewer_mode=scene["mode"],
                resume_text=scene["resume_text"],
                history=history,
            )
            for event in stream:
                if event["type"] == "delta":
                    emitted = True
                elif event["type"] == "done":
                    decision = event["decision"]
                    break
            if decision is None:
                raise RuntimeError("LLM stream ended without done event")
            break
        except retryable as exc:
            if emitted or attempt >= len(retry_backoff):
                raise
            last_error = exc
            time.sleep(retry_backoff[attempt])

    if decision is None:
        raise last_error or RuntimeError("LLM generation failed")

    record = client.last or CallRecord(settings.llm_question_thinking, 0.0, 0.0, "")
    raw_output = record.raw_output
    question = decision.question

    try:
        json.loads(agent._extract_json(raw_output))  # noqa: SLF001
        parse_failed = False
    except Exception:  # noqa: BLE001
        parse_failed = True

    truncated = detect_truncation(agent, raw_question_field(agent, raw_output), question or "")

    turn = Turn(
        decision=decision.decision,
        question=question,
        reason=decision.reason,
        raw_output=raw_output,
        first_token_ms=round(record.first_token_ms),
        total_ms=round(record.total_ms),
        retried=attempts > 1,
        parse_failed=parse_failed,
        sanitize_truncated=truncated,
    )

    # 重复检测 → 重生成 → 静态兜底，与 InterviewService.submit_answer_stream 完全一致
    if turn.decision != "end" and turn.question:
        if service._is_repeated_question(turn.question, history):  # noqa: SLF001
            turn.regen_triggered = True
            regenerated = agent.regenerate_question_avoiding_history(
                job_role=scene["job_role"],
                direction=scene["direction"],
                interviewer_mode=scene["mode"],
                duplicated_question=turn.question,
                history=history,
            )
            if regenerated and not service._is_repeated_question(regenerated, history):  # noqa: SLF001
                turn.question = regenerated
                turn.regen_success = True
            else:
                turn.question = service._build_non_repeated_question(  # noqa: SLF001
                    scene["direction"], history
                )
                turn.regen_success = False
                turn.fallback_hit = True

    return turn


# --------------------------------------------------------------------------- #
# 会话编排
# --------------------------------------------------------------------------- #
def system_history_entry(resume_text: str) -> dict[str, str]:
    prefix = "RESUME_CONTEXT"
    return {"role": "SYSTEM", "round_no": "0", "content": f"{prefix}\n{resume_text}"}


def export_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """导出用的问答序列：assistant = 面试官，user = 候选人；SYSTEM 简历上下文不重复导出。"""
    exported: list[dict[str, str]] = []
    for item in history:
        role = item.get("role")
        if role == "AI_INTERVIEWER":
            exported.append({"role": "assistant", "content": item.get("content", "")})
        elif role == "USER_CANDIDATE":
            exported.append({"role": "user", "content": item.get("content", "")})
    return exported


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.scenes_payload = json.loads((SCRIPT_DIR / "scenes.json").read_text(encoding="utf-8"))
        self.scenes = self.scenes_payload["scenes"]
        self.duration_minutes = self.scenes_payload["duration_minutes"]
        self.simulator_template = (SCRIPT_DIR / "simulator_prompt.txt").read_text(encoding="utf-8")
        self.resumes = {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted((SCRIPT_DIR / "resumes").glob("R*.txt"))
        }

        self.out_dir = Path(args.out_dir)
        self.samples_path = self.out_dir / "samples.jsonl"
        self.sessions_path = self.out_dir / "session_meta.jsonl"
        self.errors_path = self.out_dir / "errors.jsonl"
        self.meta_path = self.out_dir / "run_meta.json"

        self.client: RecordingClient
        self.simulator: CandidateSimulator
        if args.mock:
            self.client = RecordingClient(MockInterviewerClient())
            self.simulator = CandidateSimulator(self.simulator_template, MockSimulator())
        else:
            self.client = RecordingClient(OpenAICompatibleClient())
            self.simulator = CandidateSimulator(self.simulator_template, self._real_simulator_call)

        self.agent = InterviewerAgent(llm_client=self.client)
        self.service = InterviewService(repository=None)  # type: ignore[arg-type] - 只用无状态方法

        self._sim_client: Any = None
        self.seen_samples: set[str] = set()
        self.seen_sessions: set[str] = set()
        self.existing_samples: dict[str, dict[str, Any]] = {}
        self._load_existing()

    # -- 持久化 -------------------------------------------------------------
    def _load_existing(self) -> None:
        if self.samples_path.exists():
            for line in self.samples_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("sample_id"):
                    self.seen_samples.add(record["sample_id"])
                    self.existing_samples[record["sample_id"]] = record
        if self.sessions_path.exists():
            for line in self.sessions_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("session_id") and record.get("status") == "complete":
                    self.seen_sessions.add(record["session_id"])

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _record_error(self, session_id: str, scene_id: str, group: str, stage: str, exc: Exception) -> None:
        self._append(
            self.errors_path,
            {
                "session_id": session_id,
                "scene_id": scene_id,
                "group": group,
                "stage": stage,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "created_at": utc_iso(),
            },
        )

    # -- 模拟器 -------------------------------------------------------------
    def _real_simulator_call(self, messages: list[dict[str, str]]) -> str:
        from openai import APIConnectionError, APITimeoutError, RateLimitError, OpenAI

        if self._sim_client is None:
            self._sim_client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout_seconds,
            )
        client = self._sim_client
        retryable = (RateLimitError, APITimeoutError, APIConnectionError)
        backoff = (3.0, 10.0)
        for attempt in range(len(backoff) + 1):
            try:
                response = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=self.args.simulator_max_tokens,
                    # 两组共用同一模拟器设置；显式关思考，避免模拟器自身引入组间差异
                    extra_body={"thinking": {"type": "disabled"}},
                )
                return response.choices[0].message.content or ""
            except retryable:
                if attempt >= len(backoff):
                    raise
                time.sleep(backoff[attempt])
        raise RuntimeError("simulator call failed")

    # -- 跑批 ---------------------------------------------------------------
    def run_group(self, group: str) -> None:
        # 只翻这一处开关；模型 / temperature / timeout 在 configure_settings 里已定死
        settings.llm_question_thinking = group
        batch_id = "A" if group == "disabled" else "B"
        started = utc_now()
        print(f"[{utc_iso(started)}] batch {batch_id} / {group} 开始", flush=True)

        for scene in self.scenes:
            scene = dict(scene)
            scene["resume_text"] = self.resumes[scene["resume_id"]]
            self._run_single_samples(scene, group, batch_id)
            self._run_full_session(scene, group, batch_id)

        finished = utc_now()
        print(f"[{utc_iso(finished)}] batch {batch_id} / {group} 结束", flush=True)
        self._update_meta_batch(group, batch_id, started, finished)

    def _base_record(
        self,
        *,
        session_id: str,
        sample_id: str,
        scene: dict[str, Any],
        group: str,
        batch_id: str,
        round_no: int,
        scored: bool,
        turn: Turn,
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        record = {
            "sample_id": sample_id,
            "session_id": session_id,
            "scene_id": scene["scene_id"],
            "group": group,
            "batch_id": batch_id,
            "job_role": scene["job_role"],
            "resume_id": scene["resume_id"],
            "direction": scene["direction"],
            "mode": scene["mode"],
            "duration_minutes": self.duration_minutes,
            "round_no": round_no,
            "is_first_of_session": round_no == 1,
            "scored": scored,
            "history": export_history(history),
            "decision": turn.decision,
            "reason": turn.reason,
            "raw_output": turn.raw_output,
            "question": turn.question,
            "sanitize_truncated": turn.sanitize_truncated,
            "regen_triggered": turn.regen_triggered,
            "regen_success": turn.regen_success,
            "fallback_hit": turn.fallback_hit,
            "parse_failed": turn.parse_failed,
            "retried": turn.retried,
            "first_token_ms": turn.first_token_ms,
            "total_ms": turn.total_ms,
            "model": settings.llm_model,
            "prompt_version": prompt_version(),
            "created_at": utc_iso(),
            "resume_text": scene["resume_text"],
        }
        return {key: record[key] for key in SAMPLE_FIELDS}

    def _generate(
        self,
        scene: dict[str, Any],
        history: list[dict[str, str]],
        round_no: int,
        session_id: str,
        group: str,
    ) -> Turn:
        return generate_turn(
            agent=self.agent,
            service=self.service,
            client=self.client,
            scene=scene,
            history=history,
            round_no=round_no,
            elapsed_minutes=(round_no - 1) * self.args.elapsed_step_minutes,
            duration_minutes=self.duration_minutes,
        )

    def _run_single_samples(self, scene: dict[str, Any], group: str, batch_id: str) -> None:
        """单题重复采样：同一场景同一输入，只生成首题，不进入追问。"""
        for index in range(1, self.args.single_samples + 1):
            session_id = f"{scene['scene_id']}-{index:02d}-{group}"
            sample_id = f"{session_id}-1"
            if session_id in self.seen_sessions or sample_id in self.seen_samples:
                continue
            history = [system_history_entry(scene["resume_text"])]
            try:
                turn = self._generate(scene, history, 1, session_id, group)
            except Exception as exc:  # noqa: BLE001
                self._record_error(session_id, scene["scene_id"], group, "single", exc)
                continue
            self._append(
                self.samples_path,
                self._base_record(
                    session_id=session_id,
                    sample_id=sample_id,
                    scene=scene,
                    group=group,
                    batch_id=batch_id,
                    round_no=1,
                    scored=True,
                    turn=turn,
                    history=history,
                ),
            )
            self.seen_samples.add(sample_id)
            print(f"  {sample_id} {turn.first_token_ms}ms", flush=True)

    def _run_full_session(self, scene: dict[str, Any], group: str, batch_id: str) -> None:
        """完整面试：首轮出题 → 模拟器作答 → 追问，直到第 rounds 轮。"""
        session_id = f"{scene['scene_id']}-{self.args.single_samples + 1:02d}-{group}"
        if session_id in self.seen_sessions:
            return

        history: list[dict[str, str]] = [system_history_entry(scene["resume_text"])]
        status = "complete"
        simulator_lengths: list[int] = []
        rounds_done = 0

        for round_no in range(1, self.args.rounds + 1):
            sample_id = f"{session_id}-{round_no}"
            if sample_id not in self.seen_samples:
                try:
                    turn = self._generate(scene, history, round_no, session_id, group)
                except Exception as exc:  # noqa: BLE001
                    self._record_error(session_id, scene["scene_id"], group, f"round{round_no}", exc)
                    status = "aborted_llm_error"
                    break
                self._append(
                    self.samples_path,
                    self._base_record(
                        session_id=session_id,
                        sample_id=sample_id,
                        scene=scene,
                        group=group,
                        batch_id=batch_id,
                        round_no=round_no,
                        scored=round_no != 1,
                        turn=turn,
                        history=history,
                    ),
                )
                self.seen_samples.add(sample_id)
                print(f"  {sample_id} {turn.first_token_ms}ms", flush=True)
            else:
                # 续跑：复用已落盘的题面，才能把同一场面试接着跑完
                previous = self.existing_samples.get(sample_id, {})
                turn = Turn(
                    decision=previous.get("decision") or "continue",
                    question=previous.get("question"),
                    reason=previous.get("reason"),
                    raw_output=previous.get("raw_output", ""),
                    first_token_ms=previous.get("first_token_ms", 0),
                    total_ms=previous.get("total_ms", 0),
                    retried=bool(previous.get("retried")),
                    parse_failed=bool(previous.get("parse_failed")),
                    sanitize_truncated=previous.get("sanitize_truncated"),
                )

            if turn.decision == "end":
                status = "ended_by_interviewer"
                rounds_done = round_no
                break
            if not turn.question:
                status = "aborted_no_question"
                rounds_done = round_no
                break

            rounds_done = round_no
            history.append(
                {"role": "AI_INTERVIEWER", "round_no": str(round_no), "content": turn.question}
            )
            if round_no == self.args.rounds:
                break

            try:
                answer = self.simulator.answer(
                    resume_text=scene["resume_text"],
                    job_role=scene["job_role"],
                    direction=scene["direction"],
                    question=turn.question,
                    history=history,
                )
            except Exception as exc:  # noqa: BLE001
                self._record_error(session_id, scene["scene_id"], group, f"simulator{round_no}", exc)
                status = "aborted_simulator_error"
                break
            simulator_lengths.append(len(answer))
            history.append(
                {"role": "USER_CANDIDATE", "round_no": str(round_no), "content": answer}
            )

        self._append(
            self.sessions_path,
            {
                "session_id": session_id,
                "scene_id": scene["scene_id"],
                "group": group,
                "status": status,
                "rounds_completed": rounds_done,
                "simulator_answer_chars": simulator_lengths,
                "finished_at": utc_iso(),
            },
        )
        if status == "complete":
            self.seen_sessions.add(session_id)

    # -- 元数据 -------------------------------------------------------------
    def _load_meta(self) -> dict[str, Any]:
        if self.meta_path.exists():
            try:
                return json.loads(self.meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {"batches": {}, "runs": []}

    def _update_meta_batch(
        self, group: str, batch_id: str, started: datetime, finished: datetime
    ) -> None:
        meta = self._load_meta()
        meta.setdefault("batches", {})[group] = {
            "batch_id": batch_id,
            "started_at": utc_iso(started),
            "finished_at": utc_iso(finished),
        }
        meta["config"] = self._config_snapshot()
        meta.setdefault("runs", []).append(
            {"group": group, "started_at": utc_iso(started), "finished_at": utc_iso(finished)}
        )
        self.meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _config_snapshot(self) -> dict[str, Any]:
        return {
            "mock": self.args.mock,
            "model": settings.llm_model,
            "base_url": settings.llm_base_url or "(openai default)",
            "temperature": settings.llm_temperature,
            "timeout_seconds": settings.llm_timeout_seconds,
            "prompt_version": prompt_version(),
            "simulator": {
                "model": settings.llm_model,
                "temperature": 0.0,
                "max_tokens": self.args.simulator_max_tokens,
                "thinking": "disabled",
                "prompt_version": simulator_prompt_version(self.simulator_template),
            },
            "duration_minutes": self.duration_minutes,
            "single_samples": self.args.single_samples,
            "rounds": self.args.rounds,
            "elapsed_step_minutes": self.args.elapsed_step_minutes,
            "scenes": [item["scene_id"] for item in self.scenes],
        }


# --------------------------------------------------------------------------- #
# README 生成
# --------------------------------------------------------------------------- #
def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]


def fmt_ms(value: float | None) -> str:
    return "-" if value is None else f"{value:.0f}"


def write_readme(out_dir: Path, args: argparse.Namespace) -> None:
    samples = read_jsonl(out_dir / "samples.jsonl")
    # 续跑会为同一 session 追加新的 meta 行，按 session_id 取最后一条
    sessions_by_id: dict[str, dict[str, Any]] = {}
    for item in read_jsonl(out_dir / "session_meta.jsonl"):
        sessions_by_id[item.get("session_id", "")] = item
    sessions = list(sessions_by_id.values())
    errors = read_jsonl(out_dir / "errors.jsonl")
    meta_path = out_dir / "run_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    config = meta.get("config", {})

    lines: list[str] = []
    add = lines.append
    add("# AIC-80 对比样本跑批说明")
    add("")
    add(f"> 生成时间：{utc_iso()}")
    add("")
    if args.mock:
        add("> **本次是 mock 运行，样本内容是假数据，只能用来校验脚本，禁止用于任何质量结论。**")
        add("")

    add("## 1. 跑批时间窗")
    add("")
    add(f"- 时间戳一律 UTC（ISO8601，带 `Z`）；本机时区 {local_tz_label()}，README 中的时间不做本地化换算。")
    add(f"- 本批每条样本的 `created_at` 也是 UTC。")
    add("")
    add("| 组 | batch_id | 开始 (UTC) | 结束 (UTC) |")
    add("|----|----------|------------|------------|")
    batches = meta.get("batches", {})
    for group in ("disabled", "enabled"):
        item = batches.get(group)
        if not item:
            add(f"| {group} | - | 未执行 | 未执行 |")
            continue
        add(
            f"| {group} | {item.get('batch_id')} | {item.get('started_at')} | "
            f"{item.get('finished_at')} |"
        )
    add("")

    add("## 2. 模型与参数")
    add("")
    add(f"- `llm_model` 实际值：`{config.get('model', '(unknown)')}`")
    add(f"- `llm_base_url`：`{config.get('base_url', '(unknown)')}`")
    add(f"- `temperature`：{config.get('temperature', '(unknown)')}")
    add(f"- `timeout_seconds`：{config.get('timeout_seconds', '(unknown)')}")
    add(f"- prompt 版本：`{config.get('prompt_version', '(unknown)')}`")
    add("")
    if config.get("model") and config["model"] != PRODUCTION_MODEL and not args.mock:
        add(
            f"> **偏差告警**：production 使用 `{PRODUCTION_MODEL}`，本次样本用的是 "
            f"`{config['model']}`。两组之间仍可比（同模型、同 prompt、同 temperature），"
            f"但结论能否外推到 production 需要评审方单独确认。"
        )
        add("")

    add("## 3. direction / mode 枚举映射")
    add("")
    add("输入包第 4 节用的是语义名，产品实际传的就是下列枚举值，本批未做改写。")
    add("")
    add("| direction 枚举值 | 产品中文名 | 本批使用场景 |")
    add("|------------------|------------|--------------|")
    used = {}
    for sample in samples:
        used.setdefault(sample.get("direction"), set()).add(sample.get("scene_id"))
    for value, label in DIRECTION_LABELS.items():
        scenes = ",".join(sorted(item for item in used.get(value, set()) if item)) or "-"
        add(f"| `{value}` | {label} | {scenes} |")
    add("")
    add("| mode 枚举值 | 产品中文名 | 本批使用场景 |")
    add("|-------------|------------|--------------|")
    used_modes = {}
    for sample in samples:
        used_modes.setdefault(sample.get("mode"), set()).add(sample.get("scene_id"))
    for value, label in MODE_LABELS.items():
        scenes = ",".join(sorted(item for item in used_modes.get(value, set()) if item)) or "-"
        add(f"| `{value}` | {label} | {scenes} |")
    add("")

    add("## 4. 候选人模拟器（输入包 5.2）")
    add("")
    sim = config.get("simulator", {})
    add("| 项 | 值 |")
    add("|----|----|")
    add(f"| 模型 | `{sim.get('model', '(unknown)')}` |")
    add(f"| temperature | {sim.get('temperature', '(unknown)')} |")
    add(f"| max_tokens | {sim.get('max_tokens', '(unknown)')} |")
    add(f"| thinking | `{sim.get('thinking', '(unknown)')}` |")
    add(f"| prompt 版本 | `{sim.get('prompt_version', '(unknown)')}` |")
    add("")
    add("两组共用同一个模拟器实例与同一份 prompt；模拟器请求里不含任何组别信息。")
    add("")

    add("## 5. 每个完整面试场的模拟器平均回答长度")
    add("")
    add("| session_id | 场景 | 组 | 状态 | 轮次 | 平均字数 | 各轮字数 |")
    add("|------------|------|----|------|------|----------|----------|")
    per_group_lengths: dict[str, list[float]] = {"disabled": [], "enabled": []}
    for item in sorted(sessions, key=lambda row: (row.get("group", ""), row.get("session_id", ""))):
        lengths = item.get("simulator_answer_chars") or []
        average = sum(lengths) / len(lengths) if lengths else None
        if average is not None:
            per_group_lengths.setdefault(item.get("group", ""), []).append(average)
        add(
            f"| {item.get('session_id')} | {item.get('scene_id')} | {item.get('group')} | "
            f"{item.get('status')} | {item.get('rounds_completed')} | "
            f"{'-' if average is None else f'{average:.0f}'} | "
            f"{', '.join(str(v) for v in lengths) or '-'} |"
        )
    add("")
    add("| 组 | 场次数 | 模拟器回答平均字数（场均） |")
    add("|----|--------|------------------------------|")
    for group, values in per_group_lengths.items():
        add(f"| {group} | {len(values)} | {'-' if not values else f'{sum(values) / len(values):.1f}'} |")
    add("")

    add("## 6. 重试与失败记录")
    add("")
    retried = [item for item in samples if item.get("retried")]
    add(f"- 重试过的样本：{len(retried)} 条" + (
        "（" + ", ".join(item["sample_id"] for item in retried) + "）" if retried else "")
    )
    add(f"- 生成失败（进 `errors.jsonl`）：{len(errors)} 条")
    if errors:
        add("")
        add("| session_id | 阶段 | 错误类型 |")
        add("|------------|------|----------|")
        for item in errors:
            add(f"| {item.get('session_id')} | {item.get('stage')} | {item.get('error_type')} |")
    add("")
    add("延迟统计已剔除 `retried=true` 的样本；质量统计保留全部样本（含重试）。")
    add("")

    add("## 7. 样本计数核对")
    add("")
    add("| 组 | 导出条数 | 计分条数（scored=true） | 场次数 |")
    add("|----|----------|--------------------------|--------|")
    for group in ("disabled", "enabled"):
        group_samples = [item for item in samples if item.get("group") == group]
        group_sessions = [item for item in sessions if item.get("group") == group]
        add(
            f"| {group} | {len(group_samples)} | "
            f"{sum(1 for item in group_samples if item.get('scored'))} | {len(group_sessions)} |"
        )
    add("")
    add(
        f"预期（输入包 6.3）：每组 3 题 × 12 场景 + 12 场 × 5 轮 = 96 条导出、84 条计分；"
        f"两组共 192 条导出、168 条计分。"
    )
    add("")

    add("## 8. 延迟（首 token）")
    add("")
    add("| 组 | 样本范围 | n | P50 (ms) | P90 (ms) | 均值 (ms) |")
    add("|----|----------|---|----------|----------|-----------|")
    for group in ("disabled", "enabled"):
        pool = [
            item for item in samples
            if item.get("group") == group and not item.get("retried")
        ]
        firsts = [item["first_token_ms"] for item in pool if item.get("is_first_of_session")]
        all_rows = [item["first_token_ms"] for item in pool]
        add(
            f"| {group} | 首题（单题采样 + 完整面试第 1 轮） | {len(firsts)} | "
            f"{fmt_ms(percentile(firsts, 0.5))} | {fmt_ms(percentile(firsts, 0.9))} | "
            f"{fmt_ms(statistics.mean(firsts) if firsts else None)} |"
        )
        add(
            f"| {group} | 全部出题 | {len(all_rows)} | "
            f"{fmt_ms(percentile(all_rows, 0.5))} | {fmt_ms(percentile(all_rows, 0.9))} | "
            f"{fmt_ms(statistics.mean(all_rows) if all_rows else None)} |"
        )
    add("")
    add("首 token = `chat_stream` 吐出的第一个内容 chunk（thinking 的 reasoning token 不计入）。")
    add("")

    add("## 9. 质量否决项相关计数")
    add("")
    add("| 指标 | disabled | enabled |")
    add("|------|----------|---------|")
    for label, predicate in (
        ("JSON 解析失败（parse_failed）", lambda item: item.get("parse_failed")),
        ("重复检测触发（regen_triggered）", lambda item: item.get("regen_triggered")),
        ("重生成成功（regen_success）", lambda item: item.get("regen_success") is True),
        ("静态兜底命中（fallback_hit）", lambda item: item.get("fallback_hit")),
        ("疑似被截断（sanitize_truncated=true）", lambda item: item.get("sanitize_truncated") is True),
        ("截断无法判定（sanitize_truncated=null）", lambda item: item.get("sanitize_truncated") is None),
        (
            "空题走默认问句",
            lambda item: item.get("question") == EMPTY_QUESTION_DEFAULT,
        ),
    ):
        row = []
        for group in ("disabled", "enabled"):
            row.append(str(sum(1 for item in samples if item.get("group") == group and predicate(item))))
        add(f"| {label} | {row[0]} | {row[1]} |")
    add("")

    add("## 10. 字段与口径说明")
    add("")
    add("- `history`：`assistant` = 面试官问题，`user` = 候选人回答；SYSTEM 角色的简历上下文不重复导出，简历见 `resume_text`。")
    add("- `sample_id` / `session_id`：`<场景>-<会话序号>-<组>`，`sample_id` 再加 `-<轮次>`。序号 01-03 是单题采样，第 04 个是完整面试。")
    add("- `scored`：完整面试第 1 轮为 `false`（与单题采样重复计数），其余为 `true`。")
    add("- `sanitize_truncated`：对比「清洗前的问题字段」与「最终 question」，若 `_normalize_single_question()` 在第一个 `？` 或分隔符处切掉了尾部则为 `true`；无法判断时为 `null`。")
    add("- `regen_success`：未触发重复检测时为 `null`。")
    add("- `first_token_ms` / `total_ms`：只计成功那一次调用；重试耗时不计入。")
    add("- `raw_output`：模型原始输出（sanitize 之前）。`question`：sanitize 之后的最终题面。")
    add("")

    add("## 11. 口径偏差与已知局限（请评审前先看这一节）")
    add("")
    add("1. **首题语义**：产品里 `InterviewService.start_interview()` 的第 1 题是静态模板（自我介绍），LLM 第一次真正出题是第 2 轮。本批按抽检标准 §2.1「第 1 题没有上一轮回答，D2 记为 N/A」的口径，把「无历史上下文时 LLM 生成的第一题」记为第 1 轮。因此本批的第 1 轮并不是线上用户看到的第一句话。")
    add("2. **thinking 切换方式**：生产通过改环境变量后重建容器生效；本脚本不走 HTTP/DB，直接读 `settings.llm_question_thinking`，切换是在进程内翻这个配置。`InterviewerAgent` 每次调用都会读它并序列化成同一个 `extra_body`，因此效果等价，但没有「重建测试实例」这一步。")
    add("3. **时间参数**：`elapsed_minutes` 按轮次固定递增（每轮 +%d 分钟），不用墙钟。" % args.elapsed_step_minutes
        + "两组必须拿到同样的节奏提示，否则 prompt 里「距上限还有约 X 分钟」会变成组间差异。")
    add("4. **模拟器**：会引入方差，输入包 5.4 已说明第 2-5 轮只做整场横向比较、不做逐题配对。")
    add("5. **重试样本**：延迟统计剔除，质量统计保留。")
    add("")

    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AIC-80 关思考/开思考对比样本跑批",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--group", choices=["disabled", "enabled", "all"], default="all",
                        help="跑哪一组；all 会先 disabled 再 enabled（默认）")
    parser.add_argument("--scenes", default="", help="逗号分隔的场景号，如 S01,S07；默认全部 12 个")
    parser.add_argument("--out-dir", default="", help="输出目录，默认 scripts/quality_sampling/out/aic80-<UTC 时间>")
    parser.add_argument("--single-samples", type=int, default=3, help="每个场景单题采样次数（默认 3）")
    parser.add_argument("--rounds", type=int, default=5, help="完整面试轮次（默认 5）")
    parser.add_argument("--elapsed-step-minutes", type=int, default=5,
                        help="模拟时钟每轮递增分钟数（默认 5）")
    parser.add_argument("--gap-seconds", type=int, default=30, help="Batch A/B 之间的间隔秒数（默认 30）")
    parser.add_argument("--simulator-max-tokens", type=int, default=400)
    parser.add_argument("--temperature", type=float, default=None, help="默认读 LLM_TEMPERATURE，注释要求 0.7")
    parser.add_argument("--model", default="", help="模型标识，默认读 LLM_MODEL")
    parser.add_argument("--base-url", default="", help="OpenAI 兼容网关地址，默认读 LLM_BASE_URL")
    parser.add_argument("--api-key", default="", help="API Key，默认读 LLM_API_KEY")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="默认读 LLM_TIMEOUT_SECONDS")
    parser.add_argument("--allow-model-mismatch", action="store_true",
                        help=f"模型不是生产值 {PRODUCTION_MODEL} 时仍然继续（README 会记录偏差）")
    parser.add_argument("--mock", action="store_true", help="用假 LLM 校验脚本，不产生真实样本")
    return parser


def configure_settings(args: argparse.Namespace) -> None:
    if args.mock:
        args.model = args.model or "mock-model"
        args.base_url = args.base_url or ""
        settings.llm_api_key = settings.llm_api_key or "mock-key"
        settings.llm_model = args.model
        settings.llm_base_url = None
        settings.llm_temperature = args.temperature if args.temperature is not None else 0.7
        return

    args.api_key = args.api_key or os.environ.get("LLM_API_KEY", "")
    args.base_url = args.base_url or os.environ.get("LLM_BASE_URL", "")
    args.model = args.model or os.environ.get("LLM_MODEL", "")

    if not args.api_key:
        raise SystemExit(
            "缺少 LLM_API_KEY。请通过 --api-key 或环境变量传入生产同源网关的凭据，"
            "或先加 --mock 校验脚本。"
        )
    if not args.model:
        raise SystemExit("缺少 LLM_MODEL（例如 deepseek-v4-flash）。")

    settings.llm_api_key = args.api_key
    settings.llm_base_url = args.base_url or None
    settings.llm_model = args.model
    settings.llm_temperature = args.temperature if args.temperature is not None else float(
        os.environ.get("LLM_TEMPERATURE", 0.7)
    )
    settings.llm_timeout_seconds = args.timeout_seconds or int(
        os.environ.get("LLM_TIMEOUT_SECONDS", 60)
    )

    if args.temperature is not None and abs(args.temperature - 0.7) > 1e-9:
        raise SystemExit(
            f"temperature 必须是 0.7（输入包固定参数），收到 {args.temperature}。"
            "不要为了结果好看调整它。"
        )

    if args.model != PRODUCTION_MODEL and not args.allow_model_mismatch:
        raise SystemExit(
            f"模型 `{args.model}` 与 production 的 `{PRODUCTION_MODEL}` 不一致。\n"
            "输入包要求结论可外推到线上，换模型会让样本失去外推能力。\n"
            "确实要用代理模型跑，请显式加 --allow-model-mismatch，README 会记录这一偏差。"
        )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.out_dir:
        args.out_dir = str(default_out_dir())
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    configure_settings(args)

    runner = Runner(args)
    if args.scenes:
        wanted = {item.strip() for item in args.scenes.split(",") if item.strip()}
        unknown = wanted - {item["scene_id"] for item in runner.scenes}
        if unknown:
            raise SystemExit(f"未知场景：{sorted(unknown)}")
        runner.scenes = [item for item in runner.scenes if item["scene_id"] in wanted]

    print(
        f"输出目录：{Path(args.out_dir).resolve()}\n"
        f"模型：{settings.llm_model} @ {settings.llm_base_url or 'openai default'}\n"
        f"temperature：{settings.llm_temperature}　mock：{args.mock}\n",
        flush=True,
    )

    groups = ["disabled", "enabled"] if args.group == "all" else [args.group]
    try:
        for index, group in enumerate(groups):
            runner.run_group(group)
            if index == 0 and len(groups) > 1 and args.gap_seconds > 0:
                print(f"Batch A 完成，{args.gap_seconds}s 后切到 enabled", flush=True)
                time.sleep(args.gap_seconds)
    except KeyboardInterrupt:
        print("收到中断，已写入的样本保留；重跑同一命令会跳过已完成部分。", flush=True)
    finally:
        write_readme(Path(args.out_dir), args)
        print(f"README 已生成：{Path(args.out_dir) / 'README.md'}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
