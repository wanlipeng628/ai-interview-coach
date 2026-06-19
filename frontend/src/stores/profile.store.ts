import { defineStore } from 'pinia'

import type { KnowledgeNode, MasterySlice, ProfileRadarItem } from '@/types/profile'

export const useProfileStore = defineStore('profile', {
  state: () => ({
    radar: [
      { name: 'Java 基础', value: 82 },
      { name: '并发编程', value: 58 },
      { name: 'JVM', value: 64 },
      { name: 'MySQL', value: 72 },
      { name: 'Redis', value: 76 },
      { name: '系统设计', value: 61 },
    ] satisfies ProfileRadarItem[],
    mastery: [
      { name: '熟练掌握', value: 38 },
      { name: '基本掌握', value: 42 },
      { name: '需要巩固', value: 20 },
    ] satisfies MasterySlice[],
    knowledge: [
      { name: 'Java 集合', score: 86, status: '掌握良好' },
      { name: 'Spring 事务', score: 74, status: '掌握良好' },
      { name: 'Redis 缓存一致性', score: 66, status: '需要巩固' },
      { name: 'JVM GC 调优', score: 62, status: '需要巩固' },
      { name: 'AQS 原理', score: 48, status: '薄弱' },
      { name: 'CAS 与 ABA', score: 42, status: '薄弱' },
    ] satisfies KnowledgeNode[],
  }),
})
