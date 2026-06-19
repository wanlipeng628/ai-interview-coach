import { defineStore } from 'pinia'

import type {
  AbilityScore,
  InterviewRecord,
  TrainingMetric,
  TrendPoint,
  WeakKnowledgePoint,
} from '@/types/dashboard'

interface DashboardState {
  userName: string
  targetRole: string
  readinessScore: number
  trainingMetrics: TrainingMetric[]
  scoreTrend: TrendPoint[]
  abilities: AbilityScore[]
  weakPoints: WeakKnowledgePoint[]
  recentRecords: InterviewRecord[]
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => ({
    userName: '程序员小林',
    targetRole: 'Java 后端工程师',
    readinessScore: 72,
    trainingMetrics: [
      { label: '今日训练', value: '3 组', trend: '+1 组', tone: 'blue' },
      { label: '训练时长', value: '86 分钟', trend: '+24 分钟', tone: 'green' },
      { label: '新增错题', value: '5 道', trend: '-2 道', tone: 'orange' },
      { label: '连续打卡', value: '12 天', trend: '稳定', tone: 'purple' },
    ],
    scoreTrend: [
      { date: '05-20', score: 58 },
      { date: '05-24', score: 62 },
      { date: '05-28', score: 65 },
      { date: '06-01', score: 61 },
      { date: '06-05', score: 69 },
      { date: '06-09', score: 73 },
      { date: '06-13', score: 68 },
      { date: '06-16', score: 76 },
    ],
    abilities: [
      { name: 'Java 基础', value: 80 },
      { name: '并发编程', value: 58 },
      { name: 'JVM', value: 60 },
      { name: 'Redis', value: 78 },
      { name: 'MySQL', value: 72 },
      { name: 'MQ', value: 65 },
    ],
    weakPoints: [
      { name: 'CAS 机制', description: '概念理解偏浅，缺少 ABA 问题展开', riskLevel: '高风险', score: 40 },
      { name: 'Redis 持久化', description: 'RDB/AOF 取舍表达不完整', riskLevel: '高风险', score: 45 },
      { name: 'AQS 原理', description: '同步队列和等待队列关系不清晰', riskLevel: '中风险', score: 52 },
      { name: 'MQ 幂等性', description: '缺少业务唯一键和去重表方案', riskLevel: '中风险', score: 55 },
      { name: 'JVM 内存模型', description: '运行时数据区和 GC 关联不足', riskLevel: '低风险', score: 60 },
    ],
    recentRecords: [
      { id: '1', company: '字节跳动', role: 'Java 开发工程师', date: '2026-06-16', score: 68, result: '待加强' },
      { id: '2', company: '阿里巴巴', role: 'Java 后端工程师', date: '2026-06-12', score: 72, result: '良好' },
      { id: '3', company: '腾讯', role: '后端开发工程师', date: '2026-06-08', score: 65, result: '待加强' },
      { id: '4', company: '美团', role: 'Java 开发工程师', date: '2026-06-02', score: 70, result: '良好' },
    ],
  }),
})
