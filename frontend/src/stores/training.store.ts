import { defineStore } from 'pinia'

import type { TrainingPlan, TrainingTopic } from '@/types/training'

export const useTrainingStore = defineStore('training', {
  state: () => ({
    plan: {
      title: '并发编程冲刺训练',
      description: '系统强化 Java 面试中高频并发题，适合 3 天内集中突破。',
      estimatedTime: '2.5 小时',
      topics: 4,
    } satisfies TrainingPlan,
    topics: [
      { id: 'cas', title: 'CAS 机制', description: '原子操作、ABA 问题、Unsafe 与 Atomic 类。', progress: 35, difficulty: '中级', duration: '25 分钟' },
      { id: 'aqs', title: 'AQS 原理', description: '同步队列、独占锁、共享锁、Condition。', progress: 20, difficulty: '高级', duration: '35 分钟' },
      { id: 'pool', title: '线程池调优', description: '核心参数、拒绝策略、线上监控与隔离。', progress: 55, difficulty: '中级', duration: '30 分钟' },
      { id: 'lock', title: '锁优化方案', description: '锁粒度、读写锁、无锁化和热点拆分。', progress: 10, difficulty: '高级', duration: '40 分钟' },
    ] satisfies TrainingTopic[],
  }),
})
