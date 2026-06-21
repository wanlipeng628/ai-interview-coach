import { defineStore } from 'pinia'

import {
  finishInterviewApi,
  getInterviewSessionApi,
  getLatestActiveInterviewApi,
  listInterviewMessagesApi,
  startInterviewApi,
  submitAnswerApi,
} from '@/api/interview.api'
import type {
  AnsweredQuestion,
  InterviewInfo,
  InterviewMessage,
  InterviewRole,
  LatestActiveInterview,
} from '@/types/interview'

interface InterviewState {
  info: InterviewInfo
  messages: InterviewMessage[]
  answeredQuestions: AnsweredQuestion[]
  latestActive: LatestActiveInterview | null
  isStreaming: boolean
  loading: boolean
  generating: boolean
  errorMessage: string
}

interface StartInterviewOptions {
  jobRole?: string
  durationMinutes?: number
  resumeText?: string
  direction?: string
  interviewerMode?: string
}

const finishMessage =
  '本次模拟面试已经结束，稍后可以进入复盘报告查看整体评分、薄弱知识点和训练建议。'

export const useInterviewStore = defineStore('interview', {
  state: (): InterviewState => ({
    info: {
      sessionId: 'demo-session',
      jobRole: 'Java开发工程师',
      direction: 'FULL_MOCK',
      interviewerMode: 'NORMAL',
      currentQuestionNo: 1,
      totalQuestions: 999,
      durationLimitMinutes: 45,
      startedAt: Date.now(),
      durationSeconds: 0,
      status: 'in_progress',
    },
    messages: [
      {
        id: crypto.randomUUID(),
        role: 'ai',
        questionNo: 1,
        content:
          '你好，欢迎参加 Java 开发工程师模拟面试。请先介绍一下你最近参与的一个 Java 项目，重点说明你的职责、核心技术栈，以及你解决过的一个技术难点。',
        createdAt: new Date().toISOString(),
      },
    ],
    answeredQuestions: [],
    latestActive: null,
    isStreaming: false,
    loading: false,
    generating: false,
    errorMessage: '',
  }),

  getters: {
    progressPercent: (state) =>
      Math.round((state.answeredQuestions.length / state.info.totalQuestions) * 100),
  },

  actions: {
    async fetchLatestActive() {
      const response = await getLatestActiveInterviewApi()
      this.latestActive = {
        hasActive: response.has_active,
        sessionId: response.session_id,
        jobRole: response.job_role,
        direction: response.direction,
        interviewerMode: response.interviewer_mode,
        startedAt: response.started_at,
        answeredCount: response.answered_count,
      }
    },

    async startInterview(options: StartInterviewOptions | string = {}) {
      if (this.loading) return
      this.loading = true
      this.errorMessage = ''
      const normalizedOptions = typeof options === 'string' ? { jobRole: options } : options
      const jobRole = normalizedOptions.jobRole?.trim() || 'Java开发工程师'
      const durationMinutes = normalizedOptions.durationMinutes ?? 45
      const direction = normalizedOptions.direction ?? 'FULL_MOCK'
      const interviewerMode = normalizedOptions.interviewerMode ?? 'NORMAL'

      try {
        const response = await startInterviewApi({
          job_role: jobRole,
          direction,
          interviewer_mode: interviewerMode,
          duration_minutes: durationMinutes,
          resume_text: normalizedOptions.resumeText?.trim() || undefined,
        })
        this.info = {
          sessionId: response.session_id,
          jobRole,
          direction,
          interviewerMode,
          currentQuestionNo: 1,
          totalQuestions: 999,
          durationLimitMinutes: durationMinutes,
          startedAt: Date.now(),
          durationSeconds: 0,
          status: 'in_progress',
        }
        this.messages = [
          {
            id: crypto.randomUUID(),
            role: 'ai',
            questionNo: 1,
            content: response.first_question,
            createdAt: new Date().toISOString(),
          },
        ]
        this.answeredQuestions = []
        this.isStreaming = false
        this.generating = false
      } finally {
        this.loading = false
      }
    },

    async restoreInterview(sessionId: string) {
      this.loading = true
      this.errorMessage = ''
      try {
        const session = await getInterviewSessionApi(sessionId)
        const messages = await listInterviewMessagesApi(sessionId)

        this.info = {
          sessionId: session.session_id,
          jobRole: session.job_role,
          direction: session.direction,
          interviewerMode: session.interviewer_mode,
          currentQuestionNo: session.current_round,
          totalQuestions: 999,
          durationLimitMinutes: session.duration_minutes,
          startedAt: new Date(session.started_at).getTime() || Date.now(),
          durationSeconds: 0,
          status: session.status === 'FINISHED' ? 'finished' : 'in_progress',
        }
        this.messages = messages
          .map((item) => ({
            id: crypto.randomUUID(),
            role: mapRestoredRole(item.role),
            content: item.content,
            questionNo: item.round_no || undefined,
            createdAt: item.created_at,
            streaming: false,
          }))
          .filter((item) => item.content.trim())
        this.answeredQuestions = messages
          .filter((item) => item.role === 'USER_CANDIDATE')
          .map((item) => ({
            questionNo: item.round_no,
            title:
              messages.find(
                (message) => message.role === 'AI_INTERVIEWER' && message.round_no === item.round_no,
              )?.content ?? '',
            answeredAt: item.created_at,
          }))
        this.isStreaming = false
        this.generating = false
      } finally {
        this.loading = false
      }
    },

    tickDuration() {
      if (this.info.status === 'finished') return
      this.info.durationSeconds = Math.floor((Date.now() - this.info.startedAt) / 1000)
    },

    async submitAnswer(answer: string) {
      const text = answer.trim()
      if (!text || this.loading || this.isStreaming || this.info.status === 'finished') return

      const questionNo = this.info.currentQuestionNo
      const userMessage: InterviewMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        questionNo,
        createdAt: new Date().toISOString(),
      }
      this.messages.push(userMessage)

      const answeredQuestion: AnsweredQuestion = {
        questionNo,
        title:
          this.messages.find((item) => item.role === 'ai' && item.questionNo === questionNo)
            ?.content ?? '',
        answeredAt: new Date().toISOString(),
      }
      this.answeredQuestions.push(answeredQuestion)

      this.loading = true
      this.generating = true
      this.errorMessage = ''
      try {
        const response = await submitAnswerApi(this.info.sessionId, { answer: text })

        if (response.is_finished || !response.next_question) {
          this.markFinished()
          return
        }

        this.info.currentQuestionNo = response.round_no
        this.streamNextQuestion(response.next_question)
      } catch (error) {
        this.messages = this.messages.filter((item) => item.id !== userMessage.id)
        this.answeredQuestions = this.answeredQuestions.filter((item) => item !== answeredQuestion)
        this.errorMessage = getRequestErrorMessage(error)
        throw error
      } finally {
        this.loading = false
        if (!this.isStreaming) {
          this.generating = false
        }
      }
    },

    streamNextQuestion(question: string) {
      this.isStreaming = true
      const messageId = crypto.randomUUID()
      const message: InterviewMessage = {
        id: messageId,
        role: 'ai',
        questionNo: this.info.currentQuestionNo,
        content: '',
        createdAt: new Date().toISOString(),
        streaming: true,
      }

      this.messages.push(message)
      const messageIndex = this.messages.findIndex((item) => item.id === messageId)

      let index = 0
      const timer = window.setInterval(() => {
        const currentMessage = this.messages[messageIndex]
        if (!currentMessage) {
          window.clearInterval(timer)
          this.isStreaming = false
          this.generating = false
          return
        }

        currentMessage.content += question[index] ?? ''
        index += 1

        if (index >= question.length) {
          window.clearInterval(timer)
          currentMessage.streaming = false
          this.isStreaming = false
          this.generating = false
        }
      }, 24)
    },

    async finishInterview() {
      if (this.info.status !== 'finished' && this.info.sessionId !== 'demo-session') {
        await finishInterviewApi(this.info.sessionId)
      }
      this.markFinished()
    },

    markFinished() {
      this.info.status = 'finished'
      this.isStreaming = false
      this.generating = false
      const alreadyHasFinishMessage = this.messages.some((item) => item.content === finishMessage)
      if (!alreadyHasFinishMessage) {
        this.messages.push({
          id: crypto.randomUUID(),
          role: 'ai',
          content: finishMessage,
          createdAt: new Date().toISOString(),
        })
      }
    },
  },
})

const getRequestErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    return response?.data?.detail ?? '提交回答失败，请稍后重试'
  }
  return '提交回答失败，请确认后端服务和数据库连接正常'
}

const mapRestoredRole = (role: string): InterviewRole => {
  if (role === 'USER_CANDIDATE') return 'user'
  return 'ai'
}
