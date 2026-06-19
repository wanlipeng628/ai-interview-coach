<template>
  <BaseChart :option="option" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'

import BaseChart from './BaseChart.vue'
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
    axisLine: { lineStyle: { color: '#d7ddea' } },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    min: 40,
    max: 100,
    splitLine: { lineStyle: { color: '#edf0f6' } },
  },
  series: [
    {
      name: '面试成绩',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: props.data.map((item) => item.score),
      lineStyle: { width: 3, color: '#2f6bff' },
      itemStyle: { color: '#2f6bff' },
      areaStyle: { color: 'rgba(47, 107, 255, 0.12)' },
    },
  ],
}))
</script>
