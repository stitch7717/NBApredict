<template>
  <div class="dashboard-page">
    <h2 class="page-title">数据看板</h2>

    <el-row :gutter="20">
      <!-- 数据源评分 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header">
            <span class="title">数据源评分</span>
            <el-button type="primary" size="small" :loading="sourceLoading" @click="loadSources">刷新</el-button>
          </div>
          <div v-if="sources.length" ref="sourceChartRef" class="chart-container"></div>
          <div v-else class="empty-state">
            <el-icon class="empty-icon"><DataAnalysis /></el-icon>
            <div class="empty-title">暂无数据源</div>
            <div class="empty-desc">请先配置数据源</div>
          </div>
        </div>
      </el-col>
      <!-- 预测误差统计 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header">
            <span class="title">预测误差统计</span>
            <el-select v-model="selectedSeason" size="small" style="width:120px" @change="loadRecords">
              <el-option label="2025-26" value="2025-26" />
              <el-option label="2024-25" value="2024-25" />
            </el-select>
          </div>
          <div v-if="records.length" ref="errorChartRef" class="chart-container"></div>
          <div v-else class="empty-state">
            <el-icon class="empty-icon"><TrendCharts /></el-icon>
            <div class="empty-title">暂无预测记录</div>
            <div class="empty-desc">完成预测校准后将展示误差统计</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <!-- 球员稳定性趋势 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">球员预测误差分布</span></div>
          <div v-if="playerErrorData.length" ref="playerChartRef" class="chart-container"></div>
          <div v-else class="empty-state">
            <el-icon class="empty-icon"><User /></el-icon>
            <div class="empty-title">暂无球员预测数据</div>
            <div class="empty-desc">完成球员预测校准后展示分布</div>
          </div>
        </div>
      </el-col>
      <!-- 数据源质量雷达 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">数据源质量雷达</span></div>
          <div v-if="sources.length" ref="radarChartRef" class="chart-container"></div>
          <div v-else class="empty-state">
            <el-icon class="empty-icon"><Connection /></el-icon>
            <div class="empty-title">暂无数据源</div>
            <div class="empty-desc">请先配置数据源</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { datasourceApi, recordApi } from '@/api'
import { DataAnalysis, TrendCharts, User, Connection } from '@element-plus/icons-vue'

const selectedSeason = ref('2025-26')
const sourceChartRef = ref(null)
const errorChartRef = ref(null)
const playerChartRef = ref(null)
const radarChartRef = ref(null)

const sources = ref([])
const records = ref([])
const playerErrorData = ref([])
const sourceLoading = ref(false)
let charts = []

const chartColors = ['#1d428a', '#50C878', '#E6A762', '#E97451', '#A8C1B6', '#D9C7B8']

onMounted(async () => {
  await Promise.all([loadSources(), loadRecords()])
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  charts.forEach(c => c.dispose())
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => { charts.forEach(c => c.resize()) }

const disposeCharts = () => {
  charts.forEach(c => c.dispose())
  charts = []
}

const loadSources = async () => {
  sourceLoading.value = true
  try {
    const res = await datasourceApi.getList()
    sources.value = res.data || []
    await nextTick()
    if (sources.value.length) {
      initSourceChart()
      initRadarChart()
    }
  } catch {} finally { sourceLoading.value = false }
}

const loadRecords = async () => {
  try {
    const res = await recordApi.getList({ page: 1, size: 200, predictType: 'PLAYER' })
    records.value = res.data?.records || []
    processPlayerErrors()
    await nextTick()
    if (records.value.length) {
      initErrorChart()
    }
    if (playerErrorData.value.length) {
      initPlayerChart()
    }
  } catch {}
}

const processPlayerErrors = () => {
  const errors = records.value.filter(r => r.errorPoints != null).map(r => r.errorPoints)
  if (!errors.length) { playerErrorData.value = []; return }

  // 分布: 0-2, 2-4, 4-6, 6-8, 8-10, 10+
  const buckets = [0, 0, 0, 0, 0, 0]
  const labels = ['0-2', '2-4', '4-6', '6-8', '8-10', '10+']
  errors.forEach(e => {
    if (e < 2) buckets[0]++
    else if (e < 4) buckets[1]++
    else if (e < 6) buckets[2]++
    else if (e < 8) buckets[3]++
    else if (e < 10) buckets[4]++
    else buckets[5]++
  })
  playerErrorData.value = labels.map((l, i) => ({ label: l, count: buckets[i] }))
}

const initSourceChart = () => {
  if (!sourceChartRef.value) return
  const chart = echarts.init(sourceChartRef.value)
  charts.push(chart)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: '#1E1E1E', borderColor: '#2A2A2A', textStyle: { color: '#fff' } },
    grid: { top: 20, right: 20, bottom: 40, left: 60 },
    xAxis: {
      type: 'category',
      data: sources.value.map(s => s.sourceName),
      axisLine: { lineStyle: { color: '#2A2A2A' } },
      axisLabel: { color: '#B0B0B0', rotate: sources.value.length > 4 ? 15 : 0 },
    },
    yAxis: {
      type: 'value', max: 100,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#2A2A2A' } },
      axisLabel: { color: '#6B6B6B' },
    },
    series: [{
      type: 'bar',
      data: sources.value.map((s, i) => ({
        value: Number(s.totalScore) || 0,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: chartColors[i % chartColors.length] },
            { offset: 1, color: chartColors[i % chartColors.length] + '40' },
          ]),
        },
      })),
      barWidth: Math.min(48, 300 / sources.value.length),
    }],
  })
}

const initErrorChart = () => {
  if (!errorChartRef.value) return
  const chart = echarts.init(errorChartRef.value)
  charts.push(chart)

  // 按月分组计算平均误差
  const monthlyMap = {}
  records.value.forEach(r => {
    if (r.errorPoints == null || !r.createTime) return
    const month = r.createTime.substring(0, 7) // yyyy-MM
    if (!monthlyMap[month]) monthlyMap[month] = []
    monthlyMap[month].push(r.errorPoints)
  })
  const months = Object.keys(monthlyMap).sort().slice(-6)
  const avgErrors = months.map(m => {
    const arr = monthlyMap[m]
    return Number((arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2))
  })

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: '#1E1E1E', borderColor: '#2A2A2A', textStyle: { color: '#fff' } },
    grid: { top: 20, right: 20, bottom: 40, left: 50 },
    xAxis: {
      type: 'category',
      data: months,
      axisLine: { lineStyle: { color: '#2A2A2A' } },
      axisLabel: { color: '#B0B0B0' },
    },
    yAxis: {
      type: 'value', name: 'MAE',
      nameTextStyle: { color: '#6B6B6B' },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#2A2A2A' } },
      axisLabel: { color: '#6B6B6B' },
    },
    series: [{
      type: 'line',
      data: avgErrors,
      smooth: true,
      lineStyle: { width: 2, color: '#1d428a' },
      itemStyle: { color: '#1d428a' },
      symbolSize: 6,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(29,66,138,0.25)' },
          { offset: 1, color: 'rgba(29,66,138,0.02)' },
        ]),
      },
    }],
  })
}

const initPlayerChart = () => {
  if (!playerChartRef.value || !playerErrorData.value.length) return
  const chart = echarts.init(playerChartRef.value)
  charts.push(chart)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: '#1E1E1E', borderColor: '#2A2A2A', textStyle: { color: '#fff' } },
    grid: { top: 20, right: 20, bottom: 40, left: 50 },
    xAxis: {
      type: 'category',
      data: playerErrorData.value.map(d => d.label),
      axisLine: { lineStyle: { color: '#2A2A2A' } },
      axisLabel: { color: '#B0B0B0' },
    },
    yAxis: {
      type: 'value', name: '记录数',
      nameTextStyle: { color: '#6B6B6B' },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#2A2A2A' } },
      axisLabel: { color: '#6B6B6B' },
    },
    series: [{
      type: 'bar',
      data: playerErrorData.value.map((d, i) => ({
        value: d.count,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: i < 3 ? '#50C878' : '#E97451' },
            { offset: 1, color: i < 3 ? 'rgba(80,200,120,0.3)' : 'rgba(233,116,81,0.3)' },
          ]),
        },
      })),
      barWidth: 36,
    }],
  })
}

const initRadarChart = () => {
  if (!radarChartRef.value || !sources.value.length) return
  const chart = echarts.init(radarChartRef.value)
  charts.push(chart)

  const indicators = [
    { name: 'MAE', max: 100 },
    { name: '校准度', max: 100 },
    { name: '完整性', max: 100 },
    { name: '及时性', max: 100 },
    { name: '稳定性', max: 100 },
  ]

  const seriesData = sources.value.slice(0, 4).map((s, i) => ({
    name: s.sourceName,
    value: [
      Number(s.maeScore) || 0,
      Number(s.calibrationScore) || 0,
      Number(s.completenessScore) || 0,
      Number(s.timelinessScore) || 0,
      Number(s.stabilityScore) || 0,
    ],
    areaStyle: { color: chartColors[i] + '20' },
    lineStyle: { color: chartColors[i], width: 2 },
    itemStyle: { color: chartColors[i] },
  }))

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { backgroundColor: '#1E1E1E', borderColor: '#2A2A2A', textStyle: { color: '#fff' } },
    legend: {
      data: sources.value.slice(0, 4).map(s => s.sourceName),
      textStyle: { color: '#B0B0B0' },
      bottom: 0,
    },
    radar: {
      indicator: indicators,
      axisName: { color: '#B0B0B0' },
      splitLine: { lineStyle: { color: '#2A2A2A' } },
      splitArea: { areaStyle: { color: ['rgba(29,66,138,0.05)', 'rgba(29,66,138,0.1)'] } },
      axisLine: { lineStyle: { color: '#2A2A2A' } },
    },
    series: [{ type: 'radar', data: seriesData }],
  })
}
</script>

<style lang="scss" scoped>
.dashboard-page { max-width: 1400px; }
</style>
