<template>
  <BaseChart :option="option" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'

import BaseChart from './BaseChart.vue'
import { tokens } from '@/assets/styles/tokens'
import type { TrainingTopic } from '@/types/training'

const props = defineProps<{
  data: TrainingTopic[]
}>()

const option = computed<EChartsOption>(() => ({
  grid: { top: 20, right: 20, bottom: 28, left: 80 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'value',
    max: 100,
    splitLine: { lineStyle: { color: tokens.color.border.light } },
    axisLabel: { color: tokens.color.text.tertiary },
  },
  yAxis: {
    type: 'category',
    data: props.data.map((item) => item.title),
    axisTick: { show: false },
    axisLabel: { color: tokens.color.text.secondary },
  },
  series: [
    {
      type: 'bar',
      data: props.data.map((item) => item.progress),
      barWidth: 14,
      itemStyle: { color: tokens.color.primary[500], borderRadius: 8 },
    },
  ],
}))
</script>
