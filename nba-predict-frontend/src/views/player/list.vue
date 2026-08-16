<template>
  <div class="player-list-page">
    <h2 class="page-title">球员列表</h2>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索球员姓名..." clearable style="width:240px" @keyup.enter="loadPlayers" />
      <el-select v-model="position" placeholder="位置筛选" clearable style="width:120px">
        <el-option label="PG 控卫" value="PG" />
        <el-option label="SG 分卫" value="SG" />
        <el-option label="SF 小前" value="SF" />
        <el-option label="PF 大前" value="PF" />
        <el-option label="C 中锋" value="C" />
      </el-select>
      <el-select v-model="teamId" placeholder="球队筛选" clearable filterable style="width:160px">
        <el-option v-for="t in teamOptions" :key="t.teamId" :label="t.teamName" :value="t.teamId">
          <span class="team-cell">
            <TeamLogo :abbr="t.abbreviation || ''" :size="20" />
            <span>{{ t.teamName }}</span>
          </span>
        </el-option>
      </el-select>
      <el-button type="primary" @click="loadPlayers">
        <el-icon><Search /></el-icon>搜索
      </el-button>
    </div>

    <!-- 球员表格 -->
    <div class="neu-card" style="padding:0;overflow:hidden">
      <el-table :data="players" stripe v-loading="loading" style="width:100%">
        <el-table-column prop="playerName" label="姓名" width="140">
          <template #default="{ row }">
            <span class="player-name">{{ row.playerName }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="position" label="位置" width="80">
          <template #default="{ row }">
            <span class="neu-tag neu-tag--blue">{{ row.position }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="teamName" label="球队" width="130">
          <template #default="{ row }">
            <span class="team-cell">
              <TeamLogo :abbr="teamAbbrOf(row.teamName)" :size="22" />
              <span>{{ row.teamName || '-' }}</span>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="70" />
        <el-table-column prop="height" label="身高(cm)" width="100" />
        <el-table-column prop="allStarCount" label="全明星" width="80">
          <template #default="{ row }">
            <span :style="{ color: row.allStarCount > 0 ? '#E6A762' : '#6B6B6B' }">{{ row.allStarCount || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="playerType" label="类型" width="100">
          <template #default="{ row }">
            <span class="neu-tag neu-tag--gray">{{ row.playerType || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="injuryStatus" label="状态" width="100">
          <template #default="{ row }">
            <span class="neu-tag" :class="row.injuryStatus === 'HEALTHY' ? 'neu-tag--green' : 'neu-tag--red'">
              {{ row.injuryStatus === 'HEALTHY' ? '健康' : '伤病' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goToPredict(row)">
              <el-icon><TrendCharts /></el-icon> 预测
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
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
import { playerApi, teamApi } from '@/api'
import { teamAbbrOf } from '@/constants/teams'
import { Search, TrendCharts } from '@element-plus/icons-vue'

const router = useRouter()
const keyword = ref('')
const position = ref('')
const teamId = ref('')
const players = ref([])
const teamOptions = ref([])
const loading = ref(false)
const page = ref(1)
const size = ref(20)
const total = ref(0)

onMounted(() => {
  loadPlayers()
  loadTeams()
})

const loadTeams = async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    teamOptions.value = res.data?.records || []
  } catch (e) { console.error(e) }
}

const loadPlayers = async () => {
  loading.value = true
  try {
    const res = await playerApi.getList({
      page: page.value,
      size: size.value,
      keyword: keyword.value,
      position: position.value,
      teamId: teamId.value,
    })
    players.value = res.data?.records || []
    total.value = res.data?.total || 0
  } catch (e) { console.error(e) } finally {
    loading.value = false
  }
}

const goToPredict = (player) => {
  router.push({ path: '/player/predict', query: { playerId: player.playerId } })
}
</script>

<style lang="scss" scoped>
.player-list-page { max-width: 1400px; margin: 0 auto; }

.player-name {
  font-weight: 600;
  color: $text-primary;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
