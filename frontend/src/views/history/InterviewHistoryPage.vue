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
    />

    <InterviewReviewDrawer
      :visible="reviewVisible"
      :loading="history.loadingReview"
      :review="history.currentReview"
      @close="handleCloseReview"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import LineTrendChart from '@/components/charts/LineTrendChart.vue'
import ChartCard from '@/components/dashboard/ChartCard.vue'
import HistoryRecordTable from '@/components/history/HistoryRecordTable.vue'
import InterviewReviewDrawer from '@/components/history/InterviewReviewDrawer.vue'
import { useHistoryStore } from '@/stores/history.store'

const history = useHistoryStore()
const router = useRouter()
const reviewVisible = ref(false)

const handleDetail = async (sessionId: string) => {
  reviewVisible.value = true
  await history.fetchReview(sessionId)
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
