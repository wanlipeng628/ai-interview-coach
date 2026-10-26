import request, { API_BASE_URL } from './request'
import { readSseStream } from '@/utils/sse'
import type { SseEvent } from '@/utils/sse'

export interface StartInterviewRequest {
  job_role: string
  direction?: string
  interviewer_mode?: string
  resume_text?: string
  duration_minutes?: number
}

export interface StartInterviewResponse {
  session_id: string
  first_question: string
}

export interface SubmitAnswerRequest {
  answer: string
}

export interface SubmitAnswerResponse {
  session_id: string
  round_no: number
  next_question: string | null
  is_finished: boolean
  decision: 'continue' | 'switch' | 'end'
  reason?: string | null
}

/** stage 事件：等待期间的阶段提示文案 */
export interface SubmitAnswerStageEvent {
  stage: string
  label: string
}

export interface SubmitAnswerDeltaEvent {
  text: string
}

export interface SubmitAnswerStreamHandlers {
  onStage?: (event: SubmitAnswerStageEvent) => void
  /** 题目正文的一片，直接追加到当前 AI 气泡 */
  onDelta?: (event: SubmitAnswerDeltaEvent) => void
}

/**
 * 流式问答的失败统一用它表达：HTTP 非 2xx、流内 error 事件、流意外中断。
 * 调用方据此回落同步接口，detail 用于最后的提示文案。
 */
export class SubmitAnswerStreamError extends Error {
  readonly detail: string

  constructor(detail: string) {
    super(detail)
    this.name = 'SubmitAnswerStreamError'
    this.detail = detail
  }
}

export interface FinishInterviewResponse {
  session_id: string
  is_finished: boolean
}

export interface InterviewSessionResponse {
  session_id: string
  job_role: string
  direction?: string | null
  interviewer_mode?: string | null
  status: string
  current_round: number
  duration_minutes: number
  started_at: string
}

export interface InterviewMessageResponse {
  role: string
  content: string
  round_no: number
  created_at: string
}

export interface InterviewHistoryItemResponse {
  session_id: string
  job_role: string
  direction?: string | null
  interviewer_mode?: string | null
  status: string
  current_round: number
  message_count: number
  answered_count: number
  duration_minutes: number
  started_at: string
  ended_at: string | null
  has_report: boolean
  is_valid: boolean
  overall_score: number | null
}

export interface LatestActiveInterviewResponse {
  has_active: boolean
  session_id?: string | null
  job_role?: string | null
  direction?: string | null
  interviewer_mode?: string | null
  started_at?: string | null
  answered_count: number
}

export interface SuccessResponse {
  success: boolean
}

export interface InterviewReviewRoundResponse {
  round_no: number
  question: string
  answer: string
  evaluation: string
  reference_points: string[]
  sample_answer: string
  level: 'good' | 'normal' | 'weak'
}

export interface InterviewReviewResponse {
  session_id: string
  job_role: string
  status: string
  started_at: string
  ended_at: string | null
  answered_count: number
  has_report: boolean
  rounds: InterviewReviewRoundResponse[]
}

export const startInterviewApi = (data: StartInterviewRequest) =>
  request.post<StartInterviewResponse, StartInterviewResponse>('/interview/start', data)

export const submitAnswerApi = (sessionId: string, data: SubmitAnswerRequest) =>
  request.post<SubmitAnswerResponse, SubmitAnswerResponse>(`/interview/${sessionId}/answer`, data)

const readStreamErrorDetail = async (response: Response) => {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload?.detail === 'string' && payload.detail.trim()) return payload.detail
  } catch {
    // 网关错误页之类的非 JSON 响应，没有 detail 可读
  }
  return `流式接口不可用（HTTP ${response.status}）`
}

const parseSseJson = <T>(raw: string): T | null => {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

const handleStreamEvent = (
  event: SseEvent,
  handlers: SubmitAnswerStreamHandlers,
): SubmitAnswerResponse | null => {
  if (event.event === 'stage') {
    const payload = parseSseJson<SubmitAnswerStageEvent>(event.data)
    if (payload?.label) handlers.onStage?.(payload)
    return null
  }

  if (event.event === 'delta') {
    const payload = parseSseJson<SubmitAnswerDeltaEvent>(event.data)
    if (payload?.text) handlers.onDelta?.(payload)
    return null
  }

  if (event.event === 'done') {
    const payload = parseSseJson<SubmitAnswerResponse>(event.data)
    if (!payload) throw new SubmitAnswerStreamError('流式返回格式异常，请重试')
    return payload
  }

  if (event.event === 'error') {
    const payload = parseSseJson<{ detail?: string }>(event.data)
    throw new SubmitAnswerStreamError(payload?.detail?.trim() || 'AI 生成失败，请稍后重试')
  }

  // 未知事件（心跳等）忽略
  return null
}

/**
 * POST + fetch 读 SSE：EventSource 只支持 GET，这里的问答必须带请求体。
 * 成功时返回 done 事件的完整返回体；HTTP 非 2xx、流内 error、流中断都抛
 * SubmitAnswerStreamError，网络错误与 abort 原样抛出，由调用方决定是否回落同步接口。
 */
export const submitAnswerStreamApi = async (
  sessionId: string,
  data: SubmitAnswerRequest,
  handlers: SubmitAnswerStreamHandlers = {},
  signal?: AbortSignal,
): Promise<SubmitAnswerResponse> => {
  const response = await fetch(`${API_BASE_URL}/interview/${sessionId}/answer/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(data),
    signal,
  })

  if (!response.ok) {
    throw new SubmitAnswerStreamError(await readStreamErrorDetail(response))
  }
  if (!response.body) {
    throw new SubmitAnswerStreamError('当前浏览器不支持流式响应')
  }

  const done = await readSseStream(response.body, (event) => handleStreamEvent(event, handlers))
  if (!done) {
    throw new SubmitAnswerStreamError('流式响应中断，正在改用普通模式重试')
  }
  return done
}

export const finishInterviewApi = (sessionId: string) =>
  request.post<FinishInterviewResponse, FinishInterviewResponse>(`/interview/${sessionId}/finish`)

export const getInterviewSessionApi = (sessionId: string) =>
  request.get<InterviewSessionResponse, InterviewSessionResponse>(`/interview/${sessionId}`)

export const listInterviewMessagesApi = (sessionId: string) =>
  request.get<InterviewMessageResponse[], InterviewMessageResponse[]>(`/interview/${sessionId}/messages`)

export const listInterviewHistoryApi = (includeEmpty = false) =>
  request.get<InterviewHistoryItemResponse[], InterviewHistoryItemResponse[]>('/interview/history', {
    params: { include_empty: includeEmpty },
  })

export const getInterviewReviewApi = (sessionId: string) =>
  request.get<InterviewReviewResponse, InterviewReviewResponse>(`/interview/${sessionId}/review`)

export const regenerateInterviewReviewsApi = (sessionId: string) =>
  request.post<SuccessResponse, SuccessResponse>(`/interview/${sessionId}/reviews/regenerate`)

export const getLatestActiveInterviewApi = () =>
  request.get<LatestActiveInterviewResponse, LatestActiveInterviewResponse>('/interview/latest-active')

export const deleteInterviewApi = (sessionId: string) =>
  request.delete<SuccessResponse, SuccessResponse>(`/interview/${sessionId}`)

export const updateInterviewValidityApi = (sessionId: string, isValid: boolean) =>
  request.patch<SuccessResponse, SuccessResponse>(`/interview/${sessionId}/validity`, {
    is_valid: isValid,
  })
