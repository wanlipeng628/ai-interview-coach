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
</style>
