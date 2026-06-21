import request from './request'

export interface TrainingTaskResponse {
  id: number
  title: string
  source_session_id?: string | null
  has_report: boolean
  reason?: string | null
  severity: string
  status: string
  create_time: string
}

export interface TrainingTaskDetailResponse extends TrainingTaskResponse {
  latest_session_id?: number | null
  latest_session_status?: string | null
}

export interface TrainingMessageResponse {
  id: number
  role: string
  content: string
  round_no: number
  feedback?: string | null
  reference_points: string[]
  sample_answer?: string | null
  create_time: string
}

export interface StartTrainingResponse {
  session_id: number
  task: TrainingTaskDetailResponse
  first_question: string
  messages: TrainingMessageResponse[]
}

export interface SubmitTrainingAnswerResponse {
  session_id: number
  round_no: number
  feedback: string
  reference_points: string[]
  sample_answer: string
  next_question?: string | null
  is_finished: boolean
  messages: TrainingMessageResponse[]
}

export interface SuccessResponse {
  success: boolean
}

export const listTrainingTasksApi = () =>
  request.get<TrainingTaskResponse[], TrainingTaskResponse[]>('/training/tasks')

export const getTrainingTaskApi = (taskId: number) =>
  request.get<TrainingTaskDetailResponse, TrainingTaskDetailResponse>(`/training/tasks/${taskId}`)

export const startTrainingApi = (taskId: number) =>
  request.post<StartTrainingResponse, StartTrainingResponse>(`/training/tasks/${taskId}/start`)

export const updateTrainingTaskStatusApi = (taskId: number, status: string) =>
  request.patch<SuccessResponse, SuccessResponse>(`/training/tasks/${taskId}/status`, { status })

export const submitTrainingAnswerApi = (sessionId: number, answer: string) =>
  request.post<SubmitTrainingAnswerResponse, SubmitTrainingAnswerResponse>(
    `/training/sessions/${sessionId}/answer`,
    { answer },
  )

export const finishTrainingApi = (sessionId: number) =>
  request.post<SuccessResponse, SuccessResponse>(`/training/sessions/${sessionId}/finish`)
