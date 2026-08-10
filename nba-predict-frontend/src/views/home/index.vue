<template>
  <div class="home-page">
    <!-- 欢迎区 -->
    <div class="welcome-banner animate-fade-in">
      <div class="welcome-text">
        <h1>NBA球员与球队表现预测系统</h1>
        <p>基于数据驱动的智能预测分析平台 · 赛季 2025-26</p>
      </div>
      <div class="welcome-art">
        <svg viewBox="0 0 120 120" width="120" height="120">
          <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(29,66,138,0.3)" stroke-width="2" />
          <circle cx="60" cy="60" r="35" fill="none" stroke="rgba(200,16,46,0.2)" stroke-width="1.5" />
          <circle cx="60" cy="60" r="20" fill="none" stroke="rgba(80,200,120,0.2)" stroke-width="1" />
        </svg>
      </div>
    </div>

    <!-- 核心统计卡片 -->
    <div class="grid-4 animate-fade-in stagger-1">
      <div class="stat-card neu-card neu-card--blue">
        <div class="stat-card-icon">
          <el-icon :size="24"><User /></el-icon>
        </div>
        <div class="stat-card-body">
          <div class="stat-value">{{ overview.playerCount }}+</div>
          <div class="stat-label">现役球员数据</div>
        </div>
        <div class="stat-change stat-change--up">30+ 维度</div>
      </div>

      <div class="stat-card neu-card neu-card--green">
        <div class="stat-card-icon">
          <el-icon :size="24"><Trophy /></el-icon>
        </div>
        <div class="stat-card-body">
          <div class="stat-value">{{ overview.teamCount }}</div>
          <div class="stat-label">NBA球队覆盖</div>
        </div>
        <div class="stat-change stat-change--up">{{ overview.seasonCount }}赛季</div>
      </div>

      <div class="stat-card neu-card neu-card--orange">
        <div class="stat-card-icon">
          <el-icon :size="24"><DataAnalysis /></el-icon>
        </div>
        <div class="stat-card-body">
          <div class="stat-value stat-value--positive">&le;{{ overview.avgError }}</div>
          <div class="stat-label">球员预测 MAE</div>
        </div>
        <div class="stat-change stat-change--up">优化中</div>
      </div>

      <div class="stat-card neu-card neu-card--beige">
        <div class="stat-card-icon">
          <el-icon :size="24"><Connection /></el-icon>
        </div>
        <div class="stat-card-body">
          <div class="stat-value">{{ overview.sourceCount }}</div>
          <div class="stat-label">数据源接入</div>
        </div>
        <div class="neu-tag neu-tag--green">正常运行</div>
      </div>
    </div>

    <!-- 功能入口 -->
    <div class="grid-2 animate-fade-in stagger-2" style="margin-top:24px">
      <div class="entry-card neu-card" @click="router.push('/player/predict')">
        <div class="entry-icon entry-icon--blue">
          <el-icon :size="40"><User /></el-icon>
        </div>
        <div class="entry-body">
          <h3>球员表现预测</h3>
          <p>预测球员单场得分、命中率等数据区间，支持对位分析</p>
        </div>
        <el-icon class="entry-arrow"><ArrowRight /></el-icon>
      </div>

      <div class="entry-card neu-card" @click="router.push('/team/predict')">
        <div class="entry-icon entry-icon--red">
          <el-icon :size="40"><Trophy /></el-icon>
        </div>
        <div class="entry-body">
          <h3>球队比分预测</h3>
          <p>预测球队对战总分、分差及单队得分，支持赔率融合</p>
        </div>
        <el-icon class="entry-arrow"><ArrowRight /></el-icon>
      </div>
    </div>

    <!-- 系统架构 + 系列赛之星 -->
    <div class="grid-2 animate-fade-in stagger-3" style="margin-top:24px">
      <div class="neu-card">
        <div class="neu-card-header">
          <span class="title">系统架构</span>
        </div>
        <div class="arch-grid">
          <div class="arch-item">
            <span class="arch-label">前端</span>
            <span class="arch-value">Vue3 + Element Plus</span>
          </div>
          <div class="arch-item">
            <span class="arch-label">后端</span>
            <span class="arch-value">SpringBoot 3.2</span>
          </div>
          <div class="arch-item">
            <span class="arch-label">算法</span>
            <span class="arch-value">Python + FastAPI</span>
          </div>
          <div class="arch-item">
            <span class="arch-label">数据库</span>
            <span class="arch-value">MySQL 8.0</span>
          </div>
        </div>
      </div>

      <div class="neu-card">
        <div class="neu-card-header">
          <span class="title">最新系列赛之星</span>
          <el-button type="primary" size="small" @click="router.push('/series')">查看全部</el-button>
        </div>
        <div v-if="starsLoading" class="empty-state">
          <div class="loading-spinner"></div>
          <div class="loading-text">加载中...</div>
        </div>
        <div v-else-if="starPlayers.length" class="star-list">
          <div v-for="(p, i) in starPlayers" :key="p.starId" class="star-item">
            <div class="star-rank" :class="'rank-' + (i+1)">{{ i + 1 }}</div>
            <div class="star-info">
              <span class="star-name">{{ playerNameMap[p.playerId] || '球员 #' + p.playerId }}</span>
              <span class="star-team">{{ teamNameMap[p.teamId] || '球队' }} vs {{ teamNameMap[p.opponentTeamId] || '对手' }}</span>
            </div>
            <div class="star-stats">
              <span class="star-pts">{{ p.avgScore }}分</span>
              <span class="star-pct">{{ (Number(p.avgFgPct) * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-icon class="empty-icon"><Star /></el-icon>
          <div class="empty-title">暂无数据</div>
          <div class="empty-desc">系列赛之星数据将在赛季开始后更新</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { User, Trophy, DataAnalysis, Connection, Star, ArrowRight } from '@element-plus/icons-vue'
import { seriesApi, playerApi, teamApi, datasourceApi, recordApi } from '@/api'

const router = useRouter()

const overview = reactive({
  playerCount: 450,
  teamCount: 30,
  seasonCount: 3,
  avgError: 5,
  sourceCount: 4,
})

const starPlayers = ref([])
const starsLoading = ref(false)
const playerNameMap = ref({})
const teamNameMap = ref({})

onMounted(() => {
  loadOverview()
  loadStarPlayers()
})

const loadOverview = async () => {
  // 并行加载各维度数据
  try {
    const [teamRes, sourceRes, recordRes] = await Promise.allSettled([
      teamApi.getList({ page: 1, size: 1 }),
      datasourceApi.getList(),
      recordApi.getList({ page: 1, size: 100, status: 'CALIBRATED' }),
    ])

    if (teamRes.status === 'fulfilled' && teamRes.value?.data) {
      overview.teamCount = teamRes.value.data.total || 30
    }

    if (sourceRes.status === 'fulfilled' && sourceRes.value?.data) {
      const sources = sourceRes.value.data
      overview.sourceCount = sources.length || 4
      const activeCount = sources.filter(s => s.status === 'ACTIVE').length
      if (activeCount > 0) {
        overview.sourceCount = activeCount
      }
    }

    if (recordRes.status === 'fulfilled' && recordRes.value?.data?.records) {
      const records = recordRes.value.data.records
      const errors = records.filter(r => r.errorPoints != null).map(r => r.errorPoints)
      if (errors.length > 0) {
        const avgError = errors.reduce((a, b) => a + b, 0) / errors.length
        overview.avgError = avgError.toFixed(1)
      }
    }
  } catch (e) { console.error(e) }
}

const loadStarPlayers = async () => {
  starsLoading.value = true
  try {
    const res = await seriesApi.getStarList({ page: 1, size: 5, season: '2025-26' })
    const records = res.data?.records || []
    starPlayers.value = records

    // 异步加载球员名和球队名
    const playerIds = [...new Set(records.map(r => r.playerId).filter(Boolean))]
    const teamIds = [...new Set([
      ...records.map(r => r.teamId),
      ...records.map(r => r.opponentTeamId),
    ].filter(Boolean))]

    // 批量并行查询球员名
    const playerPromises = playerIds.map(pid =>
      playerApi.getDetail(pid, { silent: true })
        .then(pRes => { if (pRes.data?.playerName) playerNameMap.value[pid] = pRes.data.playerName })
        .catch(e => console.error(e))
    )
    await Promise.all(playerPromises)

    // 批量查询球队名
    const teamListRes = await teamApi.getList({ page: 1, size: 30 })
    if (teamListRes.data?.records) {
      for (const t of teamListRes.data.records) {
        teamNameMap.value[t.teamId] = t.teamName
      }
    }
  } catch (e) { console.error(e) } finally {
    starsLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.home-page {
  max-width: 1400px;
}

.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 32px 36px;
  background: linear-gradient(135deg, rgba($color-nba-blue, 0.12), rgba($color-nba-red, 0.06));
  border-radius: $radius-xl;
  border: 1px solid $border-dark;
  box-shadow: $neu-raised;
  margin-bottom: 24px;

  h1 {
    font-size: 28px;
    font-weight: 800;
    color: $text-primary;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
  }

  p {
    font-size: 15px;
    color: $text-secondary;
  }
}

.welcome-art {
  opacity: 0.6;
  flex-shrink: 0;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
}

.stat-card-icon {
  width: 52px;
  height: 52px;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: $text-primary;

  .stat-card.neu-card--blue & { background: rgba(29,66,138,0.15); }
  .stat-card.neu-card--green & { background: rgba(168,193,182,0.15); }
  .stat-card.neu-card--orange & { background: rgba(230,167,98,0.15); }
  .stat-card.neu-card--beige & { background: rgba(217,199,184,0.15); }
}

.stat-card-body {
  flex: 1;
  min-width: 0;
}

.entry-card {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 28px 32px;
  cursor: pointer;

  .entry-icon {
    width: 80px;
    height: 80px;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: #fff;

    &--blue { background: linear-gradient(135deg, $color-nba-blue, color.adjust($color-nba-blue, $lightness: 10%)); }
    &--red { background: linear-gradient(135deg, $color-nba-red, color.adjust($color-nba-red, $lightness: 10%)); }
  }

  .entry-body {
    flex: 1;

    h3 {
      font-size: 20px;
      font-weight: 700;
      color: $text-primary;
      margin-bottom: 6px;
    }

    p {
      font-size: 14px;
      color: $text-secondary;
      line-height: 1.5;
    }
  }

  .entry-arrow {
    color: $text-muted;
    font-size: 20px;
    flex-shrink: 0;
    transition: transform $transition-fast;
  }

  &:hover .entry-arrow {
    transform: translateX(4px);
    color: $color-nba-blue;
  }
}

.arch-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;

  .arch-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 14px 16px;
    background: $bg-elevated;
    border-radius: $radius-md;
    border: 1px solid $border-dark;

    .arch-label {
      font-size: 12px;
      color: $text-muted;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .arch-value {
      font-size: 14px;
      font-weight: 600;
      color: $text-primary;
    }
  }
}

.star-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.star-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  transition: all $transition-fast;

  &:hover {
    background: rgba($color-nba-blue, 0.06);
    border-color: rgba($color-nba-blue, 0.2);
  }
}

.star-rank {
  width: 28px;
  height: 28px;
  border-radius: $radius-full;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  background: $bg-card;
  color: $text-secondary;
  border: 1px solid $border-dark;

  &.rank-1 { background: rgba($color-warning, 0.2); color: $color-warning; border-color: rgba($color-warning, 0.3); }
  &.rank-2 { background: rgba($text-secondary, 0.15); color: $text-secondary; }
  &.rank-3 { background: rgba($accent-orange, 0.15); color: $accent-orange; }
}

.star-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;

  .star-name {
    font-size: 14px;
    font-weight: 600;
    color: $text-primary;
  }

  .star-team {
    font-size: 12px;
    color: $text-muted;
  }
}

.star-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;

  .star-pts {
    font-size: 15px;
    font-weight: 700;
    color: $color-positive;
  }

  .star-pct {
    font-size: 12px;
    color: $text-secondary;
  }
}
</style>
