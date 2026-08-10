<template>
  <div class="home-page">
    <h2 class="page-title">NBA 赛程</h2>

    <!-- 日期选择 + 标签切换 -->
    <div class="schedule-controls">
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="选择日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        :clearable="false"
        class="neu-date-picker"
        @change="handleDateChange"
      />
      <div class="tab-switch">
        <button
          :class="['tab-btn', { active: activeTab === 'today' }]"
          @click="switchTab('today')"
        >
          今日赛程
        </button>
        <button
          :class="['tab-btn', { active: activeTab === 'recent' }]"
          @click="switchTab('recent')"
        >
          近期赛果
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="neu-card">
      <div class="loading-overlay" style="position:static;min-height:200px">
        <div class="loading-spinner"></div>
        <div class="loading-text">赛程加载中...</div>
      </div>
    </div>

    <!-- 比赛列表 -->
    <template v-else-if="gameList.length">
      <div class="game-list animate-fade-in">
        <div
          v-for="game in gameList"
          :key="game.gameId"
          class="game-card neu-card neu-card--flat"
          @click="goToGame(game.gameId)"
        >
          <!-- 左侧: 状态标识 -->
          <div class="game-status">
            <span :class="['status-badge', statusClass(game)]">
              {{ statusText(game) }}
            </span>
          </div>

          <!-- 中间: 对阵信息 -->
          <div class="game-matchup">
            <div class="team team--home" :class="{ winner: game.homeWin === 1 }">
              <span class="team-abbr">{{ teamMap[game.homeTeamId]?.abbreviation || 'HOM' }}</span>
              <span v-if="isFinished(game)" class="team-score">{{ game.homeScore }}</span>
            </div>
            <div class="matchup-divider">
              <span class="vs-text">VS</span>
              <span v-if="isScheduled(game)" class="game-time">{{ formatTime(game.gameDate) }}</span>
            </div>
            <div class="team team--away" :class="{ winner: game.homeWin === 0 }">
              <span class="team-abbr">{{ teamMap[game.awayTeamId]?.abbreviation || 'AWY' }}</span>
              <span v-if="isFinished(game)" class="team-score">{{ game.awayScore }}</span>
            </div>
          </div>

          <!-- 右侧: 操作 / 胜者标记 -->
          <div class="game-action">
            <template v-if="isFinished(game)">
              <span class="win-badge" v-if="game.homeWin === 1">主胜</span>
              <span class="win-badge win-badge--away" v-else>客胜</span>
              <span class="score-diff">分差 {{ game.scoreDiff }}</span>
            </template>
            <template v-else>
              <el-button type="primary" size="small" class="predict-btn" @click.stop="goToGame(game.gameId)">
                预测
              </el-button>
            </template>
          </div>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="neu-card">
      <div class="empty-state">
        <el-icon class="empty-icon"><Calendar /></el-icon>
        <div class="empty-title">今日无比赛</div>
        <div class="empty-desc">{{ activeTab === 'today' ? '当天没有比赛安排' : '近期没有比赛记录' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Calendar } from '@element-plus/icons-vue'
import { gameApi, teamApi } from '@/api'

const router = useRouter()

const formatDateStr = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const activeTab = ref('today')
const selectedDate = ref(formatDateStr(new Date()))
const gameList = ref([])
const loading = ref(false)
const teamMap = ref({})

const addDays = (dateStr, days) => {
  const date = new Date(dateStr)
  date.setDate(date.getDate() + days)
  return formatDateStr(date)
}

onMounted(() => {
  loadTeamMap()
  loadGames()
})

const loadTeamMap = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    const records = res.data?.records || []
    for (const t of records) {
      if (t.teamId != null) {
        teamMap.value[t.teamId] = t
      }
    }
  } catch (e) {
    console.error('加载球队列表失败', e)
  }
}

const loadGames = async () => {
  loading.value = true
  try {
    let params
    if (activeTab.value === 'today') {
      params = { gameDate: selectedDate.value, page: 1, size: 100 }
    } else {
      // 近期赛果: 最近7天
      params = {
        page: 1,
        size: 200,
      }
    }

    const res = await gameApi.getList(params)
    let records = res.data?.records || []

    if (activeTab.value === 'recent') {
      // 过滤最近7天
      const cutoff = addDays(formatDateStr(new Date()), -7)
      records = records.filter((g) => g.gameDate >= cutoff)
      records.sort((a, b) => {
        if (a.gameDate !== b.gameDate) return b.gameDate.localeCompare(a.gameDate)
        return (b.gameId || 0) - (a.gameId || 0)
      })
    }

    gameList.value = records
  } catch (e) {
    console.error('加载赛程失败', e)
    gameList.value = []
  } finally {
    loading.value = false
  }
}

const handleDateChange = () => {
  if (activeTab.value === 'today') {
    loadGames()
  }
}

const switchTab = (tab) => {
  activeTab.value = tab
  if (tab === 'today') {
    selectedDate.value = formatDateStr(new Date())
  }
  loadGames()
}

const isFinished = (game) => game.status === 'FINISHED'
const isScheduled = (game) => game.status === 'SCHEDULED'
const isLive = (game) => game.status === 'LIVE' || game.status === 'IN_PROGRESS'

const statusClass = (game) => {
  if (isFinished(game)) return 'status--finished'
  if (isLive(game)) return 'status--live'
  return 'status--upcoming'
}

const statusText = (game) => {
  if (isFinished(game)) return '已结束'
  if (isLive(game)) return '进行中'
  return '未开始'
}

const formatTime = (dateStr) => {
  if (!dateStr) return ''
  // gameDate字段是日期，没有具体时间；对未开始比赛显示日期即可
  const d = new Date(dateStr)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${m}-${day}`
}

const goToGame = (gameId) => {
  router.push(`/game/${gameId}`)
}
</script>

<style lang="scss" scoped>
.home-page {
  max-width: 1200px;
}

// 控制栏
.schedule-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.neu-date-picker {
  :deep(.el-input__wrapper) {
    background: $bg-elevated;
    box-shadow: $neu-pressed;
    border: 1px solid $border-dark;
    border-radius: $radius-md;
  }
  :deep(.el-input__inner) {
    color: $text-primary;
  }
}

.tab-switch {
  display: flex;
  gap: 0;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  box-shadow: $neu-pressed;
  overflow: hidden;
}

.tab-btn {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: $text-secondary;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all $transition-fast;

  &.active {
    background: $color-nba-blue;
    color: #fff;
    box-shadow: $neu-raised-sm;
  }

  &:not(.active):hover {
    color: $text-primary;
    background: rgba($color-nba-blue, 0.08);
  }
}

// 比赛列表
.game-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.game-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 24px;
  cursor: pointer;
  transition: all $transition-fast;
  border-left: 3px solid transparent;

  &:hover {
    border-left-color: $color-nba-blue;
  }
}

// 状态
.game-status {
  flex-shrink: 0;
  width: 64px;
}

.status-badge {
  display: inline-block;
  padding: 3px 10px;
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

// 对阵
.game-matchup {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
}

.team {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 100px;
  justify-content: flex-end;

  &--away {
    justify-content: flex-start;
  }

  .team-abbr {
    font-size: 18px;
    font-weight: 700;
    color: $text-primary;
    letter-spacing: 0.5px;
  }

  .team-score {
    font-size: 28px;
    font-weight: 800;
    color: $text-primary;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  &.winner .team-score {
    color: $color-positive;
  }

  &.winner .team-abbr {
    color: $color-positive;
  }
}

.matchup-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;

  .vs-text {
    font-size: 13px;
    font-weight: 700;
    color: $text-muted;
    padding: 4px 12px;
    border-radius: $radius-full;
    background: $bg-elevated;
    border: 1px solid $border-dark;
  }

  .game-time {
    font-size: 11px;
    color: $text-muted;
  }
}

// 操作区
.game-action {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.win-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: $radius-full;
  font-size: 11px;
  font-weight: 700;
  background: rgba($color-positive, 0.12);
  color: $color-positive;
  border: 1px solid rgba($color-positive, 0.25);

  &--away {
    background: rgba($color-nba-red, 0.12);
    color: $color-nba-red;
    border-color: rgba($color-nba-red, 0.25);
  }
}

.score-diff {
  font-size: 11px;
  color: $text-muted;
}

.predict-btn {
  background: $color-nba-blue !important;
  border-color: $color-nba-blue !important;

  &:hover {
    background: color.adjust($color-nba-blue, $lightness: 8%) !important;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (max-width: $breakpoint-lg) {
  .game-card {
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  }

  .game-status { width: auto; }
  .game-matchup { width: 100%; }
  .team { min-width: 80px; }
}
</style>
