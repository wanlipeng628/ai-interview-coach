import { defineStore } from 'pinia'

import {
  finishInterviewApi,
  getInterviewSessionApi,
  getLatestActiveInterviewApi,
  listInterviewMessagesApi,
  startInterviewApi,
  submitAnswerApi,
  submitAnswerStreamApi,
  SubmitAnswerStreamError,
} from '@/api/interview.api'
import type {
  AnsweredQuestion,
  InterviewInfo,
  InterviewMessage,
  InterviewRole,
  LatestActiveInterview,
} from '@/types/interview'
import type { SubmitAnswerResponse } from '@/api/interview.api'

import { uuid } from '@/utils/uuid'

interface InterviewState {
  info: InterviewInfo
  messages: InterviewMessage[]
  answeredQuestions: AnsweredQuestion[]
  latestActive: LatestActiveInterview | null
  isStreaming: boolean
  loading: boolean
  generating: boolean
  errorMessage: string
  failedDraft: string
  /** stage 事件给出的等待提示，空串表示还没收到 */
  stageLabel: string
}

// 流式请求的控制句柄和 attempt 序号不进 state：它们不是渲染数据，也不该被 Pinia 代理
let submitToken = 0
let activeStream: AbortController | null = null

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
        id: uuid(),
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
    failedDraft: '',
    stageLabel: '',
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
            id: uuid(),
            role: 'ai',
            questionNo: 1,
            content: response.first_question,
            createdAt: new Date().toISOString(),
          },
        ]
        this.answeredQuestions = []
        this.isStreaming = false
        this.generating = false
        this.stageLabel = ''
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
            id: uuid(),
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
        this.stageLabel = ''
      } finally {
        this.loading = false
      }
    },

    tickDuration() {
      if (this.info.status === 'finished') return
      // clamp 到 0：时间源有偏差时（比如服务端与设备时区不一致）
      // 宁可显示 00:00 也不要让负数直接流到界面上
      const elapsed = Math.floor((Date.now() - this.info.startedAt) / 1000)
      this.info.durationSeconds = Math.max(0, elapsed)
    },

    async submitAnswer(answer: string) {
      const text = answer.trim()
      if (!text || this.loading || this.isStreaming || this.info.status === 'finished') return

      const questionNo = this.info.currentQuestionNo
      const userMessage: InterviewMessage = {
        id: uuid(),
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
      this.failedDraft = ''
      this.stageLabel = ''

      const token = ++submitToken
      const controller = new AbortController()
      activeStream = controller
      let streamedMessageId: string | null = null

      // 结束后 / 已中断的 attempt 迟到的回调一律丢弃，避免往已收尾的会话里写消息
      const isStale = () => token !== submitToken

      try {
        try {
          await submitAnswerStreamApi(
            this.info.sessionId,
            { answer: text },
            {
              onStage: ({ label }) => {
                if (!isStale()) this.stageLabel = label
              },
              onDelta: ({ text: delta }) => {
                if (isStale() || !delta) return
                if (!streamedMessageId) {
                  streamedMessageId = uuid()
                  this.messages.push({
                    id: streamedMessageId,
                    role: 'ai',
                    content: '',
                    createdAt: new Date().toISOString(),
                    streaming: true,
                  })
                  this.isStreaming = true
                }
                const message = this.messages.find((item) => item.id === streamedMessageId)
                if (message) message.content += delta
              },
              onDone: (response) => {
                if (!isStale()) this.applyAnswerResponse(response, streamedMessageId)
              },
            },
            controller.signal,
          )
          if (isStale()) return
        } catch (streamError) {
          if (isAbortError(streamError) || isStale()) return

          // 流式不可用（后端没开 / 连接中断 / 流内 error）：丢掉半截气泡，回落同步接口重试一次
          this.discardStreamedMessages()
          streamedMessageId = null
          this.isStreaming = false
          this.stageLabel = ''

          const response = await submitAnswerApi(this.info.sessionId, { answer: text })
          if (isStale()) return
          this.applyAnswerResponse(response, null)
        }
      } catch (error) {
        if (isAbortError(error) || isStale()) return

        // AIC-71 的失败路径：回滚这条回答，把原文还回输入框，轻提示可重发
        this.discardStreamedMessages()
        this.messages = this.messages.filter((item) => item.id !== userMessage.id)
        this.answeredQuestions = this.answeredQuestions.filter((item) => item !== answeredQuestion)
        this.errorMessage = getRequestErrorMessage(error)
        this.failedDraft = text
        throw error
      } finally {
        if (token === submitToken) {
          this.loading = false
          this.stageLabel = ''
          if (!this.isStreaming) {
            this.generating = false
          }
          if (activeStream === controller) activeStream = null
        }
      }
    },

    /** 用 done / 同步返回体收尾：贴题号、判定是否结束 */
    applyAnswerResponse(response: SubmitAnswerResponse, streamedMessageId: string | null) {
      if (response.is_finished || !response.next_question) {
        this.discardStreamedMessages()
        this.markFinished()
        return
      }

      const message = streamedMessageId
        ? this.messages.find((item) => item.id === streamedMessageId)
        : undefined

      if (message) {
        // delta 已经把题目逐字写出来了，这里只贴题号收尾；
        // 万一服务端没发 delta，用完整题目兜底
        if (!message.content.trim()) message.content = response.next_question
        message.questionNo = response.round_no
        message.streaming = false
      } else {
        this.messages.push({
          id: uuid(),
          role: 'ai',
          questionNo: response.round_no,
          content: response.next_question,
          createdAt: new Date().toISOString(),
        })
      }

      this.info.currentQuestionNo = response.round_no
      this.isStreaming = false
      this.generating = false
    },

    /** 结束面试 / 离开房间时断开流，别让 SSE 一直挂着 */
    cancelStream() {
      submitToken += 1
      activeStream?.abort()
      activeStream = null

      this.discardStreamedMessages()
      this.isStreaming = false
      this.generating = false
      this.stageLabel = ''
      this.loading = false
    },

    discardStreamedMessages() {
      if (!this.messages.some((item) => item.streaming)) return
      this.messages = this.messages.filter((item) => !item.streaming)
    },

    async finishInterview() {
      this.cancelStream()
      if (this.info.status === 'finished') return

      this.loading = true
      try {
        if (this.info.sessionId !== 'demo-session') {
          await finishInterviewApi(this.info.sessionId)
        }
        this.markFinished()
      } finally {
        this.loading = false
      }
    },

    markFinished() {
      this.info.status = 'finished'
      this.isStreaming = false
      this.generating = false
      this.stageLabel = ''
      const alreadyHasFinishMessage = this.messages.some((item) => item.content === finishMessage)
      if (!alreadyHasFinishMessage) {
        this.messages.push({
          id: uuid(),
          role: 'ai',
          content: finishMessage,
          createdAt: new Date().toISOString(),
        })
      }
    },
  },
})

const isAbortError = (error: unknown) =>
  typeof error === 'object' && error !== null && (error as { name?: string }).name === 'AbortError'

const getRequestErrorMessage = (error: unknown) => {
  if (error instanceof SubmitAnswerStreamError) return error.detail
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
