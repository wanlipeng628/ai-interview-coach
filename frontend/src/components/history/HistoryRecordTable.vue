<template>
  <el-card shadow="never" class="history-card">
    <template #header><h2>面试记录</h2></template>
    <el-table :data="records" :loading="loading">
      <el-table-column prop="jobRole" label="岗位" min-width="150" />
      <el-table-column label="方向" min-width="110">
        <template #default="{ row }">{{ getDirectionText(row.direction) }}</template>
      </el-table-column>
      <el-table-column label="模式" min-width="100">
        <template #default="{ row }">{{ getModeText(row.interviewerMode) }}</template>
      </el-table-column>
      <el-table-column label="开始时间" min-width="150">
        <template #default="{ row }">{{ formatTime(row.startedAt) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row)">{{ row.statusText }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="有效" width="90">
        <template #default="{ row }">
          <el-tag :type="row.isValid ? 'success' : 'info'">
            {{ row.isValid ? '有效' : '无效' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="回答" width="90">
        <template #default="{ row }">{{ row.answeredCount }} 轮</template>
      </el-table-column>
      <el-table-column label="分数" width="90">
        <template #default="{ row }">
          <strong v-if="row.overallScore !== null" :class="{ low: row.overallScore < 70 }">
            {{ Math.round(row.overallScore) }}
          </strong>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$emit('detail', row.sessionId)">
            复盘
          </el-button>
          <el-button v-if="row.status === 'IN_PROGRESS'" link type="primary" @click="$emit('continue', row.sessionId)">
            继续
          </el-button>
          <el-button link type="primary" @click="$emit('report', row.sessionId)">
            {{ row.hasReport ? '报告' : '生成报告' }}
          </el-button>
          <el-button link type="warning" @click="$emit('validity', row.sessionId, !row.isValid)">
            {{ row.isValid ? '标记无效' : '标记有效' }}
          </el-button>
          <el-button link type="danger" @click="$emit('delete', row.sessionId)">
            删除
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
  delete: [sessionId: string]
  validity: [sessionId: string, isValid: boolean]
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

const getDirectionText = (value?: string | null) => {
  const map: Record<string, string> = {
    FULL_MOCK: '完整模拟',
    PROJECT_DEEP_DIVE: '项目深挖',
    JAVA_BASIC: 'Java基础',
    CONCURRENCY: '并发',
    JVM: 'JVM',
    MYSQL: 'MySQL',
    REDIS: 'Redis',
    SPRING: 'Spring',
    SYSTEM_DESIGN: '系统设计',
    TROUBLESHOOTING: '线上排查',
  }
  return value ? map[value] ?? value : '-'
}

const getModeText = (value?: string | null) => {
  const map: Record<string, string> = {
    GENTLE: '温和',
    NORMAL: '正常',
    STRICT: '严格',
    BIG_TECH_FIRST_ROUND: '大厂一面',
    PROJECT_DEEP_DIVE: '项目深挖',
  }
  return value ? map[value] ?? value : '-'
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
