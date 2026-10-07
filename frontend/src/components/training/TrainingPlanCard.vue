<template>
  <el-card shadow="never" class="plan-card card card--float">
    <PageHeader variant="plain" eyebrow="系统推荐" :title="plan.title" :description="plan.description" />
    <div class="meta">
      <strong>{{ plan.estimatedTime }}</strong>
      <strong>{{ plan.topics }} 个任务</strong>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import PageHeader from '@/components/common/PageHeader.vue'
import type { TrainingPlan } from '@/types/training'

defineProps<{ plan: TrainingPlan }>()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.plan-card {
  .meta {
    display: flex;
    gap: 18px;
    margin-top: 18px;
    padding-top: 18px;
    border-top: 1px solid var(--c-border-light);

    strong {
      color: var(--c-text-primary);
      font-weight: 600;
      font-size: 15px;
    }
  }
}

@include mobile {
  .plan-card .meta {
    flex-wrap: wrap;
    gap: 10px 16px;
    margin-top: 14px;
    padding-top: 14px;
  }
}
</style>
