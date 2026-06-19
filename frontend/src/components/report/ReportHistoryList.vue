<template>
  <el-card shadow="never" class="history-card">
    <template #header>
      <div class="header">
        <h2>历史报告</h2>
        <el-tag>{{ reports.length }} 份</el-tag>
      </div>
    </template>

    <el-scrollbar height="calc(100vh - 238px)">
      <el-skeleton v-if="loading" :rows="5" animated />
      <el-empty v-else-if="reports.length === 0" description="暂无历史报告" />
      <button
        v-for="item in reports"
        v-else
        :key="item.sessionId"
        class="report-item"
        :class="{ active: item.sessionId === activeSessionId }"
        type="button"
        @click="$emit('select', item.sessionId)"
      >
        <span class="role">{{ item.jobRole }}</span>
        <span class="time">{{ formatTime(item.reportTime) }}</span>
        <span class="score">{{ item.overallScore }} 分</span>
      </button>
    </el-scrollbar>
  </el-card>
</template>

<script setup lang="ts">
import type { ReportListItem } from '@/types/report'

defineProps<{
  reports: ReportListItem[]
  activeSessionId: string
  loading: boolean
}>()

defineEmits<{
  select: [sessionId: string]
}>()

const formatTime = (value: string) => {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped lang="scss">
.history-card {
  border: 0;
  border-radius: 8px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

h2 {
  margin: 0;
  font-size: 17px;
}

.report-item {
  position: relative;
  display: grid;
  width: 100%;
  gap: 6px;
  padding: 14px 48px 14px 14px;
  margin-bottom: 10px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #fff;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;

  &:hover,
  &.active {
    border-color: #2f6bff;
    background: #f5f8ff;
    box-shadow: 0 8px 22px rgba(47, 107, 255, 0.08);
  }
}

.role {
  font-weight: 700;
}

.time {
  color: #667085;
  font-size: 13px;
}

.score {
  position: absolute;
  top: 14px;
  right: 14px;
  color: #e26a2c;
  font-weight: 800;
}
</style>
