<template>
  <div class="predict-page">
    <h2 class="page-title">自由预测</h2>

    <el-row :gutter="24">
      <!-- 左侧 - 预测参数 -->
      <el-col :span="10">
        <div class="neu-card">
          <div class="neu-card-header">
            <span class="title">预测参数</span>
          </div>

          <el-form :model="form" label-width="70px">
            <el-form-item label="主队" required>
              <el-select
                v-model="form.homeTeamId"
                filterable
                placeholder="选择主队"
                style="width: 100%"
                @change="onTeamChange"
              >
                <el-option
                  v-for="t in teamOptions"
                  :key="t.teamId"
                  :label="t.teamName"
                  :value="t.teamId"
                  :disabled="t.teamId === form.awayTeamId"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="客队" required>
              <el-select
                v-model="form.awayTeamId"
                filterable
                placeholder="选择客队"
                style="width: 100%"
                @change="onTeamChange"
              >
                <el-option
                  v-for="t in teamOptions"
                  :key="t.teamId"
                  :label="t.teamName"
                  :value="t.teamId"
                  :disabled="t.teamId === form.homeTeamId"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="场景">
              <el-radio-group v-model="form.scene">
                <el-radio-button label="常规赛">常规赛</el-radio-button>
                <el-radio-button label="季后赛">季后赛</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="predicting"
                style="width: 100%"
                @click="handlePredict"
              >
                <el-icon><TrendCharts /></el-icon> 开始预测
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 近期交锋 -->
        <div
          v-if="battleRecords.length"
          class="neu-card animate-fade-in"
          style="margin-top: 16px"
        >
          <div class="neu-card-header">
            <span class="title">近期交锋</span>
          </div>
          <div class="battle-list">
            <div
              v-for="(b, i) in battleRecords"
              :key="i"
              class="battle-item"
            >
              <span class="battle-date">{{ b.gameDate || '-' }}</span>
              <span class="battle-teams">{{ b.homeTeam }} {{ b.homeScore }} - {{ b.awayScore }} {{ b.awayTeam }}</span>
              <span class="neu-tag neu-tag--gray">{{ b.result || '-' }}</span>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 右侧 - 预测结果 -->
      <el-col :span="14">
        <div v-if="result" class="result-section animate-fade-in">
          <!-- 胜率条 -->
          <div class="neu-card">
            <div class="neu-card-header">
              <span class="title">胜率预测</span>
              <span class="neu-tag" :class="result.homeWinProb >= 0.5 ? 'neu-tag--blue' : 'neu-tag--red'">
                {{ result.homeWinProb >= 0.5 ? '主队占优' : '客队占优' }}
              </span>
            </div>
            <div class="prob-row">
              <span class="prob-label prob-label--home">{{ homeTeamName }}</span>
              <el-progress
                :percentage="Math.round(result.homeWinProb * 100)"
                :stroke-width="18"
                class="prob-bar"
              >
                <span class="prob-text">{{ (result.homeWinProb * 100).toFixed(1) }}%</span>
              </el-progress>
              <span class="prob-label prob-label--away">{{ awayTeamName }}</span>
            </div>
            <div class="prob-row" style="margin-top: 4px">
              <span class="prob-sub">{{ (result.homeWinProb * 100).toFixed(1) }}%</span>
              <span class="prob-sub" style="text-align: right">{{ ((1 - result.homeWinProb) * 100).toFixed(1) }}%</span>
            </div>
          </div>

          <!-- 比分预测 -->
          <div class="neu-card" style="margin-top: 16px">
            <div class="neu-card-header">
              <span class="title">比分预测</span>
            </div>
            <div class="score-display">
              <div class="team-score team-score--home">
                <div class="score-label">{{ homeTeamName }}</div>
                <div class="score-value">{{ result.predictHomeScore }}</div>
                <div class="score-sub">主队得分</div>
              </div>
              <div class="vs-badge">VS</div>
              <div class="team-score team-score--away">
                <div class="score-label">{{ awayTeamName }}</div>
                <div class="score-value">{{ result.predictAwayScore }}</div>
                <div class="score-sub">客队得分</div>
              </div>
            </div>
            <div class="grid-3">
              <div class="summary-stat">
                <div class="summary-label">预测总分</div>
                <div class="summary-value">{{ result.predictTotalScore }}</div>
              </div>
              <div class="summary-stat">
                <div class="summary-label">预测分差</div>
                <div
                  class="summary-value"
                  :class="result.predictScoreDiff > 0 ? 'summary-value--positive' : 'summary-value--negative'"
                >
                  {{ result.predictScoreDiff > 0 ? '+' : '' }}{{ result.predictScoreDiff }}
                </div>
              </div>
              <div class="summary-stat">
                <div class="summary-label">预测胜负</div>
                <div
                  class="summary-value"
                  :class="result.predictScoreDiff > 0 ? 'summary-value--positive' : 'summary-value--negative'"
                >
                  {{ result.predictScoreDiff > 0 ? '主胜' : result.predictScoreDiff === 0 ? '平局' : '客胜' }}
                </div>
              </div>
            </div>
          </div>

          <!-- 球员表现预测 -->
          <div class="neu-card" style="margin-top: 16px">
            <div class="neu-card-header">
              <span class="title">球员表现预测</span>
            </div>
            <el-row :gutter="16">
              <!-- 主队球员 -->
              <el-col :span="12">
                <div class="player-section-label">主队球员表现</div>
                <div v-if="homePlayersLoading" class="loading-row">
                  <div class="loading-spinner" style="width: 24px; height: 24px"></div>
                  <span class="loading-text" style="margin-left: 8px">加载中...</span>
                </div>
                <div v-else-if="homePlayers.length === 0" class="empty-hint">暂无球员数据</div>
                <div v-else class="player-cards">
                  <div
                    v-for="p in homePlayers"
                    :key="p.playerId"
                    class="player-card"
                  >
                    <div class="player-card-header">
                      <span class="player-name">{{ p.playerName || '球员 #' + p.playerId }}</span>
                      <span class="neu-tag neu-tag--blue">{{ p.position || '-' }}</span>
                    </div>
                    <div class="player-prediction">
                      <span class="pred-label">预测得分</span>
                      <span class="pred-range">
                        <span class="pred-low">{{ p.predLow || '-' }}</span>
                        <span class="pred-sep">-</span>
                        <span class="pred-mid">{{ p.predMid || '-' }}</span>
                        <span class="pred-sep">-</span>
                        <span class="pred-high">{{ p.predHigh || '-' }}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </el-col>
              <!-- 客队球员 -->
              <el-col :span="12">
                <div class="player-section-label">客队球员表现</div>
                <div v-if="awayPlayersLoading" class="loading-row">
                  <div class="loading-spinner" style="width: 24px; height: 24px"></div>
                  <span class="loading-text" style="margin-left: 8px">加载中...</span>
                </div>
                <div v-else-if="awayPlayers.length === 0" class="empty-hint">暂无球员数据</div>
                <div v-else class="player-cards">
                  <div
                    v-for="p in awayPlayers"
                    :key="p.playerId"
                    class="player-card"
                  >
                    <div class="player-card-header">
                      <span class="player-name">{{ p.playerName || '球员 #' + p.playerId }}</span>
                      <span class="neu-tag neu-tag--red">{{ p.position || '-' }}</span>
                    </div>
                    <div class="player-prediction">
                      <span class="pred-label">预测得分</span>
                      <span class="pred-range">
                        <span class="pred-low">{{ p.predLow || '-' }}</span>
                        <span class="pred-sep">-</span>
                        <span class="pred-mid">{{ p.predMid || '-' }}</span>
                        <span class="pred-sep">-</span>
                        <span class="pred-high">{{ p.predHigh || '-' }}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="neu-card">
          <div class="empty-state">
            <el-icon class="empty-icon"><Trophy /></el-icon>
            <div class="empty-title">选择主客队开始预测</div>
            <div class="empty-desc">在左侧选择主队和客队，点击预测按钮查看比分和球员表现预测</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Trophy, TrendCharts } from '@element-plus/icons-vue'
import { teamApi, playerApi, dataApi } from '@/api'

const form = reactive({
  homeTeamId: null,
  awayTeamId: null,
  scene: '常规赛',
})

const teamOptions = ref([])
const predicting = ref(false)
const result = ref(null)
const battleRecords = ref([])

const homePlayers = ref([])
const awayPlayers = ref([])
const homePlayersLoading = ref(false)
const awayPlayersLoading = ref(false)

const homeTeamName = computed(() => {
  const t = teamOptions.value.find((t) => t.teamId === form.homeTeamId)
  return t ? t.teamName : '主队'
})

const awayTeamName = computed(() => {
  const t = teamOptions.value.find((t) => t.teamId === form.awayTeamId)
  return t ? t.teamName : '客队'
})

onMounted(async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    teamOptions.value = res.data?.records || []
  } catch (e) {
    console.error(e)
  }
})

const onTeamChange = () => {
  result.value = null
  battleRecords.value = []
  homePlayers.value = []
  awayPlayers.value = []
}

const handlePredict = async () => {
  if (!form.homeTeamId || !form.awayTeamId) {
    ElMessage.warning('请选择主客队')
    return
  }
  if (form.homeTeamId === form.awayTeamId) {
    ElMessage.warning('主客队不能相同')
    return
  }
  predicting.value = true
  try {
    const res = await teamApi.predict({
      homeTeamId: form.homeTeamId,
      awayTeamId: form.awayTeamId,
      scene: form.scene,
      useOdds: false,
    })
    result.value = res.data
    ElMessage.success('预测完成')

    loadPlayerPredictions()
    loadBattleRecords()
  } catch {
    ElMessage.error('预测失败')
  } finally {
    predicting.value = false
  }
}

const loadBattleRecords = async () => {
  try {
    const res = await teamApi.getBattleRecord({
      team1Id: form.homeTeamId,
      team2Id: form.awayTeamId,
    })
    battleRecords.value = res.data?.records || res.data || []
  } catch {
    // 非关键接口，静默失败
  }
}

const loadPlayerPredictions = async () => {
  homePlayersLoading.value = true
  awayPlayersLoading.value = true
  try {
    const [homeRosterRes, awayRosterRes] = await Promise.allSettled([
      dataApi.getTeamRoster(form.homeTeamId),
      dataApi.getTeamRoster(form.awayTeamId),
    ])

    if (homeRosterRes.status === 'fulfilled' && homeRosterRes.value?.data) {
      const roster = Array.isArray(homeRosterRes.value.data)
        ? homeRosterRes.value.data
        : homeRosterRes.value.data.players || []
      homePlayers.value = roster.map((p) => ({
        ...p,
        playerId: p.playerId || p.player_id || p.id,
        playerName: p.playerName || p.player_name || p.name,
        pointsPerGame: p.pointsPerGame || p.points_per_game || p.season_data?.points_per_game,
      }))
      await predictPlayers(homePlayers.value, 'home')
    }

    if (awayRosterRes.status === 'fulfilled' && awayRosterRes.value?.data) {
      const roster = Array.isArray(awayRosterRes.value.data)
        ? awayRosterRes.value.data
        : awayRosterRes.value.data.players || []
      awayPlayers.value = roster.map((p) => ({
        ...p,
        playerId: p.playerId || p.player_id || p.id,
        playerName: p.playerName || p.player_name || p.name,
        pointsPerGame: p.pointsPerGame || p.points_per_game || p.season_data?.points_per_game,
      }))
      await predictPlayers(awayPlayers.value, 'away')
    }
  } catch (e) {
    console.error(e)
  } finally {
    homePlayersLoading.value = false
    awayPlayersLoading.value = false
  }
}

const predictPlayers = async (players, side) => {
  if (!players.length) return
  const target = side === 'home' ? homePlayers : awayPlayers
  try {
    const predictions = await Promise.allSettled(
      players.slice(0, 8).map((p) =>
        playerApi.predict({ playerId: p.playerId }).then((res) => ({
          playerId: p.playerId,
          ...res.data,
        }))
      )
    )
    const predMap = {}
    predictions.forEach((r) => {
      if (r.status === 'fulfilled') {
        predMap[r.value.playerId] = r.value
      }
    })
    target.value = target.value.map((p) => ({
      ...p,
      predLow: predMap[p.playerId]?.predLow ?? '-',
      predMid: predMap[p.playerId]?.predMid ?? '-',
      predHigh: predMap[p.playerId]?.predHigh ?? '-',
    }))
  } catch {
    // 静默处理
  }
}
</script>

<style lang="scss" scoped>
.predict-page {
  max-width: 1400px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

// 胜率条
.prob-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 8px;
}

.prob-label {
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
  min-width: 0;

  &--home {
    color: $color-nba-blue;
  }

  &--away {
    color: $color-nba-red;
  }
}

.prob-bar {
  flex: 1;

  :deep(.el-progress-bar__outer) {
    background: $border-light;
    border-radius: $radius-full;
  }

  :deep(.el-progress-bar__inner) {
    background: linear-gradient(90deg, $color-nba-blue, $text-muted 50%, $color-nba-red);
    border-radius: $radius-full;
  }

  :deep(.el-progress__text) {
    color: $text-primary;
    font-weight: 600;
  }
}

.prob-text {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.prob-sub {
  flex: 1;
  font-size: 12px;
  color: $text-muted;
}

// 比分展示
.score-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
  padding: 32px 0;
}

.team-score {
  text-align: center;

  .score-label {
    font-size: 16px;
    color: $text-secondary;
    margin-bottom: 8px;
    font-weight: 600;
  }

  .score-value {
    font-size: 56px;
    font-weight: 800;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  .score-sub {
    font-size: 12px;
    color: $text-muted;
    margin-top: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  &--home .score-value {
    color: $color-nba-blue;
  }

  &--away .score-value {
    color: $color-nba-red;
  }
}

.vs-badge {
  font-size: 20px;
  font-weight: 800;
  color: $text-muted;
  padding: 12px 16px;
  border-radius: $radius-full;
  background: $bg-elevated;
  border: 1px solid $border-dark;
}

// 汇总统计
.summary-stat {
  text-align: center;
  padding: 18px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .summary-label {
    font-size: 12px;
    color: $text-muted;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .summary-value {
    font-size: 28px;
    font-weight: 800;
    color: $text-primary;
    font-variant-numeric: tabular-nums;

    &--positive {
      color: $color-positive;
    }

    &--negative {
      color: $color-negative;
    }
  }
}

// 近期交锋
.battle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.battle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  font-size: 13px;

  .battle-date {
    color: $text-muted;
    font-size: 12px;
  }

  .battle-teams {
    color: $text-secondary;
    font-weight: 500;
  }
}

// 球员预测
.player-section-label {
  font-size: 14px;
  font-weight: 600;
  color: $text-secondary;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid $border-dark;
}

.player-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.player-card {
  padding: 10px 14px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  transition: all $transition-fast;

  &:hover {
    border-color: $border-light;
    background: rgba($color-nba-blue, 0.04);
  }
}

.player-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;

  .player-name {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }
}

.player-prediction {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .pred-label {
    font-size: 11px;
    color: $text-muted;
  }

  .pred-range {
    display: flex;
    align-items: center;
    gap: 2px;
    font-variant-numeric: tabular-nums;
  }

  .pred-low {
    font-size: 12px;
    color: $text-muted;
  }

  .pred-mid {
    font-size: 14px;
    font-weight: 700;
    color: $color-warning;
  }

  .pred-high {
    font-size: 12px;
    color: $text-muted;
  }

  .pred-sep {
    font-size: 11px;
    color: $text-muted;
  }
}

.loading-row {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 0;
}

.empty-hint {
  text-align: center;
  padding: 24px 0;
  font-size: 13px;
  color: $text-muted;
}
</style>
