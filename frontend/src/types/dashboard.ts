export interface TrainingMetric {
  label: string
  value: string
  trend: string
  tone: 'blue' | 'green' | 'orange' | 'purple'
}

export interface TrendPoint {
  date: string
  score: number
}

export interface AbilityScore {
  name: string
  value: number
}

export interface WeakKnowledgePoint {
  name: string
  description: string
  riskLevel: '高风险' | '中风险' | '低风险'
  score: number
}

export interface InterviewRecord {
  id: string
  company: string
  role: string
  date: string
  score: number
  result: string
}
