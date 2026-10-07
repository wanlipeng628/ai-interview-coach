import { defineStore } from 'pinia'

import {
  finalizeResumeAssistantApi,
  getResumeAssistantApi,
  startResumeAssistantApi,
  submitResumeAnswerApi,
} from '@/api/resumeAssistant.api'
import {
  mockFinalizeResumeAssistant,
  mockGetResumeAssistant,
  mockStartResumeAssistant,
  mockSubmitResumeAnswer,
} from '@/api/resumeAssistant.mock'
import type {
  AssistantMessage,
  AssistantProgress,
  ResumeResult,
  ResumeSection,
  ResumeStage,
} from '@/types/resumeAssistant'
import { RESUME_SECTIONS } from '@/types/resumeAssistant'

import { uuid } from '@/utils/uuid'

interface ResumeAssistantState {
  draftId: string
  status: string
  stage: ResumeStage
  messages: AssistantMessage[]
  progress: AssistantProgress
  readyToFinalize: boolean
  usingMock: boolean
  starting: boolean
  submitting: boolean
  finalizing: boolean
  errorMessage: string
  result: ResumeResult | null
}

// 用户以自然语言要求生成时，跳过本轮问答直接生成
const FINALIZE_PATTERN = /帮我生成|生成简历|生成吧|生成出来|可以生成/

// 后端 /api/resume/assistant/* 未就绪（404/405）或不可达时回退到本地演示数据
const isBackendUnavailable = (error: unknown): boolean => {
  if (typeof error !== 'object' || error === null) return false
  const response = (error as { response?: { status?: number } }).response
  if (!response) return true
  return response.status === 404 || response.status === 405
}

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const response = (error as { response?: { status?: number; data?: { detail?: string } } }).response
    if (response?.data?.detail) return response.data.detail
    if (isBackendUnavailable(error)) return '后端简历助手接口未就绪，已使用本地演示数据'
  }
  return fallback
}

const toStage = (value: string | undefined, fallback: ResumeStage): ResumeStage => {
  const stage = String(value || '').toUpperCase()
  if (stage === 'DONE') return 'DONE'
  return RESUME_SECTIONS.some((item) => item.key === stage) ? (stage as ResumeSection) : fallback
}

export const useResumeAssistantStore = defineStore('resumeAssistant', {
  state: (): ResumeAssistantState => ({
    draftId: '',
    status: '',
    stage: 'BASIC',
    messages: [],
    progress: { completed: [], current: 'BASIC' },
    readyToFinalize: false,
    usingMock: false,
    starting: false,
    submitting: false,
    finalizing: false,
    errorMessage: '',
    result: null,
  }),

  getters: {
    progressPercent: (state) =>
      Math.round((state.progress.completed.length / RESUME_SECTIONS.length) * 100),
    busy: (state) => state.starting || state.submitting || state.finalizing,
  },

  actions: {
    pushUserMessage(content: string) {
      this.messages.push({
        id: uuid(),
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      })
    },

    pushAiMessage(content: string, hint?: string | null) {
      this.messages.push({
        id: uuid(),
        role: 'ai',
        content,
        hint: hint ?? null,
        createdAt: new Date().toISOString(),
      })
    },

    applyProgress(progress: AssistantProgress) {
      this.progress = {
        completed: progress?.completed ?? [],
        current: progress?.current ?? this.stage,
      }
      this.stage = this.progress.current
    },

    async start(targetRole?: string, title?: string) {
      if (this.starting) return
      this.starting = true
      this.errorMessage = ''
      this.result = null
      try {
        const response = await this.callStart(targetRole, title)
        this.draftId = response.draft_id
        this.status = response.status
        this.stage = toStage(response.stage, 'BASIC')
        this.readyToFinalize = false
        this.messages = []
        if (response.question) this.pushAiMessage(response.question, response.hint)
        this.applyProgress(response.progress)
      } catch (error) {
        this.errorMessage = getErrorMessage(error, '无法开始简历引导，请稍后重试')
        throw error
      } finally {
        this.starting = false
      }
    },

    async callStart(targetRole?: string, title?: string) {
      try {
        const response = await startResumeAssistantApi({
          target_role: targetRole?.trim() || undefined,
          title: title?.trim() || undefined,
        })
        this.usingMock = false
        return response
      } catch (error) {
        if (!isBackendUnavailable(error)) throw error
        this.usingMock = true
        return mockStartResumeAssistant({ target_role: targetRole, title })
      }
    },

    async restore(draftId: string) {
      if (this.starting) return
      this.starting = true
      this.errorMessage = ''
      this.result = null
      try {
        const detail = await this.callDetail(draftId)
        this.draftId = detail.draft_id
        this.status = detail.status
        this.usingMock = draftId.startsWith('mock-')
        this.messages = (detail.messages ?? [])
          .filter((item) => item.content?.trim())
          .map((item) => ({
            id: uuid(),
            role: item.role === 'USER' || item.role === 'user' ? 'user' : 'ai',
            content: item.content,
            hint: item.hint ?? null,
            createdAt: item.created_at || new Date().toISOString(),
          }))
        this.applyProgress(detail.progress)
        this.readyToFinalize = this.progress.current === 'DONE'
      } catch (error) {
        this.errorMessage = getErrorMessage(error, '无法恢复简历引导记录')
        throw error
      } finally {
        this.starting = false
      }
    },

    async callDetail(draftId: string) {
      try {
        const response = await getResumeAssistantApi(draftId)
        this.usingMock = false
        return response
      } catch (error) {
        if (!isBackendUnavailable(error) || !draftId.startsWith('mock-')) throw error
        return mockGetResumeAssistant(draftId)
      }
    },

    async sendAnswer(raw: string) {
      const text = raw.trim()
      if (!text || this.busy) return
      this.pushUserMessage(text)

      if (FINALIZE_PATTERN.test(text)) {
        await this.finalize()
        return
      }

      this.submitting = true
      this.errorMessage = ''
      try {
        const response = await this.callAnswer(text)
        this.readyToFinalize = response.ready_to_finalize
        this.applyProgress(response.progress)
        if (response.question) {
          this.pushAiMessage(response.question, response.hint)
        } else if (response.ready_to_finalize) {
          this.pushAiMessage('信息已经收集完整，点击下方「生成简历」即可生成你的简历。')
        }
      } catch (error) {
        this.errorMessage = getErrorMessage(error, '提交回答失败，请稍后重试')
        throw error
      } finally {
        this.submitting = false
      }
    },

    async callAnswer(answer: string) {
      try {
        const response = await submitResumeAnswerApi(this.draftId, { answer })
        this.usingMock = false
        return response
      } catch (error) {
        if (!isBackendUnavailable(error) || !this.usingMock) throw error
        return mockSubmitResumeAnswer(this.draftId, answer)
      }
    },

    async finalize() {
      if (this.finalizing) return
      this.finalizing = true
      this.errorMessage = ''
      try {
        const response = await this.callFinalize()
        this.result = {
          draftId: response.draft_id,
          profileId: response.profile_id,
          title: response.title,
          content: response.content,
          summary: response.summary,
        }
        this.readyToFinalize = true
      } catch (error) {
        this.errorMessage = getErrorMessage(error, '生成简历失败，请稍后重试')
        throw error
      } finally {
        this.finalizing = false
      }
    },

    async callFinalize() {
      try {
        const response = await finalizeResumeAssistantApi(this.draftId)
        this.usingMock = false
        return response
      } catch (error) {
        if (!isBackendUnavailable(error) || !this.usingMock) throw error
        return mockFinalizeResumeAssistant(this.draftId)
      }
    },

    closeResult() {
      this.result = null
    },
  },
})

export { FINALIZE_PATTERN }
