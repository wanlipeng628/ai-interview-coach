import { defineStore } from 'pinia'

import { getInterviewReviewApi, listInterviewHistoryApi } from '@/api/interview.api'
import type { TrendPoint } from '@/types/dashboard'
import type { HistoryRecord, InterviewReview } from '@/types/history'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    loading: false,
    loadingReview: false,
    errorMessage: '',
    records: [] as HistoryRecord[],
    trend: [] as TrendPoint[],
    currentReview: null as InterviewReview | null,
  }),

  actions: {
    async fetchHistory(includeEmpty = false) {
      this.loading = true
      this.errorMessage = ''
      try {
        const list = await listInterviewHistoryApi(includeEmpty)
        this.records = list.map((item) => ({
          sessionId: item.session_id,
          jobRole: item.job_role,
          status: item.status,
          statusText: getStatusText(item.status, item.has_report),
          currentRound: item.current_round,
          messageCount: item.message_count,
          answeredCount: item.answered_count,
          durationMinutes: item.duration_minutes,
          startedAt: item.started_at,
          endedAt: item.ended_at,
          hasReport: item.has_report,
          overallScore: item.overall_score,
        }))
        this.trend = this.records
          .filter((item) => item.overallScore !== null)
          .slice()
          .reverse()
          .slice(-5)
          .map((item) => ({
            date: formatShortDate(item.startedAt),
            score: item.overallScore ?? 0,
          }))
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
      } finally {
        this.loading = false
      }
    },

    async fetchReview(sessionId: string) {
      this.loadingReview = true
      this.errorMessage = ''
      try {
        const review = await getInterviewReviewApi(sessionId)
        this.currentReview = {
          sessionId: review.session_id,
          jobRole: review.job_role,
          status: review.status,
          startedAt: review.started_at,
          endedAt: review.ended_at,
          answeredCount: review.answered_count,
          hasReport: review.has_report,
          rounds: review.rounds.map((item) => ({
            roundNo: item.round_no,
            question: item.question,
            answer: item.answer,
            evaluation: item.evaluation,
            referencePoints: item.reference_points,
            sampleAnswer: item.sample_answer,
            level: item.level,
          })),
        }
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        this.currentReview = null
      } finally {
        this.loadingReview = false
      }
    },

    clearReview() {
      this.currentReview = null
    },
  },
})

const getStatusText = (status: string, hasReport: boolean) => {
  if (hasReport) return '已生成报告'
  if (status === 'FINISHED') return '已结束'
  if (status === 'IN_PROGRESS') return '进行中'
  if (status === 'CANCELLED') return '已取消'
  return status
}

const formatShortDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const getErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    return response?.data?.detail ?? '面试历史加载失败，请稍后重试'
  }
  return '面试历史加载失败，请确认后端服务正常'
}
