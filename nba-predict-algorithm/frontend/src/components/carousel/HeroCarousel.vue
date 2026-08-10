<template>
  <div
    class="relative w-full overflow-hidden"
    @mousemove="onMouseMove"
    @mouseleave="onMouseLeave"
  >
    <div
      class="absolute inset-0 transition-all duration-700 opacity-30 pointer-events-none"
      :style="{ background: activeGradient }"
    ></div>

    <swiper
      :modules="[Autoplay, EffectCoverflow, Pagination]"
      :slides-per-view="1.1"
      :centered-slides="true"
      :space-between="20"
      :autoplay="{ delay: 6000, disableOnInteraction: false, pauseOnMouseEnter: true }"
      :effect="'coverflow'"
      :coverflow-effect="{ rotate: 6, stretch: 0, depth: 160, modifier: 1.2, slideShadows: false }"
      :pagination="{ clickable: true }"
      :breakpoints="{ 768: { slidesPerView: 1.4 }, 1024: { slidesPerView: 1.6 } }"
      @swiper="onSwiper"
      @slide-change="onSlideChange"
      class="w-full max-w-[1100px] mx-auto"
    >
      <swiper-slide v-for="(slide, i) in slides" :key="i">
        <div
          class="slide-card card cursor-pointer select-none"
          :class="{ 'ring-1 ring-primary/30': activeIndex === i }"
          :style="cardTransform(i)"
        >
          <!-- 比赛 slide -->
          <div v-if="slide.type === 'game'" class="flex flex-col items-center gap-5">
            <span class="caption">{{ slide.dateLabel }}</span>
            <div class="flex items-center gap-10">
              <div class="text-center">
                <div class="w-14 h-14 rounded-xl bg-primary/15 flex items-center justify-center text-xl font-black text-primary">
                  {{ slide.homeAbbr }}
                </div>
                <div class="text-xs text-text-muted mt-1">{{ slide.homeName }}</div>
              </div>
              <div class="text-center">
                <div v-if="slide.hasScore" class="data-value text-text">{{ slide.homeScore }} - {{ slide.awayScore }}</div>
                <div v-else class="text-2xl font-bold text-text-muted">VS</div>
                <div class="caption mt-1">{{ slide.hasScore ? '比分' : '未开始' }}</div>
              </div>
              <div class="text-center">
                <div class="w-14 h-14 rounded-xl bg-loss/15 flex items-center justify-center text-xl font-black text-loss">
                  {{ slide.awayAbbr }}
                </div>
                <div class="text-xs text-text-muted mt-1">{{ slide.awayName }}</div>
              </div>
            </div>
            <!-- 预测胜率 -->
            <div v-if="slide.predHomePct" class="flex items-center gap-3 w-full max-w-[240px]">
              <span class="text-[11px] text-text-muted w-8">{{ slide.homeAbbr }}</span>
              <div class="progress-bar flex-1">
                <div class="fill bg-primary" :style="{ width: slide.predHomePct + '%' }"></div>
              </div>
              <span class="text-xs font-mono text-text-secondary">{{ slide.predHomePct }}%</span>
            </div>
            <div class="tag tag-info">{{ slide.tag }}</div>
          </div>

          <!-- 分析能力 -->
          <div v-else-if="slide.type === 'analysis'" class="flex flex-col items-center gap-5">
            <span class="caption">分析能力</span>
            <div class="grid grid-cols-2 gap-4 w-full max-w-[360px]">
              <div v-for="cap in slide.capabilities" :key="cap.label" class="card-flat text-center py-4">
                <div class="text-xl font-bold text-text">{{ cap.value }}</div>
                <div class="data-label mt-1">{{ cap.label }}</div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-win"></span>
              <span class="text-xs text-text-secondary">基于真实 boxscore 数据计算</span>
            </div>
          </div>
        </div>
      </swiper-slide>

      <!-- 加载中 -->
      <swiper-slide v-if="loading">
        <div class="slide-card card flex items-center justify-center">
          <div class="text-text-muted">加载赛程...</div>
        </div>
      </swiper-slide>
    </swiper>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Swiper, SwiperSlide } from 'swiper/vue'
import { Autoplay, EffectCoverflow, Pagination } from 'swiper/modules'
import { getTodayGames, getStandings } from '../../api/data'
import { predictTeam } from '../../api/algorithm'
import 'swiper/css'
import 'swiper/css/effect-coverflow'
import 'swiper/css/pagination'

const activeIndex = ref(0)
const mouseX = ref(0.5)
const mouseY = ref(0.5)
const isHovering = ref(false)
const loading = ref(true)
let swiperInstance = null

const slides = ref([])

const activeGradient = computed(() => slides.value[activeIndex.value]?.gradient || '')

onMounted(async () => {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const [games, standings] = await Promise.all([
      getTodayGames(2),
      getStandings(),
    ])

    // 构建 abbr -> team_id 映射
    const allTeams = [...(standings.east || []), ...(standings.west || [])]
    const abbrToId = {}
    for (const t of allTeams) {
      abbrToId[t.abbreviation] = t.team_id
    }

    const gameSlides = []
    for (const g of (games || []).slice(0, 8)) {
      const homeId = abbrToId[g.home_abbr]
      const awayId = abbrToId[g.away_abbr]
      let predHomePct = null
      let predScore = null

      // 获取预测
      if (homeId && awayId) {
        try {
          const pred = await predictTeam({
            home_team_id: homeId,
            away_team_id: awayId,
          })
          predScore = `${pred.predict_home_score || 0} - ${pred.predict_away_score || 0}`
          predHomePct = pred.coefficients?.home_win_prob
            ? Math.round(pred.coefficients.home_win_prob * 100)
            : null
        } catch {
          // 预测失败不影响展示
        }
      }

      const hasScore = g.home_score > 0 || g.away_score > 0
      const isToday = g.game_date === today
      const dateLabel = isToday ? '今日' : '明日'

      gameSlides.push({
        type: 'game',
        dateLabel,
        homeAbbr: g.home_abbr,
        homeName: g.home_team,
        awayAbbr: g.away_abbr,
        awayName: g.away_team,
        homeScore: g.home_score,
        awayScore: g.away_score,
        hasScore,
        predHomePct,
        tag: predScore ? `预测 ${predScore}` : '系统预测',
        gradient: 'radial-gradient(ellipse at 40% 50%, rgba(37,99,235,0.15) 0%, transparent 60%)',
      })
    }

    slides.value = [
      ...gameSlides,
      {
        type: 'analysis',
        capabilities: [
          { label: '对位分析', value: '攻防对比' },
          { label: '球员聚类', value: '7 类角色' },
          { label: '球队分类', value: '风格识别' },
          { label: '系列赛', value: '之星评选' },
        ],
        gradient: 'radial-gradient(ellipse at 60% 50%, rgba(16,185,129,0.12) 0%, transparent 60%)',
      },
    ]
  } catch (e) {
    console.error('Failed to load carousel data:', e)
    slides.value = []
  } finally {
    loading.value = false
  }
})

function onSwiper(sw) { swiperInstance = sw }
function onSlideChange() { if (swiperInstance) activeIndex.value = swiperInstance.activeIndex }
function onMouseMove(e) {
  const rect = e.currentTarget.getBoundingClientRect()
  mouseX.value = (e.clientX - rect.left) / rect.width
  mouseY.value = (e.clientY - rect.top) / rect.height
  isHovering.value = true
}
function onMouseLeave() { isHovering.value = false; mouseX.value = 0.5; mouseY.value = 0.5 }
function cardTransform(index) {
  if (index !== activeIndex.value || !isHovering.value) return {}
  const rX = (mouseY.value - 0.5) * -6
  const rY = (mouseX.value - 0.5) * 6
  return { transform: `perspective(800px) rotateX(${rX}deg) rotateY(${rY}deg) scale(1.01)`, transition: 'transform 0.1s ease-out' }
}
</script>

<style scoped>
.slide-card {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform-style: preserve-3d;
  will-change: transform;
}
</style>
