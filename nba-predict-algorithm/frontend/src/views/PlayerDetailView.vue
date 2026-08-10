<template>
  <div class="pt-14">
    <section class="max-w-[1200px] mx-auto px-6 py-8">
      <!-- 返回按钮 -->
      <button class="btn btn-ghost mb-6" @click="$router.back()">
        &larr; 返回
      </button>

      <div v-if="player" class="space-y-6">
        <!-- 球员头部 -->
        <div class="card animate-fade-up">
          <div class="flex items-center gap-6">
            <div class="w-20 h-20 rounded-2xl bg-primary/15 flex items-center justify-center text-3xl font-black text-primary">
              {{ player.jersey_number ? '#' + player.jersey_number : player.player_name?.charAt(0) }}
            </div>
            <div>
              <h1 class="text-2xl font-bold text-text">{{ player.player_name }}</h1>
              <div class="flex items-center gap-3 mt-1">
                <span class="text-sm text-text-secondary">{{ player.team_abbr }}</span>
                <span class="text-sm text-text-muted">{{ player.position || '-' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 赛季数据 -->
        <div v-if="seasonData" class="grid grid-cols-4 gap-4 animate-fade-up" style="animation-delay: 0.1s">
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-black text-primary">{{ seasonData.points_per_game }}</div>
            <div class="data-label mt-1">PPG</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-bold text-text">{{ seasonData.rebounds_per_game }}</div>
            <div class="data-label mt-1">RPG</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-bold text-text">{{ seasonData.assists_per_game }}</div>
            <div class="data-label mt-1">APG</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-bold text-text">{{ formatPct(seasonData.fg_percentage) }}</div>
            <div class="data-label mt-1">FG%</div>
          </div>
        </div>

        <!-- 详细数据表 -->
        <div v-if="seasonData" class="card animate-fade-up" style="animation-delay: 0.15s">
          <div class="section-header">
            <h2 class="heading-3 text-text">赛季详细数据</h2>
            <select
              v-model="selectedSeason"
              class="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm text-text focus:border-primary focus:outline-none"
            >
              <option v-for="s in availableSeasons" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-6">
            <!-- 基础数据 -->
            <div>
              <div class="caption mb-3">基础数据</div>
              <div class="space-y-2">
                <div v-for="stat in basicStats" :key="stat.label" class="flex items-center justify-between py-1">
                  <span class="data-label">{{ stat.label }}</span>
                  <span class="text-sm font-mono text-text">{{ stat.value }}</span>
                </div>
              </div>
            </div>

            <!-- 高阶数据 -->
            <div>
              <div class="caption mb-3">高阶指标</div>
              <div class="space-y-2">
                <div v-for="stat in advancedStats" :key="stat.label" class="flex items-center justify-between py-1">
                  <span class="data-label">{{ stat.label }}</span>
                  <span class="text-sm font-mono text-text">{{ stat.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 预测 -->
        <div class="card animate-fade-up" style="animation-delay: 0.2s">
          <div class="section-header">
            <h2 class="heading-3 text-text">预测分析</h2>
          </div>
          <div v-if="prediction" class="grid grid-cols-3 gap-4">
            <div class="card-flat text-center py-4">
              <div class="text-lg font-mono text-text-muted">{{ prediction.points_low }}</div>
              <div class="data-label mt-1">低</div>
            </div>
            <div class="card-flat text-center py-4 ring-1 ring-primary/30">
              <div class="text-2xl font-black text-primary">{{ prediction.points_mid }}</div>
              <div class="data-label mt-1">预测得分</div>
            </div>
            <div class="card-flat text-center py-4">
              <div class="text-lg font-mono text-text-muted">{{ prediction.points_high }}</div>
              <div class="data-label mt-1">高</div>
            </div>
          </div>
          <div v-else class="py-6 text-center">
            <button class="btn btn-primary" @click="runPrediction" :disabled="predicting">
              {{ predicting ? '预测中...' : '运行预测' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-else-if="loading" class="py-20 text-center">
        <div class="text-text-muted">加载中...</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getPlayer } from '../api/data'

const route = useRoute()
const player = ref(null)
const seasonData = ref(null)
const allSeasonData = ref([])
const selectedSeason = ref('2025-26')
const loading = ref(false)
const prediction = ref(null)
const predicting = ref(false)

const availableSeasons = computed(() => {
  return allSeasonData.value.map(d => d.season).sort().reverse()
})

const basicStats = computed(() => {
  if (!seasonData.value) return []
  const d = seasonData.value
  return [
    { label: 'GP', value: d.games_played },
    { label: 'MPG', value: d.minutes_per_game },
    { label: 'PPG', value: d.points_per_game },
    { label: 'RPG', value: d.rebounds_per_game },
    { label: 'APG', value: d.assists_per_game },
    { label: 'SPG', value: d.steals_per_game },
    { label: 'BPG', value: d.blocks_per_game },
    { label: 'TOPG', value: d.turnovers_per_game },
  ]
})

const advancedStats = computed(() => {
  if (!seasonData.value) return []
  const d = seasonData.value
  return [
    { label: 'FG%', value: formatPct(d.fg_percentage) },
    { label: '3P%', value: formatPct(d.three_percentage) },
    { label: 'FT%', value: formatPct(d.ft_percentage) },
    { label: 'TS%', value: formatPct(d.true_shooting_pct) },
    { label: 'eFG%', value: formatPct(d.effective_fg_pct) },
    { label: 'USG%', value: formatPct(d.usage_rate) },
    { label: 'AST%', value: formatPct(d.assist_pct) },
    { label: 'REB%', value: formatPct(d.rebound_pct) },
  ]
})

function formatPct(val) {
  if (!val && val !== 0) return '-'
  return typeof val === 'number' ? (val * 100).toFixed(1) + '%' : val
}

async function loadPlayer() {
  loading.value = true
  try {
    const data = await getPlayer(route.params.id)
    player.value = data
    allSeasonData.value = data.season_data || []
    if (allSeasonData.value.length > 0) {
      selectedSeason.value = allSeasonData.value[0].season
      seasonData.value = allSeasonData.value[0]
    }
  } catch (e) {
    console.error('Failed to load player:', e)
  } finally {
    loading.value = false
  }
}

watch(selectedSeason, (val) => {
  seasonData.value = allSeasonData.value.find(d => d.season === val) || null
  prediction.value = null
})

async function runPrediction() {
  predicting.value = true
  try {
    const { predictPlayer } = await import('../api/algorithm')
    const data = await predictPlayer({ player_id: parseInt(route.params.id) })
    prediction.value = data
  } catch (e) {
    console.error('Prediction failed:', e)
  } finally {
    predicting.value = false
  }
}

onMounted(() => {
  loadPlayer()
})
</script>
