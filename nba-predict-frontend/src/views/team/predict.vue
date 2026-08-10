<template>
  <div class="team-predict-page">
    <h2 class="page-title">球队比分预测</h2>

    <el-row :gutter="24">
      <!-- 左侧 -->
      <el-col :span="8">
        <div class="neu-card">
          <div class="neu-card-header"><span class="title">预测参数</span></div>

          <el-form :model="form" label-width="70px">
            <el-form-item label="主队" required>
              <el-select v-model="form.homeTeamId" filterable placeholder="选择主队" style="width:100%">
                <el-option v-for="t in teamOptions" :key="t.teamId" :label="t.teamName" :value="t.teamId" />
              </el-select>
            </el-form-item>
            <el-form-item label="客队" required>
              <el-select v-model="form.awayTeamId" filterable placeholder="选择客队" style="width:100%">
                <el-option v-for="t in teamOptions" :key="t.teamId" :label="t.teamName" :value="t.teamId" />
              </el-select>
            </el-form-item>
            <el-form-item label="场景">
              <el-radio-group v-model="form.scene">
                <el-radio-button label="常规赛">常规赛</el-radio-button>
                <el-radio-button label="季后赛">季后赛</el-radio-button>
                <el-radio-button label="关键战">关键战</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="赔率融合">
              <el-switch v-model="form.useOdds" />
              <span class="hint-text">融合赔率数据</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="predicting" @click="handlePredict" style="width:100%">
                <el-icon><TrendCharts /></el-icon> 开始预测
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 克制关系 -->
        <div v-if="result?.styleMatchup" class="neu-card" style="margin-top:16px">
          <div class="neu-card-header"><span class="title">风格克制</span></div>
          <p class="matchup-text">{{ result.styleMatchup }}</p>
        </div>
      </el-col>

      <!-- 右侧 -->
      <el-col :span="16">
        <div v-if="result" class="animate-fade-in">
          <div class="neu-card">
            <div class="neu-card-header">
              <span class="title">预测结果</span>
              <span class="neu-tag neu-tag--orange">{{ form.scene }}</span>
            </div>

            <el-tabs v-model="activeVersion" class="dark-tabs">
              <el-tab-pane label="纯系统预测" name="system">
                <div class="score-display">
                  <div class="team-score team-score--home">
                    <div class="team-name">{{ result.homeTeamName }}</div>
                    <div class="score">{{ result.predictHomeScore }}</div>
                    <div class="label">主队得分</div>
                  </div>
                  <div class="vs-badge">VS</div>
                  <div class="team-score team-score--away">
                    <div class="team-name">{{ result.awayTeamName }}</div>
                    <div class="score">{{ result.predictAwayScore }}</div>
                    <div class="label">客队得分</div>
                  </div>
                </div>
                <div class="grid-3" style="margin-top:24px">
                  <div class="summary-stat">
                    <div class="summary-label">预测总分</div>
                    <div class="summary-value">{{ result.predictTotalScore }}</div>
                  </div>
                  <div class="summary-stat">
                    <div class="summary-label">预测分差</div>
                    <div class="summary-value" :style="{ color: result.predictScoreDiff > 0 ? '#50C878' : '#E97451' }">
                      {{ result.predictScoreDiff > 0 ? '+' : '' }}{{ result.predictScoreDiff }}
                    </div>
                  </div>
                  <div class="summary-stat">
                    <div class="summary-label">预测胜负</div>
                    <div class="summary-value" :style="{ color: result.predictScoreDiff > 0 ? '#50C878' : '#E97451' }">
                      {{ result.predictScoreDiff > 0 ? '主胜' : '客胜' }}
                    </div>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="融合预测" name="odds" :disabled="!form.useOdds">
                <template v-if="form.useOdds">
                  <div class="score-display">
                    <div class="team-score team-score--home">
                      <div class="team-name">{{ result.homeTeamName }}</div>
                      <div class="score">{{ result.predictHomeScoreOdds }}</div>
                      <div class="label">主队得分</div>
                    </div>
                    <div class="vs-badge">VS</div>
                    <div class="team-score team-score--away">
                      <div class="team-name">{{ result.awayTeamName }}</div>
                      <div class="score">{{ result.predictAwayScoreOdds }}</div>
                      <div class="label">客队得分</div>
                    </div>
                  </div>
                  <div class="grid-3" style="margin-top:24px">
                    <div class="summary-stat">
                      <div class="summary-label">预测总分</div>
                      <div class="summary-value">{{ result.predictTotalScoreOdds }}</div>
                    </div>
                    <div class="summary-stat">
                      <div class="summary-label">预测分差</div>
                      <div class="summary-value">{{ result.predictScoreDiffOdds }}</div>
                    </div>
                    <div class="summary-stat">
                      <div class="summary-label">赔率权重</div>
                      <div class="summary-value">20%</div>
                    </div>
                  </div>
                </template>
                <div v-else class="empty-state">
                  <div class="empty-title">请开启赔率融合</div>
                  <div class="empty-desc">在左侧开启赔率融合功能后可查看融合预测结果</div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>

          <!-- 系数详情 -->
          <div class="neu-card" style="margin-top:16px" v-if="result.coefficients">
            <div class="neu-card-header"><span class="title">系数详情</span></div>
            <el-descriptions :column="3" border>
              <el-descriptions-item v-for="(value, key) in result.coefficients" :key="key" :label="String(key)">
                {{ value }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>

        <div v-else class="neu-card">
          <div class="empty-state">
            <el-icon class="empty-icon"><Trophy /></el-icon>
            <div class="empty-title">选择主客队开始预测</div>
            <div class="empty-desc">在左侧选择主队和客队，点击预测按钮查看比分预测结果</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { teamApi } from '@/api'
import { Trophy, TrendCharts } from '@element-plus/icons-vue'

const form = reactive({ homeTeamId: null, awayTeamId: null, scene: '常规赛', useOdds: false })
const teamOptions = ref([])
const predicting = ref(false)
const result = ref(null)
const activeVersion = ref('system')

onMounted(async () => {
  try {
    const res = await teamApi.getList({ page: 1, size: 30 })
    teamOptions.value = res.data?.records || []
  } catch (e) { console.error(e) }
})

const handlePredict = async () => {
  if (!form.homeTeamId || !form.awayTeamId) { ElMessage.warning('请选择主客队'); return }
  if (form.homeTeamId === form.awayTeamId) { ElMessage.warning('主客队不能相同'); return }
  predicting.value = true
  try {
    const res = await teamApi.predict({ ...form })
    result.value = res.data
    activeVersion.value = 'system'
    ElMessage.success('预测完成')
  } catch { ElMessage.error('预测失败') } finally { predicting.value = false }
}
</script>

<style lang="scss" scoped>
.team-predict-page { max-width: 1400px; }

.hint-text { margin-left: 10px; font-size: 12px; color: $text-muted; }
.matchup-text { font-size: 14px; color: $text-secondary; line-height: 1.7; }

.score-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 48px;
  padding: 32px 0;
}

.team-score {
  text-align: center;

  .team-name { font-size: 16px; color: $text-secondary; margin-bottom: 8px; }
  .score { font-size: 56px; font-weight: 800; line-height: 1; }
  .label { font-size: 12px; color: $text-muted; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.5px; }

  &--home .score { color: $color-nba-blue; }
  &--away .score { color: $color-nba-red; }
}

.vs-badge {
  font-size: 20px;
  font-weight: 800;
  color: $text-muted;
  padding: 12px 16px;
  border-radius: $radius-full;
  background: $bg-elevated;
  border: 1px solid $border-dark;
}

.summary-stat {
  text-align: center;
  padding: 18px;
  background: $bg-elevated;
  border-radius: $radius-md;
  border: 1px solid $border-dark;

  .summary-label { font-size: 12px; color: $text-muted; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .summary-value { font-size: 28px; font-weight: 800; color: $text-primary; }
}

.dark-tabs {
  :deep(.el-tabs__item) {
    color: $text-secondary;
    &.is-active { color: $color-nba-blue; }
  }
  :deep(.el-tabs__active-bar) { background: $color-nba-blue; }
  :deep(.el-tabs__nav-wrap::after) { background: $border-dark; }
}
</style>
