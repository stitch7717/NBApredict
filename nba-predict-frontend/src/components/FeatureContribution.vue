<template>
  <div ref="chartRef" class="feature-contribution" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** [{ group, contribution }]，contribution 为对预测分差的影响（分） */
  items: { type: Array, default: () => [] },
  height: { type: Number, default: 240 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)

  // 负值在下、正值在上，读起来更顺
  const data = [...props.items].sort((a, b) => a.contribution - b.contribution)

  chart.setOption({
    grid: { left: 118, right: 40, top: 10, bottom: 34 },
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.name}<br/>对分差影响 ${p.value > 0 ? '+' : ''}${p.value} 分`,
    },
    xAxis: {
      type: 'value',
      name: '对预测分差的影响（分）',
      nameLocation: 'middle',
      nameGap: 26,
      nameTextStyle: { color: '#6B6B6B', fontSize: 11 },
      axisLabel: { color: '#6B6B6B', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } },
      axisLine: { show: false },
    },
    yAxis: {
      type: 'category',
      data: data.map((d) => d.group),
      axisLabel: { color: '#B0B0B0', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },
      axisTick: { show: false },
    },
    series: [
      {
        type: 'bar',
        barWidth: '52%',
        data: data.map((d) => ({
          value: d.contribution,
          itemStyle: {
            color: d.contribution >= 0 ? '#1d428a' : '#c8102e',
            borderRadius: 2,
          },
          label: {
            show: true,
            position: d.contribution >= 0 ? 'right' : 'left',
            formatter: `${d.contribution > 0 ? '+' : ''}${d.contribution}`,
            color: '#8a8a8a',
            fontSize: 10,
          },
        })),
      },
    ],
  })
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

watch(() => props.items, () => render(), { deep: true })
</script>

<style lang="scss" scoped>
.feature-contribution {
  width: 100%;
}
</style>
