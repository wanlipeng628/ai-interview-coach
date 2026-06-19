export interface HistoryRecord {
  sessionId: string
  jobRole: string
  status: string
  statusText: string
  currentRound: number
  messageCount: number
  answeredCount: number
  durationMinutes: number
  startedAt: string
  endedAt: string | null
  hasReport: boolean
  overallScore: number | null
}

export interface InterviewReviewRound {
  roundNo: number
  question: string
  answer: string
  evaluation: string
  referencePoints: string[]
  sampleAnswer: string
  level: 'good' | 'normal' | 'weak'
}

export interface InterviewReview {
  sessionId: string
  jobRole: string
  status: string
  startedAt: string
  endedAt: string | null
  answeredCount: number
  hasReport: boolean
  rounds: InterviewReviewRound[]
}
