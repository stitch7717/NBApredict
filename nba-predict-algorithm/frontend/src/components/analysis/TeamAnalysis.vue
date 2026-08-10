<template>
  <div class="card animate-fade-up">
    <!-- 标题栏 -->
    <div class="flex items-center justify-between mb-6">
      <div class="section-header mb-0">
        <h2 class="heading-2 text-text">球队分析</h2>
      </div>
      <span class="caption">TEAM ANALYSIS</span>
    </div>

    <!-- 选队 -->
    <div class="flex items-center gap-4 mb-6">
      <select
        v-model="homeId"
        class="flex-1 bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text focus:border-primary focus:outline-none transition-colors"
      >
        <option :value="null" disabled>选择主队</option>
        <option v-for="t in teams" :key="t.team_id" :value="t.team_id">
          {{ t.abbreviation }} - {{ t.team_name }}
        </option>
      </select>

      <div class="text-text-muted font-bold text-sm">VS</div>

      <select
        v-model="awayId"
        class="flex-1 bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text focus:border-primary focus:outline-none transition-colors"
      >
        <option :value="null" disabled>选择客队</option>
        <option v-for="t in teams" :key="t.team_id" :value="t.team_id">
          {{ t.abbreviation }} - {{ t.team_name }}
        </option>
      </select>

      <button
        class="btn btn-primary"
        :disabled="!homeId || !awayId || homeId === awayId"
        @click="runAnalysis"
      >
        分析
      </button>
    </div>

    <!-- 分析结果 -->
    <div v-if="result" class="space-y-6">
      <!-- 对决头部 -->
      <div class="flex items-center justify-center gap-8 py-6">
        <div class="text-center">
          <div class="w-16 h-16 rounded-xl bg-primary/20 flex items-center justify-center text-2xl font-black text-primary mb-2">
            {{ result.home.abbr }}
          </div>
          <div class="text-sm font-medium text-text">{{ result.home.name }}</div>
          <div class="caption mt-1">主场</div>
        </div>

        <div class="text-center px-6">
          <div class="data-value text-text">{{ result.predHome }} - {{ result.predAway }}</div>
          <div class="caption mt-1">预测比分</div>
          <div class="mt-3">
            <span class="tag" :class="result.homeWinPct >= 50 ? 'tag-win' : 'tag-loss'">
              主胜 {{ result.homeWinPct }}%
            </span>
          </div>
        </div>

        <div class="text-center">
          <div class="w-16 h-16 rounded-xl bg-loss/20 flex items-center justify-center text-2xl font-black text-loss mb-2">
            {{ result.away.abbr }}
          </div>
          <div class="text-sm font-medium text-text">{{ result.away.name }}</div>
          <div class="caption mt-1">客场</div>
        </div>
      </div>

      <!-- 攻防对比条 -->
      <div class="card-flat">
        <div class="caption mb-4">攻防效率对比</div>
        <div class="space-y-3">
          <div v-for="stat in compareStats" :key="stat.label" class="stat-compare">
            <div class="w-10 text-right text-xs font-mono text-primary font-semibold">{{ stat.left }}</div>
            <div class="bar-left">
              <div class="fill" :style="{ width: stat.leftPct + '%' }"></div>
            </div>
            <div class="w-20 text-center text-[11px] text-text-muted font-medium">{{ stat.label }}</div>
            <div class="bar-right">
              <div class="fill" :style="{ width: stat.rightPct + '%' }"></div>
            </div>
            <div class="w-10 text-left text-xs font-mono text-loss font-semibold">{{ stat.right }}</div>
          </div>
        </div>
      </div>

      <!-- 风格克制 + 关键对位 -->
      <div class="grid-2">
        <!-- 风格克制 -->
        <div class="card-flat">
          <div class="caption mb-3">风格克制</div>
          <div class="text-sm text-text mb-2">{{ result.styleMatchup }}</div>
          <div class="space-y-2 mt-4">
            <div v-for="tag in result.matchupTags" :key="tag" class="tag tag-info">{{ tag }}</div>
          </div>
        </div>

        <!-- 关键球员对位 -->
        <div class="card-flat">
          <div class="caption mb-3">关键球员对位</div>
          <div class="space-y-3">
            <div
              v-for="duel in result.keyDuels"
              :key="duel.position"
              class="flex items-center gap-3"
            >
              <div class="w-7 text-center text-[11px] text-text-muted font-bold">{{ duel.position }}</div>
              <div class="flex-1 text-right text-sm text-text">{{ duel.homePlayer }}</div>
              <div class="w-12 text-center text-xs font-mono text-text-muted">{{ duel.homeVal }} vs {{ duel.awayVal }}</div>
              <div class="flex-1 text-sm text-text">{{ duel.awayPlayer }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 历史交锋 -->
      <div class="card-flat">
        <div class="caption mb-3">本赛季交锋记录</div>
        <div class="flex items-center gap-6">
          <div class="text-center">
            <div class="text-2xl font-bold text-win">{{ result.h2h.homeWins }}</div>
            <div class="data-label">{{ result.home.abbr }} 胜</div>
          </div>
          <div class="flex-1">
            <div class="progress-bar">
              <div class="fill bg-win" :style="{ width: result.h2h.homeWinPct + '%' }"></div>
            </div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-loss">{{ result.h2h.awayWins }}</div>
            <div class="data-label">{{ result.away.abbr }} 胜</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="py-12 text-center">
      <div class="text-text-muted text-sm">选择两支球队开始球队分析</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getTeams } from '../../api/data'

const teams = ref([])
const homeId = ref(null)
const awayId = ref(null)
const result = ref(null)

onMounted(async () => {
  try {
    teams.value = await getTeams()
  } catch {
    // fallback
  }
})

const compareStats = computed(() => {
  if (!result.value) return []
  const h = result.value.home
  const a = result.value.away
  return [
    { label: '进攻效率', left: h.offRtg, right: a.offRtg, leftPct: h.offRtg / 1.3, rightPct: a.offRtg / 1.3 },
    { label: '防守效率', left: h.defRtg, right: a.defRtg, leftPct: (130 - h.defRtg) / 30 * 100, rightPct: (130 - a.defRtg) / 30 * 100 },
    { label: '节奏', left: h.pace, right: a.pace, leftPct: h.pace / 1.1, rightPct: a.pace / 1.1 },
    { label: '净效率', left: h.netRtg > 0 ? '+' + h.netRtg : h.netRtg, right: a.netRtg > 0 ? '+' + a.netRtg : a.netRtg, leftPct: Math.max(0, (h.netRtg + 10) / 20 * 100), rightPct: Math.max(0, (a.netRtg + 10) / 20 * 100) },
    { label: 'TS%', left: h.tsPct, right: a.tsPct, leftPct: h.tsPct / 0.7 * 100, rightPct: a.tsPct / 0.7 * 100 },
  ]
})

async function runAnalysis() {
  if (!homeId.value || !awayId.value || homeId.value === awayId.value) return
  try {
    const { getMatchup } = await import('../../api/algorithm')
    const data = await getMatchup(homeId.value, awayId.value)

    const homeTeam = teams.value.find(t => t.team_id === homeId.value)
    const awayTeam = teams.value.find(t => t.team_id === awayId.value)

    // 获取两队数据
    const { getTeam } = await import('../../api/data')
    const [homeData, awayData] = await Promise.all([
      getTeam(homeId.value),
      getTeam(awayId.value),
    ])

    const hs = homeData.season_data || {}
    const as_ = awayData.season_data || {}

    result.value = {
      home: { abbr: homeTeam?.abbreviation || '', name: homeTeam?.team_name || '', offRtg: hs.offensive_rating || 0, defRtg: hs.defensive_rating || 0, pace: hs.pace || 0, netRtg: hs.net_rating || 0, tsPct: hs.true_shooting_pct || 0 },
      away: { abbr: awayTeam?.abbreviation || '', name: awayTeam?.team_name || '', offRtg: as_.offensive_rating || 0, defRtg: as_.defensive_rating || 0, pace: as_.pace || 0, netRtg: as_.net_rating || 0, tsPct: as_.true_shooting_pct || 0 },
      predHome: data.predict_home_score || 0,
      predAway: data.predict_away_score || 0,
      homeWinPct: data.coefficients?.home_win_prob ? Math.round(data.coefficients.home_win_prob * 100) : 55,
      styleMatchup: data.style_matchup || '数据加载中...',
      matchupTags: data.matchup_tags || [],
      keyDuels: [
        { position: 'PG', homePlayer: '-', awayPlayer: '-', homeVal: '-', awayVal: '-' },
        { position: 'SG', homePlayer: '-', awayPlayer: '-', homeVal: '-', awayVal: '-' },
        { position: 'SF', homePlayer: '-', awayPlayer: '-', homeVal: '-', awayVal: '-' },
        { position: 'PF', homePlayer: '-', awayPlayer: '-', homeVal: '-', awayVal: '-' },
        { position: 'C', homePlayer: '-', awayPlayer: '-', homeVal: '-', awayVal: '-' },
      ],
      h2h: { homeWins: 0, awayWins: 0, homeWinPct: 50 },
    }
  } catch (e) {
    console.error('Analysis failed:', e)
  }
}
</script>
