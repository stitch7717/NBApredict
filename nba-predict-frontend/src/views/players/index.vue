<template>
  <div class="players-page">
    <h2 class="page-title">球员数据</h2>

    <!-- 筛选栏 -->
    <div class="search-bar">
      <el-select
        v-model="season"
        placeholder="赛季"
        style="width: 130px"
        @change="loadPlayers"
      >
        <el-option
          v-for="s in SEASONS"
          :key="s"
          :label="s"
          :value="s"
        />
      </el-select>
      <el-select
        v-model="teamFilter"
        filterable
        clearable
        placeholder="球队筛选"
        style="width: 160px"
        @change="loadPlayers"
      >
        <el-option
          v-for="t in teamOptions"
          :key="t.teamId"
          :label="t.teamName"
          :value="t.teamId"
        >
          <span class="team-cell">
            <TeamLogo :abbr="t.abbreviation || ''" :size="20" />
            <span>{{ t.teamName }}</span>
          </span>
        </el-option>
      </el-select>
      <el-select
        v-model="positionFilter"
        clearable
        placeholder="位置筛选"
        style="width: 140px"
        @change="loadPlayers"
      >
        <el-option label="后卫 (PG/SG)" value="backcourt" />
        <el-option label="前场 (SF/PF/C)" value="frontcourt" />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="搜索球员姓名..."
        clearable
        style="width: 200px"
        @keyup.enter="loadPlayers"
        @clear="loadPlayers"
      />
      <el-button type="primary" @click="loadPlayers">
        <el-icon><Search /></el-icon>搜索
      </el-button>
    </div>

    <!-- 数据表 -->
    <div class="neu-card" style="padding: 0; overflow: hidden">
      <el-table
        :data="players"
        v-loading="loading"
        stripe
        style="width: 100%"
        @row-click="goToPlayerDetail"
        @sort-change="onSortChange"
        :default-sort="{ prop: 'pointsPerGame', order: 'descending' }"
      >
        <el-table-column
          prop="playerName"
          label="球员名"
          width="150"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="player-name-cell">{{ row.playerName }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="position"
          label="位置"
          width="80"
        >
          <template #default="{ row }">
            <span class="neu-tag" :class="positionTagClass(row.position)">{{ row.position || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="teamName"
          label="球队"
          width="130"
        >
          <template #default="{ row }">
            <span class="team-cell">
              <TeamLogo :abbr="row.teamAbbr || ''" :size="22" />
              <span>{{ row.teamName || '-' }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="gamesPlayed"
          label="场次"
          width="80"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ row.gamesPlayed || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="pointsPerGame"
          label="得分"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="stat-highlight mono-num">{{ formatStat(row.pointsPerGame) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="reboundsPerGame"
          label="篮板"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.reboundsPerGame) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="assistsPerGame"
          label="助攻"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.assistsPerGame) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="fieldGoalPct"
          label="命中率"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.fieldGoalPct) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="threePtPct"
          label="三分%"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.threePtPct) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="per"
          label="PER"
          width="80"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.per) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="usageRate"
          label="使用率"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.usageRate) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="limit"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadPlayers"
        @size-change="loadPlayers"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { teamApi } from '@/api'
import { dataApi } from '@/api'
import { SEASONS } from '@/constants'

const router = useRouter()
const season = ref(SEASONS[0])
const teamFilter = ref('')
const positionFilter = ref('')
const keyword = ref('')
const sortBy = ref('pointsPerGame')
const sortOrder = ref('desc')

const players = ref([])
const teamOptions = ref([])
const teamMap = ref({})
const loading = ref(false)
const page = ref(1)
const limit = ref(20)
const total = ref(0)

onMounted(async () => {
  await loadTeams()
  loadPlayers()
})

const loadTeams = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    const records = res.data?.records || []
    teamOptions.value = records
    for (const t of records) {
      if (t.teamId != null) {
        teamMap.value[t.teamId] = t
      }
    }
  } catch (e) {
    console.error(e)
  }
}

// 位置字段兼容多位置（如 "PG,SG" / "SF-PF"），取第一个
const firstPosition = (pos) => {
  if (!pos) return ''
  return String(pos).split(/[/,、\-]/)[0].trim().toUpperCase()
}

// 驼峰 → 下划线映射（前端展示字段 → Python API 排序字段）
const SORT_FIELD_MAP = {
  pointsPerGame: 'points_per_game',
  reboundsPerGame: 'rebounds_per_game',
  assistsPerGame: 'assists_per_game',
  fieldGoalPct: 'fg_percentage',
  threePointPct: 'three_percentage',
  per: 'per',
  usageRate: 'usage_rate',
}

// 下划线 → 驼峰映射（Python API 响应 → 前端展示字段）
// 注意：百分比保持原始小数（0.471），由 formatPct 统一乘 100
const toCamel = (row) => {
  const team = teamMap.value[row.team_id]
  return {
    playerId: row.player_id,
    playerName: row.player_name,
    playerNameEn: row.player_name_en,
    position: firstPosition(row.position),
    teamId: row.team_id,
    teamName: team?.teamName || row.team_name || '',
    teamAbbr: team?.abbreviation || '',
    age: row.age,
    height: row.height,
    weight: row.weight,
    gamesPlayed: row.games_played,
    pointsPerGame: row.points_per_game,
    reboundsPerGame: row.rebounds_per_game,
    assistsPerGame: row.assists_per_game,
    stealsPerGame: row.steals_per_game,
    blocksPerGame: row.blocks_per_game,
    turnoversPerGame: row.turnovers_per_game,
    minutesPerGame: row.minutes_per_game,
    fieldGoalPct: row.fg_percentage ?? null,
    threePointPct: row.three_percentage ?? null,
    ftPercentage: row.ft_percentage ?? null,
    per: row.per,
    trueShootingPct: row.true_shooting_pct,
    usageRate: row.usage_rate,
    offensiveRating: row.offensive_rating,
    defensiveRating: row.defensive_rating,
    netRating: row.net_rating,
    effectiveFgPct: row.effective_fg_pct,
  }
}

const loadPlayers = async () => {
  loading.value = true
  try {
    const params = {
      season: season.value,
      sort_by: SORT_FIELD_MAP[sortBy.value] || 'points_per_game',
      order: sortOrder.value === 'asc' ? 'asc' : 'desc',
      page: page.value,
      limit: limit.value,
    }
    if (teamFilter.value) params.team_id = teamFilter.value
    if (positionFilter.value === 'backcourt') params.positions = 'PG,SG'
    if (positionFilter.value === 'frontcourt') params.positions = 'SF,PF,C'
    if (keyword.value) params.keyword = keyword.value

    const res = await dataApi.getPlayers(params)
    const body = res.data || res
    const rawItems = body?.items || []
    players.value = rawItems.map(toCamel)
    total.value = body?.total || players.value.length
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const onSortChange = ({ prop, order }) => {
  if (!prop) return
  sortBy.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  loadPlayers()
}

const goToPlayerDetail = (row) => {
  router.push(`/player/detail/${row.playerId}`)
}

const formatStat = (val) => {
  if (val == null) return '-'
  const n = Number(val)
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

const formatPct = (val) => {
  if (val == null) return '-'
  return (Number(val) * 100).toFixed(1) + '%'
}

const positionTagClass = (pos) => {
  if (!pos) return 'neu-tag--gray'
  const map = { PG: 'neu-tag--blue', SG: 'neu-tag--green', SF: 'neu-tag--orange', PF: 'neu-tag--red', C: 'neu-tag--gray' }
  return map[pos] || 'neu-tag--gray'
}
</script>

<style lang="scss" scoped>
.players-page {
  max-width: 1400px;
  margin: 0 auto;
}

.player-name-cell {
  font-weight: 600;
  color: $text-dark;
  cursor: pointer;

  &:hover {
    color: $color-nba-blue;
  }
}

.mono-num {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}

.stat-highlight {
  font-weight: 700;
  color: $color-nba-blue;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
