<template>
  <el-card shadow="never" class="suggestion-card card card--float">
    <template #header><h2>推荐训练方向</h2></template>
    <div class="suggestions">
      <div v-for="item in suggestions" :key="item.title" class="suggestion">
        <el-tag :type="item.priority === '高' ? 'danger' : 'warning'" effect="light">
          {{ item.priority }}优先级
        </el-tag>
        <div>
          <strong>{{ item.title }}</strong>
          <p>{{ item.description }}</p>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { TrainingSuggestion } from '@/types/report'

defineProps<{ suggestions: TrainingSuggestion[] }>()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.suggestion-card {
  h2 {
    margin: 0;
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
  }
}

.suggestions {
  display: grid;
  gap: 14px;
}

.suggestion {
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 12px;
  align-items: start;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--c-border-light);

  &:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }

  strong {
    color: var(--c-text-primary);
    font-weight: 600;
  }

  p {
    margin: 6px 0 0;
    color: var(--c-text-tertiary);
    line-height: 1.6;
  }
}

@include mobile {
  // 标签列 92px 在 375px 屏上占比过高，收窄给正文留出空间
  .suggestion {
    grid-template-columns: 76px minmax(0, 1fr);

    > div {
      min-width: 0;
    }

    strong,
    p {
      overflow-wrap: anywhere;
    }
  }
}
</style>
