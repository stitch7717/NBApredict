<template>
  <div class="team-detail-page animate-fade-in">
    <!-- 加载状态 -->
    <div v-if="loading" class="neu-card detail-narrow">
      <div class="loading-overlay" style="position: static; min-height: 300px">
        <div class="loading-spinner"></div>
        <div class="loading-text">球队数据加载中...</div>
      </div>
    </div>

    <template v-else-if="team">
      <!-- 球队头部 -->
      <div class="neu-card team-hero">
        <div class="hero-body">
          <div class="hero-logo">
            <TeamLogo :abbr="team.abbreviation || ''" :size="120" />
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
            </div>
          </div>
          <!-- 球队基本信息 -->
          <div class="hero-basic">
            <div class="basic-row">
              <span class="basic-label">所属分区</span>
              <span class="basic-value">{{ team.division || '-' }}</span>
            </div>
            <div class="basic-row">
              <span class="basic-label">进攻风格</span>
              <span class="basic-value">{{ team.offenseType || '-' }}</span>
            </div>
            <div class="basic-row">
              <span class="basic-label">防守风格</span>
              <span class="basic-value">{{ team.defenseType || '-' }}</span>
            </div>
          </div>
          <div class="hero-actions">
            <el-button type="primary" @click="goPredict">
              <el-icon><TrendCharts /></el-icon>预测
            </el-button>
            <el-button @click="router.back()">返回</el-button>
          </div>
        </div>
      </div>

      <!-- 赛季数据 -->
      <div class="detail-narrow">
        <div class="neu-card" style="margin-top: 16px">
        <div class="neu-card-header">
          <div class="season-title-group">
            <span class="title">{{ season }}赛季</span>
            <el-dropdown trigger="click" @command="switchSeason">
              <span class="season-switch">
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="s in seasonOptions" :key="s" :command="s">
                    {{ s }}赛季
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        <!-- 战绩概览 -->
        <div class="season-record">
          <div class="record-line">
            <span class="record-w">{{ sd.wins ?? '-' }}</span>
            <span class="record-sep">-</span>
            <span class="record-l">{{ sd.losses ?? '-' }}</span>
            <span class="record-pct">胜率 {{ formatPct(sd.win_percentage) }}</span>
          </div>
          <div class="record-detail">
            主场 {{ sd.home_wins ?? 0 }}-{{ sd.home_losses ?? 0 }} · 客场 {{ sd.away_wins ?? 0 }}-{{ sd.away_losses ?? 0 }}
          </div>
        </div>
        <!-- 能力图 + 命中率图 -->
        <el-row :gutter="16" style="margin-bottom: 16px">
          <el-col :span="12">
            <div class="chart-block">
              <div class="chart-block-title">六宫格能力图</div>
              <AbilityRadar
                :dimensions="abilityDimensions"
                :values="abilityValues"
                :color="radarColor"
                :height="280"
              />
            </div>
          </el-col>
          <el-col :span="12">
            <div class="chart-block">
              <div class="chart-block-title">半场投篮热区</div>
              <ShootingCourt
                :zones="team.shootingZones || []"
                :fg-pct="sd.fg_percentage ?? 0"
                :three-pct="sd.three_percentage ?? 0"
                :ft-pct="sd.ft_percentage ?? 0"
                :ts-pct="sd.true_shooting_pct ?? 0"
              />
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col v-for="item in statItems" :key="item.label" :xs="12" :sm="8" :md="6">
            <div class="stat-cell">
              <span class="stat-label">{{ item.label }}</span>
              <span class="stat-value mono-num" :class="item.cls">{{ item.value }}</span>
            </div>
          </el-col>
        </el-row>
        </div>
      </div>

      <!-- 球员名单 -->
      <div class="detail-narrow">
        <div class="neu-card" style="margin-top: 16px; padding: 0; overflow: hidden">
        <div class="neu-card-header" style="padding: 16px 24px">
          <span class="title">球员名单</span>
        </div>
        <el-table
          :data="roster"
          stripe
          v-loading="rosterLoading"
          style="width: 100%"
          @row-click="goToPlayerDetail"
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
      </div>
    </template>

    <!-- 错误状态 -->
    <div v-else class="neu-card detail-narrow">
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
import { TrendCharts, Warning, ArrowDown } from '@element-plus/icons-vue'
import { dataApi } from '@/api'
import { CURRENT_SEASON } from '@/constants'
import { teamPrimaryColor } from '@/constants/teams'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const team = ref(null)
const roster = ref([])
const rosterLoading = ref(false)
const season = ref(CURRENT_SEASON)
const seasonOptions = ref([CURRENT_SEASON])

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

// 六宫格能力图：维度与归一化参考上限（全部"越高越好"）
const abilityDimensions = [
  { name: '进攻效率', max: 130 },
  { name: '节奏', max: 110 },
  { name: '场均得分', max: 130 },
  { name: '场均篮板', max: 55 },
  { name: '场均助攻', max: 32 },
  { name: '净效率', max: 15 },
]

const abilityValues = computed(() => {
  const s = sd.value
  return [
    s.offensive_rating ?? 0,
    s.pace ?? 0,
    s.points_per_game ?? 0,
    s.rebounds_per_game ?? 0,
    s.assists_per_game ?? 0,
    Math.max(s.net_rating ?? 0, 0),
  ]
})

const radarColor = computed(() => teamPrimaryColor(team.value?.abbreviation || ''))

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
    const res = await dataApi.getTeamDetail(teamId.value, season.value)
    const data = res.data || res
    team.value = {
      ...toTeamCamel(data),
      seasonData: data.season_data || {},
      shootingZones: data.shooting_zones || [],
    }
    // 从历史赛季列表提取可选赛季（响应中 seasons 数组）
    const history = (data.seasons || []).map((s) => s.season).filter(Boolean)
    if (history.length) {
      seasonOptions.value = history
      if (!history.includes(season.value)) season.value = history[0]
    } else if (!seasonOptions.value.includes(season.value)) {
      seasonOptions.value.push(season.value)
    }
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
    const res = await dataApi.getTeamRoster(teamId.value, season.value)
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

const switchSeason = (s) => {
  if (s === season.value) return
  season.value = s
  loadTeamDetail()
}

const goPredict = () => {
  router.push({ path: '/predict', query: { homeTeamId: team.value.teamId } })
}

const goToPlayerDetail = (player) => {
  router.push(`/player/detail/${player.playerId}`)
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
// 页面全宽：头部卡片贴住内容区左右边缘
.team-detail-page {
  // 不加 max-width
}

// 除头部外的模块保持窄宽居中
.detail-narrow {
  max-width: 1200px;
  margin: 0 auto;
}

// 头部：整卡贴边，向上撑满，左右顶到内容区边缘
.team-hero {
  display: flex;
  flex-wrap: wrap;
  padding: 0;
  overflow: hidden;
  margin: -32px -32px 0;

  .hero-body {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 28px;
    flex-wrap: wrap;
    padding: 30px 100px 18px;
  }

  .hero-logo {
    flex-shrink: 0;
    // 只放大图标视觉，不撑高卡片：布局占位保持 120px
    transform: scale(1.3);
    transform-origin: center;
  }

  .hero-info {
    flex: 1;
    min-width: 220px;

    .hero-name {
      font-size: 30px;
      font-weight: 800;
      color: $text-primary;
      margin: 0 0 10px;
      letter-spacing: -0.3px;
    }

    .hero-name-en {
      font-size: 16px;
      font-weight: 500;
      color: $text-secondary;
      margin-left: 10px;
    }

    .hero-tags {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
  }

  .hero-basic {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 140px;

    .basic-row {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 15px;
    }

    .basic-label {
      color: $text-muted;
      flex-shrink: 0;
    }

    .basic-value {
      color: $text-primary;
      font-weight: 600;
    }
  }

  .hero-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

// 赛季切换：标题旁的小箭头按钮，融入背景
.season-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.season-switch {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: $radius-full;
  border: 1px solid transparent;
  color: $text-muted;
  cursor: pointer;
  transition: all $transition-fast;
  outline: none;

  &:hover {
    color: $text-primary;
    border-color: $border-subtle;
    background: rgba(255, 255, 255, 0.05);
  }
}

// 图表块
.chart-block {
  padding: 16px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  margin-bottom: 16px;
}

.chart-block-title {
  font-size: 13px;
  font-weight: 600;
  color: $color-nba-blue;
  margin-bottom: 8px;
}

// 战绩概览（赛季数据模块顶部；高度与数据格子一致）
.season-record {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
  min-height: 88px;
  padding: 14px 18px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .record-line {
    display: flex;
    align-items: baseline;
    gap: 6px;

    .record-w,
    .record-l {
      font-size: 36px;
      font-weight: 800;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }

    .record-w { color: $color-nba-blue; }
    .record-l { color: $color-nba-red; }

    .record-sep {
      font-size: 26px;
      font-weight: 700;
      color: $text-muted;
    }

    .record-pct {
      margin-left: 22px;
      font-size: 17px;
      font-weight: 700;
      color: $color-positive;
    }
  }

  .record-detail {
    font-size: 15px;
    color: $text-secondary;
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
    color: $text-secondary;
    margin-bottom: 8px;
  }

  .stat-value {
    display: block;
    font-size: 22px;
    font-weight: 700;
    color: $text-primary;
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
