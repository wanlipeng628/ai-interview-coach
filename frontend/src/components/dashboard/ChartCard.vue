<template>
  <el-card shadow="never" class="chart-card card card--float">
    <template #header>
      <div class="card__header">
        <div>
          <h2>{{ title }}</h2>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <slot name="extra" />
      </div>
    </template>
    <slot />
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.chart-card {
  height: 100%;
}

.card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: var(--fs-lg);
    font-weight: var(--fw-semibold);
    color: var(--c-text-primary);
  }

  p {
    margin: 6px 0 0;
    color: var(--c-text-tertiary);
    font-size: var(--fs-sm);
  }
}

@include mobile {
  // 标题与 extra 插槽在窄屏并排会被挤到卡片外，允许换行并让标题块可收缩
  .card__header {
    flex-wrap: wrap;
    gap: 8px;

    > div:first-child {
      min-width: 0;
    }

    h2 {
      font-size: 16px;
    }
  }
}
</style>
