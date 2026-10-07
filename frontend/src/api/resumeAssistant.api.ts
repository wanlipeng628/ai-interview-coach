import request from './request'
import type { AssistantProgress, ResumeSection, ResumeStage } from '@/types/resumeAssistant'

export interface StartResumeAssistantRequest {
  target_role?: string
  title?: string
}

export interface ResumeAssistantStartResponse {
  draft_id: string
  status: string
  stage: ResumeStage
  question: string | null
  // 契约未固定 hint 字段，后端提供引导提示时按可选字段消费
  hint?: string | null
  progress: AssistantProgress
}

export interface SubmitResumeAnswerRequest {
  answer: string
}

export interface ResumeAssistantAnswerResponse {
  draft_id: string
  status: string
  stage: ResumeStage
  question: string | null
  hint?: string | null
  ready_to_finalize: boolean
  progress: AssistantProgress
}

export interface ResumeAssistantFinalizeResponse {
  draft_id: string
  profile_id: number | string | null
  title: string
  content: string
  summary: string
}

export interface ResumeAssistantMessageResponse {
  role?: string
  content: string
  hint?: string | null
  stage?: string
  created_at?: string
}

export interface ResumeAssistantDetailResponse {
  draft_id: string
  status: string
  stage: ResumeStage
  messages: ResumeAssistantMessageResponse[]
  sections: Record<string, unknown>
  progress: AssistantProgress
}

export const startResumeAssistantApi = (data: StartResumeAssistantRequest) =>
  request.post<ResumeAssistantStartResponse, ResumeAssistantStartResponse>(
    '/resume/assistant/start',
    data,
  )

export const submitResumeAnswerApi = (draftId: string, data: SubmitResumeAnswerRequest) =>
  request.post<ResumeAssistantAnswerResponse, ResumeAssistantAnswerResponse>(
    `/resume/assistant/${draftId}/answer`,
    data,
  )

export const finalizeResumeAssistantApi = (draftId: string) =>
  request.post<ResumeAssistantFinalizeResponse, ResumeAssistantFinalizeResponse>(
    `/resume/assistant/${draftId}/finalize`,
  )

export const getResumeAssistantApi = (draftId: string) =>
  request.get<ResumeAssistantDetailResponse, ResumeAssistantDetailResponse>(
    `/resume/assistant/${draftId}`,
  )

export type { ResumeSection, ResumeStage }
