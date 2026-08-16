<template>
  <div class="player-detail-page animate-fade-in">
    <!-- 加载状态 -->
    <div v-if="loading" class="neu-card detail-narrow">
      <div class="loading-overlay" style="position: static; min-height: 300px">
        <div class="loading-spinner"></div>
        <div class="loading-text">球员数据加载中...</div>
      </div>
    </div>

    <template v-else-if="player">
      <!-- 头部卡片（与球队详情页同款：全宽贴边） -->
      <div class="neu-card player-hero">
        <div class="hero-body">
          <div class="hero-logo">
            <TeamLogo :abbr="player.teamAbbr || ''" :size="120" />
          </div>
          <div class="hero-info">
            <h2 class="hero-name">
              {{ player.playerName }}
              <span class="hero-name-en">{{ player.playerNameEn }}</span>
            </h2>
            <div class="hero-tags">
              <span class="neu-tag neu-tag--blue">{{ player.teamName || '-' }}</span>
              <span class="neu-tag" :class="player.injuryStatus === 'HEALTHY' ? 'neu-tag--green' : 'neu-tag--red'">
                {{ player.injuryStatus === 'HEALTHY' ? '健康' : '伤病' }}
              </span>
            </div>
          </div>
          <!-- 球员基本信息 -->
          <div class="hero-basic">
            <div class="basic-row">
              <span class="basic-label">位置</span>
              <span class="basic-value">{{ player.position || '-' }}</span>
            </div>
            <div class="basic-row">
              <span class="basic-label">身高</span>
              <span class="basic-value">{{ player.height != null ? player.height + 'cm' : '-' }}</span>
            </div>
            <div class="basic-row">
              <span class="basic-label">体重</span>
              <span class="basic-value">{{ player.weight != null ? player.weight + 'kg' : '-' }}</span>
            </div>
            <div class="basic-row">
              <span class="basic-label">全明星</span>
              <span class="basic-value">{{ player.allStarCount || 0 }} 次</span>
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

      <!-- 数据卡片 -->
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
    </template>

    <!-- 错误状态 -->
    <div v-else class="neu-card detail-narrow">
      <div class="empty-state">
        <el-icon class="empty-icon"><Warning /></el-icon>
        <div class="empty-title">球员不存在</div>
        <div class="empty-desc">未找到该球员的数据</div>
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

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const player = ref(null)
const season = ref(CURRENT_SEASON)
const seasonOptions = ref([CURRENT_SEASON])

const playerId = computed(() => Number(route.params.playerId))

// Python API 响应 → 展示字段
const toPlayerCamel = (p) => ({
  playerId: p.player_id,
  playerName: p.player_name,
  playerNameEn: p.player_name_en,
  position: p.position,
  jerseyNumber: p.jersey_number,
  teamId: p.team_id,
  teamName: p.team_name,
  teamAbbr: p.team_abbr,
  age: p.age,
  height: p.height,
  weight: p.weight,
  allStarCount: p.all_star_count,
  injuryStatus: p.injury_status,
})

const sd = computed(() => player.value?.seasonData || {})

const statItems = computed(() => {
  const s = sd.value
  const signed = (v) => ({
    value: formatSigned(v),
    cls: (v ?? 0) >= 0 ? 'text-positive' : 'text-negative',
  })
  return [
    { label: '场均得分', value: formatStat(s.points_per_game) },
    { label: '场均篮板', value: formatStat(s.rebounds_per_game) },
    { label: '场均助攻', value: formatStat(s.assists_per_game) },
    { label: '场均抢断', value: formatStat(s.steals_per_game) },
    { label: '场均盖帽', value: formatStat(s.blocks_per_game) },
    { label: '场均失误', value: formatStat(s.turnovers_per_game) },
    { label: '上场时间', value: formatStat(s.minutes_per_game) },
    { label: '场次', value: formatStat(s.games_played) },
    { label: '命中率', value: formatPct(s.fg_percentage) },
    { label: '三分命中率', value: formatPct(s.three_percentage) },
    { label: '罚球命中率', value: formatPct(s.ft_percentage) },
    { label: '真实命中率', value: formatPct(s.true_shooting_pct) },
    { label: '有效命中率', value: formatPct(s.effective_fg_pct) },
    { label: '使用率', value: formatPctRaw(s.usage_rate) },
    { label: '进攻效率', value: formatStat(s.offensive_rating) },
    { label: '防守效率', value: formatStat(s.defensive_rating) },
    { ...signed(s.net_rating), label: '净效率' },
  ]
})

onMounted(() => {
  loadPlayerDetail()
})

const loadPlayerDetail = async () => {
  loading.value = true
  try {
    const res = await dataApi.getPlayerDetail(playerId.value, season.value)
    const data = res.data || res
    player.value = { ...toPlayerCamel(data), seasonData: data.season_data || {} }
    // 从历史赛季列表提取可选赛季
    const history = (data.seasons || []).map((s) => s.season).filter(Boolean)
    if (history.length) {
      seasonOptions.value = history
      if (!history.includes(season.value)) season.value = history[0]
    } else if (!seasonOptions.value.includes(season.value)) {
      seasonOptions.value.push(season.value)
    }
  } catch (e) {
    console.error('加载球员详情失败', e)
    player.value = null
  } finally {
    loading.value = false
  }
}

const switchSeason = (s) => {
  if (s === season.value) return
  season.value = s
  loadPlayerDetail()
}

const goPredict = () => {
  router.push({ path: '/player/predict', query: { playerId: player.value.playerId } })
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

// 使用率等接口直接给百分数刻度的字段
const formatPctRaw = (val) => {
  if (val == null) return '-'
  return Number(val).toFixed(1) + '%'
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
.player-detail-page {
  // 不加 max-width
}

// 除头部外的模块保持窄宽居中
.detail-narrow {
  max-width: 1200px;
  margin: 0 auto;
}

// 头部：整卡贴边，向上撑满，左右顶到内容区边缘
.player-hero {
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
</style>
