<template>
  <section class="metric-grid">
    <article v-for="metric in metrics" :key="metric.label" class="metric-card" :class="`is-${metric.tone}`">
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
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(19, 34, 66, 0.05);

  span {
    color: #667085;
    font-size: 14px;
  }

  strong {
    color: #101828;
    font-size: 28px;
  }

  small {
    font-weight: 700;
  }
}

.is-blue small { color: #2f6bff; }
.is-green small { color: #17a568; }
.is-orange small { color: #e26a2c; }
.is-purple small { color: #7a5af8; }

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
