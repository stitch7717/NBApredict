<template>
  <div class="pt-14">
    <section class="max-w-[1200px] mx-auto px-6 py-8">
      <!-- 标题 -->
      <div class="mb-6">
        <h1 class="heading-1 text-text">预测中心</h1>
        <p class="text-sm text-text-muted mt-1">选择两支球队进行对战预测，或选择球员进行个人表现预测</p>
      </div>

      <!-- 球队预测 -->
      <div class="card animate-fade-up mb-6">
        <div class="flex items-center justify-between mb-6">
          <div class="section-header mb-0">
            <h2 class="heading-2 text-text">球队对战预测</h2>
          </div>
          <span class="caption">TEAM PREDICTION</span>
        </div>

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
            :disabled="!homeId || !awayId || homeId === awayId || predicting"
            @click="runTeamPrediction"
          >
            {{ predicting ? '预测中...' : '预测' }}
          </button>
        </div>

        <!-- 预测结果 -->
        <div v-if="teamResult" class="space-y-4">
          <div class="flex items-center justify-center gap-8 py-4">
            <div class="text-center">
              <div class="w-14 h-14 rounded-xl bg-primary/20 flex items-center justify-center text-xl font-black text-primary mb-2">
                {{ teamResult.homeAbbr }}
              </div>
              <div class="text-sm font-medium text-text">{{ teamResult.homeName }}</div>
            </div>

            <div class="text-center px-6">
              <div class="data-value text-text">{{ teamResult.predHome }} - {{ teamResult.predAway }}</div>
              <div class="caption mt-1">预测比分</div>
              <div class="mt-3">
                <span class="tag" :class="teamResult.homeWinPct >= 50 ? 'tag-win' : 'tag-loss'">
                  主胜 {{ teamResult.homeWinPct }}%
                </span>
              </div>
            </div>

            <div class="text-center">
              <div class="w-14 h-14 rounded-xl bg-loss/20 flex items-center justify-center text-xl font-black text-loss mb-2">
                {{ teamResult.awayAbbr }}
              </div>
              <div class="text-sm font-medium text-text">{{ teamResult.awayName }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 球员预测 -->
      <div class="card animate-fade-up" style="animation-delay: 0.1s">
        <div class="flex items-center justify-between mb-6">
          <div class="section-header mb-0">
            <h2 class="heading-2 text-text">球员表现预测</h2>
          </div>
          <span class="caption">PLAYER PREDICTION</span>
        </div>

        <div class="flex items-center gap-4 mb-6">
          <select
            v-model="playerId"
            class="flex-1 bg-surface border border-border rounded-lg px-4 py-2.5 text-sm text-text focus:border-primary focus:outline-none transition-colors"
          >
            <option :value="null" disabled>选择球员</option>
            <option v-for="p in players" :key="p.player_id" :value="p.player_id">
              {{ p.player_name }} ({{ p.position || '-' }}) {{ p.team_abbr || '' }}
            </option>
          </select>

          <button
            class="btn btn-primary"
            :disabled="!playerId || predictingPlayer"
            @click="runPlayerPrediction"
          >
            {{ predictingPlayer ? '预测中...' : '预测' }}
          </button>
        </div>

        <!-- 球员预测结果 -->
        <div v-if="playerResult" class="grid grid-cols-3 gap-4">
          <div class="card-flat text-center py-4">
            <div class="text-lg font-mono text-text-muted">{{ playerResult.points_low }}</div>
            <div class="data-label mt-1">低</div>
          </div>
          <div class="card-flat text-center py-4 ring-1 ring-primary/30">
            <div class="text-3xl font-black text-primary">{{ playerResult.points_mid }}</div>
            <div class="data-label mt-1">预测得分</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-lg font-mono text-text-muted">{{ playerResult.points_high }}</div>
            <div class="data-label mt-1">高</div>
          </div>
          <div class="col-span-3 card-flat">
            <div class="grid grid-cols-3 gap-4 text-center">
              <div>
                <div class="text-sm font-mono text-text">{{ playerResult.fg_pct ? (playerResult.fg_pct * 100).toFixed(1) + '%' : '-' }}</div>
                <div class="data-label">预测命中率</div>
              </div>
              <div>
                <div class="text-sm font-mono text-text">{{ playerResult.total_coeff?.toFixed(3) || '-' }}</div>
                <div class="data-label">综合系数</div>
              </div>
              <div>
                <div class="text-sm font-mono text-text">{{ playerResult.player_name || '-' }}</div>
                <div class="data-label">球员</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTeams, getPlayers } from '../api/data'

const teams = ref([])
const players = ref([])

const homeId = ref(null)
const awayId = ref(null)
const predicting = ref(false)
const teamResult = ref(null)

const playerId = ref(null)
const predictingPlayer = ref(false)
const playerResult = ref(null)

async function runTeamPrediction() {
  if (!homeId.value || !awayId.value) return
  predicting.value = true
  try {
    const { getMatchup } = await import('../api/algorithm')
    const data = await getMatchup(homeId.value, awayId.value)
    const homeTeam = teams.value.find(t => t.team_id === homeId.value)
    const awayTeam = teams.value.find(t => t.team_id === awayId.value)
    teamResult.value = {
      homeAbbr: homeTeam?.abbreviation || '',
      homeName: homeTeam?.team_name || '',
      awayAbbr: awayTeam?.abbreviation || '',
      awayName: awayTeam?.team_name || '',
      predHome: data.predict_home_score || 0,
      predAway: data.predict_away_score || 0,
      homeWinPct: data.coefficients?.home_win_prob ? Math.round(data.coefficients.home_win_prob * 100) : 50,
    }
  } catch (e) {
    console.error('Team prediction failed:', e)
  } finally {
    predicting.value = false
  }
}

async function runPlayerPrediction() {
  if (!playerId.value) return
  predictingPlayer.value = true
  try {
    const { predictPlayer } = await import('../api/algorithm')
    const data = await predictPlayer({ player_id: playerId.value })
    playerResult.value = data
  } catch (e) {
    console.error('Player prediction failed:', e)
  } finally {
    predictingPlayer.value = false
  }
}

onMounted(async () => {
  try {
    const [teamsData, playersData] = await Promise.all([
      getTeams(),
      getPlayers({ limit: 500, sort_by: 'points_per_game' }),
    ])
    teams.value = teamsData || []
    players.value = playersData.items || []
  } catch (e) {
    console.error('Failed to load data:', e)
  }
})
</script>
