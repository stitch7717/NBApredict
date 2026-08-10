<template>
  <div class="pt-14">
    <!-- 轮播区 -->
    <section class="py-8">
      <HeroCarousel />
    </section>

    <!-- 主内容区：左右分栏 -->
    <section class="max-w-[1200px] mx-auto px-6 pb-16">
      <div class="flex gap-6">
        <!-- 左侧主栏 (2/3) -->
        <div class="flex-1 min-w-0 space-y-6">
          <!-- 球员对位分析 — 核心模块 -->
          <PlayerMatchup />

          <!-- 球队分析 -->
          <TeamAnalysis />

          <!-- 近期比赛 -->
          <div class="card animate-fade-up" style="animation-delay: 0.1s">
            <div class="flex items-center justify-between mb-5">
              <div class="section-header mb-0">
                <h2 class="heading-2 text-text">近期比赛</h2>
              </div>
            </div>

            <div v-if="recentGames.length > 0" class="space-y-3">
              <div
                v-for="game in recentGames"
                :key="game.game_id"
                class="card-flat flex items-center gap-4"
              >
                <div class="w-16 flex flex-col items-center gap-1">
                  <span class="text-[11px] text-text-muted">{{ game.game_date?.slice(5) }}</span>
                </div>

                <div class="flex items-center gap-3 flex-1">
                  <span class="text-sm font-bold text-text w-10 text-right">{{ game.home_abbr }}</span>
                  <div class="flex items-center gap-1.5">
                    <span class="text-base font-mono font-bold" :class="game.home_score > game.away_score ? 'text-win' : 'text-text'">{{ game.home_score }}</span>
                    <span class="text-xs text-text-muted">-</span>
                    <span class="text-base font-mono font-bold" :class="game.away_score > game.home_score ? 'text-win' : 'text-text'">{{ game.away_score }}</span>
                  </div>
                  <span class="text-sm font-bold text-text w-10">{{ game.away_abbr }}</span>
                </div>

                <div class="w-20 text-right">
                  <span class="text-[11px] font-mono" :class="game.score_diff > 0 ? 'text-win' : 'text-loss'">
                    {{ game.score_diff > 0 ? '+' : '' }}{{ game.score_diff }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else class="py-6 text-center text-text-muted text-sm">暂无近期比赛数据</div>
          </div>
        </div>

        <!-- 右侧边栏 (1/3) -->
        <div class="w-[320px] flex-shrink-0 space-y-6">
          <!-- 模型性能概览 -->
          <div class="card animate-fade-up" style="animation-delay: 0.15s">
            <div class="section-header">
              <h3 class="heading-3 text-text">模型性能</h3>
            </div>

            <div class="flex items-baseline gap-1 mb-4">
              <span class="text-4xl font-black text-text">67.6</span>
              <span class="text-lg font-bold text-primary">%</span>
            </div>
            <div class="text-xs text-text-secondary mb-4">验证集胜率准确度</div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="data-label">模型</span>
                <span class="text-xs font-medium text-text">Ridge Regression v2</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="data-label">特征维度</span>
                <span class="text-xs font-medium text-text">30</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="data-label">训练数据</span>
                <span class="text-xs font-medium text-text">4 赛季 / 5500+ 场</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="data-label">数据源</span>
                <span class="text-xs font-medium text-text">ESPN Boxscore</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="data-label">高阶指标</span>
                <div class="flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-win"></span>
                  <span class="text-xs font-medium text-text">真实计算</span>
                </div>
              </div>
            </div>

            <div class="mt-5 pt-4 border-t border-border">
              <router-link to="/model" class="btn btn-ghost w-full justify-center text-xs">
                查看详细面板
              </router-link>
            </div>
          </div>

          <!-- 东部排名 -->
          <div class="card animate-fade-up" style="animation-delay: 0.2s">
            <div class="flex items-center justify-between mb-4">
              <div class="section-header mb-0">
                <h3 class="heading-3 text-text">东部排名</h3>
              </div>
              <router-link to="/teams" class="text-xs text-primary hover:text-primary-light transition-colors">
                全部 &rarr;
              </router-link>
            </div>

            <div class="space-y-1">
              <div
                v-for="(team, i) in eastStandings"
                :key="team.abbr"
                class="flex items-center gap-2.5 py-1.5 px-2 rounded-md transition-colors hover:bg-white/[0.03] cursor-pointer"
              >
                <span class="w-5 text-[11px] font-mono text-text-muted text-right">{{ i + 1 }}</span>
                <span class="text-[13px] font-medium text-text flex-1">{{ team.abbr }}</span>
                <span class="text-[11px] font-mono text-text-secondary">{{ team.wins }}-{{ team.losses }}</span>
                <span class="text-[11px] font-mono text-text-muted w-10 text-right">
                  {{ team.pct }}
                </span>
              </div>
            </div>
          </div>

          <!-- 西部排名 -->
          <div class="card animate-fade-up" style="animation-delay: 0.25s">
            <div class="flex items-center justify-between mb-4">
              <div class="section-header mb-0">
                <h3 class="heading-3 text-text">西部排名</h3>
              </div>
              <router-link to="/teams" class="text-xs text-primary hover:text-primary-light transition-colors">
                全部 &rarr;
              </router-link>
            </div>

            <div class="space-y-1">
              <div
                v-for="(team, i) in westStandings"
                :key="team.abbr"
                class="flex items-center gap-2.5 py-1.5 px-2 rounded-md transition-colors hover:bg-white/[0.03] cursor-pointer"
              >
                <span class="w-5 text-[11px] font-mono text-text-muted text-right">{{ i + 1 }}</span>
                <span class="text-[13px] font-medium text-text flex-1">{{ team.abbr }}</span>
                <span class="text-[11px] font-mono text-text-secondary">{{ team.wins }}-{{ team.losses }}</span>
                <span class="text-[11px] font-mono text-text-muted w-10 text-right">
                  {{ team.pct }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import HeroCarousel from '../components/carousel/HeroCarousel.vue'
import PlayerMatchup from '../components/analysis/PlayerMatchup.vue'
import TeamAnalysis from '../components/analysis/TeamAnalysis.vue'
import { getStandings, getRecentGames } from '../api/data'

const eastStandings = ref([])
const westStandings = ref([])
const recentGames = ref([])

onMounted(async () => {
  try {
    const [standingsData, gamesData] = await Promise.all([
      getStandings(),
      getRecentGames(),
    ])

    eastStandings.value = (standingsData.east || []).slice(0, 8).map(t => ({
      abbr: t.abbreviation,
      wins: t.wins,
      losses: t.losses,
      pct: t.win_percentage?.toFixed(3) || '.000',
    }))
    westStandings.value = (standingsData.west || []).slice(0, 8).map(t => ({
      abbr: t.abbreviation,
      wins: t.wins,
      losses: t.losses,
      pct: t.win_percentage?.toFixed(3) || '.000',
    }))
    recentGames.value = (gamesData || []).slice(0, 5)
  } catch (e) {
    console.error('Failed to load home data:', e)
  }
})
</script>
