<template>
  <el-card shadow="never" class="insight-card">
    <template #header><h2>表现总结</h2></template>
    <div class="insights">
      <el-alert
        v-for="item in insights"
        :key="item.title"
        :title="item.title"
        :description="item.content"
        :type="item.type"
        :closable="false"
        show-icon
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { ReportInsight } from '@/types/report'

defineProps<{ insights: ReportInsight[] }>()
</script>

<style scoped lang="scss">
.insight-card {
  border: 0;
  border-radius: 8px;
}

h2 {
  margin: 0;
  font-size: 17px;
}

.insights {
  display: grid;
  gap: 12px;
}
</style>
