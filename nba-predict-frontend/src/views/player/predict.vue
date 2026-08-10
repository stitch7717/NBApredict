<template>
  <div class="player-predict-page">
    <h2 class="page-title">球员表现预测</h2>

    <el-row :gutter="24">
      <!-- 左侧表单 -->
      <el-col :span="8">
        <div class="neu-card">
          <div class="neu-card-header">
            <span class="title">预测参数</span>
          </div>

          <el-form :model="form" label-width="90px" :rules="rules" ref="formRef">
            <el-form-item label="选择球员" prop="playerId" required>
              <el-select v-model="form.playerId" filterable remote placeholder="搜索球员姓名" :remote-method="searchPlayerDebounced" :loading="playerLoading" style="width:100%">
                <el-option v-for="item in playerOptions" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>

            <el-form-item label="对位球员">
              <el-select v-model="form.opponentPlayerId" filterable remote placeholder="搜索对位球员(可选)" :remote-method="searchOpponent" clearable style="width:100%">
                <el-option v-for="item in opponentOptions" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>

            <el-form-item label="比赛场景" prop="scene" required>
              <el-radio-group v-model="form.scene">
                <el-radio-button label="常规赛">常规赛</el-radio-button>
                <el-radio-button label="季后赛">季后赛</el-radio-button>
                <el-radio-button label="关键战">关键战</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="主客场" prop="homeAway" required>
              <el-radio-group v-model="form.homeAway">
                <el-radio-button label="home">主场</el-radio-button>
                <el-radio-button label="away">客场</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="predicting" @click="handlePredict" style="width:100%">
                <el-icon><TrendCharts /></el-icon> 开始预测
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <!-- 右侧结果 -->
      <el-col :span="16">
        <!-- 有结果 -->
        <div v-if="result" class="animate-fade-in">
          <!-- 球员信息 -->
          <div class="neu-card" style="margin-bottom:20px">
            <div class="player-header">
              <div class="player-avatar">
                <el-icon :size="32"><User /></el-icon>
              </div>
              <div class="player-meta">
                <h3>{{ result.playerName }}</h3>
                <div class="tags">
                  <span v-for="tag in result.matchupTags" :key="tag" class="neu-tag neu-tag--blue">{{ tag }}</span>
                </div>
              </div>
              <div class="scene-tag">
                <span class="neu-tag neu-tag--orange">{{ form.scene }}</span>
              </div>
            </div>
          </div>

          <!-- 三区间预测 -->
          <div class="grid-3" style="margin-bottom:20px">
            <div class="range-card neu-card neu-card--negative">
              <div class="range-label">拉胯区间</div>
              <div class="stat-value stat-value--negative">{{ result.pointsLow }}</div>
              <div class="stat-label">表现低迷时得分</div>
            </div>
            <div class="range-card neu-card neu-card--blue">
              <div class="range-label">常规区间</div>
              <div class="stat-value">{{ result.pointsMid }}</div>
              <div class="stat-label">正常发挥得分</div>
            </div>
            <div class="range-card neu-card neu-card--positive">
              <div class="range-label">爆发区间</div>
              <div class="stat-value stat-value--positive">{{ result.pointsHigh }}</div>
              <div class="stat-label">状态火热时得分</div>
            </div>
          </div>

          <!-- 概览 + 系数 -->
          <el-row :gutter="20">
            <el-col :span="10">
              <div class="neu-card">
                <div class="neu-card-header"><span class="title">预测概览</span></div>
                <div class="overview-grid">
                  <div class="overview-item">
                    <span class="overview-label">预测命中率</span>
                    <span class="overview-value">{{ (result.fgPct * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="overview-item">
                    <span class="overview-label">总修正系数</span>
                    <span class="overview-value">{{ result.totalCoeff }}</span>
                  </div>
                </div>
              </div>
            </el-col>
            <el-col :span="14">
              <div class="neu-card">
                <div class="neu-card-header"><span class="title">系数详情</span></div>
                <el-table :data="coefficientList" stripe style="width:100%">
                  <el-table-column prop="name" label="系数名称" />
                  <el-table-column prop="value" label="数值" width="100" />
                  <el-table-column prop="desc" label="说明" />
                </el-table>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 空状态 -->
        <div v-else class="neu-card">
          <div class="empty-state">
            <el-icon class="empty-icon"><DataAnalysis /></el-icon>
            <div class="empty-title">选择球员开始预测</div>
            <div class="empty-desc">在左侧选择球员和比赛条件，点击预测按钮查看结果</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { playerApi } from '@/api'
import { User, DataAnalysis, TrendCharts } from '@element-plus/icons-vue'

const formRef = ref(null)
const form = reactive({ playerId: null, opponentPlayerId: null, scene: '常规赛', homeAway: 'home' })
const rules = {
  playerId: [{ required: true, message: '请选择球员', trigger: 'change' }],
  scene: [{ required: true, message: '请选择比赛场景', trigger: 'change' }],
  homeAway: [{ required: true, message: '请选择主客场', trigger: 'change' }],
}

const playerOptions = ref([])
const opponentOptions = ref([])
const playerLoading = ref(false)
const predicting = ref(false)
const result = ref(null)

const coefficientList = computed(() => {
  if (!result.value) return []
  return [
    { name: '全明星系数', value: result.value.allStarCoeff, desc: '基于全明星次数和投票排名' },
    { name: '老将系数', value: result.value.veteranCoeff, desc: '基于年龄和经验' },
    { name: '伤病系数', value: result.value.injuryCoeff, desc: '基于伤病状态' },
    { name: '关键球系数', value: result.value.clutchCoeff, desc: '基于关键战表现' },
    { name: '主场系数', value: result.value.homeCoeff, desc: '基于主客场优势' },
    { name: '疲劳系数', value: result.value.fatigueCoeff, desc: '基于赛程密度' },
  ]
})

const searchPlayer = async (query) => {
  if (!query) return
  playerLoading.value = true
  try {
    const res = await playerApi.getList({ keyword: query, page: 1, size: 20 })
    playerOptions.value = res.data?.records || []
  } catch (e) { console.error(e) } finally { playerLoading.value = false }
}

let searchTimer = null
const searchPlayerDebounced = (query) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => searchPlayer(query), 300)
}

const searchOpponent = async (query) => {
  if (!query) return
  try {
    const res = await playerApi.getList({ keyword: query, page: 1, size: 20 })
    opponentOptions.value = res.data?.records || []
  } catch (e) { console.error(e) }
}

const handlePredict = async () => {
  if (!form.playerId) { ElMessage.warning('请选择球员'); return }
  try {
    await formRef.value?.validate()
  } catch { return }
  predicting.value = true
  try {
    const res = await playerApi.predict({ ...form })
    result.value = res.data
    ElMessage.success('预测完成')
  } catch { ElMessage.error('预测失败') } finally { predicting.value = false }
}
</script>

<style lang="scss" scoped>
.player-predict-page { max-width: 1400px; }

.player-header {
  display: flex;
  align-items: center;
  gap: 16px;

  .player-avatar {
    width: 56px;
    height: 56px;
    border-radius: $radius-full;
    background: linear-gradient(135deg, $color-nba-blue, color.adjust($color-nba-blue, $lightness: 12%));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    flex-shrink: 0;
  }

  .player-meta {
    flex: 1;

    h3 {
      font-size: 20px;
      font-weight: 700;
      color: $text-primary;
      margin-bottom: 6px;
    }

    .tags { display: flex; gap: 8px; flex-wrap: wrap; }
  }
}

.range-card {
  text-align: center;
  padding: 28px 20px;

  .range-label {
    font-size: 13px;
    color: $text-muted;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .overview-label {
    font-size: 12px;
    color: $text-muted;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .overview-value {
    font-size: 22px;
    font-weight: 700;
    color: $text-primary;
  }
}
</style>
