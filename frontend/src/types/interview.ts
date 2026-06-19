export type InterviewRole = 'ai' | 'user'

export interface InterviewMessage {
  id: string
  role: InterviewRole
  content: string
  questionNo?: number
  createdAt: string
  streaming?: boolean
}

export interface AnsweredQuestion {
  questionNo: number
  title: string
  answeredAt: string
}

export interface InterviewInfo {
  sessionId: string
  jobRole: string
  currentQuestionNo: number
  totalQuestions: number
  durationLimitMinutes: number
  startedAt: number
  durationSeconds: number
  status: 'in_progress' | 'finished'
}
