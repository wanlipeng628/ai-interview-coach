<template>
  <el-card shadow="never" class="summary-card">
    <div class="score-line">
      <strong class="score">{{ summary.overallScore }}</strong>
      <span>/ 100</span>
      <el-tag type="warning">{{ summary.level }}</el-tag>
    </div>
    <p>超过了 {{ summary.percentile }}% 的求职者</p>
    <strong class="conclusion">{{ summary.conclusion }}</strong>
  </el-card>
</template>

<script setup lang="ts">
import type { ReportSummary } from '@/types/report'

defineProps<{ summary: ReportSummary }>()
</script>

<style scoped lang="scss">
.summary-card {
  border: 0;
  border-radius: 8px;
}

.score-line {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 10px;
}

.score {
  color: #e26a2c;
  font-size: 64px;
  font-weight: 800;
  line-height: 1;
}

span,
p {
  color: #667085;
}

p {
  margin: 14px 0;
  text-align: center;
}

.conclusion {
  display: block;
  line-height: 1.7;
}
</style>
