import request from './request'

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
