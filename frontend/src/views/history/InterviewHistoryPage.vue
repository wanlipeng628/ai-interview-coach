<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p>面试历史</p>
        <h1>历史记录与报告入口</h1>
      </div>
      <el-button type="primary" @click="router.push('/mock-interview')">
        开始新面试
      </el-button>
    </header>

    <el-alert
      v-if="history.errorMessage"
      :title="history.errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <ChartCard title="成绩趋势" subtitle="最近 5 次已生成报告的面试表现">
      <LineTrendChart v-if="history.trend.length > 0" :data="history.trend" />
      <el-empty v-else description="暂无可展示的成绩趋势" />
    </ChartCard>

    <HistoryRecordTable
      :records="history.records"
      :loading="history.loading"
      @detail="handleDetail"
      @continue="handleContinue"
      @report="handleReport"
      @delete="handleDelete"
      @validity="handleValidity"
    />

    <InterviewReviewDrawer
      :visible="reviewVisible"
      :loading="history.loadingReview"
      :regenerating="regenerating"
      :review="history.currentReview"
      @close="handleCloseReview"
      @regenerate="handleRegenerate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import LineTrendChart from '@/components/charts/LineTrendChart.vue'
import ChartCard from '@/components/dashboard/ChartCard.vue'
import HistoryRecordTable from '@/components/history/HistoryRecordTable.vue'
import InterviewReviewDrawer from '@/components/history/InterviewReviewDrawer.vue'
import { useHistoryStore } from '@/stores/history.store'

const history = useHistoryStore()
const router = useRouter()
const reviewVisible = ref(false)
const regenerating = ref(false)

const handleDetail = async (sessionId: string) => {
  reviewVisible.value = true
  await history.fetchReview(sessionId)
}

const handleRegenerate = async () => {
  if (!history.currentReview) return
  regenerating.value = true
  try {
    await history.regenerateReview(history.currentReview.sessionId)
    ElMessage.success('复盘已重新生成')
  } catch {
    ElMessage.error('重新生成失败，请稍后重试')
  } finally {
    regenerating.value = false
  }
}

const handleCloseReview = () => {
  reviewVisible.value = false
  history.clearReview()
}

const handleContinue = (sessionId: string) => {
  router.push(`/mock-interview/${sessionId}`)
}

const handleReport = (sessionId: string) => {
  router.push(`/report/${sessionId}`)
}

const handleDelete = async (sessionId: string) => {
  await ElMessageBox.confirm('确认删除这条面试记录吗？删除后不会在历史列表展示。', '删除确认', {
    type: 'warning',
  })
  await history.deleteRecord(sessionId)
  ElMessage.success('面试记录已删除')
}

const handleValidity = async (sessionId: string, isValid: boolean) => {
  await history.updateValidity(sessionId, isValid)
  ElMessage.success(isValid ? '已标记为有效记录' : '已标记为无效记录')
}

onMounted(() => {
  history.fetchHistory()
})
</script>

<style scoped lang="scss">
.page {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-radius: 8px;
  background: #fff;

  p {
    margin: 0 0 8px;
    color: #2f6bff;
    font-weight: 800;
  }

  h1 {
    margin: 0;
    font-size: 24px;
  }
}
</style>
