<template>
  <div class="players-page">
    <h2 class="page-title">球员数据</h2>

    <!-- 筛选栏 -->
    <div class="search-bar">
      <el-select
        v-model="season"
        placeholder="赛季"
        style="width: 130px"
        @change="loadPlayers"
      >
        <el-option
          v-for="s in SEASONS"
          :key="s"
          :label="s"
          :value="s"
        />
      </el-select>
      <el-select
        v-model="teamFilter"
        filterable
        clearable
        placeholder="球队筛选"
        style="width: 160px"
        @change="loadPlayers"
      >
        <el-option
          v-for="t in teamOptions"
          :key="t.teamId"
          :label="t.teamName"
          :value="t.teamId"
        />
      </el-select>
      <el-select
        v-model="positionFilter"
        clearable
        placeholder="位置筛选"
        style="width: 120px"
        @change="loadPlayers"
      >
        <el-option label="PG 控卫" value="PG" />
        <el-option label="SG 分卫" value="SG" />
        <el-option label="SF 小前" value="SF" />
        <el-option label="PF 大前" value="PF" />
        <el-option label="C 中锋" value="C" />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="搜索球员姓名..."
        clearable
        style="width: 200px"
        @keyup.enter="loadPlayers"
        @clear="loadPlayers"
      />
      <el-button type="primary" @click="loadPlayers">
        <el-icon><Search /></el-icon>搜索
      </el-button>
    </div>

    <!-- 数据表 -->
    <div class="neu-card" style="padding: 0; overflow: hidden">
      <el-table
        :data="players"
        v-loading="loading"
        stripe
        style="width: 100%"
        @row-click="toggleDetail"
        @sort-change="onSortChange"
        :default-sort="{ prop: 'pointsPerGame', order: 'descending' }"
      >
        <el-table-column
          prop="playerName"
          label="球员名"
          width="150"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="player-name-cell">{{ row.playerName }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="position"
          label="位置"
          width="80"
        >
          <template #default="{ row }">
            <span class="neu-tag" :class="positionTagClass(row.position)">{{ row.position || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="teamName"
          label="球队"
          width="130"
        />
        <el-table-column
          prop="gamesPlayed"
          label="场次"
          width="80"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ row.gamesPlayed || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="pointsPerGame"
          label="得分"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="stat-highlight mono-num">{{ formatStat(row.pointsPerGame) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="reboundsPerGame"
          label="篮板"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.reboundsPerGame) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="assistsPerGame"
          label="助攻"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.assistsPerGame) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="fieldGoalPct"
          label="命中率"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.fieldGoalPct) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="threePtPct"
          label="三分%"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.threePtPct) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="per"
          label="PER"
          width="80"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatStat(row.per) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="usageRate"
          label="使用率"
          width="90"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="mono-num">{{ formatPct(row.usageRate) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 展开详情 -->
    <div v-if="expandedPlayer" class="neu-card detail-card animate-fade-in" style="margin-top: 16px">
      <div class="neu-card-header">
        <span class="title">
          {{ expandedPlayer.playerName }} - 完整数据
        </span>
        <span class="neu-tag neu-tag--blue">{{ season }}</span>
      </div>
      <el-row :gutter="16">
        <el-col :span="8">
          <div class="detail-block">
            <div class="detail-block-title">基本信息</div>
            <div class="detail-item">
              <span class="detail-label">位置</span>
              <span class="detail-value">{{ expandedPlayer.position || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">球队</span>
              <span class="detail-value">{{ expandedPlayer.teamName || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">场次</span>
              <span class="detail-value mono-num">{{ expandedPlayer.gamesPlayed || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">首发</span>
              <span class="detail-value mono-num">{{ expandedPlayer.gamesStarted || '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">上场时间</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.minutesPerGame) }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="detail-block">
            <div class="detail-block-title">得分数据</div>
            <div class="detail-item">
              <span class="detail-label">场均得分</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.pointsPerGame) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">命中率</span>
              <span class="detail-value mono-num">{{ formatPct(expandedPlayer.fieldGoalPct) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">三分%</span>
              <span class="detail-value mono-num">{{ formatPct(expandedPlayer.threePtPct) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">罚球%</span>
              <span class="detail-value mono-num">{{ formatPct(expandedPlayer.freeThrowPct) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">真实命中率</span>
              <span class="detail-value mono-num">{{ formatPct(expandedPlayer.trueShootingPct) }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="detail-block">
            <div class="detail-block-title">效率 & 进阶</div>
            <div class="detail-item">
              <span class="detail-label">篮板</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.reboundsPerGame) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">助攻</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.assistsPerGame) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">抢断</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.stealsPerGame) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">盖帽</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.blocksPerGame) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">PER</span>
              <span class="detail-value mono-num">{{ formatStat(expandedPlayer.per) }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" size="small" @click="goToPredict(expandedPlayer)">
          <el-icon><TrendCharts /></el-icon> 预测此球员
        </el-button>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="limit"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadPlayers"
        @size-change="loadPlayers"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, TrendCharts } from '@element-plus/icons-vue'
import { teamApi } from '@/api'
import { dataApi } from '@/api'
import { SEASONS } from '@/constants'

const router = useRouter()
const season = ref(SEASONS[0])
const teamFilter = ref('')
const positionFilter = ref('')
const keyword = ref('')
const sortBy = ref('pointsPerGame')
const sortOrder = ref('desc')

const players = ref([])
const teamOptions = ref([])
const loading = ref(false)
const page = ref(1)
const limit = ref(20)
const total = ref(0)

const expandedPlayer = ref(null)
const expandedPlayerId = ref(null)

onMounted(() => {
  loadPlayers()
  loadTeams()
})

const loadTeams = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    teamOptions.value = res.data?.records || []
  } catch (e) {
    console.error(e)
  }
}

const loadPlayers = async () => {
  loading.value = true
  expandedPlayer.value = null
  expandedPlayerId.value = null
  try {
    const params = {
      season: season.value,
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
      page: page.value,
      limit: limit.value,
    }
    if (teamFilter.value) params.team_id = teamFilter.value
    if (positionFilter.value) params.position = positionFilter.value
    if (keyword.value) params.keyword = keyword.value

    const res = await dataApi.getPlayers(params)
    const data = res.data || res
    players.value = data.records || data.players || data || []
    total.value = data.total || players.value.length
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const onSortChange = ({ prop, order }) => {
  if (!prop) return
  sortBy.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  loadPlayers()
}

const toggleDetail = (row) => {
  if (expandedPlayerId.value === row.playerId) {
    expandedPlayer.value = null
    expandedPlayerId.value = null
    return
  }
  expandedPlayerId.value = row.playerId
  expandedPlayer.value = row
}

const goToPredict = (player) => {
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

const positionTagClass = (pos) => {
  if (!pos) return 'neu-tag--gray'
  const map = { PG: 'neu-tag--blue', SG: 'neu-tag--green', SF: 'neu-tag--orange', PF: 'neu-tag--red', C: 'neu-tag--gray' }
  return map[pos] || 'neu-tag--gray'
}
</script>

<style lang="scss" scoped>
.players-page {
  max-width: 1400px;
}

.player-name-cell {
  font-weight: 600;
  color: $text-primary;
  cursor: pointer;

  &:hover {
    color: $color-nba-blue;
  }
}

.mono-num {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}

.stat-highlight {
  font-weight: 700;
  color: $color-nba-blue;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

// 详情卡片
.detail-card {
  .el-row {
    margin: 0;
  }
}

.detail-block {
  padding: 12px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  height: 100%;
}

.detail-block-title {
  font-size: 13px;
  font-weight: 600;
  color: $color-nba-blue;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid $border-dark;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;

  &:not(:last-child) {
    border-bottom: 1px solid rgba($border-dark, 0.5);
  }
}

.detail-label {
  font-size: 12px;
  color: $text-muted;
}

.detail-value {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}
</style>
