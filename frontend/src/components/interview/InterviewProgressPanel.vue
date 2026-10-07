<template>
  <el-card shadow="never" class="progress-panel card card--float">
    <template #header>
      <h2>面试进度</h2>
    </template>

    <el-progress :percentage="progress" :stroke-width="10" />
    <p class="summary">已完成 {{ answered.length }} / {{ total }} 题</p>

    <div class="answered-list">
      <h3>已回答题目</h3>
      <el-empty v-if="answered.length === 0" description="暂无回答" :image-size="90" />
      <div v-for="item in answered" :key="item.questionNo" class="answered-item">
        <span>Q{{ item.questionNo }}</span>
        <p>{{ item.title }}</p>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { AnsweredQuestion } from '@/types/interview'

defineProps<{
  progress: number
  total: number
  answered: AnsweredQuestion[]
}>()
</script>

<style scoped lang="scss">
.progress-panel.card {
  height: 100%;

  h2 {
    margin: 0;
  }
}

h3 {
  margin: 0;
  font-size: 15px;
  color: var(--c-text-secondary);
}

.summary {
  margin: 12px 0 22px;
  color: var(--c-text-tertiary);
  font-size: 13px;
}

.answered-list {
  display: grid;
  gap: 12px;
}

.answered-item {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 10px;
  padding: 12px;
  border-radius: var(--r-md);
  background: var(--c-bg-tint);

  span {
    color: var(--c-primary-500);
    font-weight: var(--fw-bold);
  }

  p {
    margin: 0;
    color: var(--c-text-secondary);
    font-size: 13px;
    line-height: 1.5;
  }
}
</style>
