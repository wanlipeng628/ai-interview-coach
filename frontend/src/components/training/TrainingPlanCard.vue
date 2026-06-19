<template>
  <el-card shadow="never" class="plan-card">
    <p>系统推荐</p>
    <h1>{{ plan.title }}</h1>
    <span>{{ plan.description }}</span>
    <div class="meta">
      <strong>{{ plan.estimatedTime }}</strong>
      <strong>{{ plan.topics }} 个主题</strong>
    </div>
    <el-button type="primary" size="large">开始训练</el-button>
  </el-card>
</template>

<script setup lang="ts">
import type { TrainingPlan } from '@/types/training'

defineProps<{ plan: TrainingPlan }>()
</script>

<style scoped lang="scss">
.plan-card {
  border: 0;
  border-radius: 8px;
}

p {
  margin: 0 0 10px;
  color: #2f6bff;
  font-weight: 800;
}

h1 {
  margin: 0 0 10px;
  font-size: 26px;
}

span {
  display: block;
  color: #667085;
  line-height: 1.7;
}

.meta {
  display: flex;
  gap: 18px;
  margin: 22px 0;
}
</style>
