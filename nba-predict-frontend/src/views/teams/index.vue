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

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay" style="position: relative; min-height: 400px">
      <div class="loading-spinner"></div>
      <div class="loading-text">加载球队数据...</div>
    </div>

    <!-- 球队卡片网格 -->
    <div v-else class="team-grid">
      <div
        v-for="team in filteredTeams"
        :key="team.teamId"
        class="team-card-wrapper"
      >
        <div
          class="neu-card team-card"
          :class="{
            'team-card--expanded': expandedTeamId === team.teamId,
          }"
          @click="toggleExpand(team)"
        >
          <!-- 卡片头部 -->
          <div class="team-card-header">
            <div class="team-identity">
              <span class="team-abbr neu-tag" :class="conferenceTagClass(team.conference)">
                {{ team.abbreviation || team.teamName }}
              </span>
              <div class="team-name-block">
                <span class="team-fullname">{{ team.teamName }}</span>
                <span class="team-conf">{{ team.conference === 'East' ? '东部' : '西部' }}</span>
              </div>
            </div>
            <el-icon
              class="expand-icon"
              :class="{ 'expand-icon--rotated': expandedTeamId === team.teamId }"
            >
              <ArrowDown />
            </el-icon>
          </div>

          <!-- 战绩概览 -->
          <div class="team-record">
            <div class="record-stat">
              <span class="record-value record-value--wins">{{ team.wins || 0 }}</span>
              <span class="record-unit">胜</span>
            </div>
            <span class="record-sep">-</span>
            <div class="record-stat">
              <span class="record-value record-value--losses">{{ team.losses || 0 }}</span>
              <span class="record-unit">负</span>
            </div>
            <span v-if="team.winPct != null" class="neu-tag" :class="team.winPct >= 0.5 ? 'neu-tag--green' : 'neu-tag--red'">
              {{ formatPct(team.winPct) }}
            </span>
          </div>

          <!-- 指标行 -->
          <div class="team-metrics">
            <div class="metric-item">
              <span class="metric-label">净效率</span>
              <span class="metric-value mono-num" :class="(team.netRating || 0) >= 0 ? 'metric-value--positive' : 'metric-value--negative'">
                {{ formatSigned(team.netRating) }}
              </span>
            </div>
            <div class="metric-item">
              <span class="metric-label">节奏</span>
              <span class="metric-value mono-num">{{ formatStat(team.pace) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">场均得分</span>
              <span class="metric-value mono-num">{{ formatStat(team.pointsPerGame) }}</span>
            </div>
          </div>

          <!-- 展开面板 -->
          <div v-if="expandedTeamId === team.teamId" class="team-expand animate-fade-in" @click.stop>
            <!-- 赛季数据面板 -->
            <div class="expand-section">
              <div class="expand-title">赛季数据</div>
              <el-row :gutter="12">
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">进攻效率</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.offensiveRating) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">防守效率</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.defensiveRating) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">场均得分</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.pointsPerGame) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">对手得分</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.oppPointsPerGame) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">场均篮板</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.reboundsPerGame) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">场均助攻</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.assistsPerGame) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">真实命中率</span>
                    <span class="expand-stat-value mono-num">{{ formatPct(team.trueShootingPct) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">有效命中率</span>
                    <span class="expand-stat-value mono-num">{{ formatPct(team.effectiveFgPct) }}</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="expand-stat">
                    <span class="expand-stat-label">回合数</span>
                    <span class="expand-stat-value mono-num">{{ formatStat(team.pace) }}</span>
                  </div>
                </el-col>
              </el-row>
            </div>

            <!-- 球员名单 -->
            <div class="expand-section">
              <div class="expand-title">球员名单</div>
              <div v-if="teamRosterLoading && rosterTeamId === team.teamId" class="loading-row">
                <div class="loading-spinner" style="width: 20px; height: 20px"></div>
                <span style="margin-left: 8px; font-size: 12px; color: $text-muted">加载名单...</span>
              </div>
              <div v-else-if="currentRoster.length" class="roster-table-wrap">
                <table class="roster-table">
                  <thead>
                    <tr>
                      <th>球员</th>
                      <th>位置</th>
                      <th>年龄</th>
                      <th>得分</th>
                      <th>篮板</th>
                      <th>助攻</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in currentRoster" :key="p.playerId || p.id">
                      <td class="roster-name">{{ p.playerName || p.name || '-' }}</td>
                      <td>
                        <span class="neu-tag neu-tag--blue" style="font-size: 10px; padding: 2px 6px">
                          {{ p.position || '-' }}
                        </span>
                      </td>
                      <td class="mono-num">{{ p.age || '-' }}</td>
                      <td class="mono-num">{{ formatStat(p.pointsPerGame) }}</td>
                      <td class="mono-num">{{ formatStat(p.reboundsPerGame) }}</td>
                      <td class="mono-num">{{ formatStat(p.assistsPerGame) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="empty-hint">暂无球员名单数据</div>
            </div>

            <!-- 操作 -->
            <div class="expand-actions">
              <el-button type="primary" size="small" @click="goToPredict(team)">
                <el-icon><TrendCharts /></el-icon> 预测此队
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && teams.length === 0" class="neu-card">
      <div class="empty-state">
        <el-icon class="empty-icon"><Trophy /></el-icon>
        <div class="empty-title">暂无球队数据</div>
        <div class="empty-desc">请检查数据源是否已配置球队数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Trophy, ArrowDown, TrendCharts } from '@element-plus/icons-vue'
import { dataApi } from '@/api'

const router = useRouter()

const activeTab = ref('ALL')
const teams = ref([])
const loading = ref(false)
const expandedTeamId = ref(null)

const currentRoster = ref([])
const rosterTeamId = ref(null)
const teamRosterLoading = ref(false)

const filteredTeams = computed(() => {
  if (activeTab.value === 'ALL') return teams.value
  return teams.value.filter((t) => t.conference === activeTab.value)
})

onMounted(() => {
  loadTeams()
})

const loadTeams = async () => {
  loading.value = true
  try {
    const res = await dataApi.getTeams('2025-26')
    const data = res.data || res
    teams.value = Array.isArray(data) ? data : data.teams || data.records || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const toggleExpand = async (team) => {
  if (expandedTeamId.value === team.teamId) {
    expandedTeamId.value = null
    return
  }
  expandedTeamId.value = team.teamId
  await loadRoster(team.teamId)
}

const loadRoster = async (teamId) => {
  rosterTeamId.value = teamId
  teamRosterLoading.value = true
  try {
    const res = await dataApi.getTeamRoster(teamId)
    const data = res.data || res
    currentRoster.value = Array.isArray(data)
      ? data
      : data.players || data.roster || []
  } catch {
    currentRoster.value = []
  } finally {
    teamRosterLoading.value = false
  }
}

const goToPredict = (team) => {
  router.push({ path: '/predict', query: { homeTeamId: team.teamId } })
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

const conferenceTagClass = (conf) => {
  return conf === 'East' ? 'neu-tag--green' : 'neu-tag--orange'
}
</script>

<style lang="scss" scoped>
.teams-page {
  max-width: 1400px;
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
    box-shadow: $neu-raised;
    transform: translateY(-1px);
  }

  &--active {
    background: $color-nba-blue;
    border-color: $color-nba-blue;
    color: #fff;
    box-shadow: 3px 3px 6px rgba(0, 0, 0, 0.4), -3px -3px 6px rgba(29, 66, 138, 0.2);

    &:hover {
      color: #fff;
      transform: translateY(-1px);
    }
  }
}

// 球队卡片网格
.team-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;

  @media (max-width: $breakpoint-xl) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: 1fr;
  }
}

.team-card {
  cursor: pointer;
  padding: 20px;
  transition: all $transition-normal;

  &--expanded {
    border-color: rgba($color-nba-blue, 0.3);
    box-shadow: $neu-raised-lg;
  }
}

.team-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.team-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.team-abbr {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  padding: 4px 10px;
}

.team-name-block {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.team-fullname {
  font-size: 16px;
  font-weight: 700;
  color: $text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.team-conf {
  font-size: 11px;
  color: $text-muted;
}

.expand-icon {
  flex-shrink: 0;
  color: $text-muted;
  font-size: 16px;
  transition: transform $transition-fast;
  margin-top: 4px;

  &--rotated {
    transform: rotate(180deg);
  }
}

// 战绩
.team-record {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
}

.record-stat {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.record-value {
  font-size: 24px;
  font-weight: 800;

  &--wins {
    color: $color-positive;
  }

  &--losses {
    color: $color-negative;
  }
}

.record-unit {
  font-size: 12px;
  color: $text-muted;
}

.record-sep {
  font-size: 18px;
  font-weight: 600;
  color: $text-muted;
}

// 指标行
.team-metrics {
  display: flex;
  gap: 16px;
}

.metric-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: center;
}

.metric-label {
  font-size: 11px;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.metric-value {
  font-size: 15px;
  font-weight: 700;
  color: $text-primary;

  &--positive {
    color: $color-positive;
  }

  &--negative {
    color: $color-negative;
  }
}

.mono-num {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}

// 展开面板
.team-expand {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid $border-dark;
}

.expand-section {
  margin-bottom: 16px;

  &:last-of-type {
    margin-bottom: 12px;
  }
}

.expand-title {
  font-size: 13px;
  font-weight: 600;
  color: $color-nba-blue;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.expand-stat {
  padding: 10px 12px;
  background: $bg-elevated;
  border-radius: $radius-sm;
  border: 1px solid $border-dark;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.expand-stat-label {
  font-size: 11px;
  color: $text-muted;
}

.expand-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
}

// 名单表
.roster-table-wrap {
  overflow-x: auto;
}

.roster-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;

  th {
    text-align: left;
    padding: 8px 10px;
    background: $bg-elevated;
    color: $text-secondary;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid $border-dark;
  }

  td {
    padding: 7px 10px;
    color: $text-primary;
    border-bottom: 1px solid rgba($border-dark, 0.5);
  }

  tr:last-child td {
    border-bottom: none;
  }

  tr:hover td {
    background: rgba($color-nba-blue, 0.04);
  }
}

.roster-name {
  font-weight: 600;
  color: $text-primary;
}

// 操作区
.expand-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid $border-dark;
}

.loading-row {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 0;
}

.empty-hint {
  text-align: center;
  padding: 16px 0;
  font-size: 12px;
  color: $text-muted;
}
</style>
