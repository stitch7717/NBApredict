<template>
  <div class="pt-14">
    <section class="max-w-[1200px] mx-auto px-6 py-8">
      <!-- 返回按钮 -->
      <button class="btn btn-ghost mb-6" @click="$router.back()">
        &larr; 返回
      </button>

      <div v-if="team" class="space-y-6">
        <!-- 球队头部 -->
        <div class="card animate-fade-up">
          <div class="flex items-center gap-6">
            <div class="w-20 h-20 rounded-2xl bg-primary/20 flex items-center justify-center text-3xl font-black text-primary">
              {{ team.abbreviation }}
            </div>
            <div>
              <h1 class="text-2xl font-bold text-text">{{ team.team_name }}</h1>
              <div class="flex items-center gap-3 mt-1">
                <span class="text-sm text-text-secondary">{{ team.conference }} 联盟</span>
                <span class="text-sm text-text-muted">{{ team.division || '' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 战绩 -->
        <div class="grid grid-cols-4 gap-4 animate-fade-up" style="animation-delay: 0.1s">
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-black text-win">{{ team.wins || 0 }}</div>
            <div class="data-label mt-1">胜</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-black text-loss">{{ team.losses || 0 }}</div>
            <div class="data-label mt-1">负</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-bold text-text">{{ winPct }}</div>
            <div class="data-label mt-1">胜率</div>
          </div>
          <div class="card-flat text-center py-4">
            <div class="text-2xl font-bold" :class="netRtg > 0 ? 'text-win' : 'text-loss'">
              {{ netRtg > 0 ? '+' : '' }}{{ netRtg }}
            </div>
            <div class="data-label mt-1">净效率</div>
          </div>
        </div>

        <!-- 效率数据 -->
        <div v-if="seasonData" class="card animate-fade-up" style="animation-delay: 0.15s">
          <div class="section-header">
            <h2 class="heading-3 text-text">赛季效率</h2>
          </div>
          <div class="grid grid-cols-2 gap-6">
            <div>
              <div class="caption mb-3">进攻端</div>
              <div class="space-y-2">
                <div v-for="stat in offenseStats" :key="stat.label" class="flex items-center justify-between py-1">
                  <span class="data-label">{{ stat.label }}</span>
                  <span class="text-sm font-mono text-text">{{ stat.value }}</span>
                </div>
              </div>
            </div>
            <div>
              <div class="caption mb-3">防守端</div>
              <div class="space-y-2">
                <div v-for="stat in defenseStats" :key="stat.label" class="flex items-center justify-between py-1">
                  <span class="data-label">{{ stat.label }}</span>
                  <span class="text-sm font-mono text-text">{{ stat.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 阵容 -->
        <div class="card animate-fade-up" style="animation-delay: 0.2s">
          <div class="section-header">
            <h2 class="heading-3 text-text">球队阵容</h2>
          </div>
          <div v-if="roster.length > 0" class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-border">
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-left whitespace-nowrap">球员</th>
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">位置</th>
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">GP</th>
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">PPG</th>
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">RPG</th>
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">APG</th>
                  <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">FG%</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="p in roster"
                  :key="p.player_id"
                  class="border-b border-border/50 hover:bg-white/[0.03] transition-colors cursor-pointer"
                  @click="$router.push(`/players/${p.player_id}`)"
                >
                  <td class="px-3 py-3 text-left text-sm text-text font-medium">{{ p.player_name }}</td>
                  <td class="px-3 py-3 text-center text-sm text-text-muted">{{ p.position || '-' }}</td>
                  <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ p.games_played }}</td>
                  <td class="px-3 py-3 text-center text-sm text-text font-mono font-semibold text-primary">{{ p.points_per_game }}</td>
                  <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ p.rebounds_per_game }}</td>
                  <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ p.assists_per_game }}</td>
                  <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ formatPct(p.fg_percentage) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="py-6 text-center text-text-muted">暂无阵容数据</div>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getTeam, getTeamRoster } from '../api/data'

const route = useRoute()
const team = ref(null)
const seasonData = ref(null)
const roster = ref([])
const loading = ref(false)

const winPct = computed(() => {
  if (!team.value) return '.000'
  const w = team.value.wins || 0
  const l = team.value.losses || 0
  return (w / Math.max(w + l, 1)).toFixed(3)
})

const netRtg = computed(() => {
  return seasonData.value?.net_rating?.toFixed(1) || '0'
})

const offenseStats = computed(() => {
  if (!seasonData.value) return []
  const d = seasonData.value
  return [
    { label: '进攻效率', value: d.offensive_rating?.toFixed(1) || '-' },
    { label: '节奏', value: d.pace?.toFixed(1) || '-' },
    { label: 'TS%', value: d.true_shooting_pct ? (d.true_shooting_pct * 100).toFixed(1) + '%' : '-' },
    { label: 'eFG%', value: d.effective_fg_pct ? (d.effective_fg_pct * 100).toFixed(1) + '%' : '-' },
  ]
})

const defenseStats = computed(() => {
  if (!seasonData.value) return []
  const d = seasonData.value
  return [
    { label: '防守效率', value: d.defensive_rating?.toFixed(1) || '-' },
    { label: '对手TS%', value: '-' },
    { label: 'DRB%', value: '-' },
    { label: 'STL%', value: '-' },
  ]
})

function formatPct(val) {
  if (!val && val !== 0) return '-'
  return typeof val === 'number' ? (val * 100).toFixed(1) + '%' : val
}

onMounted(async () => {
  loading.value = true
  try {
    const [teamData, rosterData] = await Promise.all([
      getTeam(route.params.id),
      getTeamRoster(route.params.id),
    ])
    team.value = teamData
    seasonData.value = teamData.season_data || null
    roster.value = rosterData || []
  } catch (e) {
    console.error('Failed to load team:', e)
  } finally {
    loading.value = false
  }
})
</script>

