<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>

    <el-row :gutter="24">
      <!-- 赔率融合权重（唯一运行时生效的调参项） -->
      <el-col :span="12">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">赔率融合权重</span></div>
          <div class="weight-control">
            <el-slider v-model="oddsWeight" :min="0" :max="30" :step="1" show-input :show-input-controls="false" />
            <div class="weight-hint">赔率数据在融合预测中的占比: <strong>{{ oddsWeight }}%</strong></div>
            <div class="weight-note">预测公式系数已由回测脚本调优（scripts/tune_coefficients.py），此处仅开放赔率融合权重</div>
            <div class="weight-actions">
              <el-button type="primary" :loading="saving" @click="saveOddsWeight">保存权重</el-button>
            </div>
          </div>
        </div>

        <!-- 功能开关 -->
        <div class="neu-card" style="margin-top:20px">
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
      </el-col>

      <!-- 数据源管理 -->
      <el-col :span="12">
        <div class="neu-card">
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
import { configApi, oddsApi } from '@/api'

const switchItems = [
  { key: 'oddsFusion', label: '赔率融合', desc: '开启后预测结果融合赔率数据' },
  { key: 'autoOptimization', label: '自动优化', desc: '开启后自动进行权重优化' },
  { key: 'autoSwitch', label: '数据源自动切换', desc: '主数据源失败时自动切换备用源' },
]

const switchForm = reactive({
  oddsFusion: true,
  autoOptimization: true,
  autoSwitch: true,
})

const oddsWeight = ref(20)
const saving = ref(false)
const sources = ref([])

onMounted(() => { loadConfig(); loadSources() })

const loadConfig = async () => {
  try {
    const res = await configApi.getByGroup('COEFFICIENT')
    const list = res.data || []
    const oddsItem = list.find(c => c.configKey === 'odds_weight' || c.config_key === 'odds_weight')
    if (oddsItem) {
      const v = parseFloat(oddsItem.configValue ?? oddsItem.config_value)
      oddsWeight.value = Math.round((v ?? 0.2) * 100)
    }
  } catch (e) { console.error(e) }
}

const loadSources = async () => {
  try { const res = await oddsApi.getSource(); sources.value = res.data || [] } catch (e) { console.error(e) }
}

const saveOddsWeight = async () => {
  saving.value = true
  try {
    await configApi.update({
      configGroup: 'COEFFICIENT',
      configKey: 'odds_weight',
      configValue: (oddsWeight.value / 100).toString(),
    })
    ElMessage.success('赔率融合权重已保存')
  } catch { ElMessage.error('保存失败') } finally { saving.value = false }
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

  .weight-note {
    margin-top: 8px;
    font-size: 12px;
    color: $text-muted;
    line-height: 1.6;
  }

  .weight-actions {
    margin-top: 14px;
  }
}
</style>
