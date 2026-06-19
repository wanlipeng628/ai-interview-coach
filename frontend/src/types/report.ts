export interface ReportListItem {
  sessionId: string
  jobRole: string
  overallScore: number
  reportTime: string
  interviewStatus: string
  reportStatus: string
}

export interface ReportSummary {
  overallScore: number
  level: string
  percentile: number
  conclusion: string
}

export interface ReportAbility {
  name: string
  value: number
}

export interface ReportInsight {
  title: string
  content: string
  type: 'success' | 'warning' | 'danger'
}

export interface ReportEvidenceItem {
  title: string
  relatedWeakness: string
  question: string
  answerSummary: string
  evidenceReason: string
  impact: 'high' | 'medium' | 'low'
}

export interface TrainingSuggestion {
  title: string
  description: string
  priority: '高' | '中' | '低'
}
