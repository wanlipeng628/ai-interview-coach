<template>
  <el-card shadow="never" class="history-card">
    <template #header><h2>面试记录</h2></template>
    <el-table :data="records" :loading="loading">
      <el-table-column prop="jobRole" label="岗位" min-width="170" />
      <el-table-column label="开始时间" min-width="150">
        <template #default="{ row }">
          {{ formatTime(row.startedAt) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row)">{{ row.statusText }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="回答轮次" width="100">
        <template #default="{ row }">{{ row.answeredCount }} 轮</template>
      </el-table-column>
      <el-table-column label="时长" width="110">
        <template #default="{ row }">{{ row.durationMinutes }} 分钟</template>
      </el-table-column>
      <el-table-column label="分数" width="90">
        <template #default="{ row }">
          <strong v-if="row.overallScore !== null" :class="{ low: row.overallScore < 70 }">
            {{ Math.round(row.overallScore) }}
          </strong>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$emit('detail', row.sessionId)">
            查看详情
          </el-button>
          <el-button v-if="row.status === 'IN_PROGRESS'" link type="primary" @click="$emit('continue', row.sessionId)">
            继续面试
          </el-button>
          <el-button v-else-if="row.hasReport" link type="primary" @click="$emit('report', row.sessionId)">
            查看报告
          </el-button>
          <el-button v-else link type="primary" @click="$emit('report', row.sessionId)">
            生成报告
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import type { HistoryRecord } from '@/types/history'

defineProps<{
  records: HistoryRecord[]
  loading: boolean
}>()

defineEmits<{
  detail: [sessionId: string]
  continue: [sessionId: string]
  report: [sessionId: string]
}>()

const formatTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const getStatusTagType = (row: HistoryRecord) => {
  if (row.hasReport) return 'success'
  if (row.status === 'FINISHED') return 'warning'
  if (row.status === 'IN_PROGRESS') return 'primary'
  return 'info'
}
</script>

<style scoped lang="scss">
.history-card {
  border: 0;
  border-radius: 8px;
}

h2 {
  margin: 0;
  font-size: 17px;
}

strong {
  color: #17a568;
}

.low {
  color: #e26a2c;
}

.muted {
  color: #98a2b3;
}
</style>
