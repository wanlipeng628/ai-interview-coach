<template>
  <BaseChart :option="option" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed } from 'vue'

import BaseChart from './BaseChart.vue'
import { tokens } from '@/assets/styles/tokens'
import type { MasterySlice } from '@/types/profile'

const props = defineProps<{
  data: MasterySlice[]
}>()

const option = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: tokens.color.text.secondary } },
  color: [tokens.color.primary[500], tokens.color.success.base, tokens.color.warning.base],
  series: [
    {
      type: 'pie',
      radius: ['52%', '72%'],
      center: ['50%', '44%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{d}%', color: tokens.color.text.primary },
      data: props.data,
    },
  ],
}))
</script>
