<template>
  <div class="team-list-page">
    <h2 class="page-title">球队列表</h2>

    <div class="search-bar">
      <el-select v-model="conference" placeholder="分区筛选" clearable style="width:120px">
        <el-option label="东部" value="East" />
        <el-option label="西部" value="West" />
      </el-select>
      <el-button type="primary" @click="loadTeams">
        <el-icon><Search /></el-icon>搜索
      </el-button>
    </div>

    <div class="neu-card" style="padding:0;overflow:hidden">
      <el-table :data="teams" stripe v-loading="loading" style="width:100%">
        <el-table-column prop="teamName" label="球队" width="140">
          <template #default="{ row }">
            <span class="team-name">{{ row.teamName }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="abbreviation" label="缩写" width="80">
          <template #default="{ row }">
            <span class="neu-tag neu-tag--blue">{{ row.abbreviation }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="conference" label="分区" width="80">
          <template #default="{ row }">
            <span class="neu-tag" :class="row.conference === 'East' ? 'neu-tag--green' : 'neu-tag--orange'">
              {{ row.conference === 'East' ? '东部' : '西部' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="defenseType" label="防守类型" width="120" />
        <el-table-column prop="offenseType" label="进攻风格" width="120" />
        <el-table-column prop="strengthLevel" label="实力" width="80" />
        <el-table-column prop="homeWinRate" label="主场胜率" width="110">
          <template #default="{ row }">
            <span :style="{ color: row.homeWinRate > 0.6 ? '#50C878' : '#B0B0B0' }">
              {{ (row.homeWinRate * 100).toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="awayWinRate" label="客场胜率" width="110">
          <template #default="{ row }">
            <span :style="{ color: row.awayWinRate > 0.5 ? '#50C878' : '#B0B0B0' }">
              {{ (row.awayWinRate * 100).toFixed(1) }}%
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

    <div class="pagination-wrap">
      <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" layout="total, prev, pager, next" @current-change="loadTeams" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { teamApi } from '@/api'
import { Search, TrendCharts } from '@element-plus/icons-vue'

const router = useRouter()
const conference = ref('')
const teams = ref([])
const loading = ref(false)
const page = ref(1)
const size = ref(30)
const total = ref(0)

onMounted(() => { loadTeams() })

const loadTeams = async () => {
  loading.value = true
  try {
    const res = await teamApi.getList({ page: page.value, size: size.value, conference: conference.value })
    teams.value = res.data?.records || []
    total.value = res.data?.total || 0
  } catch {} finally { loading.value = false }
}

const goToPredict = (team) => {
  router.push({ path: '/team/predict', query: { teamId: team.teamId } })
}
</script>

<style lang="scss" scoped>
.team-list-page { max-width: 1400px; }

.team-name { font-weight: 600; color: $text-primary; }

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
