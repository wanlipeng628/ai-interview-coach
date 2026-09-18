<template>
  <div class="dashboard-page">
    <WelcomePanel :user-name="dashboard.userName" @start="handleStartInterview" />

    <TrainingDataCards :metrics="dashboard.trainingMetrics" />

    <section class="dashboard-grid">
      <ChartCard title="最近面试成绩趋势图" subtitle="近 30 天综合面试表现">
        <LineTrendChart :data="dashboard.scoreTrend" />
      </ChartCard>

      <ChartCard title="能力雷达图" :subtitle="`综合准备度 ${dashboard.readinessScore} 分`">
        <AbilityRadarChart :data="dashboard.abilities" />
      </ChartCard>
    </section>

    <section class="dashboard-grid dashboard-grid--bottom">
      <WeakKnowledgeList :items="dashboard.weakPoints" />
      <RecentInterviewRecords :records="dashboard.recentRecords" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import AbilityRadarChart from '@/components/charts/AbilityRadarChart.vue'
import LineTrendChart from '@/components/charts/LineTrendChart.vue'
import ChartCard from '@/components/dashboard/ChartCard.vue'
import RecentInterviewRecords from '@/components/dashboard/RecentInterviewRecords.vue'
import TrainingDataCards from '@/components/dashboard/TrainingDataCards.vue'
import WeakKnowledgeList from '@/components/dashboard/WeakKnowledgeList.vue'
import WelcomePanel from '@/components/dashboard/WelcomePanel.vue'
import { useDashboardStore } from '@/stores/dashboard.store'

const dashboard = useDashboardStore()
const router = useRouter()

const handleStartInterview = () => {
  ElMessage.success('已进入模拟面试准备流程')
  router.push('/mock-interview')
}
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.dashboard-page {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(340px, 0.8fr);
  gap: 18px;

  &--bottom {
    grid-template-columns: minmax(360px, 0.85fr) minmax(0, 1.15fr);
  }
}

@media (max-width: 1180px) {
  .dashboard-grid,
  .dashboard-grid--bottom {
    grid-template-columns: 1fr;
  }
}

@include mobile {
  .dashboard-page {
    gap: 12px;
    padding: 14px;
  }

  .dashboard-grid {
    gap: 12px;
  }
}
</style>
