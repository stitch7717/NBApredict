<template>
  <div class="predict-page">
    <!-- 全局发散背景（fixed 铺满整个视口，不受页面容器限制） -->
    <div class="page-glow" :style="sideBgStyle('home')"></div>
    <div class="page-glow" :style="sideBgStyle('away')"></div>

    <!-- ============ 对阵头部 ============ -->
    <div class="duel-hero">
      <!-- 主队侧 -->
      <div class="hero-side">
        <div v-if="homeTeamAbbr" class="duel-glow" :style="glowStyle('home')"></div>
        <div class="hero-logo-wrap">
          <TeamLogo
            v-if="homeTeamAbbr"
            class="hero-logo"
            :abbr="homeTeamAbbr"
            :size="332"
          />
        </div>
        <!-- 队标旁小字：战绩 / 分区排名 -->
        <div v-if="homeTeamAbbr" class="hero-meta">
          <span class="hero-meta-text">{{ homeRecord }}</span>
          <span class="hero-meta-text">{{ homeRank }}</span>
        </div>
        <el-select
          v-model="form.homeTeamId"
          filterable
          placeholder="选择球队"
          class="frost-select"
          @change="onTeamChange('home')"
        >
          <el-option
            v-for="t in teamOptions"
            :key="t.teamId"
            :label="t.teamName"
            :value="t.teamId"
            :disabled="t.teamId === form.awayTeamId"
          >
            <span class="team-cell">
              <TeamLogo :abbr="t.abbreviation || ''" :size="20" />
              <span>{{ t.teamName }}</span>
            </span>
          </el-option>
        </el-select>
      </div>

      <!-- 中间 -->
      <div class="hero-center">
        <!-- 预测比分：数字在 VS 圆环两侧 -->
        <div v-if="result" class="score-caption">预测比分</div>
        <div class="vs-score-row">
          <span v-if="result" class="score-num score-num--home animate-fade-in">{{ result.predictHomeScore ?? result.predict_home_score ?? 0 }}</span>
          <span class="vs-ring">VS</span>
          <span v-if="result" class="score-num score-num--away animate-fade-in">{{ result.predictAwayScore ?? result.predict_away_score ?? 0 }}</span>
        </div>
        <!-- 总分与预测区间（±1σ，约覆盖 68% 的比赛） -->
        <div v-if="result && totalRange" class="total-range">
          预测总分 <b>{{ result.predictTotalScore ?? result.predict_total_score ?? '-' }}</b>
          <span class="range-hint">区间 {{ totalRange }}（±1σ，约 68% 覆盖）</span>
        </div>

        <el-radio-group v-model="form.scene" size="small" class="scene-group">
          <el-radio-button label="常规赛">常规赛</el-radio-button>
          <el-radio-button label="季后赛">季后赛</el-radio-button>
        </el-radio-group>
        <el-button
          type="primary"
          :loading="predicting"
          class="predict-main-btn"
          @click="handlePredict"
        >
          <el-icon><TrendCharts /></el-icon> 开始预测
        </el-button>
      </div>

      <!-- 客队侧 -->
      <div class="hero-side">
        <div v-if="awayTeamAbbr" class="duel-glow" :style="glowStyle('away')"></div>
        <div class="hero-logo-wrap">
          <TeamLogo
            v-if="awayTeamAbbr"
            class="hero-logo"
            :abbr="awayTeamAbbr"
            :size="332"
          />
        </div>
        <div v-if="awayTeamAbbr" class="hero-meta">
          <span class="hero-meta-text">{{ awayRecord }}</span>
          <span class="hero-meta-text">{{ awayRank }}</span>
        </div>
        <el-select
          v-model="form.awayTeamId"
          filterable
          placeholder="选择球队"
          class="frost-select"
          @change="onTeamChange('away')"
        >
          <el-option
            v-for="t in teamOptions"
            :key="t.teamId"
            :label="t.teamName"
            :value="t.teamId"
            :disabled="t.teamId === form.homeTeamId"
          >
            <span class="team-cell">
              <TeamLogo :abbr="t.abbreviation || ''" :size="20" />
              <span>{{ t.teamName }}</span>
            </span>
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- 胜率条（数据区第一行位置，左右各自队色） -->
    <div v-if="result" class="winprob-row animate-fade-in">
      <div class="winprob-labels">
        <span class="winprob-label winprob-label--home" :style="{ color: homeColor }">{{ homePct }}</span>
        <span class="winprob-label winprob-label--away" :style="{ color: awayColor }">{{ awayPct }}</span>
      </div>
      <div class="winprob-bar-custom">
        <div class="winprob-fill" :style="{ width: homePct, background: homeColor }"></div>
        <div class="winprob-fill" :style="{ width: awayPct, background: awayColor }"></div>
      </div>
    </div>

    <!-- 预测分析报告：球员状态波动检测结果 -->
    <div v-if="analysisText" class="analysis-zone animate-fade-in">
      <div class="analysis-head">
        <span class="analysis-title">预测分析</span>
        <span class="analysis-method">{{ analysisMethod }}</span>
      </div>
      <p class="analysis-text">{{ analysisText }}</p>
      <!-- 各特征组对预测分差的贡献 -->
      <div v-if="featureContribution?.length" class="contribution-block">
        <div class="contribution-title">各特征组对预测分差的贡献</div>
        <FeatureContribution :items="featureContribution" :height="235" />
      </div>

      <div v-if="analysisSignals.length" class="analysis-chips">
        <span
          v-for="s in analysisSignals"
          :key="s.key"
          class="analysis-chip"
          :class="`analysis-chip--${s.type}`"
        >{{ s.label }}</span>
      </div>
    </div>

    <!-- ============ 数据区（三行两列网格） ============ -->
    <div v-if="form.homeTeamId && form.awayTeamId" class="data-zone">
      <div class="data-col data-col--home">
        <div v-for="item in basicRows" :key="item.label" class="data-item">
          <span class="data-val mono-num" :class="item.homeCls">{{ formatVal(item.home, item.fmt) }}</span>
          <span class="data-label">{{ item.label }}</span>
        </div>
      </div>
      <div class="data-col data-col--away">
        <div v-for="item in basicRows" :key="item.label" class="data-item">
          <span class="data-val mono-num" :class="item.awayCls">{{ formatVal(item.away, item.fmt) }}</span>
          <span class="data-label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <!-- 展开后数据同格式呈现；收起按钮在底部 -->
    <div v-if="basicExpanded && form.homeTeamId && form.awayTeamId" class="data-zone animate-fade-in">
      <div class="data-col data-col--home">
        <div v-for="item in moreRows" :key="item.label" class="data-item">
          <span class="data-val mono-num" :class="item.homeCls">{{ formatVal(item.home, item.fmt) }}</span>
          <span class="data-label">{{ item.label }}</span>
        </div>
      </div>
      <div class="data-col data-col--away">
        <div v-for="item in moreRows" :key="item.label" class="data-item">
          <span class="data-val mono-num" :class="item.awayCls">{{ formatVal(item.away, item.fmt) }}</span>
          <span class="data-label">{{ item.label }}</span>
        </div>
      </div>
    </div>
    <div v-if="form.homeTeamId && form.awayTeamId" class="expand-toggle" @click="basicExpanded = !basicExpanded">
      <el-icon class="toggle-icon" :class="{ 'toggle-icon--rotated': basicExpanded }"><ArrowDown /></el-icon>
      <span>{{ basicExpanded ? '收起数据' : '展开更多数据' }}</span>
    </div>

    <!-- ============ 球员对位区（预测后出现） ============ -->
    <div v-if="result" class="player-zone animate-fade-in">
      <div class="player-zone-title">球员对位</div>
      <div class="player-selects">
        <el-select
          v-model="form.homePlayerId"
          filterable
          clearable
          placeholder="选择球员"
          class="frost-select"
          @change="resetComparison"
        >
          <el-option
            v-for="p in homeRoster"
            :key="p.playerId"
            :label="p.playerName"
            :value="p.playerId"
          />
        </el-select>
        <span class="matchup-vs">VS</span>
        <el-select
          v-model="form.awayPlayerId"
          filterable
          clearable
          placeholder="选择球员"
          class="frost-select"
          @change="resetComparison"
        >
          <el-option
            v-for="p in awayRoster"
            :key="p.playerId"
            :label="p.playerName"
            :value="p.playerId"
          />
        </el-select>
      </div>

      <!-- 球员数据（选择后出现） -->
      <div v-if="form.homePlayerId && form.awayPlayerId" class="player-data">
        <div class="player-head player-head--home">
          <span class="player-name">{{ homePlayerResult?.playerName || '...' }}</span>
          <span class="player-tags">
            <span v-for="tag in homePlayerResult?.matchupTags || []" :key="tag" class="neu-tag neu-tag--blue">{{ tag }}</span>
          </span>
        </div>
        <div class="player-head player-head--away">
          <span class="player-name">{{ awayPlayerResult?.playerName || '...' }}</span>
          <span class="player-tags">
            <span v-for="tag in awayPlayerResult?.matchupTags || []" :key="tag" class="neu-tag neu-tag--red">{{ tag }}</span>
          </span>
        </div>

        <div class="player-cols">
          <div class="data-col data-col--home">
            <div v-for="item in playerCoreRows" :key="item.label" class="data-item">
              <span class="data-val mono-num">{{ formatVal(item.home, item.fmt) }}</span>
              <span class="data-label">{{ item.label }}</span>
            </div>
          </div>
          <div class="data-col data-col--away">
            <div v-for="item in playerCoreRows" :key="item.label" class="data-item">
              <span class="data-val mono-num">{{ formatVal(item.away, item.fmt) }}</span>
              <span class="data-label">{{ item.label }}</span>
            </div>
          </div>
        </div>

        <div class="expand-toggle" @click="playerExpanded = !playerExpanded">
          <el-icon class="toggle-icon" :class="{ 'toggle-icon--rotated': playerExpanded }"><ArrowDown /></el-icon>
          <span>{{ playerExpanded ? '收起球员数据' : '展开更多球员数据' }}</span>
        </div>

        <div v-if="playerExpanded" class="animate-fade-in">
          <div class="player-cols">
            <div class="data-col data-col--home">
              <div v-for="item in playerMoreRows" :key="item.label" class="data-item">
                <span class="data-val mono-num">{{ formatVal(item.home, item.fmt) }}</span>
                <span class="data-label">{{ item.label }}</span>
              </div>
            </div>
            <div class="data-col data-col--away">
              <div v-for="item in playerMoreRows" :key="item.label" class="data-item">
                <span class="data-val mono-num">{{ formatVal(item.away, item.fmt) }}</span>
                <span class="data-label">{{ item.label }}</span>
              </div>
            </div>
          </div>

          <el-table :data="rangeRows" stripe style="width: 100%; margin-top: 16px">
            <el-table-column prop="player" label="球员" min-width="140" />
            <el-table-column prop="low" label="拉胯区间" width="110" align="center">
              <template #default="{ row }"><span class="mono-num text-negative">{{ row.low }}</span></template>
            </el-table-column>
            <el-table-column prop="mid" label="常规区间" width="110" align="center">
              <template #default="{ row }"><span class="mono-num">{{ row.mid }}</span></template>
            </el-table-column>
            <el-table-column prop="high" label="爆发区间" width="110" align="center">
              <template #default="{ row }"><span class="mono-num text-positive">{{ row.high }}</span></template>
            </el-table-column>
            <el-table-column prop="fgPct" label="预测命中率" width="110" align="center">
              <template #default="{ row }"><span class="mono-num">{{ row.fgPct }}</span></template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- ============ 近期交锋 ============ -->
    <div v-if="battleRecords.length" class="neu-card animate-fade-in" style="margin-top: 24px">
      <div class="neu-card-header">
        <span class="title">近期交锋</span>
      </div>
      <div class="battle-list">
        <div v-for="(b, i) in battleRecords" :key="i" class="battle-item">
          <span class="battle-date">{{ b.gameDate || '-' }}</span>
          <span class="battle-teams">
            <TeamLogo :abbr="teamAbbrOf(b.homeTeam)" :size="16" />
            {{ b.homeTeam }} {{ b.homeScore }} - {{ b.awayScore }} {{ b.awayTeam }}
            <TeamLogo :abbr="teamAbbrOf(b.awayTeam)" :size="16" />
          </span>
          <span class="neu-tag neu-tag--gray">{{ b.result || '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { TrendCharts, ArrowDown } from '@element-plus/icons-vue'
import { teamApi, playerApi, dataApi } from '@/api'
import { teamAbbrOf, teamPrimaryColor } from '@/constants/teams'
import { CURRENT_SEASON } from '@/constants'

const route = useRoute()

const form = reactive({
  homeTeamId: null,
  awayTeamId: null,
  homePlayerId: null,
  awayPlayerId: null,
  scene: '常规赛',
})

const teamOptions = ref([])
const teamRecords = ref({})
const teamRanks = ref({})
const homeRoster = ref([])
const awayRoster = ref([])
const predicting = ref(false)
const result = ref(null)
const battleRecords = ref([])
const basicExpanded = ref(false)
const playerExpanded = ref(false)

const homePlayerResult = ref(null)
const awayPlayerResult = ref(null)

const homeTeamName = computed(() => {
  const t = teamOptions.value.find((t) => t.teamId === form.homeTeamId)
  return t ? t.teamName : '主队'
})

const awayTeamName = computed(() => {
  const t = teamOptions.value.find((t) => t.teamId === form.awayTeamId)
  return t ? t.teamName : '客队'
})

const homeTeamAbbr = computed(() => teamOptions.value.find((t) => t.teamId === form.homeTeamId)?.abbreviation || '')
const awayTeamAbbr = computed(() => teamOptions.value.find((t) => t.teamId === form.awayTeamId)?.abbreviation || '')

// 十六进制色 → rgba
const hexA = (hex, alpha) => {
  const h = hex.replace('#', '')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// 发散式背景：队色晕染约占页面 70%，无硬边界
const sideBgStyle = (side) => {
  const abbr = side === 'home' ? homeTeamAbbr.value : awayTeamAbbr.value
  const color = abbr ? teamPrimaryColor(abbr) : '#3A3A3A'
  const pos = side === 'home' ? '18% 10%' : '82% 10%'
  return {
    background: `radial-gradient(ellipse 95% 105% at ${pos}, ${hexA(color, 0.45)} 0%, ${hexA(color, 0.22)} 50%, transparent 78%)`,
  }
}

// 队标后的大号柔光
const glowStyle = (side) => {
  const abbr = side === 'home' ? homeTeamAbbr.value : awayTeamAbbr.value
  const color = teamPrimaryColor(abbr)
  return {
    background: `radial-gradient(circle, ${hexA(color, 0.5)}, transparent 65%)`,
  }
}

// 战绩 / 分区排名
const homeTeamStats = computed(() => teamRecords.value[form.homeTeamId] || null)
const awayTeamStats = computed(() => teamRecords.value[form.awayTeamId] || null)

const homeRecord = computed(() => {
  const s = homeTeamStats.value
  if (!s) return ''
  return `${s.wins}-${s.losses} · ${(s.winPct * 100).toFixed(1)}%`
})

const awayRecord = computed(() => {
  const s = awayTeamStats.value
  if (!s) return ''
  return `${s.wins}-${s.losses} · ${(s.winPct * 100).toFixed(1)}%`
})

const homeRank = computed(() => {
  const r = teamRanks.value[form.homeTeamId]
  return r ? `分区第${r}` : ''
})

const awayRank = computed(() => {
  const r = teamRanks.value[form.awayTeamId]
  return r ? `分区第${r}` : ''
})

// 球员名单映射（season_data 嵌套）
const toRosterCamel = (p) => {
  const s = p.season_data || {}
  return {
    playerId: p.player_id,
    playerName: p.player_name,
    position: p.position,
    pointsPerGame: s.points_per_game ?? null,
    reboundsPerGame: s.rebounds_per_game ?? null,
    assistsPerGame: s.assists_per_game ?? null,
    fgPct: s.fg_percentage ?? null,
    threePct: s.three_percentage ?? null,
    ftPct: s.ft_percentage ?? null,
    trueShootingPct: s.true_shooting_pct ?? null,
    usageRate: s.usage_rate ?? null,
  }
}

const homePlayer = computed(() => homeRoster.value.find((p) => p.playerId === form.homePlayerId) || null)
const awayPlayer = computed(() => awayRoster.value.find((p) => p.playerId === form.awayPlayerId) || null)

// 基本数据（每侧 6 项，先展示）
const basicRows = computed(() => {
  const h = homeTeamStats.value
  const a = awayTeamStats.value
  if (!h || !a) return []
  const signedCls = (v) => (v ?? 0) >= 0 ? 'text-positive' : 'text-negative'
  return [
    { label: '场均得分', home: h.pointsPerGame, away: a.pointsPerGame },
    { label: '场均失分', home: h.oppPointsPerGame, away: a.oppPointsPerGame },
    {
      label: '净效率',
      home: h.netRating,
      away: a.netRating,
      homeCls: signedCls(h.netRating),
      awayCls: signedCls(a.netRating),
    },
    { label: '场均篮板', home: h.reboundsPerGame, away: a.reboundsPerGame },
    { label: '场均助攻', home: h.assistsPerGame, away: a.assistsPerGame },
    { label: '近10场胜率', home: h.recentWinRate, away: a.recentWinRate, fmt: 'pct' },
  ]
})

// 展开后的更多数据
const moreRows = computed(() => {
  const h = homeTeamStats.value
  const a = awayTeamStats.value
  if (!h || !a) return []
  const signedCls = (v) => (v ?? 0) >= 0 ? 'text-positive' : 'text-negative'
  return [
    { label: '进攻效率', home: h.offensiveRating, away: a.offensiveRating },
    { label: '防守效率', home: h.defensiveRating, away: a.defensiveRating },
    { label: '节奏', home: h.pace, away: a.pace },
    { label: '场均篮板', home: h.reboundsPerGame, away: a.reboundsPerGame },
    { label: '场均助攻', home: h.assistsPerGame, away: a.assistsPerGame },
    { label: '命中率', home: h.fgPct, away: a.fgPct, fmt: 'pct' },
    { label: '三分命中率', home: h.threePct, away: a.threePct, fmt: 'pct' },
    { label: '主场战绩', home: h.homeRecord, away: a.homeRecord },
    { label: '客场战绩', home: h.awayRecord, away: a.awayRecord },
  ]
})

// 球员核心/更多数据行
const playerCoreRows = computed(() => {
  const h = homePlayer.value
  const a = awayPlayer.value
  if (!h || !a) return []
  return [
    { label: '场均得分', home: h.pointsPerGame, away: a.pointsPerGame },
    { label: '场均篮板', home: h.reboundsPerGame, away: a.reboundsPerGame },
    { label: '场均助攻', home: h.assistsPerGame, away: a.assistsPerGame },
    { label: '命中率', home: h.fgPct, away: a.fgPct, fmt: 'pct' },
    { label: '三分命中率', home: h.threePct, away: a.threePct, fmt: 'pct' },
    { label: '常规区间预测', home: homePlayerResult.value?.pointsMid ?? null, away: awayPlayerResult.value?.pointsMid ?? null },
  ]
})

const playerMoreRows = computed(() => {
  const h = homePlayer.value
  const a = awayPlayer.value
  if (!h || !a) return []
  return [
    { label: '罚球命中率', home: h.ftPct, away: a.ftPct, fmt: 'pct' },
    { label: '真实命中率', home: h.trueShootingPct, away: a.trueShootingPct, fmt: 'pct' },
    { label: '使用率', home: h.usageRate, away: a.usageRate, fmt: 'pctRaw' },
  ]
})

const homePct = computed(() => ((result.value?.homeWinProb ?? result.value?.home_win_prob ?? 0) * 100).toFixed(1) + '%')
const awayPct = computed(() => ((1 - (result.value?.homeWinProb ?? result.value?.home_win_prob ?? 0)) * 100).toFixed(1) + '%')

// 预测区间：后端按回测残差标准差给出 ±1σ 上下界
const totalRange = computed(() => {
  const low = result.value?.predictTotalScoreLow ?? result.value?.predict_total_score_low
  const high = result.value?.predictTotalScoreHigh ?? result.value?.predict_total_score_high
  return low != null && high != null ? `${low}–${high}` : ''
})

// ---------------- 预测分析报告 ----------------
const analysisData = computed(
  () => result.value?.analysisReport ?? result.value?.analysis_report ?? null,
)
const analysisText = computed(() => analysisData.value?.text || '')
const analysisMethod = computed(() => analysisData.value?.method || '')

// 特征组贡献：后端把预测分差按六个特征层 + 模型基线拆解
const featureContribution = computed(
  () => result.value?.featureContributions ?? result.value?.feature_contributions ?? null,
)

/** 把两队的信号拍平成标签，便于一眼看出谁热谁冷 */
const analysisSignals = computed(() => {
  const data = analysisData.value
  if (!data) return []
  const iconOf = { hot: '↑', cold: '↓', absent: '⚠' }
  const list = []
  for (const side of ['home', 'away']) {
    const team = data[side]?.team_name || ''
    for (const signal of data[side]?.signals || []) {
      list.push({
        key: `${side}-${signal.type}-${signal.name}`,
        type: signal.type,
        label: `${team} ${signal.name} ${iconOf[signal.type] || ''}`,
      })
    }
  }
  return list
})
const homeColor = computed(() => teamPrimaryColor(homeTeamAbbr.value))
const awayColor = computed(() => teamPrimaryColor(awayTeamAbbr.value))

const rangeRows = computed(() => {
  const rows = []
  if (homePlayerResult.value) {
    rows.push({
      player: homePlayerResult.value.playerName,
      low: homePlayerResult.value.pointsLow ?? '-',
      mid: homePlayerResult.value.pointsMid ?? '-',
      high: homePlayerResult.value.pointsHigh ?? '-',
      fgPct: homePlayerResult.value.fgPct != null ? (homePlayerResult.value.fgPct * 100).toFixed(1) + '%' : '-',
    })
  }
  if (awayPlayerResult.value) {
    rows.push({
      player: awayPlayerResult.value.playerName,
      low: awayPlayerResult.value.pointsLow ?? '-',
      mid: awayPlayerResult.value.pointsMid ?? '-',
      high: awayPlayerResult.value.pointsHigh ?? '-',
      fgPct: awayPlayerResult.value.fgPct != null ? (awayPlayerResult.value.fgPct * 100).toFixed(1) + '%' : '-',
    })
  }
  return rows
})

const formatVal = (val, fmt) => {
  if (val == null) return '-'
  if (fmt === 'pct') return (Number(val) * 100).toFixed(1) + '%'
  if (fmt === 'pctRaw') return Number(val).toFixed(1) + '%'
  const n = Number(val)
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

onMounted(async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    teamOptions.value = res.data?.records || []
  } catch (e) {
    console.error(e)
  }
  await loadTeamRecords()
  // 支持从其他页面带主队进入（如球队详情页「预测」按钮）
  const queryHomeId = Number(route.query.homeTeamId)
  if (queryHomeId && teamOptions.value.some((t) => t.teamId === queryHomeId)) {
    form.homeTeamId = queryHomeId
    loadRoster('home')
  }
})

// 加载 30 队战绩并计算分区排名
const loadTeamRecords = async () => {
  try {
    const res = await dataApi.getTeams(CURRENT_SEASON)
    const list = Array.isArray(res.data) ? res.data : res.data?.teams || res.data?.records || []
    const map = {}
    for (const t of list) {
      const s = t.season_data || {}
      map[t.team_id] = {
        wins: s.wins ?? 0,
        losses: s.losses ?? 0,
        winPct: s.win_percentage ?? 0,
        pointsPerGame: s.points_per_game ?? null,
        oppPointsPerGame: s.opponent_points ?? null,
        netRating: s.net_rating ?? null,
        recentWinRate: s.recent_win_rate ?? null,
        offensiveRating: s.offensive_rating ?? null,
        defensiveRating: s.defensive_rating ?? null,
        pace: s.pace ?? null,
        reboundsPerGame: s.rebounds_per_game ?? null,
        assistsPerGame: s.assists_per_game ?? null,
        fgPct: s.fg_percentage ?? null,
        threePct: s.three_percentage ?? null,
        homeRecord: `${s.home_wins ?? 0}-${s.home_losses ?? 0}`,
        awayRecord: `${s.away_wins ?? 0}-${s.away_losses ?? 0}`,
        conference: t.conference,
      }
    }
    teamRecords.value = map
    // 分区内按胜率排名
    const ranks = {}
    for (const conf of ['East', 'West']) {
      const listConf = Object.values(map).filter((x) => x.conference === conf)
      listConf.sort((a, b) => b.winPct - a.winPct)
      listConf.forEach((_, i) => {
        const key = Object.keys(map).find((k) => map[k] === listConf[i])
        if (key != null) ranks[key] = i + 1
      })
    }
    teamRanks.value = ranks
  } catch (e) {
    console.error('加载球队战绩失败', e)
  }
}

const onTeamChange = (side) => {
  if (side === 'home') {
    form.homePlayerId = null
  } else {
    form.awayPlayerId = null
  }
  resetComparison()
  loadRoster(side)
}

const loadRoster = async (side) => {
  const teamId = side === 'home' ? form.homeTeamId : form.awayTeamId
  if (!teamId) {
    if (side === 'home') homeRoster.value = []
    else awayRoster.value = []
    return
  }
  try {
    const res = await dataApi.getTeamRoster(teamId, CURRENT_SEASON)
    const data = res.data || res
    const list = Array.isArray(data) ? data : data.players || data.roster || []
    const mapped = list.map(toRosterCamel).sort((a, b) => (b.pointsPerGame ?? 0) - (a.pointsPerGame ?? 0))
    if (side === 'home') homeRoster.value = mapped
    else awayRoster.value = mapped
  } catch (e) {
    console.error('加载球员名单失败', e)
  }
}

const resetComparison = () => {
  homePlayerResult.value = null
  awayPlayerResult.value = null
  playerExpanded.value = false
}

// 两侧都选了球员 → 自动对位预测
watch(
  () => [form.homePlayerId, form.awayPlayerId],
  async ([homeId, awayId]) => {
    if (homeId && awayId && result.value) {
      await predictPlayer('home')
      await predictPlayer('away')
    } else {
      resetComparison()
    }
  },
)

const handlePredict = async () => {
  if (!form.homeTeamId || !form.awayTeamId) {
    ElMessage.warning('请选择主客队')
    return
  }
  if (form.homeTeamId === form.awayTeamId) {
    ElMessage.warning('主客队不能相同')
    return
  }
  predicting.value = true
  result.value = null
  battleRecords.value = []
  resetComparison()
  try {
    const res = await teamApi.predict({
      homeTeamId: form.homeTeamId,
      awayTeamId: form.awayTeamId,
      scene: form.scene,
      useOdds: false,
    })
    result.value = res.data
    if (res.data?.degraded) {
      ElMessage.warning('算法服务不可用，当前为降级数据（仅队名，无预测数值）')
    } else {
      ElMessage.success('预测完成')
    }
    loadBattleRecords()
  } catch (e) {
    console.error('预测失败', e)
    ElMessage.error('预测失败')
  } finally {
    predicting.value = false
  }
}

const predictPlayer = async (side) => {
  const isHome = side === 'home'
  const playerId = isHome ? form.homePlayerId : form.awayPlayerId
  const opponentId = isHome ? form.awayPlayerId : form.homePlayerId
  try {
    const res = await playerApi.predict({
      playerId,
      opponentPlayerId: opponentId,
      scene: form.scene,
      homeAway: isHome ? 'home' : 'away',
    })
    if (isHome) homePlayerResult.value = res.data
    else awayPlayerResult.value = res.data
    if (res.data?.degraded) {
      ElMessage.warning(`${isHome ? '主队' : '客队'}球员预测：算法服务不可用，当前为降级数据`)
    }
  } catch (e) {
    console.error('球员预测失败', e)
    ElMessage.error(`${isHome ? '主队' : '客队'}球员预测失败`)
  }
}

const loadBattleRecords = async () => {
  try {
    const res = await teamApi.getBattleRecord({
      team1Id: form.homeTeamId,
      team2Id: form.awayTeamId,
      season: CURRENT_SEASON,
    })
    battleRecords.value = res.data?.battle_records || res.data?.records || []
  } catch (e) {
    console.error('加载近期交锋失败', e)
    battleRecords.value = []
  }
}
</script>

<style lang="scss" scoped>
.predict-page {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 140px;
}

// ============ 全局发散背景 ============
.page-glow {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  pointer-events: none;
  z-index: -1;
}

// ============ 对阵头部 ============
.duel-hero {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: stretch;
  gap: 36px;
  padding-top: 0;
}

.hero-side {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  padding: 0 28px 16px;
  min-height: 390px;
}

.duel-glow {
  position: absolute;
  top: 32%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 420px;
  height: 420px;
  border-radius: 50%;
  filter: blur(36px);
  pointer-events: none;
  z-index: 0;
}

.hero-logo-wrap {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 268px;
}

.hero-logo {
  filter: drop-shadow(0 16px 40px rgba(0, 0, 0, 0.55));
}

.hero-meta {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  align-items: center;

  .hero-meta-text {
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.92);
    text-shadow: 0 1px 6px rgba(0, 0, 0, 0.55);
    letter-spacing: 0.5px;
  }
}

.hero-center {
  flex-shrink: 0;
  width: 330px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 32px;
}

// 比分数字分列 VS 圆环两侧，大小与圆环相当
.vs-score-row {
  display: flex;
  align-items: center;
  gap: 32px;

  .score-num {
    font-size: 58px;
    font-weight: 800;
    line-height: 1;
    font-variant-numeric: tabular-nums;

    &--home { color: $color-nba-blue; }
    &--away { color: $color-nba-red; }
  }
}

.score-caption {
  font-size: 11px;
  color: $text-muted;
  letter-spacing: 2px;
  margin-bottom: -10px;
}

.vs-ring {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  border: 1px solid $border-subtle;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 1px;
  color: $text-secondary;
  background: radial-gradient(circle at 32% 30%, $bg-elevated, $bg-card);
  box-shadow: $neu-raised;
}

.predict-main-btn {
  width: 180px;
  height: 40px;
}

.scene-group {
  :deep(.el-radio-button__inner) {
    padding: 9px 22px;
    font-size: 13px;
  }
}

// 下划线式透明选择器（Element Plus 2.6 的 el-select 结构为 .el-select__wrapper）
.frost-select {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 260px;

  :deep(.el-select__wrapper) {
    background: transparent;
    box-shadow: none !important;
    border-radius: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.16);
    padding: 4px 0;
    min-height: 38px;
    transition: border-color $transition-fast;
  }

  :deep(.el-select__wrapper.is-focused) {
    border-bottom-color: rgba(255, 255, 255, 0.5);
  }

  :deep(.el-select__placeholder) {
    color: rgba(255, 255, 255, 0.5);
  }

  :deep(.el-select__selected-item) {
    width: 100%;
    text-align: center;
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  }
}

// ============ 数据区（左右两列往下） ============
.data-zone {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: stretch;
  gap: 10%;
  margin-top: 12px;
  padding: 0 10%;
}

.data-col {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px 20px;

  &--home .data-item {
    align-items: flex-start;
  }

  &--away .data-item {
    align-items: flex-end;
  }
}

.data-item {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .data-val {
    font-size: 26px;
    font-weight: 700;
    color: $text-primary;
    line-height: 1;
  }

  .data-label {
    font-size: 12px;
    color: $text-muted;
  }
}

// 胜率条（数据区第一行位置；宽度小于两侧数据间隔，条左右各自队色）
.winprob-row {
  position: relative;
  z-index: 1;
  width: 28%;
  min-width: 76px;
  margin: 10px auto 0;
  display: flex;
  flex-direction: column;
  gap: 6px;

  .winprob-labels {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    font-weight: 700;
  }

  .winprob-bar-custom {
    display: flex;
    width: 100%;
    height: 16px;
    border-radius: $radius-full;
    overflow: hidden;
    background: $border-light;

    .winprob-fill {
      height: 100%;
      transition: width 0.4s ease;
    }
  }
}

// 展开箭头
.expand-toggle {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 18px;
  padding: 10px;
  font-size: 13px;
  color: $text-secondary;
  cursor: pointer;
  user-select: none;
  transition: color $transition-fast;

  &:hover {
    color: $color-nba-blue;
  }

  .toggle-icon {
    transition: transform $transition-fast;

    &--rotated {
      transform: rotate(180deg);
    }
  }
}

// ============ 球员对位区 ============
.player-zone {
  position: relative;
  z-index: 1;
  margin-top: 28px;
  padding-top: 28px;
  border-top: 1px dashed $border-dark;
}

.player-zone-title {
  font-size: 14px;
  font-weight: 700;
  color: $text-secondary;
  text-align: center;
  letter-spacing: 2px;
  margin-bottom: 20px;
}

.player-selects {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;

  .frost-select {
    max-width: 240px;
  }
}

.player-data {
  margin-top: 24px;
}

.player-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;

  .player-name {
    font-size: 20px;
    font-weight: 700;
    color: $text-primary;
  }

  .player-tags {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    justify-content: center;
  }
}

.player-cols {
  display: flex;
  align-items: stretch;
  gap: 10%;
  padding: 0 10%;
}

// ============ 近期交锋 ============
.battle-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.battle-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .battle-date {
    flex-shrink: 0;
    font-size: 12px;
    color: $text-muted;
    width: 90px;
  }

  .battle-teams {
    flex: 1;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: $text-secondary;
    font-weight: 500;
  }
}

// 响应式
@media (max-width: $breakpoint-lg) {
  .duel-hero {
    flex-direction: column;
    gap: 20px;
  }

  .hero-center {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .data-zone,
  .player-cols {
    flex-direction: column;
    gap: 16px;
  }
}
// 总分与预测区间
.total-range {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  margin-top: -12px;
  font-size: 12px;
  color: $text-secondary;

  b {
    color: $text-primary;
    font-size: 15px;
  }

  .range-hint {
    font-size: 11px;
    color: $text-muted;
  }
}

// ============ 预测分析报告 ============
.analysis-zone {
  position: relative;
  z-index: 1;
  margin-top: 28px;
  padding: 18px 20px;
  background: $bg-elevated;
  border: 1px solid $border-dark;
  border-radius: $radius-md;
}

.analysis-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.analysis-title {
  font-size: 14px;
  font-weight: 700;
  color: $color-nba-blue;
  letter-spacing: 1px;
}

.analysis-method {
  font-size: 11px;
  color: $text-muted;
  text-align: right;
}

.contribution-block {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px dashed $border-dark;
}

.contribution-title {
  margin-bottom: 4px;
  font-size: 12px;
  color: $text-muted;
}

.analysis-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.9;
  color: $text-secondary;
}

.analysis-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.analysis-chip {
  padding: 3px 10px;
  font-size: 12px;
  border-radius: $radius-full;
  border: 1px solid transparent;

  &--hot {
    color: #E6A762;
    border-color: rgba(230, 167, 98, 0.35);
    background: rgba(230, 167, 98, 0.10);
  }

  &--cold {
    color: #7A9CC6;
    border-color: rgba(122, 156, 198, 0.35);
    background: rgba(122, 156, 198, 0.10);
  }

  &--absent {
    color: #C05C5C;
    border-color: rgba(192, 92, 92, 0.35);
    background: rgba(192, 92, 92, 0.10);
  }
}
</style>
