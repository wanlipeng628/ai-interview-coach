import { defineStore } from 'pinia'

import {
  finalizeResumeAssistantApi,
  getResumeAssistantApi,
  startResumeAssistantApi,
  submitResumeAnswerApi,
} from '@/api/resumeAssistant.api'
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
  starting: boolean
  submitting: boolean
  finalizing: boolean
  errorMessage: string
  result: ResumeResult | null
}

const normalizeSections = (value: unknown): ResumeSection[] => {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => String(item).toUpperCase())
    .filter((key): key is ResumeSection => RESUME_SECTIONS.some((item) => item.key === key))
}

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
    if (detail) return detail
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
    starting: false,
    submitting: false,
    finalizing: false,
    errorMessage: '',
    result: null,
  }),

  getters: {
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
        completed: normalizeSections(progress?.completed),
        current: toStage(progress?.current, this.stage),
      }
      this.stage = this.progress.current
    },

    async start(targetRole?: string, title?: string) {
      if (this.starting) return
      this.starting = true
      this.errorMessage = ''
      this.result = null
      try {
        const response = await startResumeAssistantApi({
          target_role: targetRole?.trim() || undefined,
          title: title?.trim() || undefined,
        })
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

    async restore(draftId: string) {
      if (this.starting) return
      this.starting = true
      this.errorMessage = ''
      this.result = null
      try {
        const detail = await getResumeAssistantApi(draftId)
        this.draftId = detail.draft_id
        this.status = detail.status
        this.stage = toStage(detail.stage, 'BASIC')
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
        this.readyToFinalize = detail.ready_to_finalize ?? this.progress.current === 'DONE'
      } catch (error) {
        this.errorMessage = getErrorMessage(error, '无法恢复简历引导记录')
        throw error
      } finally {
        this.starting = false
      }
    },

    async sendAnswer(raw: string) {
      const text = raw.trim()
      if (!text || this.busy) return

      // 生成指令由后端统一判定：原话照常提交，命中时后端返回 question=null + ready_to_finalize=true
      this.pushUserMessage(text)
      this.submitting = true
      this.errorMessage = ''
      try {
        const response = await submitResumeAnswerApi(this.draftId, { answer: text })
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

    async finalize() {
      if (this.finalizing) return
      this.finalizing = true
      this.errorMessage = ''
      try {
        const response = await finalizeResumeAssistantApi(this.draftId)
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
  },
})
