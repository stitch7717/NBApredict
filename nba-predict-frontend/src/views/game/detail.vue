<template>
  <div class="game-detail-page animate-fade-in">
    <!-- 加载状态 -->
    <div v-if="loading" class="neu-card">
      <div class="loading-overlay" style="position:static;min-height:300px">
        <div class="loading-spinner"></div>
        <div class="loading-text">比赛数据加载中...</div>
      </div>
    </div>

    <template v-else-if="game">
      <!-- 比赛头部 -->
      <div class="game-header neu-card">
        <div class="header-matchup">
          <div class="header-team header-team--home" :class="{ winner: game.homeWin === 1 }">
            <div class="ht-abbr">{{ homeTeam?.abbreviation || 'HOM' }}</div>
            <div class="ht-name">{{ homeTeam?.teamName || '主队' }}</div>
            <div v-if="isFinished" class="ht-score">{{ game.homeScore }}</div>
          </div>
          <div class="header-vs">
            <span class="vs-badge">VS</span>
            <span v-if="game.gameDate" class="game-date">{{ formatDate(game.gameDate) }}</span>
            <span :class="['status-tag', statusTagClass]">{{ statusText }}</span>
          </div>
          <div class="header-team header-team--away" :class="{ winner: game.homeWin === 0 }">
            <div class="ht-abbr">{{ awayTeam?.abbreviation || 'AWY' }}</div>
            <div class="ht-name">{{ awayTeam?.teamName || '客队' }}</div>
            <div v-if="isFinished" class="ht-score">{{ game.awayScore }}</div>
          </div>
        </div>
        <div v-if="isFinished" class="header-result">
          最终比分 <strong>{{ game.homeScore }} - {{ game.awayScore }}</strong>
          <span v-if="game.scoreDiff != null">，分差 {{ Math.abs(game.scoreDiff) }}</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="detail-tabs neu-card" style="margin-top:16px">
        <el-tabs v-model="activeTab" class="dark-tabs">
          <!-- Tab 1: 比赛预测 -->
          <el-tab-pane label="比赛预测" name="predict">
            <div v-if="predicting" class="loading-inline">
              <div class="loading-spinner" style="width:24px;height:24px"></div>
              <span>预测计算中...</span>
            </div>

            <div v-else-if="predictResult" class="predict-content">
              <!-- 胜率条 -->
              <div class="prob-section">
                <div class="prob-labels">
                  <span class="prob-label prob-label--home">{{ homeTeam?.teamName || '主队' }}</span>
                  <span class="prob-label prob-label--away">{{ awayTeam?.teamName || '客队' }}</span>
                </div>
                <div class="prob-bar-track">
                  <div
                    class="prob-bar-fill prob-bar--home"
                    :style="{ width: homeWinProb + '%' }"
                  >
                    <span v-if="homeWinProb > 20">{{ homeWinProb }}%</span>
                  </div>
                  <div
                    class="prob-bar-fill prob-bar--away"
                    :style="{ width: (100 - homeWinProb) + '%' }"
                  >
                    <span v-if="(100 - homeWinProb) > 20">{{ 100 - homeWinProb }}%</span>
                  </div>
                </div>
              </div>

              <!-- 预测比分 -->
              <div class="score-display">
                <div class="team-score team-score--home">
                  <div class="ts-name">{{ predictResult.homeTeamName || predictResult.home_team_name || '主队' }}</div>
                  <div class="ts-score">{{ predictResult.predictHomeScore || predictResult.home_score || '-' }}</div>
                  <div class="ts-label">预测得分</div>
                </div>
                <div class="ts-vs">VS</div>
                <div class="team-score team-score--away">
                  <div class="ts-name">{{ predictResult.awayTeamName || predictResult.away_team_name || '客队' }}</div>
                  <div class="ts-score">{{ predictResult.predictAwayScore || predictResult.away_score || '-' }}</div>
                  <div class="ts-label">预测得分</div>
                </div>
              </div>

              <!-- 预测汇总 -->
              <div class="grid-3" style="margin-top:24px">
                <div class="summary-stat">
                  <div class="summary-label">预测总分</div>
                  <div class="summary-value">
                    {{ predictResult.predictTotalScore || predictResult.total_score || '-' }}
                  </div>
                </div>
                <div class="summary-stat">
                  <div class="summary-label">预测分差</div>
                  <div class="summary-value" :style="{ color: predDiff > 0 ? $colorPositive : $colorNegative }">
                    {{ predDiff > 0 ? '+' : '' }}{{ predDiff }}
                  </div>
                </div>
                <div class="summary-stat">
                  <div class="summary-label">预测胜负</div>
                  <div class="summary-value" :style="{ color: predDiff > 0 ? $colorPositive : $colorNegative }">
                    {{ predDiff > 0 ? '主胜' : predDiff < 0 ? '客胜' : '平' }}
                  </div>
                </div>
              </div>

              <!-- 实际结果对比 (如果比赛已结束) -->
              <div v-if="isFinished" class="comparison-section">
                <div class="neu-card-header">
                  <span class="title">预测 vs 实际</span>
                </div>
                <el-descriptions :column="3" border class="dark-descriptions">
                  <el-descriptions-item label="主队得分">
                    <span class="predict-val">{{ predictResult.predictHomeScore || predictResult.home_score || '-' }}</span>
                    <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                    <span class="actual-val">{{ game.homeScore }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="客队得分">
                    <span class="predict-val">{{ predictResult.predictAwayScore || predictResult.away_score || '-' }}</span>
                    <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                    <span class="actual-val">{{ game.awayScore }}</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="总分">
                    <span class="predict-val">{{ predictResult.predictTotalScore || predictResult.total_score || '-' }}</span>
                    <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                    <span class="actual-val">{{ (game.homeScore || 0) + (game.awayScore || 0) }}</span>
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </div>

            <div v-else class="empty-state" style="padding:40px">
              <el-icon class="empty-icon"><TrendCharts /></el-icon>
              <div class="empty-title">暂无预测数据</div>
              <div class="empty-desc">点击下方按钮开始预测</div>
              <el-button type="primary" style="margin-top:16px" :loading="predicting" @click="runPredict">
                开始预测
              </el-button>
            </div>
          </el-tab-pane>

          <!-- Tab 2: 交手记录 -->
          <el-tab-pane label="交手记录" name="battle">
            <div v-if="battleLoading" class="loading-inline">
              <div class="loading-spinner" style="width:24px;height:24px"></div>
              <span>加载交手记录...</span>
            </div>

            <div v-else-if="battleRecords && battleRecords.length" class="battle-section">
              <el-table :data="battleRecords" stripe class="dark-table">
                <el-table-column label="日期" prop="gameDate" width="130">
                  <template #default="{ row }">
                    {{ row.gameDate || row.season || '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="主队得分" width="110">
                  <template #default="{ row }">
                    <span class="score-cell">{{ row.homeScore ?? row.team1Score ?? '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="客队得分" width="110">
                  <template #default="{ row }">
                    <span class="score-cell">{{ row.awayScore ?? row.team2Score ?? '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="胜者" width="120">
                  <template #default="{ row }">
                    <span v-if="(row.homeWin ?? row.winner) === 1 || row.winner === homeTeamId" class="neu-tag neu-tag--green">主队胜</span>
                    <span v-else-if="(row.homeWin ?? row.winner) === 0 || row.winner === awayTeamId" class="neu-tag neu-tag--red">客队胜</span>
                    <span v-else class="neu-tag neu-tag--gray">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="总分" width="90">
                  <template #default="{ row }">
                    {{ (row.totalScore ?? ((row.homeScore ?? 0) + (row.awayScore ?? 0))) || '-' }}
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div v-else class="empty-state">
              <el-icon class="empty-icon"><Connection /></el-icon>
              <div class="empty-title">暂无交手记录</div>
              <div class="empty-desc">这两支球队最近没有交手记录</div>
            </div>
          </el-tab-pane>

          <!-- Tab 3: 球员对位 -->
          <el-tab-pane label="球员对位" name="player">
            <div class="player-placeholder">
              <div class="empty-state">
                <el-icon class="empty-icon"><User /></el-icon>
                <div class="empty-title">球员对位数据加载中...</div>
                <div class="empty-desc">球员对位分析功能将在后续版本中上线</div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>

    <!-- 比赛不存在 -->
    <div v-else class="neu-card">
      <div class="empty-state">
        <el-icon class="empty-icon"><Warning /></el-icon>
        <div class="empty-title">比赛未找到</div>
        <div class="empty-desc">该比赛不存在或已被移除</div>
        <el-button style="margin-top:16px" @click="router.push('/')">返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { TrendCharts, Connection, User, Warning, ArrowRight } from '@element-plus/icons-vue'
import { gameApi, teamApi } from '@/api'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const game = ref(null)
const homeTeam = ref(null)
const awayTeam = ref(null)
const teamMap = ref({})

const activeTab = ref('predict')

const predicting = ref(false)
const predictResult = ref(null)

const battleLoading = ref(false)
const battleRecords = ref([])

const STATUS = {
  FINISHED: 'FINISHED',
  SCHEDULED: 'SCHEDULED',
  LIVE: 'LIVE',
  IN_PROGRESS: 'IN_PROGRESS',
}

const $colorPositive = '#50C878'
const $colorNegative = '#E97451'

onMounted(() => {
  loadGameDetail()
})

const loadGameDetail = async () => {
  loading.value = true
  try {
    const gameId = route.params.gameId
    const res = await gameApi.getDetail(gameId)
    game.value = res.data

    // 加载球队信息
    await loadTeams()

    // 自动加载预测
    if (game.value) {
      runPredict()
      loadBattleRecords()
    }
  } catch (e) {
    console.error('加载比赛详情失败', e)
    game.value = null
  } finally {
    loading.value = false
  }
}

const loadTeams = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    const records = res.data?.records || []
    for (const t of records) {
      if (t.teamId != null) {
        teamMap.value[t.teamId] = t
      }
    }
    if (game.value) {
      homeTeam.value = teamMap.value[game.value.homeTeamId] || null
      awayTeam.value = teamMap.value[game.value.awayTeamId] || null
    }
  } catch (e) {
    console.error('加载球队列表失败', e)
  }
}

const runPredict = async () => {
  if (!game.value) return
  predicting.value = true
  try {
    const res = await teamApi.predict({
      homeTeamId: game.value.homeTeamId,
      awayTeamId: game.value.awayTeamId,
      scene: '常规赛',
      useOdds: false,
    })
    predictResult.value = res.data || res
  } catch (e) {
    console.error('预测失败', e)
    ElMessage.warning('预测服务暂不可用')
  } finally {
    predicting.value = false
  }
}

const loadBattleRecords = async () => {
  if (!game.value) return
  battleLoading.value = true
  try {
    const res = await gameApi.getBattle({
      team1Id: game.value.homeTeamId,
      team2Id: game.value.awayTeamId,
      season: game.value.season || '2025-26',
    })
    battleRecords.value = res.data?.battle_records || res.data?.records || []
  } catch (e) {
    console.error('加载交手记录失败', e)
    battleRecords.value = []
  } finally {
    battleLoading.value = false
  }
}

const isFinished = computed(() => {
  return game.value?.status === STATUS.FINISHED
})

const statusText = computed(() => {
  const s = game.value?.status
  if (s === STATUS.FINISHED) return '已结束'
  if (s === STATUS.LIVE || s === STATUS.IN_PROGRESS) return '进行中'
  return '未开始'
})

const statusTagClass = computed(() => {
  const s = game.value?.status
  if (s === STATUS.FINISHED) return 'status--finished'
  if (s === STATUS.LIVE || s === STATUS.IN_PROGRESS) return 'status--live'
  return 'status--upcoming'
})

const homeWinProb = computed(() => {
  if (!predictResult.value) return 50
  const prob = predictResult.value.homeWinProb
    ?? predictResult.value.home_win_prob
    ?? predictResult.value.home_win_probability
  if (prob != null) return Math.round(Number(prob) * 100)
  // 从分差估算
  const diff = predDiff.value
  return Math.round(Math.min(95, Math.max(5, 50 + diff * 3)))
})

const predDiff = computed(() => {
  if (!predictResult.value) return 0
  const diff = predictResult.value.predictScoreDiff
    ?? predictResult.value.score_diff
    ?? predictResult.value.predict_score_diff
  if (diff != null) return Number(diff)
  const home = Number(predictResult.value.predictHomeScore || predictResult.value.home_score || 0)
  const away = Number(predictResult.value.predictAwayScore || predictResult.value.away_score || 0)
  return home - away
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
</script>

<style lang="scss" scoped>
.game-detail-page {
  max-width: 1000px;
}

// Header
.game-header {
  text-align: center;
}

.header-matchup {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
  padding: 24px 0;
}

.header-team {
  text-align: center;
  min-width: 140px;

  .ht-abbr {
    font-size: 36px;
    font-weight: 800;
    color: $text-primary;
    letter-spacing: 1px;
    line-height: 1.2;
  }

  .ht-name {
    font-size: 14px;
    color: $text-secondary;
    margin-top: 4px;
  }

  .ht-score {
    font-size: 56px;
    font-weight: 800;
    color: $text-primary;
    line-height: 1;
    margin-top: 8px;
    font-variant-numeric: tabular-nums;
  }

  &--home {
    .ht-abbr { color: $color-nba-blue; }
    &.winner .ht-score { color: $color-positive; }
  }

  &--away {
    .ht-abbr { color: $color-nba-red; }
    &.winner .ht-score { color: $color-positive; }
  }
}

.header-vs {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;

  .vs-badge {
    font-size: 18px;
    font-weight: 800;
    color: $text-muted;
    padding: 10px 18px;
    border-radius: $radius-full;
    background: $bg-elevated;
    border: 1px solid $border-dark;
    box-shadow: $neu-pressed;
  }

  .game-date {
    font-size: 13px;
    color: $text-secondary;
  }
}

.status-tag {
  display: inline-block;
  padding: 2px 12px;
  border-radius: $radius-full;
  font-size: 12px;
  font-weight: 600;

  &.status--finished {
    background: rgba($text-secondary, 0.1);
    color: $text-secondary;
    border: 1px solid rgba($text-secondary, 0.2);
  }
  &.status--upcoming {
    background: rgba($color-nba-blue, 0.12);
    color: color.adjust($color-nba-blue, $lightness: 20%);
    border: 1px solid rgba($color-nba-blue, 0.25);
  }
  &.status--live {
    background: rgba($color-nba-red, 0.12);
    color: $color-nba-red;
    border: 1px solid rgba($color-nba-red, 0.25);
    animation: pulse 1.5s ease-in-out infinite;
  }
}

.header-result {
  margin-top: 16px;
  padding: 12px 20px;
  background: $bg-elevated;
  border-radius: $radius-md;
  font-size: 15px;
  color: $text-secondary;
  border: 1px solid $border-dark;

  strong {
    color: $text-primary;
    font-size: 18px;
    margin: 0 4px;
  }
}

// Tabs
.dark-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 20px;
  }
  :deep(.el-tabs__item) {
    color: $text-secondary;
    font-size: 15px;
    font-weight: 500;
    &.is-active { color: $color-nba-blue; }
  }
  :deep(.el-tabs__active-bar) { background: $color-nba-blue; }
  :deep(.el-tabs__nav-wrap::after) { background: $border-dark; }
}

// Predict: Win probability bar
.prob-section {
  margin-bottom: 24px;
}

.prob-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.prob-label {
  font-size: 13px;
  font-weight: 600;
  color: $text-secondary;

  &--home { color: $color-nba-blue; }
  &--away { color: $color-nba-red; }
}

.prob-bar-track {
  display: flex;
  height: 32px;
  border-radius: $radius-md;
  overflow: hidden;
  background: $bg-elevated;
  border: 1px solid $border-dark;
  box-shadow: $neu-pressed;
}

.prob-bar-fill {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  transition: width 0.6s ease;

  &.prob-bar--home {
    background: linear-gradient(90deg, $color-nba-blue, color.adjust($color-nba-blue, $lightness: 8%));
  }
  &.prob-bar--away {
    background: linear-gradient(90deg, color.adjust($color-nba-red, $lightness: 8%), $color-nba-red);
  }
}

// Predict: Score display
.score-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
  padding: 24px 0;
}

.team-score {
  text-align: center;

  .ts-name { font-size: 15px; color: $text-secondary; margin-bottom: 8px; }
  .ts-score { font-size: 52px; font-weight: 800; line-height: 1; }
  .ts-label { font-size: 12px; color: $text-muted; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.5px; }

  &--home .ts-score { color: $color-nba-blue; }
  &--away .ts-score { color: $color-nba-red; }
}

.ts-vs {
  font-size: 18px;
  font-weight: 800;
  color: $text-muted;
  padding: 10px 16px;
  border-radius: $radius-full;
  background: $bg-elevated;
  border: 1px solid $border-dark;
  box-shadow: $neu-pressed;
}

// Summary stats
.summary-stat {
  text-align: center;
  padding: 18px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .summary-label { font-size: 12px; color: $text-muted; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .summary-value { font-size: 28px; font-weight: 800; color: $text-primary; }
}

// Comparison
.comparison-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid $border-dark;
}

.predict-val { color: $text-secondary; }
.actual-val { color: $text-primary; font-weight: 700; }
.arrow-icon { margin: 0 6px; color: $text-muted; font-size: 12px; }

// Table dark override
.dark-table {
  :deep(.el-table) {
    --el-table-bg-color: transparent;
    --el-table-tr-bg-color: transparent;
  }
}

// Loading inline
.loading-inline {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: $text-secondary;
  font-size: 14px;
}

// Descriptions dark
.dark-descriptions {
  :deep(.el-descriptions__label) {
    color: $text-secondary !important;
    background: $bg-elevated !important;
    border-color: $border-dark !important;
  }
  :deep(.el-descriptions__content) {
    color: $text-primary !important;
    background: $bg-card !important;
    border-color: $border-dark !important;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (max-width: $breakpoint-lg) {
  .header-matchup {
    gap: 20px;
    flex-wrap: wrap;
  }
  .header-team { min-width: 100px; }
  .score-display { gap: 24px; }
}
</style>
