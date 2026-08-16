<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>

    <el-row :gutter="24">
      <!-- 系数配置 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">预测系数配置</span></div>
          <el-form :model="coeffForm" label-width="110px">
            <el-form-item v-for="item in coeffItems" :key="item.key" :label="item.label">
              <el-slider v-model="coeffForm[item.key]" :min="item.min" :max="item.max" :step="item.step" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveCoefficients">保存系数</el-button>
              <el-button @click="resetCoefficients">重置默认</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <!-- 功能开关 -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">功能开关</span></div>
          <div class="switch-list">
            <div class="switch-item" v-for="sw in switchItems" :key="sw.key">
              <div class="switch-info">
                <div class="switch-label">{{ sw.label }}</div>
                <div class="switch-desc">{{ sw.desc }}</div>
              </div>
              <el-switch v-model="switchForm[sw.key]" />
            </div>
          </div>
        </div>

        <div class="neu-card" style="margin-top:20px">
          <div class="neu-card-header"><span class="title">赔率融合权重</span></div>
          <div class="weight-control">
            <el-slider v-model="oddsWeight" :min="0" :max="30" :step="1" show-input :show-input-controls="false" />
            <div class="weight-hint">赔率数据在融合预测中的占比: <strong>{{ oddsWeight }}%</strong></div>
          </div>
        </div>

        <div class="neu-card" style="margin-top:20px">
          <div class="neu-card-header"><span class="title">数据源管理</span></div>
          <el-table :data="sources" stripe style="width:100%">
            <el-table-column prop="name" label="数据源" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <span class="neu-tag" :class="row.status === 'ACTIVE' ? 'neu-tag--green' : 'neu-tag--red'">
                  {{ row.status === 'ACTIVE' ? '正常' : '异常' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="isPrimary" label="主数据源" width="100">
              <template #default="{ row }">
                <span v-if="row.isPrimary" class="neu-tag neu-tag--orange">主</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { SEASONS } from '@/constants'
import { configApi, oddsApi } from '@/api'

const coeffItems = [
  { key: 'allStarCoeff', label: '全明星系数', min: 1.0, max: 1.4, step: 0.01 },
  { key: 'veteranCoeff', label: '老将系数', min: 0.8, max: 0.95, step: 0.01 },
  { key: 'injuryCoeff', label: '伤病系数', min: 0.7, max: 1.0, step: 0.01 },
  { key: 'clutchCoeff', label: '关键球系数', min: 0.7, max: 1.3, step: 0.01 },
  { key: 'homeCoeff', label: '主场系数', min: 1.03, max: 1.08, step: 0.001 },
  { key: 'fatigueCoeff', label: '疲劳系数', min: 0.92, max: 1.0, step: 0.01 },
]

const switchItems = [
  { key: 'oddsFusion', label: '赔率融合', desc: '开启后预测结果融合赔率数据' },
  { key: 'autoOptimization', label: '自动优化', desc: '开启后自动进行权重优化' },
  { key: 'autoSwitch', label: '数据源自动切换', desc: '主数据源失败时自动切换备用源' },
]

const coeffForm = reactive({
  allStarCoeff: 1.20,
  veteranCoeff: 0.875,
  injuryCoeff: 0.85,
  clutchCoeff: 1.00,
  homeCoeff: 1.055,
  fatigueCoeff: 0.96,
})

const switchForm = reactive({
  oddsFusion: true,
  autoOptimization: true,
  autoSwitch: true,
})

const oddsWeight = ref(20)
const availableSeasons = SEASONS
const sources = ref([])

onMounted(() => { loadConfig(); loadSources() })

const loadConfig = async () => {
  try { await configApi.get() } catch (e) { console.error(e) }
}

const loadSources = async () => {
  try { const res = await oddsApi.getSource(); sources.value = res.data || [] } catch (e) { console.error(e) }
}

const saveCoefficients = async () => {
  try {
    const keys = ['all_star_coeff', 'veteran_coeff', 'injury_coeff', 'clutch_coeff', 'home_coeff', 'fatigue_coeff']
    const values = [coeffForm.allStarCoeff, coeffForm.veteranCoeff, coeffForm.injuryCoeff,
                    coeffForm.clutchCoeff, coeffForm.homeCoeff, coeffForm.fatigueCoeff]
    await Promise.all(keys.map((key, i) =>
      configApi.update({ configGroup: 'COEFFICIENT', configKey: key, configValue: values[i].toString() })
    ))
    ElMessage.success('全部系数已保存')
  } catch { ElMessage.error('保存失败') }
}

const resetCoefficients = () => {
  coeffForm.allStarCoeff = 1.20
  coeffForm.veteranCoeff = 0.875
  coeffForm.injuryCoeff = 0.85
  coeffForm.clutchCoeff = 1.00
  coeffForm.homeCoeff = 1.055
  coeffForm.fatigueCoeff = 0.96
  ElMessage.info('已重置为默认值')
}
</script>

<style lang="scss" scoped>
.settings-page { max-width: 1400px; margin: 0 auto; }

.switch-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.switch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  transition: border-color $transition-fast;

  &:hover { border-color: $border-light; }
}

.switch-info {
  .switch-label { font-size: 14px; font-weight: 600; color: $text-primary; }
  .switch-desc { font-size: 12px; color: $text-muted; margin-top: 2px; }
}

.weight-control {
  .weight-hint {
    margin-top: 10px;
    font-size: 13px;
    color: $text-secondary;
    strong { color: $color-nba-blue; }
  }
}
</style>
