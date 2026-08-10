<template>
  <div class="pt-14">
    <section class="max-w-[1200px] mx-auto px-6 py-8">
      <!-- 标题 -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="heading-1 text-text">球员排名</h1>
          <p class="text-sm text-text-muted mt-1">按赛季数据排序，点击查看详细分析</p>
        </div>
        <div class="flex items-center gap-3">
          <select
            v-model="season"
            class="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
          >
            <option v-for="s in seasons" :key="s" :value="s">{{ s }}</option>
          </select>
          <select
            v-model="sortField"
            class="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text focus:border-primary focus:outline-none"
          >
            <option value="points_per_game">得分</option>
            <option value="rebounds_per_game">篮板</option>
            <option value="assists_per_game">助攻</option>
            <option value="steals_per_game">抢断</option>
            <option value="blocks_per_game">盖帽</option>
            <option value="true_shooting_pct">TS%</option>
            <option value="usage_rate">USG%</option>
          </select>
          <input
            v-model="search"
            type="text"
            placeholder="搜索球员..."
            class="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text w-48 focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <!-- 球员列表 -->
      <div class="card">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border">
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap w-10">#</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-left whitespace-nowrap">球员</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-left whitespace-nowrap">球队</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap">位置</th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('games_played')">
                  GP <span v-if="sortField === 'games_played'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('minutes_per_game')">
                  MPG
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('points_per_game')">
                  PPG <span v-if="sortField === 'points_per_game'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('rebounds_per_game')">
                  RPG
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('assists_per_game')">
                  APG
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('fg_percentage')">
                  FG%
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('true_shooting_pct')">
                  TS%
                </th>
                <th class="px-3 py-3 text-xs font-semibold text-text-muted uppercase tracking-wider text-center whitespace-nowrap cursor-pointer hover:text-primary" @click="sortBy('usage_rate')">
                  USG%
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(player, i) in filteredPlayers"
                :key="player.player_id"
                class="border-b border-border/50 hover:bg-white/[0.03] transition-colors cursor-pointer"
                @click="goToPlayer(player.player_id)"
              >
                <td class="px-3 py-3 text-center text-sm text-text-muted">{{ i + 1 }}</td>
                <td class="px-3 py-3 text-left text-sm text-text">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center text-xs font-bold text-primary">
                      {{ player.player_name?.charAt(0) || '?' }}
                    </div>
                    <span class="font-medium">{{ player.player_name }}</span>
                  </div>
                </td>
                <td class="px-3 py-3 text-left text-sm text-text-secondary">{{ player.team_abbr || '-' }}</td>
                <td class="px-3 py-3 text-center text-sm text-text-muted">{{ player.position || '-' }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ player.games_played }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ player.minutes_per_game }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono font-semibold text-primary">{{ player.points_per_game }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ player.rebounds_per_game }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ player.assists_per_game }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ formatPct(player.fg_percentage) }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ formatPct(player.true_shooting_pct) }}</td>
                <td class="px-3 py-3 text-center text-sm text-text font-mono">{{ formatPct(player.usage_rate) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 加载更多 -->
        <div v-if="hasMore" class="p-4 text-center">
          <button class="btn btn-ghost" @click="loadMore">加载更多</button>
        </div>

        <!-- 空状态 -->
        <div v-if="!loading && filteredPlayers.length === 0" class="py-12 text-center">
          <div class="text-text-muted">暂无数据</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getPlayers } from '../api/data'

const router = useRouter()
const players = ref([])
const loading = ref(false)
const page = ref(1)
const hasMore = ref(true)
const total = ref(0)

const season = ref('2025-26')
const sortField = ref('points_per_game')
const sortDir = ref('desc')
const search = ref('')

const seasons = ['2025-26', '2024-25', '2023-24', '2022-23']

const filteredPlayers = computed(() => {
  let list = [...players.value]
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(p => p.player_name?.toLowerCase().includes(q) || p.team_abbr?.toLowerCase().includes(q))
  }
  return list
})

function formatPct(val) {
  if (!val && val !== 0) return '-'
  return typeof val === 'number' ? (val * 100).toFixed(1) + '%' : val
}

function sortBy(field) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'desc'
  }
  page.value = 1
  players.value = []
  loadPlayers()
}

function goToPlayer(id) {
  router.push(`/players/${id}`)
}

async function loadPlayers() {
  loading.value = true
  try {
    const data = await getPlayers({
      season: season.value,
      sort_by: sortField.value,
      sort_dir: sortDir.value,
      page: page.value,
      limit: 50,
    })
    if (page.value === 1) {
      players.value = data.items || []
    } else {
      players.value = [...players.value, ...(data.items || [])]
    }
    total.value = data.total || 0
    hasMore.value = players.value.length < total.value
  } catch (e) {
    console.error('Failed to load players:', e)
  } finally {
    loading.value = false
  }
}

function loadMore() {
  page.value++
  loadPlayers()
}

watch(season, () => {
  page.value = 1
  players.value = []
  loadPlayers()
})

onMounted(() => {
  loadPlayers()
})
</script>

