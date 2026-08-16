<template>
  <div class="entry-page" @mousemove="onMouseMove">
    <!-- 星空粒子画布 -->
    <canvas ref="starCanvas" class="star-canvas"></canvas>

    <!-- 光晕 -->
    <div class="glow glow--left" :style="glowStyle.left"></div>
    <div class="glow glow--right" :style="glowStyle.right"></div>

    <!-- 中央标题 -->
    <div class="entry-center">
      <div class="entry-badge">NBA PREDICTION SYSTEM</div>
      <h1 class="entry-title">
        <span class="title-line">篮球</span>
        <span class="title-line title-line--accent">预测之门</span>
      </h1>
      <p class="entry-sub">选择你的身份，进入数据宇宙</p>

      <!-- 两个身份门 -->
      <div class="portal-row">
        <!-- 普通用户 -->
        <div
          class="portal portal--guest"
          :style="tiltStyle.guest"
          @mouseenter="hoverPortal('guest')"
          @mouseleave="unhoverPortal"
          @click="enter('guest')"
        >
          <div class="portal-ring"></div>
          <div class="portal-icon">
            <el-icon :size="46"><User /></el-icon>
          </div>
          <div class="portal-name">普通用户</div>
          <div class="portal-desc">浏览赛程 · 球员数据 · 球队数据 · 比赛预测</div>
          <div class="portal-hint">点击进入 →</div>
        </div>

        <div class="portal-divider">
          <span class="divider-line"></span>
          <span class="divider-ball">🏀</span>
          <span class="divider-line"></span>
        </div>

        <!-- 管理员 -->
        <div
          class="portal portal--admin"
          :style="tiltStyle.admin"
          @mouseenter="hoverPortal('admin')"
          @mouseleave="unhoverPortal"
          @click="enter('admin')"
        >
          <div class="portal-ring"></div>
          <div class="portal-icon">
            <el-icon :size="46"><Setting /></el-icon>
          </div>
          <div class="portal-name">管理员</div>
          <div class="portal-desc">全部功能 · 数据看板 · 赔率管理 · 系统设置</div>
          <div class="portal-hint">点击进入 →</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { User, Setting } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const starCanvas = ref(null)
const glowStyle = reactive({
  left: { transform: 'translate(0, 0)', opacity: 0.5 },
  right: { transform: 'translate(0, 0)', opacity: 0.5 },
})
const tiltStyle = reactive({
  guest: {},
  admin: {},
})

// 鼠标位置（-1 到 1）
const mouse = reactive({ x: 0, y: 0 })

let stars = []
let animationId = null

const onMouseMove = (e) => {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1
  mouse.y = (e.clientY / window.innerHeight) * 2 - 1

  // 光晕跟随鼠标
  const mx = e.clientX - window.innerWidth / 2
  const my = e.clientY - window.innerHeight / 2
  glowStyle.left = {
    transform: `translate(${mx * 0.08}px, ${my * 0.08}px)`,
    opacity: 0.6,
  }
  glowStyle.right = {
    transform: `translate(${mx * -0.06}px, ${my * -0.06}px)`,
    opacity: 0.5,
  }
}

const hoverPortal = (side) => {
  if (side === 'guest') tiltStyle.guest = { transform: 'perspective(800px) rotateY(-8deg) scale(1.05)' }
  else tiltStyle.admin = { transform: 'perspective(800px) rotateY(8deg) scale(1.05)' }
}

const unhoverPortal = () => {
  tiltStyle.guest = {}
  tiltStyle.admin = {}
}

const enter = (role) => {
  userStore.enterAs(role)
  router.push('/')
}

// 星空粒子
const initStars = () => {
  const canvas = starCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  stars = Array.from({ length: 180 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 1.6 + 0.4,
    vx: (Math.random() - 0.5) * 0.25,
    vy: (Math.random() - 0.5) * 0.25,
    twinkle: Math.random() * Math.PI * 2,
  }))

  const draw = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    for (const s of stars) {
      s.x += s.vx + mouse.x * 0.3
      s.y += s.vy + mouse.y * 0.3
      // 环绕边界
      if (s.x < -5) s.x = canvas.width + 5
      if (s.x > canvas.width + 5) s.x = -5
      if (s.y < -5) s.y = canvas.height + 5
      if (s.y > canvas.height + 5) s.y = -5

      s.twinkle += 0.03
      const alpha = 0.3 + Math.abs(Math.sin(s.twinkle)) * 0.6
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(160, 200, 255, ${alpha})`
      ctx.fill()
    }
    animationId = requestAnimationFrame(draw)
  }
  draw()
}

const onResize = () => {
  const canvas = starCanvas.value
  if (canvas) {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
}

onMounted(() => {
  initStars()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
})
</script>

<style lang="scss" scoped>
.entry-page {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 20%, rgba(29, 66, 138, 0.35) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 75%, rgba(200, 16, 46, 0.22) 0%, transparent 55%),
    radial-gradient(ellipse at 50% 50%, #10182e 0%, #05070f 100%);
  overflow: hidden;
  cursor: default;
}

.star-canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.glow {
  position: absolute;
  width: 45vmax;
  height: 45vmax;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  transition: transform 0.4s ease-out, opacity 0.4s ease-out;
}

.glow--left {
  top: -10%;
  left: -8%;
  background: rgba(29, 66, 138, 0.5);
}

.glow--right {
  bottom: -12%;
  right: -8%;
  background: rgba(200, 16, 46, 0.35);
}

.entry-center {
  position: relative;
  z-index: 2;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
}

.entry-badge {
  font-size: 13px;
  letter-spacing: 6px;
  color: rgba(140, 180, 255, 0.75);
  text-transform: uppercase;
  animation: badge-in 1s ease-out both;
}

@keyframes badge-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.entry-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.1;
  margin: 4px 0 8px;
}

.title-line {
  font-size: clamp(44px, 8vw, 92px);
  font-weight: 800;
  background: linear-gradient(180deg, #fff 30%, #8fa8d8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: 0 0 60px rgba(120, 160, 255, 0.4);
  animation: title-in 0.9s ease-out both;
}

.title-line--accent {
  background: linear-gradient(180deg, #ffb1a8 10%, #c8102e 60%, #6b0818 100%);
  -webkit-background-clip: text;
  background-clip: text;
  text-shadow: 0 0 60px rgba(200, 16, 46, 0.45);
  animation-delay: 0.15s;
}

@keyframes title-in {
  from { opacity: 0; transform: translateY(30px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.entry-sub {
  color: rgba(180, 200, 230, 0.6);
  font-size: 15px;
  letter-spacing: 2px;
  margin-bottom: 34px;
  animation: badge-in 1s ease-out 0.3s both;
}

.portal-row {
  display: flex;
  align-items: stretch;
  gap: clamp(16px, 4vw, 60px);
}

.portal {
  position: relative;
  width: clamp(240px, 26vw, 320px);
  padding: 42px 28px;
  border-radius: 22px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.35s;
  animation: portal-in 0.8s ease-out both;
  backdrop-filter: blur(8px);

  &:nth-child(1) { animation-delay: 0.35s; }
  &:nth-child(3) { animation-delay: 0.5s; }
}

@keyframes portal-in {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}

.portal--guest {
  background: linear-gradient(160deg, rgba(29, 66, 138, 0.28), rgba(10, 18, 40, 0.75));
  border: 1px solid rgba(80, 130, 220, 0.35);
  box-shadow: 0 0 40px rgba(29, 66, 138, 0.25), inset 0 0 30px rgba(29, 66, 138, 0.12);

  &:hover {
    box-shadow: 0 0 70px rgba(50, 110, 220, 0.5), inset 0 0 40px rgba(50, 110, 220, 0.2);
    border-color: rgba(120, 170, 255, 0.7);
  }
}

.portal--admin {
  background: linear-gradient(160deg, rgba(200, 16, 46, 0.25), rgba(40, 8, 14, 0.75));
  border: 1px solid rgba(220, 80, 100, 0.35);
  box-shadow: 0 0 40px rgba(200, 16, 46, 0.25), inset 0 0 30px rgba(200, 16, 46, 0.12);

  &:hover {
    box-shadow: 0 0 70px rgba(230, 60, 90, 0.5), inset 0 0 40px rgba(230, 60, 90, 0.2);
    border-color: rgba(255, 130, 150, 0.7);
  }
}

.portal-ring {
  position: absolute;
  inset: -2px;
  border-radius: 23px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.portal:hover .portal-ring {
  opacity: 1;
}

.portal--guest .portal-ring {
  box-shadow: 0 0 0 2px rgba(80, 140, 255, 0.4);
  animation: ring-pulse 1.6s ease-in-out infinite;
}

.portal--admin .portal-ring {
  box-shadow: 0 0 0 2px rgba(255, 100, 120, 0.4);
  animation: ring-pulse 1.6s ease-in-out infinite;
}

@keyframes ring-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(120, 170, 255, 0.35); }
  50% { box-shadow: 0 0 0 6px rgba(120, 170, 255, 0.12); }
}

.portal--admin .portal-ring {
  @keyframes ring-pulse-admin {
    0%, 100% { box-shadow: 0 0 0 2px rgba(255, 120, 140, 0.35); }
    50% { box-shadow: 0 0 0 6px rgba(255, 120, 140, 0.12); }
  }
  animation-name: ring-pulse-admin;
}

.portal-icon {
  margin-bottom: 16px;
  color: #fff;
  animation: icon-float 3s ease-in-out infinite;
}

.portal--guest .portal-icon { color: #7fa8ff; }
.portal--admin .portal-icon { color: #ff8598; }

@keyframes icon-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.portal-name {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 10px;
  letter-spacing: 2px;
}

.portal-desc {
  font-size: 13px;
  color: rgba(190, 205, 230, 0.65);
  line-height: 1.7;
  margin-bottom: 18px;
}

.portal-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
  transition: color 0.3s, transform 0.3s;
}

.portal:hover .portal-hint {
  color: #fff;
  transform: translateX(4px);
}

.portal-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.divider-line {
  width: 1px;
  height: 60px;
  background: linear-gradient(180deg, transparent, rgba(150, 170, 220, 0.4), transparent);
}

.divider-ball {
  font-size: 22px;
  filter: drop-shadow(0 0 12px rgba(255, 180, 100, 0.6));
  animation: ball-spin 4s linear infinite;
}

@keyframes ball-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 720px) {
  .portal-row { flex-direction: column; }
  .portal-divider { flex-direction: row; }
  .divider-line { width: 40px; height: 1px; background: linear-gradient(90deg, transparent, rgba(150, 170, 220, 0.4), transparent); }
}
</style>
