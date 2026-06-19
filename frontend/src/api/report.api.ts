import request from './request'

export interface BackendWeaknessPoint {
  name: string
  reason: string
  severity: string
}

export interface BackendTrainingItem {
  title: string
  description: string
  priority: string
}

export interface BackendReportEvidenceItem {
  title: string
  related_weakness: string
  question: string
  answer_summary: string
  evidence_reason: string
  impact: string
}

export interface BackendInterviewReport {
  session_id: string
  overall_score: number
  technical_analysis: string
  communication_analysis: string
  project_analysis: string
  weakness_points: BackendWeaknessPoint[]
  improvement_suggestions: BackendTrainingItem[]
  recommended_training: BackendTrainingItem[]
  evidence_items: BackendReportEvidenceItem[]
  raw_report_json: Record<string, unknown>
}

export interface BackendInterviewReportListItem {
  session_id: string
  job_role: string
  overall_score: number
  report_time: string
  interview_status: string
  report_status: string
}

export const listInterviewReportsApi = () =>
  request.get<BackendInterviewReportListItem[], BackendInterviewReportListItem[]>('/interview/reports')

export const getInterviewReportApi = (sessionId: string) =>
  request.get<BackendInterviewReport, BackendInterviewReport>(`/interview/${sessionId}/report`)

export const generateInterviewReportApi = (sessionId: string) =>
  request.post<BackendInterviewReport, BackendInterviewReport>(
    `/interview/${sessionId}/report/generate`,
  )
