import { defineStore } from 'pinia'

import {
  finishTrainingApi,
  getTrainingTaskApi,
  listTrainingTasksApi,
  startTrainingApi,
  submitTrainingAnswerApi,
  updateTrainingTaskStatusApi,
} from '@/api/training.api'
import type { TrainingMessage, TrainingPlan, TrainingTask } from '@/types/training'

export const useTrainingStore = defineStore('training', {
  state: () => ({
    loading: false,
    submitting: false,
    errorMessage: '',
    tasks: [] as TrainingTask[],
    currentTask: null as TrainingTask | null,
    currentSessionId: null as number | null,
    messages: [] as TrainingMessage[],
    latestFeedback: '',
    latestReferencePoints: [] as string[],
    latestSampleAnswer: '',
    isFinished: false,
  }),

  getters: {
    plan: (state): TrainingPlan => ({
      title: '薄弱点训练清单',
      description:
        state.tasks.length > 0
          ? '这些任务来自你的面试报告和问答复盘，建议优先处理高优先级问题。'
          : '完成一次面试并生成报告后，系统会自动沉淀训练任务。',
      estimatedTime: `${Math.max(state.tasks.length, 1)} 项`,
      topics: state.tasks.length,
    }),
  },

  actions: {
    async fetchTasks() {
      this.loading = true
      this.errorMessage = ''
      try {
        const list = await listTrainingTasksApi()
        this.tasks = list.map(mapTask)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
      } finally {
        this.loading = false
      }
    },

    async fetchTaskDetail(taskId: number) {
      this.loading = true
      this.errorMessage = ''
      try {
        const task = await getTrainingTaskApi(taskId)
        this.currentTask = mapTask(task)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateTaskStatus(taskId: number, status: TrainingTask['status']) {
      await updateTrainingTaskStatusApi(taskId, status)
      const task = this.tasks.find((item) => item.id === taskId)
      if (task) {
        task.status = status
      }
    },

    async startTraining(taskId: number) {
      this.loading = true
      this.errorMessage = ''
      this.latestFeedback = ''
      this.latestReferencePoints = []
      this.latestSampleAnswer = ''
      try {
        const response = await startTrainingApi(taskId)
        this.currentTask = mapTask(response.task)
        this.currentSessionId = response.session_id
        this.messages = response.messages.map(mapMessage)
        this.isFinished = response.task.status === 'DONE'
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async submitTrainingAnswer(answer: string) {
      if (!this.currentSessionId || this.submitting) return
      this.submitting = true
      this.errorMessage = ''
      try {
        const response = await submitTrainingAnswerApi(this.currentSessionId, answer)
        this.messages = response.messages.map(mapMessage)
        this.latestFeedback = response.feedback
        this.latestReferencePoints = response.reference_points
        this.latestSampleAnswer = response.sample_answer
        this.isFinished = response.is_finished
        if (this.currentTask && response.is_finished) {
          this.currentTask.status = 'DONE'
        }
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.submitting = false
      }
    },

    async finishTraining() {
      if (!this.currentSessionId) return
      await finishTrainingApi(this.currentSessionId)
      this.isFinished = true
      if (this.currentTask) {
        this.currentTask.status = 'DONE'
      }
    },
  },
})

const mapTask = (item: {
  id: number
  title: string
  source_session_id?: string | null
  has_report?: boolean
  reason?: string | null
  severity: string
  status: string
  create_time: string
  latest_session_id?: number | null
  latest_session_status?: string | null
}): TrainingTask => ({
  id: item.id,
  title: item.title,
  sourceSessionId: item.source_session_id,
  hasReport: Boolean(item.has_report),
  reason: item.reason,
  severity: item.severity,
  status: normalizeStatus(item.status),
  createTime: item.create_time,
  latestSessionId: item.latest_session_id,
  latestSessionStatus: item.latest_session_status,
})

const mapMessage = (item: {
  id: number
  role: string
  content: string
  round_no: number
  feedback?: string | null
  reference_points: string[]
  sample_answer?: string | null
  create_time: string
}): TrainingMessage => ({
  id: item.id,
  role: item.role === 'USER' ? 'USER' : 'AI_COACH',
  content: item.content,
  roundNo: item.round_no,
  feedback: item.feedback,
  referencePoints: item.reference_points ?? [],
  sampleAnswer: item.sample_answer,
  createTime: item.create_time,
})

const normalizeStatus = (status: string): TrainingTask['status'] => {
  if (status === 'IN_PROGRESS' || status === 'DONE') return status
  return 'TODO'
}

const getErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    return response?.data?.detail ?? '训练任务加载失败'
  }
  return '训练任务加载失败'
}
