<template>
  <section class="metric-grid">
    <article
      v-for="metric in metrics"
      :key="metric.label"
      class="metric-card card card--float"
      :class="`is-${metric.tone}`"
    >
      <span>{{ metric.label }}</span>
      <strong>{{ metric.value }}</strong>
      <small>{{ metric.trend }}</small>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { TrainingMetric } from '@/types/dashboard'

defineProps<{
  metrics: TrainingMetric[]
}>()
</script>

<style scoped lang="scss">
@use '../../assets/styles/responsive' as *;

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  display: grid;
  gap: 8px;
  min-height: 112px;
  padding: 18px;

  span {
    color: var(--c-text-tertiary);
    font-size: 14px;
  }

  strong {
    color: var(--c-text-primary);
    font-size: 28px;
    font-weight: 700;
  }

  small {
    font-weight: 600;
  }
}

.is-blue small   { color: var(--c-primary-500); }
.is-green small  { color: var(--c-success-text); }
.is-orange small { color: var(--c-warning-text); }
.is-purple small { color: var(--c-chart-purple); }

@media (max-width: 980px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@include mobile {
  .metric-grid {
    gap: 10px;
  }

  .metric-card {
    gap: 6px;
    min-height: 92px;
    padding: 14px;

    span {
      font-size: 13px;
    }

    strong {
      font-size: 22px;
    }
  }
}
</style>
