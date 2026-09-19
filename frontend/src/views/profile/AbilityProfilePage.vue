<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p>能力画像</p>
        <h1>Java 面试能力全景图</h1>
      </div>
      <el-button>导出画像</el-button>
    </header>

    <section class="grid">
      <ChartCard title="能力雷达">
        <AbilityRadarChart :data="profile.radar" />
      </ChartCard>
      <ChartCard title="掌握度分布">
        <DonutChart :data="profile.mastery" />
      </ChartCard>
    </section>

    <KnowledgeList :items="profile.knowledge" />
  </div>
</template>

<script setup lang="ts">
import AbilityRadarChart from '@/components/charts/AbilityRadarChart.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import ChartCard from '@/components/dashboard/ChartCard.vue'
import KnowledgeList from '@/components/profile/KnowledgeList.vue'
import { useProfileStore } from '@/stores/profile.store'

const profile = useProfileStore()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

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
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

@media (max-width: 1080px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@include mobile {
  .page {
    gap: 12px;
    padding: 14px;
  }

  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 18px;

    h1 {
      font-size: 20px;
    }

    .el-button {
      width: 100%;
    }
  }

  .grid {
    gap: 12px;
  }
}
</style>
