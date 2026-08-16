<template>
  <div class="team-detail-page animate-fade-in">
    <!-- 加载状态 -->
    <div v-if="loading" class="neu-card">
      <div class="loading-overlay" style="position: static; min-height: 300px">
        <div class="loading-spinner"></div>
        <div class="loading-text">球队数据加载中...</div>
      </div>
    </div>

    <template v-else-if="team">
      <!-- 球队头部 -->
      <div class="neu-card team-hero">
        <div class="hero-logo">
          <TeamLogo :abbr="team.abbreviation || ''" :size="80" />
        </div>
        <div class="hero-info">
          <h2 class="hero-name">
            {{ team.teamName }}
            <span class="hero-name-en">{{ team.teamNameEn }}</span>
          </h2>
          <div class="hero-tags">
            <span class="neu-tag" :class="team.conference === 'East' ? 'neu-tag--green' : 'neu-tag--orange'">
              {{ team.conference === 'East' ? '东部' : '西部' }}
            </span>
            <span class="neu-tag neu-tag--gray">{{ team.division || '-' }}</span>
            <span v-if="team.offenseType" class="neu-tag neu-tag--blue">{{ team.offenseType }}</span>
            <span v-if="team.defenseType" class="neu-tag neu-tag--red">{{ team.defenseType }}</span>
          </div>
        </div>
        <div class="hero-record">
          <div class="record-main">
            <span class="record-w">{{ sd.wins ?? '-' }}</span>
            <span class="record-sep">-</span>
            <span class="record-l">{{ sd.losses ?? '-' }}</span>
          </div>
          <div class="record-sub">胜率 {{ formatPct(sd.win_percentage) }}</div>
          <div class="record-sub">
            主场 {{ sd.home_wins ?? 0 }}-{{ sd.home_losses ?? 0 }} · 客场 {{ sd.away_wins ?? 0 }}-{{ sd.away_losses ?? 0 }}
          </div>
        </div>
        <div class="hero-actions">
          <el-button type="primary" @click="goPredict">
            <el-icon><TrendCharts /></el-icon>预测
          </el-button>
          <el-button @click="router.back()">返回</el-button>
        </div>
      </div>

      <!-- 赛季数据 -->
      <div class="neu-card" style="margin-top: 16px">
        <div class="neu-card-header">
          <span class="title">赛季数据</span>
          <span class="neu-tag neu-tag--blue">{{ sd.season || CURRENT_SEASON }}</span>
        </div>
        <el-row :gutter="16">
          <el-col v-for="item in statItems" :key="item.label" :xs="12" :sm="8" :md="6">
            <div class="stat-cell">
              <span class="stat-label">{{ item.label }}</span>
              <span class="stat-value mono-num" :class="item.cls">{{ item.value }}</span>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 球员名单 -->
      <div class="neu-card" style="margin-top: 16px; padding: 0; overflow: hidden">
        <div class="neu-card-header" style="padding: 16px 24px">
          <span class="title">球员名单</span>
        </div>
        <el-table
          :data="roster"
          stripe
          v-loading="rosterLoading"
          style="width: 100%"
          @row-click="goToPlayerPredict"
        >
          <el-table-column prop="playerName" label="球员" min-width="160">
            <template #default="{ row }">
              <span class="roster-name">{{ row.playerName }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="position" label="位置" width="90">
            <template #default="{ row }">
              <span class="neu-tag neu-tag--blue">{{ row.position || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="age" label="年龄" width="80">
            <template #default="{ row }">
              <span class="mono-num">{{ row.age ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="height" label="身高(cm)" width="100">
            <template #default="{ row }">
              <span class="mono-num">{{ row.height ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="gamesPlayed" label="场次" width="80">
            <template #default="{ row }">
              <span class="mono-num">{{ row.gamesPlayed ?? '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="pointsPerGame" label="得分" width="90">
            <template #default="{ row }">
              <span class="mono-num stat-highlight">{{ formatStat(row.pointsPerGame) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="reboundsPerGame" label="篮板" width="90">
            <template #default="{ row }">
              <span class="mono-num">{{ formatStat(row.reboundsPerGame) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="assistsPerGame" label="助攻" width="90">
            <template #default="{ row }">
              <span class="mono-num">{{ formatStat(row.assistsPerGame) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <!-- 错误状态 -->
    <div v-else class="neu-card">
      <div class="empty-state">
        <el-icon class="empty-icon"><Warning /></el-icon>
        <div class="empty-title">球队不存在</div>
        <div class="empty-desc">未找到该球队的数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { TrendCharts, Warning } from '@element-plus/icons-vue'
import { dataApi } from '@/api'
import { CURRENT_SEASON } from '@/constants'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const team = ref(null)
const roster = ref([])
const rosterLoading = ref(false)

const teamId = computed(() => Number(route.params.teamId))

// Python API 响应 → 展示字段
const toTeamCamel = (t) => ({
  teamId: t.team_id,
  teamName: t.team_name,
  teamNameEn: t.team_name_en,
  abbreviation: t.abbreviation,
  conference: t.conference,
  division: t.division,
  offenseType: t.offense_type,
  defenseType: t.defense_type,
})

const sd = computed(() => team.value?.seasonData || {})

const toRosterCamel = (p) => {
  const s = p.season_data || {}
  return {
    playerId: p.player_id,
    playerName: p.player_name,
    position: p.position,
    age: p.age,
    height: p.height,
    gamesPlayed: s.games_played,
    pointsPerGame: s.points_per_game,
    reboundsPerGame: s.rebounds_per_game,
    assistsPerGame: s.assists_per_game,
  }
}

const statItems = computed(() => {
  const s = sd.value
  const signed = (v) => ({
    value: formatSigned(v),
    cls: (v ?? 0) >= 0 ? 'text-positive' : 'text-negative',
  })
  return [
    { label: '场均得分', value: formatStat(s.points_per_game) },
    { label: '对手得分', value: formatStat(s.opponent_points) },
    { label: '进攻效率', value: formatStat(s.offensive_rating) },
    { label: '防守效率', value: formatStat(s.defensive_rating) },
    { ...signed(s.net_rating), label: '净效率' },
    { label: '节奏', value: formatStat(s.pace) },
    { label: '场均篮板', value: formatStat(s.rebounds_per_game) },
    { label: '场均助攻', value: formatStat(s.assists_per_game) },
    { label: '场均失误', value: formatStat(s.turnovers_per_game) },
    { label: '场均抢断', value: formatStat(s.steals_per_game) },
    { label: '场均盖帽', value: formatStat(s.blocks_per_game) },
    { label: '命中率', value: formatPct(s.fg_percentage) },
    { label: '三分命中率', value: formatPct(s.three_percentage) },
    { label: '罚球命中率', value: formatPct(s.ft_percentage) },
    { label: '真实命中率', value: formatPct(s.true_shooting_pct) },
    { label: '有效命中率', value: formatPct(s.effective_fg_pct) },
    { label: '近10场胜率', value: formatPct(s.recent_win_rate) },
  ]
})

onMounted(() => {
  loadTeamDetail()
})

const loadTeamDetail = async () => {
  loading.value = true
  try {
    const res = await dataApi.getTeamDetail(teamId.value, CURRENT_SEASON)
    const data = res.data || res
    team.value = { ...toTeamCamel(data), seasonData: data.season_data || {} }
    loadRoster()
  } catch (e) {
    console.error('加载球队详情失败', e)
    team.value = null
  } finally {
    loading.value = false
  }
}

const loadRoster = async () => {
  rosterLoading.value = true
  try {
    const res = await dataApi.getTeamRoster(teamId.value, CURRENT_SEASON)
    const data = res.data || res
    const list = Array.isArray(data) ? data : data.players || data.roster || []
    roster.value = list
      .map(toRosterCamel)
      .sort((a, b) => (b.pointsPerGame ?? 0) - (a.pointsPerGame ?? 0))
  } catch (e) {
    console.error('加载球员名单失败', e)
    roster.value = []
  } finally {
    rosterLoading.value = false
  }
}

const goPredict = () => {
  router.push({ path: '/predict', query: { homeTeamId: team.value.teamId } })
}

const goToPlayerPredict = (player) => {
  router.push({ path: '/player/predict', query: { playerId: player.playerId } })
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
.team-detail-page {
  max-width: 1000px;
  margin: 0 auto;
}

// 头部
.team-hero {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 28px 32px;
  flex-wrap: wrap;

  .hero-logo {
    flex-shrink: 0;
  }

  .hero-info {
    flex: 1;
    min-width: 220px;

    .hero-name {
      font-size: 24px;
      font-weight: 800;
      color: $text-dark;
      margin: 0 0 8px;
      letter-spacing: -0.3px;
    }

    .hero-name-en {
      font-size: 14px;
      font-weight: 500;
      color: $text-muted;
      margin-left: 8px;
    }

    .hero-tags {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
  }

  .hero-record {
    text-align: center;
    flex-shrink: 0;

    .record-main {
      font-size: 40px;
      font-weight: 800;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }

    .record-w { color: $color-nba-blue; }
    .record-sep { color: $text-muted; margin: 0 4px; }
    .record-l { color: $color-nba-red; }

    .record-sub {
      font-size: 12px;
      color: $text-muted;
      margin-top: 6px;
    }
  }

  .hero-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

// 赛季数据
.stat-cell {
  padding: 18px 16px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  margin-bottom: 16px;
  text-align: center;

  .stat-label {
    display: block;
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 8px;
  }

  .stat-value {
    display: block;
    font-size: 22px;
    font-weight: 700;
    color: $text-dark;
  }
}

// 球员名单
.roster-name {
  font-weight: 600;
  color: $text-dark;
  cursor: pointer;

  &:hover {
    color: $color-nba-blue;
  }
}

.stat-highlight {
  font-weight: 700;
  color: $color-nba-blue;
}
</style>
