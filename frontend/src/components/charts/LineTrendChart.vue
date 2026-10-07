<template>
  <BaseChart :option="option" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'

import BaseChart from './BaseChart.vue'
import { tokens } from '@/assets/styles/tokens'
import type { TrendPoint } from '@/types/dashboard'

const props = defineProps<{
  data: TrendPoint[]
}>()

const option = computed<EChartsOption>(() => ({
  grid: { top: 32, right: 18, bottom: 32, left: 36 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: props.data.map((item) => item.date),
    axisLine: { lineStyle: { color: tokens.color.border.base } },
    axisTick: { show: false },
    axisLabel: { color: tokens.color.text.tertiary },
  },
  yAxis: {
    type: 'value',
    min: 40,
    max: 100,
    splitLine: { lineStyle: { color: tokens.color.border.light } },
    axisLabel: { color: tokens.color.text.tertiary },
  },
  series: [
    {
      name: '面试成绩',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: props.data.map((item) => item.score),
      lineStyle: { width: 3, color: tokens.color.primary[500] },
      itemStyle: { color: tokens.color.primary[500] },
      areaStyle: { color: tokens.color.primary[50] + 'cc' },
    },
  ],
}))
</script>
