<template>
  <el-card shadow="never" class="chart-card">
    <template #header>
      <div class="card-header">
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
  border: 0;
  border-radius: 8px;
  box-shadow: 0 12px 30px rgba(19, 34, 66, 0.05);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: 17px;
    color: #101828;
  }

  p {
    margin: 6px 0 0;
    color: #667085;
    font-size: 13px;
  }
}

@include mobile {
  // 标题与 extra 插槽在窄屏并排会被挤到卡片外，允许换行并让标题块可收缩
  .card-header {
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
