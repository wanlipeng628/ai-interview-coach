class InterviewQuestionPolicy:
    """Domain policy for creating interview questions."""

    def build_first_question(self, job_role: str) -> str:
        """Build the first question for a newly created interview session."""
        return (
            f"你好，我是本次{job_role}模拟面试的技术面试官。"
            "我们先从自我介绍开始，请你介绍一下自己的背景、核心项目经历和技术栈。"
        )
