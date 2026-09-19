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
@use '../../assets/styles/responsive' as *;

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

@include mobile {
  // 64px 在 375px 屏上过重，收紧到与卡片标题同级的视觉节奏；允许换行防止评级标签顶出
  .score-line {
    flex-wrap: wrap;
  }

  .score {
    font-size: 48px;
  }

  // 结论文案来自模型输出，可能含超长英文 token，兜住不溢出
  .conclusion {
    overflow-wrap: anywhere;
  }
}
</style>
