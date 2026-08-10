<template>
  <div class="pt-14">
    <section class="max-w-[1200px] mx-auto px-6 py-8">
      <!-- 标题 -->
      <div class="mb-6">
        <h1 class="heading-1 text-text">模型面板</h1>
        <p class="text-sm text-text-muted mt-1">Ridge Regression v2 性能指标与特征分析</p>
      </div>

      <!-- 模型概览 -->
      <div class="grid grid-cols-4 gap-4 mb-6 animate-fade-up">
        <div class="card-flat text-center py-6">
          <div class="text-4xl font-black text-primary">67.6<span class="text-lg">%</span></div>
          <div class="data-label mt-2">验证集准确率</div>
        </div>
        <div class="card-flat text-center py-6">
          <div class="text-3xl font-bold text-text">30</div>
          <div class="data-label mt-2">特征维度</div>
        </div>
        <div class="card-flat text-center py-6">
          <div class="text-3xl font-bold text-text">4</div>
          <div class="data-label mt-2">训练赛季</div>
        </div>
        <div class="card-flat text-center py-6">
          <div class="text-3xl font-bold text-text">5500+</div>
          <div class="data-label mt-2">训练样本</div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-6">
        <!-- 模型信息 -->
        <div class="card animate-fade-up" style="animation-delay: 0.1s">
          <div class="section-header">
            <h2 class="heading-3 text-text">模型配置</h2>
          </div>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="data-label">算法</span>
              <span class="text-sm text-text">Ridge Regression</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">版本</span>
              <span class="text-sm text-text">v2</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">正则化</span>
              <span class="text-sm text-text">L2 (alpha=1.0)</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">数据源</span>
              <span class="text-sm text-text">ESPN Boxscore</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">高阶指标</span>
              <div class="flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-win"></span>
                <span class="text-xs text-text">真实计算</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 修正系数 -->
        <div class="card animate-fade-up" style="animation-delay: 0.15s">
          <div class="section-header">
            <h2 class="heading-3 text-text">修正系数</h2>
          </div>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="data-label">全明星系数</span>
              <span class="text-sm font-mono text-text">1.05-1.15</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">老将系数</span>
              <span class="text-sm font-mono text-text">1.02-1.08</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">伤病系数</span>
              <span class="text-sm font-mono text-text">0.70-0.95</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">关键球系数</span>
              <span class="text-sm font-mono text-text">1.00-1.10</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">主场系数</span>
              <span class="text-sm font-mono text-text">1.03</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="data-label">疲劳系数</span>
              <span class="text-sm font-mono text-text">0.90-1.00</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 特征列表 -->
      <div class="card animate-fade-up mt-6" style="animation-delay: 0.2s">
        <div class="section-header">
          <h2 class="heading-3 text-text">特征列表 (30维)</h2>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div v-for="feature in features" :key="feature.name" class="card-flat py-2 px-3">
            <div class="text-xs font-mono text-text">{{ feature.name }}</div>
            <div class="text-[10px] text-text-muted mt-0.5">{{ feature.desc }}</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
const features = [
  { name: 'ppg', desc: '场均得分' },
  { name: 'rpg', desc: '场均篮板' },
  { name: 'apg', desc: '场均助攻' },
  { name: 'spg', desc: '场均抢断' },
  { name: 'bpg', desc: '场均盖帽' },
  { name: 'topg', desc: '场均失误' },
  { name: 'fg_pct', desc: '投篮命中率' },
  { name: 'fg3_pct', desc: '三分命中率' },
  { name: 'ft_pct', desc: '罚球命中率' },
  { name: 'ts_pct', desc: '真实命中率' },
  { name: 'efg_pct', desc: '有效命中率' },
  { name: 'mpg', desc: '场均上场时间' },
  { name: 'gp', desc: '出场次数' },
  { name: 'usg_pct', desc: '使用率' },
  { name: 'ast_pct', desc: '助攻率' },
  { name: 'reb_pct', desc: '篮板率' },
  { name: 'stl_pct', desc: '抢断率' },
  { name: 'blk_pct', desc: '盖帽率' },
  { name: 'tov_pct', desc: '失误率' },
  { name: 'pts_std', desc: '得分标准差' },
  { name: 'pts_cv', desc: '得分变异系数' },
  { name: 'opp_def_rtg', desc: '对手防守效率' },
  { name: 'home_away', desc: '主客场' },
  { name: 'rest_days', desc: '休息天数' },
  { name: 'back_to_back', desc: '背靠背' },
  { name: 'season_progress', desc: '赛季进度' },
  { name: 'is_playoff', desc: '季后赛标志' },
  { name: 'recent_form', desc: '近5场表现' },
  { name: 'h2h_history', desc: '对位历史' },
  { name: 'team_pace', desc: '球队节奏' },
]
</script>
