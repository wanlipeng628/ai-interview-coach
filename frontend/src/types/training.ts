export interface TrainingTask {
  id: number
  title: string
  sourceSessionId?: string | null
  hasReport: boolean
  reason?: string | null
  severity: string
  status: 'TODO' | 'IN_PROGRESS' | 'DONE'
  createTime: string
  latestSessionId?: number | null
  latestSessionStatus?: string | null
}

export interface TrainingMessage {
  id: number
  role: 'AI_COACH' | 'USER'
  content: string
  roundNo: number
  feedback?: string | null
  referencePoints: string[]
  sampleAnswer?: string | null
  createTime: string
}

export interface TrainingTopic {
  id: string
  title: string
  description: string
  progress: number
  difficulty: string
  duration: string
}

export interface TrainingPlan {
  title: string
  description: string
  estimatedTime: string
  topics: number
}
