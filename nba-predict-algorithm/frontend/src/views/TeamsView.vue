<template>
  <div class="pt-14">
    <section class="max-w-[1200px] mx-auto px-6 py-8">
      <!-- 标题 -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="heading-1 text-text">球队数据</h1>
          <p class="text-sm text-text-muted mt-1">东西部排名 + 球队赛季数据</p>
        </div>
        <div class="flex items-center gap-3">
          <select
            v-model="season"
            class="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
          >
            <option v-for="s in seasons" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
      </div>

      <!-- 东西部排名 -->
      <div class="grid grid-cols-2 gap-6 mb-8">
        <!-- 东部 -->
        <div class="card">
          <div class="section-header">
            <h2 class="heading-3 text-text">东部联盟</h2>
          </div>
          <div class="space-y-1">
            <div
              v-for="(team, i) in eastTeams"
              :key="team.team_id"
              class="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-white/[0.03] transition-colors"
              @click="goToTeam(team.team_id)"
            >
              <span class="w-6 text-xs font-mono text-text-muted text-right">{{ i + 1 }}</span>
              <div class="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center text-xs font-bold text-primary">
                {{ team.abbreviation }}
              </div>
              <span class="flex-1 text-sm font-medium text-text">{{ team.team_name }}</span>
              <span class="text-sm font-mono text-text-secondary">{{ team.wins }}-{{ team.losses }}</span>
              <span class="w-14 text-xs font-mono text-text-muted text-right">{{ team.pct }}</span>
            </div>
          </div>
        </div>

        <!-- 西部 -->
        <div class="card">
          <div class="section-header">
            <h2 class="heading-3 text-text">西部联盟</h2>
          </div>
          <div class="space-y-1">
            <div
              v-for="(team, i) in westTeams"
              :key="team.team_id"
              class="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer hover:bg-white/[0.03] transition-colors"
              @click="goToTeam(team.team_id)"
            >
              <span class="w-6 text-xs font-mono text-text-muted text-right">{{ i + 1 }}</span>
              <div class="w-8 h-8 rounded-lg bg-loss/15 flex items-center justify-center text-xs font-bold text-loss">
                {{ team.abbreviation }}
              </div>
              <span class="flex-1 text-sm font-medium text-text">{{ team.team_name }}</span>
              <span class="text-sm font-mono text-text-secondary">{{ team.wins }}-{{ team.losses }}</span>
              <span class="w-14 text-xs font-mono text-text-muted text-right">{{ team.pct }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 球队数据表 -->
      <div class="card">
        <div class="section-header">
          <h2 class="heading-3 text-text">赛季数据</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border">
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-left whitespace-nowrap">球队</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">联盟</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">胜</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">负</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">胜率</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">进攻效率</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">防守效率</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">净效率</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">节奏</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">TS%</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="team in allTeams"
                :key="team.team_id"
                class="border-b border-border/50 hover:bg-white/[0.03] transition-colors cursor-pointer"
                @click="goToTeam(team.team_id)"
              >
                <td class="px-3 py-3 text-left text-sm text-text">
                  <div class="flex items-center gap-2">
                    <span class="font-medium">{{ team.abbreviation }}</span>
                    <span class="text-xs text-text-muted">{{ team.team_name }}</span>
                  </div>
                </td>
                <td class="px-3 py-3 text-center text-sm text-text-muted">{{ team.conference }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono text-win">{{ team.wins }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono text-loss">{{ team.losses }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ team.pct }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ team.offRtg }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ team.defRtg }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono" :class="team.netRtg > 0 ? 'text-win' : 'text-loss'">
                  {{ team.netRtg > 0 ? '+' : '' }}{{ team.netRtg }}
                </td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ team.pace }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ team.tsPct }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTeams, getStandings } from '../api/data'

const router = useRouter()
const teams = ref([])
const standings = ref([])
const season = ref('2025-26')
const seasons = ['2025-26', '2024-25', '2023-24', '2022-23']

const eastTeams = computed(() => {
  return standings.value
    .filter(t => t.conference === 'East')
    .sort((a, b) => b.win_pct - a.win_pct)
    .map(t => ({
      ...t,
      pct: t.win_pct?.toFixed(3) || '.000',
    }))
})

const westTeams = computed(() => {
  return standings.value
    .filter(t => t.conference === 'West')
    .sort((a, b) => b.win_pct - a.win_pct)
    .map(t => ({
      ...t,
      pct: t.win_pct?.toFixed(3) || '.000',
    }))
})

const allTeams = computed(() => {
  return [...eastTeams.value, ...westTeams.value].map(t => ({
    ...t,
    offRtg: t.offensive_rating?.toFixed(1) || '-',
    defRtg: t.defensive_rating?.toFixed(1) || '-',
    netRtg: t.net_rating?.toFixed(1) || '0',
    pace: t.pace?.toFixed(1) || '-',
    tsPct: t.true_shooting_pct ? (t.true_shooting_pct * 100).toFixed(1) + '%' : '-',
  }))
})

function goToTeam(id) {
  router.push(`/teams/${id}`)
}

onMounted(async () => {
  try {
    const [teamsData, standingsData] = await Promise.all([
      getTeams(),
      getStandings(),
    ])
    teams.value = teamsData || []
    standings.value = standingsData || []
  } catch (e) {
    console.error('Failed to load teams:', e)
  }
})
</script>

