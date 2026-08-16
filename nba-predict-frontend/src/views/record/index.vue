<template>
  <div class="record-page">
    <h2 class="page-title">预测记录</h2>

    <div class="search-bar">
      <el-select v-model="predictType" placeholder="预测类型" clearable style="width:120px">
        <el-option label="球员预测" value="PLAYER" />
        <el-option label="球队预测" value="TEAM" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width:120px">
        <el-option label="待校准" value="PENDING" />
        <el-option label="已完成" value="FINISHED" />
        <el-option label="已校准" value="CALIBRATED" />
      </el-select>
      <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
      <el-button type="primary" @click="loadRecords">
        <el-icon><Search /></el-icon>查询
      </el-button>
    </div>

    <div class="neu-card" style="padding:0;overflow:hidden">
      <el-table :data="records" stripe v-loading="loading" style="width:100%">
        <el-table-column prop="predictType" label="类型" width="100">
          <template #default="{ row }">
            <span class="neu-tag" :class="row.predictType === 'PLAYER' ? 'neu-tag--blue' : 'neu-tag--green'">
              {{ row.predictType === 'PLAYER' ? '球员' : '球队' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="playerName" label="球员/球队" width="200">
          <template #default="{ row }">
            <span v-if="row.predictType === 'TEAM'" class="team-cell">
              <TeamLogo :abbr="teamAbbrOf(row.homeTeamName)" :size="20" />
              <span>{{ row.homeTeamName }}</span>
              <span class="matchup-vs">vs</span>
              <TeamLogo :abbr="teamAbbrOf(row.awayTeamName)" :size="20" />
              <span>{{ row.awayTeamName }}</span>
            </span>
            <span v-else class="name-cell">{{ row.playerName }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="scene" label="场景" width="100" />
        <el-table-column prop="predictPointsMid" label="预测得分" width="100">
          <template #default="{ row }">
            <span :style="{ fontWeight: 600 }">{{ row.predictPointsMid ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="realPoints" label="真实得分" width="100">
          <template #default="{ row }">
            {{ row.realPoints ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="errorPoints" label="误差" width="100">
          <template #default="{ row }">
            <template v-if="row.errorPoints !== null && row.errorPoints !== undefined">
              <span class="error-value" :class="{ 'error-high': row.errorPoints > 5 }">
                {{ row.errorPoints.toFixed(1) }}
              </span>
            </template>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <span class="neu-tag" :class="statusClass(row.status)">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="预测时间" width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'FINISHED'" type="primary" link size="small" @click="handleCalibrate(row)">
              校准
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadRecords"
        @size-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { recordApi } from '@/api'
import { teamAbbrOf } from '@/constants/teams'
import { Search } from '@element-plus/icons-vue'

const predictType = ref('')
const statusFilter = ref('')
const dateRange = ref([])
const records = ref([])
const loading = ref(false)
const page = ref(1)
const size = ref(20)
const total = ref(0)

onMounted(() => { loadRecords() })

const statusLabel = (s) => ({ PENDING: '待校准', FINISHED: '已完成', CALIBRATED: '已校准' }[s] || s)
const statusClass = (s) => ({ PENDING: 'neu-tag--orange', FINISHED: 'neu-tag--blue', CALIBRATED: 'neu-tag--green' }[s] || 'neu-tag--gray')

const loadRecords = async () => {
  loading.value = true
  try {
    const res = await recordApi.getList({ page: page.value, size: size.value, type: predictType.value, status: statusFilter.value })
    records.value = res.data?.records || []
    total.value = res.data?.total || 0
  } catch (e) { console.error(e) } finally { loading.value = false }
}

const handleCalibrate = async (row) => {
  try {
    await recordApi.calibrate({ id: row.id })
    ElMessage.success('校准完成')
    loadRecords()
  } catch { ElMessage.error('校准失败') }
}
</script>

<style lang="scss" scoped>
.record-page { max-width: 1400px; margin: 0 auto; }

.name-cell { font-weight: 600; color: $text-primary; }

.error-value {
  font-weight: 600;
  color: $color-positive;
  &.error-high { color: $color-negative; }
}

.text-muted { color: $text-muted; }

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
