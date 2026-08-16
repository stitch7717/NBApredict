<template>
  <div class="odds-page">
    <h2 class="page-title">赔率管理</h2>

    <!-- 按日期查询赔率数据 -->
    <div class="neu-card" style="margin-bottom:20px">
      <div class="neu-card-header">
        <span class="title">赔率数据</span>
        <div class="odds-query-bar">
          <el-date-picker
            v-model="oddsDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :clearable="false"
            @change="loadOddsData"
          />
        </div>
      </div>
      <el-table :data="oddsData" stripe v-loading="oddsLoading" style="width:100%">
        <el-table-column label="比赛" min-width="200">
          <template #default="{ row }">
            <span class="team-cell">
              <TeamLogo :abbr="teamAbbrOfId(row.homeTeamId)" :size="22" />
              <span>{{ teamNameOfId(row.homeTeamId) }}</span>
              <span class="matchup-vs">vs</span>
              <TeamLogo :abbr="teamAbbrOfId(row.awayTeamId)" :size="22" />
              <span>{{ teamNameOfId(row.awayTeamId) }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="主胜" width="90">
          <template #default="{ row }">
            <span class="mono-num">{{ row.homeWinOdds ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="客胜" width="90">
          <template #default="{ row }">
            <span class="mono-num">{{ row.awayWinOdds ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="让分" width="90">
          <template #default="{ row }">
            <span class="mono-num">{{ row.handicapLine ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="大小分" width="90">
          <template #default="{ row }">
            <span class="mono-num">{{ row.totalLine ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dataQuality" label="质量" width="100">
          <template #default="{ row }">
            <span class="neu-tag" :class="qualityTagClass(row.dataQuality)">{{ row.dataQuality || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="采集时间" width="170">
          <template #default="{ row }">
            <span class="mono-num">{{ row.collectTime ?? '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!oddsLoading && !oddsData.length" class="empty-state" style="padding:24px">
        <div class="empty-title">该日期暂无赔率数据</div>
        <div class="empty-desc">选择其他日期，或使用下方"手动采集"抓取</div>
      </div>
    </div>

    <el-row :gutter="24">
      <!-- 数据源状态 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header">
            <span class="title">数据源状态</span>
            <el-button type="primary" size="small" :loading="evaluating" @click="evaluateSources">评估</el-button>
          </div>
          <el-table :data="sources" stripe v-loading="sourceLoading" style="width:100%">
            <el-table-column prop="sourceName" label="数据源" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="neu-tag" :class="row.status === 'ACTIVE' ? 'neu-tag--green' : 'neu-tag--red'">
                  {{ row.status === 'ACTIVE' ? '正常' : '异常' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="totalScore" label="评分" width="80">
              <template #default="{ row }">
                <span :style="{ fontWeight: 600, color: Number(row.totalScore) >= 80 ? '#50C878' : Number(row.totalScore) >= 60 ? '#E6A762' : '#E97451' }">
                  {{ row.totalScore }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="isPrimary" label="主数据源" width="100">
              <template #default="{ row }">
                <span v-if="row.isPrimary" class="neu-tag neu-tag--orange">主</span>
                <el-button v-else type="primary" link size="small" @click="switchSource(row)">切换</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 雷达图 -->
        <div class="neu-card" style="margin-top:20px">
          <div class="neu-card-header"><span class="title">数据源质量对比</span></div>
          <div v-if="sources.length" ref="scoreChartRef" class="chart-container"></div>
          <div v-else class="empty-state">
            <div class="empty-title">暂无数据源</div>
          </div>
        </div>
      </el-col>

      <!-- 手动采集 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">手动采集</span></div>
          <el-form :model="collectForm" label-width="70px">
            <el-form-item label="数据源">
              <el-select v-model="collectForm.sourceId" placeholder="选择数据源" style="width:100%">
                <el-option v-for="s in sources" :key="s.sourceId" :label="s.sourceName" :value="s.sourceId" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期">
              <el-date-picker v-model="collectForm.date" type="date" placeholder="选择日期" style="width:100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="collecting" @click="handleCollect" style="width:100%">
                <el-icon><Download /></el-icon> 开始采集
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 历史回测 -->
        <div class="neu-card" style="margin-top:20px">
          <div class="neu-card-header"><span class="title">回测分析</span></div>
          <el-form :model="backtestForm" label-width="70px">
            <el-form-item label="数据源">
              <el-select v-model="backtestForm.sourceId" placeholder="选择数据源" style="width:100%">
                <el-option v-for="s in sources" :key="s.sourceId" :label="s.sourceName" :value="s.sourceId" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期范围">
              <el-date-picker v-model="backtestForm.dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" style="width:100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="backtesting" @click="handleBacktest" style="width:100%">
                <el-icon><DataAnalysis /></el-icon> 开始回测
              </el-button>
            </el-form-item>
          </el-form>
          <div v-if="backtestResult" class="backtest-result animate-fade-in">
            <div class="overview-grid">
              <div class="overview-item">
                <span class="overview-label">MAE</span>
                <span class="overview-value">{{ backtestResult.mae?.toFixed(2) ?? '-' }}</span>
              </div>
              <div class="overview-item">
                <span class="overview-label">校准度</span>
                <span class="overview-value">{{ backtestResult.calibration?.toFixed(1) ?? '-' }}%</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([RadarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])
import { datasourceApi, oddsApi, teamApi } from '@/api'
import { Download, DataAnalysis } from '@element-plus/icons-vue'

const sources = ref([])
const sourceLoading = ref(false)
const evaluating = ref(false)
const collecting = ref(false)
const backtesting = ref(false)
const scoreChartRef = ref(null)
const backtestResult = ref(null)
let scoreChart = null

const formatDateStr = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

// 按日期查询赔率
const oddsDate = ref(formatDateStr(new Date()))
const oddsData = ref([])
const oddsLoading = ref(false)
const teamMap = ref({})

const collectForm = reactive({ sourceId: null, date: new Date() })
const backtestForm = reactive({ sourceId: null, dateRange: [] })

const chartColors = ['#1d428a', '#50C878', '#E6A762', '#E97451', '#A8C1B6']

onMounted(() => {
  loadSources()
  loadTeamMap()
  loadOddsData()
  window.addEventListener('resize', handleResize)
})

const loadTeamMap = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    const records = res.data?.records || []
    for (const t of records) {
      teamMap.value[t.teamId] = t
    }
  } catch (e) { console.error(e) }
}

const teamNameOfId = (id) => teamMap.value[id]?.teamName || `#${id}`
const teamAbbrOfId = (id) => teamMap.value[id]?.abbreviation || ''

const qualityTagClass = (q) => {
  if (!q) return ''
  if (q === 'HIGH' || q === '高') return 'neu-tag--green'
  if (q === 'MEDIUM' || q === '中') return 'neu-tag--orange'
  if (q === 'LOW' || q === '低') return 'neu-tag--red'
  return 'neu-tag--gray' // NORMAL / 未知
}

const loadOddsData = async () => {
  oddsLoading.value = true
  try {
    const res = await oddsApi.getList({ gameDate: oddsDate.value, page: 1, size: 100 })
    oddsData.value = res.data?.records || []
  } catch (e) {
    console.error(e)
    oddsData.value = []
  } finally {
    oddsLoading.value = false
  }
}

onBeforeUnmount(() => {
  scoreChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => { scoreChart?.resize() }

const loadSources = async () => {
  sourceLoading.value = true
  try {
    const res = await datasourceApi.getList()
    sources.value = res.data || []
    await nextTick()
    if (sources.value.length) initChart()
  } catch (e) { console.error(e) } finally { sourceLoading.value = false }
}

const evaluateSources = async () => {
  evaluating.value = true
  try {
    await datasourceApi.evaluate()
    ElMessage.success('评估完成')
    loadSources()
  } catch { ElMessage.error('评估失败') } finally { evaluating.value = false }
}

const switchSource = async (source) => {
  try {
    await datasourceApi.switch(source.sourceId)
    ElMessage.success('切换成功')
    loadSources()
  } catch { ElMessage.error('切换失败') }
}

const handleCollect = async () => {
  if (!collectForm.sourceId) { ElMessage.warning('请选择数据源'); return }
  collecting.value = true
  try {
    await oddsApi.collect({ sourceId: collectForm.sourceId, date: collectForm.date })
    ElMessage.success('采集完成')
  } catch { ElMessage.error('采集失败') } finally { collecting.value = false }
}

const handleBacktest = async () => {
  if (!backtestForm.sourceId) { ElMessage.warning('请选择数据源'); return }
  if (!backtestForm.dateRange?.length) { ElMessage.warning('请选择日期范围'); return }
  backtesting.value = true
  try {
    const res = await oddsApi.backtest({
      sourceId: backtestForm.sourceId,
      startDate: backtestForm.dateRange[0],
      endDate: backtestForm.dateRange[1],
    })
    backtestResult.value = res.data
    ElMessage.success('回测完成')
  } catch { ElMessage.error('回测失败') } finally { backtesting.value = false }
}

const initChart = () => {
  if (!scoreChartRef.value || !sources.value.length) return
  scoreChart = echarts.init(scoreChartRef.value)

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

  scoreChart.setOption({
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
.odds-page { max-width: 1400px; margin: 0 auto; }

.backtest-result { margin-top: 16px; padding-top: 16px; border-top: 1px solid $border-dark; }

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .overview-label { font-size: 11px; color: $text-muted; text-transform: uppercase; letter-spacing: 0.5px; }
  .overview-value { font-size: 22px; font-weight: 700; color: $text-primary; }
}
</style>
