<template>
  <div ref="chartRef" class="ability-radar" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** 维度定义：[{ name, max }]（max 为归一化参考上限） */
  dimensions: { type: Array, default: () => [] },
  /** 与 dimensions 对齐的原始值数组，自动裁剪到 [0, max] */
  values: { type: Array, default: () => [] },
  /** 雷达主色（默认 NBA 蓝） */
  color: { type: String, default: '#1d428a' },
  height: { type: Number, default: 280 },
})

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)

  const clamped = props.values.map((v, i) => {
    const max = props.dimensions[i]?.max ?? 1
    return Math.min(Math.max(Number(v) || 0, 0), max)
  })

  chart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: props.dimensions.map((d) => ({ name: d.name, max: d.max })),
      radius: '62%',
      axisName: { color: '#B0B0B0', fontSize: 12 },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },
      splitArea: { areaStyle: { color: ['transparent'] } },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.12)' } },
    },
    series: [
      {
        type: 'radar',
        data: [{ value: clamped }],
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: props.color, width: 2 },
        itemStyle: { color: props.color },
        areaStyle: { color: props.color, opacity: 0.22 },
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

watch(
  () => [props.dimensions, props.values],
  () => render(),
  { deep: true },
)
</script>

<style lang="scss" scoped>
.ability-radar {
  width: 100%;
}
</style>
