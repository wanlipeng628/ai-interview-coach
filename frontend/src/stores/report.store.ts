import { defineStore } from 'pinia'

import {
  generateInterviewReportApi,
  getInterviewReportApi,
  listInterviewReportsApi,
  type BackendInterviewReport,
} from '@/api/report.api'
import type {
  ReportAbility,
  ReportEvidenceItem,
  ReportInsight,
  ReportListItem,
  ReportSummary,
  TrainingSuggestion,
} from '@/types/report'

const emptySummary: ReportSummary = {
  overallScore: 0,
  level: '暂无报告',
  percentile: 0,
  conclusion: '请选择一份历史报告，或完成一场面试后生成报告。',
}

export const useReportStore = defineStore('report', {
  state: () => ({
    loading: false,
    loadingList: false,
    generating: false,
    errorMessage: '',
    currentSessionId: '',
    reportList: [] as ReportListItem[],
    summary: { ...emptySummary },
    abilities: [
      { name: '技术能力', value: 0 },
      { name: '表达能力', value: 0 },
      { name: '项目能力', value: 0 },
      { name: '逻辑思维', value: 0 },
      { name: '抗压能力', value: 0 },
    ] satisfies ReportAbility[],
    insights: [] as ReportInsight[],
    evidences: [] as ReportEvidenceItem[],
    suggestions: [] as TrainingSuggestion[],
  }),

  getters: {
    currentReportMeta(state) {
      return state.reportList.find((item) => item.sessionId === state.currentSessionId)
    },
    hasReport(state) {
      return Boolean(state.currentSessionId)
    },
  },

  actions: {
    async initialize(preferredSessionId?: string) {
      this.loading = true
      await this.fetchReportList()
      if (preferredSessionId) {
        await this.loadOrGenerateReport(preferredSessionId)
        await this.fetchReportList()
        this.loading = false
        return
      }

      const latestGeneratedSessionId = this.reportList[0]?.sessionId
      if (latestGeneratedSessionId) {
        await this.selectReport(latestGeneratedSessionId)
        this.loading = false
        return
      }
      this.resetDetail()
      this.loading = false
    },

    async fetchReportList() {
      this.loadingList = true
      this.errorMessage = ''
      try {
        const list = await listInterviewReportsApi()
        this.reportList = list.map((item) => ({
          sessionId: item.session_id,
          jobRole: item.job_role,
          overallScore: Math.round(item.overall_score),
          reportTime: item.report_time,
          interviewStatus: item.interview_status,
          reportStatus: item.report_status,
        }))
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
      } finally {
        this.loadingList = false
      }
    },

    async selectReport(sessionId: string) {
      this.currentSessionId = sessionId
      await this.loadReport(sessionId)
    },

    async loadReport(sessionId: string) {
      this.loading = true
      this.errorMessage = ''
      try {
        const report = await getInterviewReportApi(sessionId)
        this.applyBackendReport(report)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        this.resetDetail()
      } finally {
        this.loading = false
      }
    },

    async loadOrGenerateReport(sessionId: string) {
      this.loading = true
      this.errorMessage = ''
      try {
        const report = await getInterviewReportApi(sessionId)
        this.currentSessionId = sessionId
        this.applyBackendReport(report)
      } catch (error) {
        if (isNotFoundError(error)) {
          await this.generateReport(sessionId)
          return
        }
        this.errorMessage = getErrorMessage(error)
      } finally {
        this.loading = false
      }
    },

    async generateReport(sessionId: string) {
      this.generating = true
      this.errorMessage = ''
      try {
        const report = await generateInterviewReportApi(sessionId)
        this.currentSessionId = sessionId
        this.applyBackendReport(report)
        await this.fetchReportList()
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        this.resetDetail()
      } finally {
        this.generating = false
      }
    },

    applyBackendReport(report: BackendInterviewReport) {
      const score = Math.round(report.overall_score)
      this.summary = {
        overallScore: score,
        level: getScoreLevel(score),
        percentile: Math.min(95, Math.max(10, score - 5)),
        conclusion: report.project_analysis || report.technical_analysis,
      }
      this.abilities = [
        { name: '技术能力', value: score },
        { name: '表达能力', value: clampScore(score - 5) },
        { name: '项目能力', value: clampScore(score + 3) },
        { name: '逻辑思维', value: clampScore(score - 2) },
        { name: '抗压能力', value: clampScore(score - 8) },
      ]
      this.insights = [
        {
          title: '技术能力分析',
          content: report.technical_analysis,
          type: evaluateInsightType(report.technical_analysis, score),
        },
        {
          title: '表达能力分析',
          content: report.communication_analysis,
          type: evaluateInsightType(report.communication_analysis, clampScore(score - 5)),
        },
        ...report.weakness_points.slice(0, 3).map((item) => ({
          title: item.name,
          content: item.reason,
          type: mapSeverity(item.severity),
        })),
      ]
      this.suggestions = [...report.improvement_suggestions, ...report.recommended_training]
        .slice(0, 5)
        .map((item) => ({
          title: item.title,
          description: item.description,
          priority: mapPriority(item.priority),
        }))
      this.evidences = (report.evidence_items ?? []).slice(0, 5).map((item) => ({
        title: item.title,
        relatedWeakness: item.related_weakness,
        question: item.question,
        answerSummary: item.answer_summary,
        evidenceReason: item.evidence_reason,
        impact: mapImpact(item.impact),
      }))
    },

    resetDetail() {
      this.currentSessionId = ''
      this.summary = { ...emptySummary }
      this.insights = []
      this.evidences = []
      this.suggestions = []
      this.abilities = this.abilities.map((item) => ({ ...item, value: 0 }))
    },
  },
})

const clampScore = (score: number) => Math.min(100, Math.max(0, Math.round(score)))

const getScoreLevel = (score: number) => {
  if (score >= 85) return '优秀'
  if (score >= 70) return '良好'
  if (score >= 60) return '中等'
  return '待提升'
}

const mapSeverity = (severity: string): ReportInsight['type'] => {
  const normalized = severity.toLowerCase()
  if (normalized === 'high' || severity === '高') return 'danger'
  return 'warning'
}

const evaluateInsightType = (content: string, score: number): ReportInsight['type'] => {
  const text = content.toLowerCase()
  const hasStrongNegative = strongNegativeKeywords.some((keyword) => text.includes(keyword))
  if (hasStrongNegative) return 'danger'

  const hasNegative = negativeKeywords.some((keyword) => text.includes(keyword))
  if (hasNegative) return 'warning'

  if (score >= 75) return 'success'
  if (score < 60) return 'danger'
  return 'warning'
}

const strongNegativeKeywords = [
  '完全无法',
  '无法回答',
  '严重不足',
  '明显薄弱',
  '明显不足',
  '不具备',
  '缺乏基本',
]

const negativeKeywords = [
  '不足',
  '薄弱',
  '不清楚',
  '不熟悉',
  '不了解',
  '缺少',
  '缺乏',
  '欠缺',
  '混乱',
  '笼统',
  '表面',
  '不够',
  '有待',
  '风险',
  '问题',
]

const mapPriority = (priority: string): TrainingSuggestion['priority'] => {
  const normalized = priority.toLowerCase()
  if (normalized === 'high' || priority === '高') return '高'
  if (normalized === 'low' || priority === '低') return '低'
  return '中'
}

const mapImpact = (impact: string): ReportEvidenceItem['impact'] => {
  const normalized = impact.toLowerCase()
  if (normalized === 'high' || impact === '高') return 'high'
  if (normalized === 'low' || impact === '低') return 'low'
  return 'medium'
}

const isNotFoundError = (error: unknown) =>
  typeof error === 'object' &&
  error !== null &&
  'response' in error &&
  (error as { response?: { status?: number } }).response?.status === 404

const getErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    return response?.data?.detail ?? '报告加载失败，请稍后重试'
  }
  return '报告加载失败，请确认后端服务和模型配置正常'
}
