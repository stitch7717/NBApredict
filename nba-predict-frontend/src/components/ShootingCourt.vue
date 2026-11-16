<template>
  <div class="shooting-court">
    <svg viewBox="0 0 500 480" class="court-svg">
      <!-- ============ 分区填充（沿真实三分弧线贴合，弧心=篮筐 (250,452) r=228） ============ -->
      <!-- 三分左翼（弧线外） -->
      <path
        d="M 20 452 L 39 452 A 228 228 0 0 1 100 280 L 20 280 Z"
        :fill="colorFor(zonePct('3p'))" class="zone"
        @mousemove="hoverZone($event, '三分（左翼）', '3p')"
      />
      <!-- 三分弧顶外 -->
      <path
        d="M 100 280 A 228 228 0 0 1 400 280 L 400 10 L 100 10 Z"
        :fill="colorFor(zonePct('3p'))" class="zone"
        @mousemove="hoverZone($event, '三分（弧顶外）', '3p')"
      />
      <!-- 三分右翼（弧线外） -->
      <path
        d="M 400 280 A 228 228 0 0 1 461 452 L 480 452 L 480 280 Z"
        :fill="colorFor(zonePct('3p'))" class="zone"
        @mousemove="hoverZone($event, '三分（右翼）', '3p')"
      />
      <!-- 长两分（弧线内、油漆区上方）：16ft-3P -->
      <path
        d="M 173 270 L 327 270 L 327 228 A 228 228 0 0 0 173 228 Z"
        :fill="colorFor(zonePct('16_3p'))" class="zone"
        @mousemove="hoverZone($event, '长两分 (16ft-3P)', '16_3p')"
      />
      <!-- 中距离左（弧线内）：3-10ft -->
      <path
        d="M 20 452 L 173 452 L 173 270 L 173 228 A 228 228 0 0 0 39 366 L 39 452 Z"
        :fill="colorFor(zonePct('3_10'))" class="zone"
        @mousemove="hoverZone($event, '中距离 (3-10ft)', '3_10')"
      />
      <!-- 中距离右（弧线内）：10-16ft -->
      <path
        d="M 480 452 L 327 452 L 327 270 L 327 228 A 228 228 0 0 0 461 366 L 461 452 Z"
        :fill="colorFor(zonePct('10_16'))" class="zone"
        @mousemove="hoverZone($event, '中距离 (10-16ft)', '10_16')"
      />
      <!-- 油漆区：篮下 at_rim -->
      <rect
        x="173" y="270" width="154" height="182"
        :fill="colorFor(zonePct('at_rim'))" class="zone"
        @mousemove="hoverZone($event, '篮下 (0-3ft)', 'at_rim')"
      />
      <!-- 罚球圈：罚球命中率（近似，无逐区数据） -->
      <circle
        cx="250" cy="270" r="58"
        :fill="colorFor(ftPct)" class="zone"
        @mousemove="hoverZone($event, '罚球', null, ftPct)"
      />
      <!-- 中圈：真实命中率（近似） -->
      <circle
        cx="250" cy="40" r="58"
        :fill="colorFor(tsPct)" class="zone"
        @mousemove="hoverZone($event, '真实命中率', null, tsPct)"
      />

      <!-- ============ 球场线条 ============ -->
      <g stroke="rgba(255,255,255,0.45)" stroke-width="2" fill="none">
        <rect x="10" y="10" width="480" height="460" rx="8" />
        <path d="M 39 452 A 228 228 0 0 1 461 452" />
        <line x1="20" y1="452" x2="39" y2="452" />
        <line x1="461" y1="452" x2="480" y2="452" />
        <rect x="173" y="270" width="154" height="182" />
        <circle cx="250" cy="270" r="58" />
        <path d="M 212 452 A 38 38 0 0 1 288 452" />
        <circle cx="250" cy="40" r="58" />
        <line x1="236" y1="458" x2="264" y2="458" stroke-width="5" />
        <circle cx="250" cy="452" r="7" />
      </g>

      <!-- ============ 数值标签 ============ -->
      <g font-size="15" font-weight="700">
        <text x="250" y="395" text-anchor="middle" :fill="textColor(zonePct('at_rim'))">{{ fmt(zonePct('at_rim')) }}</text>
        <text x="96" y="420" text-anchor="middle" :fill="textColor(zonePct('3_10'))">{{ fmt(zonePct('3_10')) }}</text>
        <text x="404" y="420" text-anchor="middle" :fill="textColor(zonePct('10_16'))">{{ fmt(zonePct('10_16')) }}</text>
        <text x="250" y="253" text-anchor="middle" font-size="13" :fill="textColor(zonePct('16_3p'))">{{ fmt(zonePct('16_3p')) }}</text>
        <text x="60" y="330" text-anchor="middle" :fill="textColor(zonePct('3p'))">{{ fmt(zonePct('3p')) }}</text>
        <text x="440" y="330" text-anchor="middle" :fill="textColor(zonePct('3p'))">{{ fmt(zonePct('3p')) }}</text>
        <text x="250" y="150" text-anchor="middle" font-size="17" :fill="textColor(zonePct('3p'))">{{ fmt(zonePct('3p')) }}</text>
        <text x="250" y="275" text-anchor="middle" font-size="14" :fill="textColor(ftPct)">{{ fmt(ftPct) }}</text>
        <text x="250" y="45" text-anchor="middle" font-size="14" :fill="textColor(tsPct)">{{ fmt(tsPct) }}</text>
      </g>
    </svg>

    <!-- 悬浮提示 -->
    <div v-if="hover" class="court-tooltip" :style="{ left: hover.x + 'px', top: hover.y + 'px' }">
      <span class="tip-name">{{ hover.name }}</span>
      <span class="tip-value">{{ fmt(hover.value) }}</span>
      <span v-if="hover.attempts" class="tip-attempts">{{ hover.attempts }} 次出手</span>
    </div>

    <!-- 图例：低 → 高 -->
    <div class="court-legend">
      <span class="legend-label">低</span>
      <span
        v-for="c in RAMP"
        :key="c"
        class="legend-cell"
        :style="{ background: c }"
      ></span>
      <span class="legend-label">高</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  /** 真实逐区数据：[{ zone, fg_made, fg_attempted, fg_percentage }]，缺省时用近似值 */
  zones: { type: Array, default: () => [] },
  /** 整体命中率（小数，近似回退用） */
  fgPct: { type: Number, default: 0 },
  /** 三分命中率（小数，近似回退用） */
  threePct: { type: Number, default: 0 },
  /** 罚球命中率（小数，近似） */
  ftPct: { type: Number, default: 0 },
  /** 真实命中率（小数，近似） */
  tsPct: { type: Number, default: 0 },
})

// 单色阶（浅蓝 → 深蓝），按命中率分 5 档
const RAMP = ['#B9C9E6', '#8BA3CC', '#5D7DB3', '#2F569A', '#0F2047']

const hover = ref(null)

const zoneMap = computed(() => {
  const map = {}
  for (const z of props.zones) {
    map[z.zone] = z
  }
  return map
})

// 有真实数据用真实数据；否则回退近似（两分区=整体命中率，三分区=三分命中率）
const zonePct = (key) => {
  const z = zoneMap.value[key]
  if (z && z.fg_attempted > 0) return z.fg_percentage
  if (key === '3p') return props.threePct
  return props.fgPct
}

const colorFor = (pct) => {
  const p = Math.min(Math.max(Number(pct) || 0, 0), 1)
  const idx = Math.min(Math.floor(p * 5), 4)
  return RAMP[idx]
}

const textColor = (pct) => ((Number(pct) || 0) >= 0.5 ? '#FFFFFF' : '#1F2329')

const fmt = (pct) => ((Number(pct) || 0) * 100).toFixed(1) + '%'

function hoverZone(e, name, zoneKey, fallbackPct) {
  const rect = e.currentTarget.closest('svg').getBoundingClientRect()
  const z = zoneKey ? zoneMap.value[zoneKey] : null
  const value = z && z.fg_attempted > 0 ? z.fg_percentage : (fallbackPct ?? zonePct(zoneKey))
  hover.value = {
    x: e.clientX - rect.left + 12,
    y: e.clientY - rect.top - 40,
    name,
    value,
    attempts: z ? `${z.fg_made}/${z.fg_attempted}` : null,
  }
}

function leaveZone() {
  hover.value = null
}
</script>

<style lang="scss" scoped>
.shooting-court {
  position: relative;
  width: 100%;
}

.court-svg {
  width: 100%;
  height: auto;
  display: block;
  background: $bg-elevated;
  border-radius: $radius-md;
}

.zone {
  cursor: pointer;
  transition: opacity $transition-fast;

  &:hover {
    opacity: 0.75;
  }
}

.court-tooltip {
  position: absolute;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: rgba(20, 20, 22, 0.92);
  border: 1px solid $border-dark;
  border-radius: $radius-sm;
  z-index: 10;
  white-space: nowrap;

  .tip-name {
    font-size: 12px;
    color: $text-secondary;
  }

  .tip-value {
    font-size: 14px;
    font-weight: 700;
    color: $text-primary;
  }

  .tip-attempts {
    font-size: 11px;
    color: $text-muted;
  }
}

.court-legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 8px;

  .legend-label {
    font-size: 11px;
    color: $text-muted;
    margin: 0 4px;
  }

  .legend-cell {
    width: 28px;
    height: 10px;
    border-radius: 2px;
  }
}
</style>
