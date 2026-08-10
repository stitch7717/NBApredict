<template>
  <div class="card animate-fade-up">
    <!-- 标题栏 -->
    <div class="flex items-center justify-between mb-6">
      <div class="section-header mb-0">
        <h2 class="heading-2 text-text">对位分析</h2>
      </div>
      <span class="caption">PLAYER MATCHUP</span>
    </div>

    <!-- 选球员 -->
    <div class="flex items-center gap-4 mb-6">
      <div class="flex-1">
        <select
          v-model="playerAId"
          class="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text focus:border-primary focus:outline-none transition-colors"
        >
          <option :value="null" disabled>选择球员 A</option>
          <option v-for="p in players" :key="p.player_id" :value="p.player_id">
            {{ p.player_name }} ({{ p.position || '-' }}) {{ p.team_abbr || '' }}
          </option>
        </select>
      </div>

      <div class="flex flex-col items-center gap-1">
        <span class="text-text-muted font-bold text-sm">VS</span>
        <span class="text-[10px] text-text-muted">对位</span>
      </div>

      <div class="flex-1">
        <select
          v-model="playerBId"
          class="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text focus:border-primary focus:outline-none transition-colors"
        >
          <option :value="null" disabled>选择球员 B</option>
          <option v-for="p in players" :key="p.player_id" :value="p.player_id">
            {{ p.player_name }} ({{ p.position || '-' }}) {{ p.team_abbr || '' }}
          </option>
        </select>
      </div>

      <button
        class="btn btn-primary"
        :disabled="!playerAId || !playerBId || playerAId === playerBId"
        @click="runMatchup"
      >
        对位
      </button>
    </div>

    <!-- 对位结果 -->
    <div v-if="result" class="space-y-5">
      <!-- 球员头像区 -->
      <div class="flex items-center justify-center gap-10 py-4">
        <div class="text-center">
          <div class="w-14 h-14 rounded-full bg-primary/15 flex items-center justify-center text-lg font-black text-primary mb-2">
            {{ result.a.jersey || '#' }}
          </div>
          <div class="text-sm font-bold text-text">{{ result.a.name }}</div>
          <div class="caption">{{ result.a.team }} &middot; {{ result.a.position }}</div>
        </div>

        <div class="text-center px-4">
          <div class="caption mb-2">效率对比</div>
          <div class="text-lg font-mono font-bold text-text">
            {{ result.a.effVal }} <span class="text-text-muted">vs</span> {{ result.b.effVal }}
          </div>
        </div>

        <div class="text-center">
          <div class="w-14 h-14 rounded-full bg-loss/15 flex items-center justify-center text-lg font-black text-loss mb-2">
            {{ result.b.jersey || '#' }}
          </div>
          <div class="text-sm font-bold text-text">{{ result.b.name }}</div>
          <div class="caption">{{ result.b.team }} &middot; {{ result.b.position }}</div>
        </div>
      </div>

      <!-- 数据对比条 -->
      <div class="card-flat">
        <div class="caption mb-4">赛季数据对比</div>
        <div class="space-y-3">
          <div v-for="stat in compareStats" :key="stat.label" class="stat-compare">
            <div class="w-12 text-right text-xs font-mono text-primary font-semibold">{{ stat.left }}</div>
            <div class="bar-left">
              <div class="fill" :style="{ width: stat.leftPct + '%' }"></div>
            </div>
            <div class="w-16 text-center text-[11px] text-text-muted font-medium">{{ stat.label }}</div>
            <div class="bar-right">
              <div class="fill" :style="{ width: stat.rightPct + '%' }"></div>
            </div>
            <div class="w-12 text-left text-xs font-mono text-loss font-semibold">{{ stat.right }}</div>
          </div>
        </div>
      </div>

      <!-- 预测 + 高阶数据 -->
      <div class="grid-2">
        <!-- 预测表现 -->
        <div class="card-flat">
          <div class="caption mb-3">球员 A 预测表现</div>
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="data-label">得分区间</span>
              <span class="text-sm font-mono text-text">
                {{ result.a.predLow }} / <span class="text-primary font-bold">{{ result.a.predMid }}</span> / {{ result.a.predHigh }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">预测命中率</span>
              <span class="text-sm font-mono text-text">{{ result.a.fgPct }}%</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">综合系数</span>
              <span class="text-sm font-mono text-text">{{ result.a.totalCoeff }}</span>
            </div>
          </div>
        </div>

        <!-- 高阶数据 -->
        <div class="card-flat">
          <div class="caption mb-3">高阶指标对比</div>
          <div class="space-y-2">
            <div v-for="adv in advancedStats" :key="adv.label" class="flex items-center gap-3">
              <span class="w-12 text-[11px] text-text-muted text-right">{{ adv.label }}</span>
              <span class="flex-1 text-right text-xs font-mono text-primary">{{ adv.left }}</span>
              <span class="w-8 text-center text-[10px] text-text-muted">vs</span>
              <span class="flex-1 text-xs font-mono text-loss">{{ adv.right }}</span>
              <span class="w-12 text-[11px] text-text-muted">{{ adv.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 系数详情 -->
      <div class="card-flat">
        <div class="caption mb-3">修正系数详情</div>
        <div class="grid grid-cols-3 gap-3">
          <div v-for="coeff in coefficients" :key="coeff.label" class="text-center py-2 rounded-lg bg-surface">
            <div class="text-sm font-mono font-bold text-text">{{ coeff.value }}</div>
            <div class="data-label mt-0.5">{{ coeff.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="py-10 text-center">
      <div class="text-text-muted text-sm">选择两名球员进行对位分析</div>
      <div class="text-[11px] text-text-muted mt-1">系统将预测对位场景下的表现差异</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPlayers } from '../../api/data'

const players = ref([])
const playerAId = ref(null)
const playerBId = ref(null)
const result = ref(null)

onMounted(async () => {
  try {
    const data = await getPlayers({ limit: 500, sort_by: 'points_per_game' })
    players.value = data.items || []
  } catch {
    // fallback
  }
})

const compareStats = computed(() => {
  if (!result.value) return []
  const a = result.value.a.stats
  const b = result.value.b.stats
  const max = (l, r) => Math.max(l, r, 1)
  return [
    { label: 'PPG', left: a.ppg, right: b.ppg, leftPct: a.ppg / max(a.ppg, b.ppg) * 100, rightPct: b.ppg / max(a.ppg, b.ppg) * 100 },
    { label: 'RPG', left: a.rpg, right: b.rpg, leftPct: a.rpg / max(a.rpg, b.rpg) * 100, rightPct: b.rpg / max(a.rpg, b.rpg) * 100 },
    { label: 'APG', left: a.apg, right: b.apg, leftPct: a.apg / max(a.apg, b.apg) * 100, rightPct: b.apg / max(a.apg, b.apg) * 100 },
    { label: 'FG%', left: a.fgPct, right: b.fgPct, leftPct: a.fgPct / max(a.fgPct, b.fgPct) * 100, rightPct: b.fgPct / max(a.fgPct, b.fgPct) * 100 },
    { label: 'TS%', left: a.tsPct, right: b.tsPct, leftPct: a.tsPct / max(a.tsPct, b.tsPct) * 100, rightPct: b.tsPct / max(a.tsPct, b.tsPct) * 100 },
    { label: 'MPG', left: a.mpg, right: b.mpg, leftPct: a.mpg / max(a.mpg, b.mpg) * 100, rightPct: b.mpg / max(a.mpg, b.mpg) * 100 },
  ]
})

const advancedStats = computed(() => {
  if (!result.value) return []
  const a = result.value.a.adv
  const b = result.value.b.adv
  return [
    { label: 'USG%', left: a.usg, right: b.usg },
    { label: 'AST%', left: a.astPct, right: b.astPct },
    { label: 'REB%', left: a.rebPct, right: b.rebPct },
    { label: 'STL%', left: a.stlPct, right: b.stlPct },
    { label: 'BLK%', left: a.blkPct, right: b.blkPct },
    { label: 'TOV%', left: a.tovPct, right: b.tovPct },
  ]
})

const coefficients = computed(() => {
  if (!result.value) return []
  const c = result.value.a.coeffs
  return [
    { label: '全明星', value: c.allStar },
    { label: '老将', value: c.veteran },
    { label: '伤病', value: c.injury },
    { label: '关键球', value: c.clutch },
    { label: '主场', value: c.home },
    { label: '疲劳', value: c.fatigue },
  ]
})

async function runMatchup() {
  if (!playerAId.value || !playerBId.value) return
  try {
    const { predictPlayer } = await import('../../api/algorithm')
    const [predA, predB] = await Promise.all([
      predictPlayer({ player_id: playerAId.value, opponent_player_id: playerBId.value, scene: '常规赛', home_away: 'home' }),
      predictPlayer({ player_id: playerBId.value, opponent_player_id: playerAId.value, scene: '常规赛', home_away: 'away' }),
    ])

    const pA = players.value.find(p => p.player_id === playerAId.value) || {}
    const pB = players.value.find(p => p.player_id === playerBId.value) || {}

    result.value = {
      a: buildPlayerResult(predA, pA),
      b: buildPlayerResult(predB, pB),
    }
  } catch (e) {
    console.error('Matchup failed:', e)
  }
}

function buildPlayerResult(pred, playerInfo) {
  return {
    name: pred.player_name || playerInfo.player_name || '-',
    team: playerInfo.team_abbr || '-',
    position: playerInfo.position || '-',
    jersey: playerInfo.jersey_number ? `#${playerInfo.jersey_number}` : '#',
    predLow: pred.points_low || 0,
    predMid: pred.points_mid || 0,
    predHigh: pred.points_high || 0,
    fgPct: pred.fg_pct ? (pred.fg_pct * 100).toFixed(1) : '-',
    totalCoeff: pred.total_coeff ? pred.total_coeff.toFixed(3) : '-',
    effVal: pred.points_mid || 0,
    stats: {
      ppg: playerInfo.points_per_game || 0,
      rpg: playerInfo.rebounds_per_game || 0,
      apg: playerInfo.assists_per_game || 0,
      fgPct: playerInfo.fg_percentage ? (playerInfo.fg_percentage * 100).toFixed(1) : 0,
      tsPct: playerInfo.true_shooting_pct ? (playerInfo.true_shooting_pct * 100).toFixed(1) : 0,
      mpg: playerInfo.minutes_per_game || 0,
    },
    adv: {
      usg: playerInfo.usage_rate ? playerInfo.usage_rate.toFixed(1) : '-',
      astPct: playerInfo.assist_pct ? playerInfo.assist_pct.toFixed(1) : '-',
      rebPct: playerInfo.rebound_pct ? playerInfo.rebound_pct.toFixed(1) : '-',
      stlPct: playerInfo.steal_pct ? playerInfo.steal_pct.toFixed(1) : '-',
      blkPct: playerInfo.block_pct ? playerInfo.block_pct.toFixed(1) : '-',
      tovPct: playerInfo.turnover_pct ? playerInfo.turnover_pct.toFixed(1) : '-',
    },
    coeffs: {
      allStar: pred.all_star_coeff ? pred.all_star_coeff.toFixed(3) : '-',
      veteran: pred.veteran_coeff ? pred.veteran_coeff.toFixed(3) : '-',
      injury: pred.injury_coeff ? pred.injury_coeff.toFixed(3) : '-',
      clutch: pred.clutch_coeff ? pred.clutch_coeff.toFixed(3) : '-',
      home: pred.home_coeff ? pred.home_coeff.toFixed(3) : '-',
      fatigue: pred.fatigue_coeff ? pred.fatigue_coeff.toFixed(3) : '-',
    },
  }
}
</script>
