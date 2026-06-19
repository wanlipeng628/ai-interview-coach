<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p>专项训练</p>
        <h1>针对薄弱点的训练计划</h1>
      </div>
      <el-button type="primary">生成今日计划</el-button>
    </header>

    <section class="grid">
      <TrainingPlanCard :plan="training.plan" />
      <ChartCard title="训练完成度">
        <BarProgressChart :data="training.topics" />
      </ChartCard>
    </section>

    <TrainingTopicList :topics="training.topics" />
  </div>
</template>

<script setup lang="ts">
import BarProgressChart from '@/components/charts/BarProgressChart.vue'
import ChartCard from '@/components/dashboard/ChartCard.vue'
import TrainingPlanCard from '@/components/training/TrainingPlanCard.vue'
import TrainingTopicList from '@/components/training/TrainingTopicList.vue'
import { useTrainingStore } from '@/stores/training.store'

const training = useTrainingStore()
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

.grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.8fr) minmax(0, 1.2fr);
  gap: 18px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
