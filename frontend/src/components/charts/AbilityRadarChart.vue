<template>
  <BaseChart :option="option" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'

import BaseChart from './BaseChart.vue'
import type { AbilityScore } from '@/types/dashboard'

const props = defineProps<{
  data: AbilityScore[]
}>()

const option = computed<EChartsOption>(() => ({
  tooltip: {},
  radar: {
    radius: '68%',
    indicator: props.data.map((item) => ({ name: item.name, max: 100 })),
    splitArea: {
      areaStyle: {
        color: ['rgba(47, 107, 255, 0.03)', 'rgba(47, 107, 255, 0.08)'],
      },
    },
    axisName: { color: '#344054' },
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: props.data.map((item) => item.value),
          name: '能力得分',
          areaStyle: { color: 'rgba(47, 107, 255, 0.22)' },
          lineStyle: { color: '#2f6bff', width: 2 },
          itemStyle: { color: '#2f6bff' },
        },
      ],
    },
  ],
}))
</script>
