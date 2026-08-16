<template>
  <div class="series-page">
    <h2 class="page-title">系列赛之星</h2>

    <div class="search-bar">
      <el-select v-model="season" placeholder="赛季" style="width:120px">
        <el-option label="2025-26" value="2025-26" />
        <el-option label="2024-25" value="2024-25" />
      </el-select>
      <el-select v-model="teamId" placeholder="球队筛选" clearable filterable style="width:160px">
        <el-option v-for="t in teams" :key="t.teamId" :label="t.teamName" :value="t.teamId">
          <span class="team-cell">
            <TeamLogo :abbr="t.abbreviation || ''" :size="20" />
            <span>{{ t.teamName }}</span>
          </span>
        </el-option>
      </el-select>
      <el-button type="primary" @click="loadStars">
        <el-icon><Search /></el-icon>查询
      </el-button>
    </div>

    <!-- 星级球员卡片 -->
    <div v-if="stars.length" class="stars-grid animate-fade-in">
      <div v-for="(player, i) in stars" :key="i" class="star-card neu-card" :class="'star-card--rank-' + Math.min(i+1, 3)">
        <div class="star-card-header">
          <div class="star-rank-badge" :class="'rank-' + Math.min(i+1, 3)">
            {{ i + 1 }}
          </div>
          <div class="star-player-info">
            <div class="star-player-name">{{ player.playerName }}</div>
            <div class="star-player-team">
              <span class="team-cell"><TeamLogo :abbr="teamAbbrOf(player.teamName)" :size="16" /> <span>{{ player.teamName }}</span></span>
              <span class="matchup-vs">vs</span>
              <span class="team-cell"><TeamLogo :abbr="teamAbbrOf(player.opponentTeamName)" :size="16" /> <span>{{ player.opponentTeamName }}</span></span>
            </div>
          </div>
        </div>
        <div class="star-card-stats">
          <div class="star-stat">
            <span class="star-stat-value">{{ player.avgScore }}</span>
            <span class="star-stat-label">场均得分</span>
          </div>
          <div class="star-stat">
            <span class="star-stat-value">{{ (player.avgFgPct * 100).toFixed(1) }}%</span>
            <span class="star-stat-label">命中率</span>
          </div>
          <div class="star-stat">
            <span class="star-stat-value" :class="{ 'text-positive': player.scoreUp > 0 }">
              +{{ player.scoreUp }}
            </span>
            <span class="star-stat-label">得分提升</span>
          </div>
          <div class="star-stat">
            <span class="star-stat-value" :class="{ 'text-positive': player.hitRateUp > 0 }">
              +{{ (player.hitRateUp * 100).toFixed(1) }}%
            </span>
            <span class="star-stat-label">命中率提升</span>
          </div>
          <div class="star-stat">
            <span class="star-stat-value">{{ player.keyGameScore }}</span>
            <span class="star-stat-label">关键场次</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading" class="neu-card">
      <div class="empty-state">
        <el-icon class="empty-icon"><Star /></el-icon>
        <div class="empty-title">暂无系列赛之星数据</div>
        <div class="empty-desc">请选择赛季和球队后查询系列赛之星球员表现</div>
      </div>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="neu-card">
      <div class="empty-state">
        <div class="loading-overlay" style="position:relative;inset:auto;background:none">
          <div class="loading-spinner"></div>
          <div class="loading-text">加载中...</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { seriesApi, teamApi } from '@/api'
import { teamAbbrOf } from '@/constants/teams'
import { CURRENT_SEASON } from '@/constants'
import { Star, Search } from '@element-plus/icons-vue'

const season = ref(CURRENT_SEASON)
const teamId = ref(null)
const stars = ref([])
const teams = ref([])
const loading = ref(false)

onMounted(() => { loadTeams(); loadStars() })

const loadTeams = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    teams.value = res.data?.records || []
  } catch (e) { console.error(e) }
}

const loadStars = async () => {
  loading.value = true
  try {
    const res = await seriesApi.getStarList({ season: season.value, teamId: teamId.value })
    stars.value = res.data || []
  } catch (e) { console.error(e) } finally { loading.value = false }
}
</script>

<style lang="scss" scoped>
.series-page { max-width: 1400px; margin: 0 auto; }

.stars-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 20px;
}

.star-card {
  &--rank-1 { border-left: 3px solid $color-warning; }
  &--rank-2 { border-left: 3px solid $text-secondary; }
  &--rank-3 { border-left: 3px solid $accent-orange; }
}

.star-card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid $border-dark;
}

.star-rank-badge {
  width: 36px;
  height: 36px;
  border-radius: $radius-full;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
  flex-shrink: 0;

  &.rank-1 { background: rgba($color-warning, 0.2); color: $color-warning; }
  &.rank-2 { background: rgba($text-secondary, 0.15); color: $text-secondary; }
  &.rank-3 { background: rgba($accent-orange, 0.15); color: $accent-orange; }
}

.star-player-info {
  .star-player-name { font-size: 17px; font-weight: 700; color: $text-primary; }
  .star-player-team {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: $text-muted;
    margin-top: 2px;
  }
}

.star-card-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.star-stat {
  text-align: center;
  padding: 10px 6px;
  background: $bg-elevated;
  border-radius: $radius-sm;
  border: 1px solid $border-dark;

  .star-stat-value {
    display: block;
    font-size: 18px;
    font-weight: 700;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .star-stat-label {
    font-size: 10px;
    color: $text-muted;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
}

.text-positive { color: $color-positive; }
</style>
