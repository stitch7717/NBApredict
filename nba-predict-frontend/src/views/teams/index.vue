<template>
  <div class="teams-page">
    <h2 class="page-title">球队数据</h2>

    <!-- 分区标签 -->
    <div class="conference-tabs">
      <button
        class="conference-tab"
        :class="{ 'conference-tab--active': activeTab === 'ALL' }"
        @click="activeTab = 'ALL'"
      >
        全部
      </button>
      <button
        class="conference-tab"
        :class="{ 'conference-tab--active': activeTab === 'East' }"
        @click="activeTab = 'East'"
      >
        东部
      </button>
      <button
        class="conference-tab"
        :class="{ 'conference-tab--active': activeTab === 'West' }"
        @click="activeTab = 'West'"
      >
        西部
      </button>
    </div>

    <!-- 战绩榜 -->
    <div class="neu-card standings-card" v-loading="loading">
      <el-table
        :data="standings"
        stripe
        style="width: 100%"
        class="standings-table"
        @row-click="goToDetail"
      >
        <el-table-column label="排名" width="70" align="center">
          <template #default="{ $index }">
            <span class="rank-num" :class="{ 'rank-num--top3': $index < 3 }">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="球队" min-width="220">
          <template #default="{ row }">
            <span class="team-cell">
              <TeamLogo :abbr="row.abbreviation || ''" :size="28" />
              <span class="standings-team">
                <span class="standings-name">{{ row.teamName }}</span>
                <span class="standings-en">{{ row.teamNameEn }}</span>
              </span>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="wins" label="胜" width="70" align="center" sortable>
          <template #default="{ row }">
            <span class="mono-num">{{ row.wins }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="losses" label="负" width="70" align="center" sortable>
          <template #default="{ row }">
            <span class="mono-num">{{ row.losses }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="winPct" label="胜率" width="100" align="center" sortable>
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.winPct) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="netRating" label="净效率" width="100" align="center" sortable>
          <template #default="{ row }">
            <span
              class="mono-num"
              :class="(row.netRating ?? 0) >= 0 ? 'text-positive' : 'text-negative'"
            >
              {{ formatSigned(row.netRating) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="pointsPerGame" label="场均得分" width="100" align="center" sortable>
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.pointsPerGame) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dataApi } from '@/api'
import { CURRENT_SEASON } from '@/constants'

const router = useRouter()

const activeTab = ref('ALL')
const teams = ref([])
const loading = ref(false)

// Python API 响应 → 展示字段（战绩在嵌套的 season_data 里）
const toCamel = (t) => {
  const s = t.season_data || {}
  return {
    teamId: t.team_id,
    teamName: t.team_name,
    teamNameEn: t.team_name_en,
    abbreviation: t.abbreviation,
    conference: t.conference,
    division: t.division,
    wins: s.wins ?? 0,
    losses: s.losses ?? 0,
    winPct: s.win_percentage ?? 0,
    netRating: s.net_rating ?? null,
    pointsPerGame: s.points_per_game ?? null,
  }
}

// 按分区筛选 + 按胜率降序（战绩榜）
const standings = computed(() => {
  let list = teams.value.map(toCamel)
  if (activeTab.value !== 'ALL') {
    list = list.filter((t) => t.conference === activeTab.value)
  }
  return list.sort((a, b) => b.winPct - a.winPct)
})

onMounted(() => {
  loadTeams()
})

const loadTeams = async () => {
  loading.value = true
  try {
    const res = await dataApi.getTeams(CURRENT_SEASON)
    const data = res.data || res
    teams.value = Array.isArray(data) ? data : data.teams || data.records || []
  } catch (e) {
    console.error('加载球队数据失败', e)
  } finally {
    loading.value = false
  }
}

const goToDetail = (team) => {
  router.push(`/team/detail/${team.teamId}`)
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

const formatSigned = (val) => {
  if (val == null) return '-'
  const n = Number(val)
  const prefix = n > 0 ? '+' : ''
  return prefix + (Number.isInteger(n) ? String(n) : n.toFixed(1))
}
</script>

<style lang="scss" scoped>
.teams-page {
  max-width: 1400px;
  margin: 0 auto;
}

// 分区标签
.conference-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.conference-tab {
  padding: 10px 24px;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  background: $bg-card;
  color: $text-secondary;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all $transition-fast;
  box-shadow: $neu-raised-sm;
  outline: none;

  &:hover {
    color: $text-primary;
  }

  &--active {
    background: $color-nba-blue;
    color: #fff;
    border-color: $color-nba-blue;
  }
}

// 战绩榜
.standings-card {
  padding: 0;
  overflow: hidden;
}

.standings-table {
  :deep(.el-table__row) {
    cursor: pointer;
  }
}

.rank-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  border-radius: $radius-sm;
  font-weight: 700;
  font-size: 13px;
  color: $text-secondary;
  background: $bg-elevated;

  &--top3 {
    background: linear-gradient(135deg, $color-nba-blue, color.adjust($color-nba-blue, $lightness: 15%));
    color: #fff;
  }
}

.standings-team {
  display: flex;
  flex-direction: column;

  .standings-name {
    font-size: 14px;
    font-weight: 600;
    color: $text-dark;
    line-height: 1.3;
  }

  .standings-en {
    font-size: 11px;
    color: $text-muted;
  }
}
</style>
