<template>
  <div ref="chartRef" class="base-chart" />
</template>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  option: EChartsOption
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined

const renderChart = () => {
  if (!chartRef.value) return
  chart ??= echarts.init(chartRef.value)
  chart.setOption(props.option, true)
}

const resizeChart = () => chart?.resize()

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', resizeChart)
})

watch(() => props.option, renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})
</script>

<style scoped>
.base-chart {
  width: 100%;
  height: 100%;
  min-height: 260px;
}
</style>
