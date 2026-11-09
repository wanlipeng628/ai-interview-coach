"""重复出题回归测试（AIC-84）。

语料来自生产库（2026-11-09）真实会话，其中 interview_sessions.id=15 那场 28 轮里
同一个问题被问了 4 次，当时的判重逻辑一次都没拦住。

字面判重（相邻两字 Jaccard）有两个已知区间，实测这两段是**重叠**的：
    合理递进追问  0.025 ~ 0.143
    真重复        0.198 ~ 0.642
所以不存在一个阈值能既抓全又不误杀。阈值定在 0.35，只负责拦下最明显的 4 对；
其余靠出题 prompt 里的「全量已问问题清单」在生成阶段预防（见本文件后半段的测试）。
语义级判重（topic 标签）是第二批工作。
"""

import pytest

from app.application.interview.interview_service import InterviewService
from app.infrastructure.agent.interview_agent import InterviewerAgent

# 字面相似度 >= 0.35，判重必须命中
DUPLICATE_PAIRS = [
    (
        "简介批量生成里非干部侧用 CompletableFuture 分批并行调用大模型，这些异步任务运行在什么样的线程池上，这个线程池具体是怎么创建和配置的？",
        "员工简介批量生成里，非干部侧用 CompletableFuture 按人数动态分批并行调用大模型，这些并行任务提交到的线程池具体是怎么创建和配置的？",
        0.642,
    ),
    (
        "你做 Oracle 到 PostgreSQL 的千万级假单迁移时，分批同步任务执行期间源库仍在产生新的假单数据，你如何保证迁移既不漏掉数据、也不重复写入？",
        "Oracle 到 PostgreSQL 的千万级假单迁移里，如果迁移窗口内源库还在持续产生新的假单，你的分批定时任务靠什么保证这部分增量数据不漏迁、也不重复写入？",
        0.402,
    ),
    (
        "简介批量生成里非干部侧用 CompletableFuture 分批并行调用大模型，这些异步任务运行在什么样的线程池上，这个线程池具体是怎么创建和配置的？",
        "简介批量生成、EAST2 导入这些地方都用了 CompletableFuture 做异步，这些异步任务实际跑在什么样的线程池上？",
        0.375,
    ),
    (
        "你在员工简介生成里用 CompletableFuture 做动态分批并行调用大模型，这段并行编排挂的是哪个线程池，它的核心线程数和队列长度你是怎么定的？",
        "员工简介批量生成里，非干部侧用 CompletableFuture 按人数动态分批并行调用大模型，这些并行任务提交到的线程池具体是怎么创建和配置的？",
        0.371,
    ),
]

# 同一项目往更深的层次走：必须放行，不能被判重切掉面试深度
PROGRESSION_PAIRS = [
    (
        "请假申请里，余额校验和插入假单如果放在同一个事务里，当两个请求同时对同一个员工的同一类假期发起申请，你是如何避免余额被超额扣减的？",
        "你用 SELECT ... FOR UPDATE 锁的是假期配置表里该员工的那行锚点记录，如果这个员工在配置表里还没有对应行、或者这一行刚好被别人删掉了，这条 SELECT 会锁住什么？",
    ),
    (
        "你用 SELECT ... FOR UPDATE 锁的是假期配置表里该员工的那行锚点记录，如果这个员工在配置表里还没有对应行、或者这一行刚好被别人删掉了，这条 SELECT 会锁住什么？",
        "月底高峰期间定时执行缓存预热，如果预热任务正在把某位员工的余额写入 Redis，而同一时间这位员工恰好有一张假单审批通过、触发了余额更新和缓存删除，这个时序下如何避免旧的余额数据被重新写回缓存？",
    ),
    (
        "EAST2 监管报送的导入在异步线程里完成解析后落库，这个落库过程的事务粒度你是怎么划定的？",
        "EAST2 月度报送导入采用先删后插来保证同一期数据唯一，那这一期的删除和插入在事务边界上是怎么划分的？",
    ),
    (
        "简介生成的定时任务用分布式锁防止重复执行，如果某个节点持锁执行到一半时宕机，这把锁和这批未完成的任务会怎么处理？",
        "你在员工简介定时批量生成任务上用的那把分布式锁，具体是用什么方式实现和释放的？",
    ),
]


def _service() -> InterviewService:
    # 判重不碰 repository / agent，传空壳即可
    return InterviewService(repository=None, interviewer_agent=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("previous", "candidate", "expected_similarity"), DUPLICATE_PAIRS
)
def test_duplicate_questions_are_detected(
    previous: str, candidate: str, expected_similarity: float
) -> None:
    service = _service()
    # 先确认语料本身确实超过阈值，避免测试因为阈值被改动而静默失效
    assert service._text_similarity(
        service._normalize_question_text(previous),
        service._normalize_question_text(candidate),
    ) >= 0.35
    history = [{"role": "AI_INTERVIEWER", "round_no": "1", "content": previous}]
    assert service._is_repeated_question(candidate, history) is True


@pytest.mark.parametrize(("previous", "candidate"), PROGRESSION_PAIRS)
def test_progression_questions_are_not_blocked(previous: str, candidate: str) -> None:
    service = _service()
    history = [{"role": "AI_INTERVIEWER", "round_no": "1", "content": previous}]
    assert service._is_repeated_question(candidate, history) is False


def test_asked_questions_include_all_rounds_not_just_recent() -> None:
    """出题 prompt 必须能看到全量已问问题，否则长会话必然重复。"""
    agent = InterviewerAgent.__new__(InterviewerAgent)
    early = "第一轮：请讲一下订单模块你负责的接口是怎么实现的？"
    history: list[dict[str, str]] = [
        {"role": "AI_INTERVIEWER", "round_no": "1", "content": early},
        {"role": "USER_CANDIDATE", "round_no": "1", "content": "我做了下单和查询接口。"},
    ]
    # 再补 20 轮，把第一轮挤出 history[-12:] 的窗口
    for round_no in range(2, 22):
        history.append(
            {
                "role": "AI_INTERVIEWER",
                "round_no": str(round_no),
                "content": f"第{round_no}轮：我们能聊聊项目里的第 {round_no} 个技术点吗？",
            }
        )
        history.append(
            {"role": "USER_CANDIDATE", "round_no": str(round_no), "content": "说明一下实现。"}
        )

    messages = agent._build_next_question_messages(
        job_role="Java 后端",
        round_no=22,
        duration_minutes=45,
        elapsed_minutes=40,
        direction="FULL_MOCK",
        interviewer_mode="NORMAL",
        resume_text="三年 Java 后端",
        history=history,
    )
    prompt = messages[1]["content"]

    assert early in prompt, "早期问过的问题没有进 prompt，长会话一定会重复"
    assert "已问过的问题（全部，不得重复）" in prompt
    # 最近几轮的对话上下文仍然在
    assert "第21轮：我们能聊聊项目里的第 21 个技术点吗？" in prompt


def test_asked_questions_fall_back_to_history_when_not_passed() -> None:
    """老调用方不传 asked_questions 时，自己从 history 抽，不能静默丢失。"""
    agent = InterviewerAgent.__new__(InterviewerAgent)
    history = [
        {"role": "AI_INTERVIEWER", "round_no": "1", "content": "第一个问题？"},
        {"role": "USER_CANDIDATE", "round_no": "1", "content": "回答内容。"},
    ]
    messages = agent._build_next_question_messages(
        job_role="Java 后端",
        round_no=2,
        duration_minutes=45,
        elapsed_minutes=5,
        direction="FULL_MOCK",
        interviewer_mode="NORMAL",
        resume_text=None,
        history=history,
    )
    assert "第一个问题？" in messages[1]["content"]
