<template>
  <el-card shadow="never" class="history-card">
    <template #header><h2>面试记录</h2></template>

    <!-- 桌面端（≥769px）：保持原有 el-table 结构 -->
    <el-table v-if="!isMobile" :data="records" :loading="loading">
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

    <!-- 移动端（≤768px）：卡片式布局，不使用横向滚动 -->
    <div v-else v-loading="loading" class="record-cards">
      <el-empty v-if="!loading && records.length === 0" description="暂无面试记录" />
      <article v-for="row in records" :key="row.sessionId" class="record-card">
        <header class="record-card__head">
          <h3>{{ row.jobRole || '未命名岗位' }}</h3>
          <el-tag :type="getStatusTagType(row)" size="small">{{ row.statusText }}</el-tag>
        </header>

        <dl class="record-card__meta">
          <div>
            <dt>方向</dt>
            <dd>{{ getDirectionText(row.direction) }}</dd>
          </div>
          <div>
            <dt>模式</dt>
            <dd>{{ getModeText(row.interviewerMode) }}</dd>
          </div>
          <div>
            <dt>开始时间</dt>
            <dd>{{ formatTime(row.startedAt) }}</dd>
          </div>
        </dl>

        <div class="record-card__stats">
          <span>回答 <strong class="count">{{ row.answeredCount }}</strong> 轮</span>
          <span>
            分数
            <strong
              v-if="row.overallScore !== null"
              :class="{ low: row.overallScore < 70 }"
            >
              {{ Math.round(row.overallScore) }}
            </strong>
            <span v-else class="muted">-</span>
          </span>
          <el-tag :type="row.isValid ? 'success' : 'info'" size="small">
            {{ row.isValid ? '有效' : '无效' }}
          </el-tag>
        </div>

        <div class="record-card__actions">
          <el-button size="small" type="primary" plain @click="$emit('detail', row.sessionId)">
            复盘
          </el-button>
          <el-button
            v-if="row.status === 'IN_PROGRESS'"
            size="small"
            type="primary"
            plain
            @click="$emit('continue', row.sessionId)"
          >
            继续
          </el-button>
          <el-button size="small" type="primary" plain @click="$emit('report', row.sessionId)">
            {{ row.hasReport ? '报告' : '生成报告' }}
          </el-button>
          <el-button
            size="small"
            type="warning"
            plain
            @click="$emit('validity', row.sessionId, !row.isValid)"
          >
            {{ row.isValid ? '标记无效' : '标记有效' }}
          </el-button>
          <el-button size="small" type="danger" plain @click="$emit('delete', row.sessionId)">
            删除
          </el-button>
        </div>
      </article>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { useMediaQuery } from '@/composables/useMediaQuery'
import type { HistoryRecord } from '@/types/history'

defineProps<{
  records: HistoryRecord[]
  loading: boolean
}>()

// 移动端改用卡片列表，桌面端 el-table 的 DOM 与样式完全不变
const isMobile = useMediaQuery('(max-width: 768px)')

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

.record-cards {
  display: grid;
  gap: 12px;
}

.record-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #fff;

  &__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;

    h3 {
      margin: 0;
      font-size: 16px;
      line-height: 1.4;
      word-break: break-word;
    }
  }

  &__meta {
    display: grid;
    gap: 6px;
    margin: 0;
    font-size: 13px;

    div {
      display: flex;
      gap: 8px;
    }

    dt {
      flex: none;
      width: 56px;
      color: #667085;
    }

    dd {
      margin: 0;
      color: #101828;
      word-break: break-word;
    }
  }

  &__stats {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #667085;
    font-size: 13px;

    strong {
      font-size: 15px;
    }

    // 轮数与分数同为 strong，轮数回到正文色，只有分数保留绿色
    .count {
      color: #101828;
    }
  }

  // 5 个操作按钮等宽铺开，窄屏自动折成两行，不依赖横向滚动
  &__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    :deep(.el-button) {
      flex: 1 1 auto;
      min-width: 88px;
      margin: 0;
    }
  }
}
</style>
