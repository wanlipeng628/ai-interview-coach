<template>
  <BaseChart :option="option" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'

import BaseChart from './BaseChart.vue'
import { tokens } from '@/assets/styles/tokens'
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
        color: [tokens.color.primary[50] + '66', tokens.color.primary[100] + '99'],
      },
    },
    axisName: { color: tokens.color.text.secondary },
    splitLine: { lineStyle: { color: tokens.color.border.light } },
    axisLine: { lineStyle: { color: tokens.color.border.base } },
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: props.data.map((item) => item.value),
          name: '能力得分',
          areaStyle: { color: tokens.color.primary[200] + '99' },
          lineStyle: { color: tokens.color.primary[500], width: 2 },
          itemStyle: { color: tokens.color.primary[500] },
        },
      ],
    },
  ],
}))
</script>
