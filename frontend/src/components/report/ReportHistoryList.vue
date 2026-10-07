<template>
  <el-card
    v-if="!isMobile || reports.length > 0"
    shadow="never"
    class="history-card card card--float"
    :class="{ 'history-card--collapsed': isMobile && !expanded }"
  >
    <template #header>
      <div class="header">
        <h2>历史报告</h2>
        <el-tag effect="light">{{ reports.length }} 份</el-tag>
        <!-- 折叠入口只在窄屏渲染，桌面端 #header 内仍只有 h2 + 计数标签，保持像素级一致 -->
        <el-button
          v-if="isMobile"
          class="header__toggle"
          link
          type="primary"
          :aria-expanded="expanded"
          @click="expanded = !expanded"
        >
          {{ expanded ? '收起' : '展开' }}
          <el-icon>
            <component :is="expanded ? ArrowUp : ArrowDown" />
          </el-icon>
        </el-button>
      </div>
    </template>

    <!-- 窄屏默认收起：历史列表在 DOM 顺序上先于报告正文，展开态会把它顶出首屏 -->
    <el-scrollbar v-if="!isMobile || expanded" height="calc(100vh - 238px)">
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
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { ref } from 'vue'

import { useMediaQuery } from '@/composables/useMediaQuery'
import type { ReportListItem } from '@/types/report'

defineProps<{
  reports: ReportListItem[]
  activeSessionId: string
  loading: boolean
}>()

defineEmits<{
  select: [sessionId: string]
}>()

// 折叠跟随本页单列断点（InterviewReportPage 的 ≤1180px），再被"桌面零改动"截断到 $desktop-min - 1。
// 不要按 $mobile-max(768) 改回去：769~1023 同样是单列、列表同样压在正文上方。
const isMobile = useMediaQuery('(max-width: 1023px)')
const expanded = ref(false)

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
@use '../../assets/styles/responsive' as *;

.history-card {
  height: 100%;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

h2 {
  margin: 0;
  font-size: var(--fs-lg);
  font-weight: var(--fw-semibold);
}

.report-item {
  position: relative;
  display: grid;
  width: 100%;
  gap: 6px;
  padding: 14px 48px 14px 14px;
  margin-bottom: 10px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  background: var(--c-bg-card);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;

  &:hover,
  &.active {
    border-color: var(--c-primary-500);
    background: var(--c-primary-50);
    box-shadow: 0 8px 22px rgba(47, 107, 255, 0.08);
  }
}

.role {
  font-weight: 600;
  color: var(--c-text-primary);
}

.time {
  color: var(--c-text-tertiary);
  font-size: 13px;
}

.score {
  position: absolute;
  top: 14px;
  right: 14px;
  color: var(--c-danger-text);
  font-weight: 700;
}

// 与 script 里的 useMediaQuery 同源：折叠跟随单列断点、被 $desktop-min 截断到 $desktop-min - 1px。
// JS 与 SCSS 是两个真值源，改一处必须同步另一处，否则会出现"CSS 折叠了但 JS 没折叠"。
@media (max-width: 1023px) {
  // 职位名保留了右侧 48px 给绝对定位的分数，长职位名兜住不溢出
  .role {
    overflow-wrap: anywhere;
  }

  .header {
    gap: 8px;
  }

  // 计数标签紧贴右侧折叠入口，避免 h2 / 标签 / 按钮三分天下
  .header :deep(.el-tag) {
    margin-left: auto;
  }

  .header__toggle {
    min-height: $touch-target;
  }

  // 折叠态 body 内不渲染滚动区（v-if），不收起内边距就会在标题下留一条空白
  .history-card--collapsed :deep(.el-card__body) {
    padding-top: 0;
    padding-bottom: 0;
  }
}
</style>
