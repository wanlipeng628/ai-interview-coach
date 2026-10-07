<template>
  <div class="page">
    <PageHeader eyebrow="能力画像" title="Java 面试能力全景图">
      <template #actions>
        <el-button>导出画像</el-button>
      </template>
    </PageHeader>

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
import PageHeader from '@/components/common/PageHeader.vue'
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

  .grid {
    gap: 12px;
  }
}
</style>
