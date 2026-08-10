import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([CanvasRenderer])

export function useChart() {
  const chartRef = ref(null)
  let chartInstance = null

  function initChart(dom) {
    if (chartInstance) chartInstance.dispose()
    chartInstance = echarts.init(dom)
    return chartInstance
  }

  function resize() {
    chartInstance?.resize()
  }

  onMounted(() => window.addEventListener('resize', resize))
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    chartInstance?.dispose()
  })

  return { chartRef, initChart, resize }
}
