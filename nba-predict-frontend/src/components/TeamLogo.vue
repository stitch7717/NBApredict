<template>
  <img
    v-if="logoSrc && !loadFailed"
    class="team-logo"
    :src="logoSrc"
    :alt="`${displayAbbr} 队标`"
    :style="sizeStyle"
    @error="handleError"
  />
  <span v-else class="team-logo-fallback" :style="fallbackStyle">{{ displayAbbr }}</span>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  /** 球队缩写，如 'LAL' */
  abbr: { type: String, default: '' },
  /** 显示尺寸（宽高相同），默认 32px */
  size: { type: Number, default: 32 },
})

// 一次性打包所有本地队标：'../assets/team-logos/ATL.svg' -> url
const logoModules = import.meta.glob('../assets/team-logos/*.svg', {
  eager: true,
  import: 'default',
})

const loadFailed = ref(false)

const displayAbbr = computed(() => (props.abbr || 'NBA').toUpperCase())

const logoSrc = computed(() => {
  if (!props.abbr) return ''
  return logoModules[`../assets/team-logos/${props.abbr.toUpperCase()}.svg`] || ''
})

// 缩写变化时重置错误状态，避免复用实例残留
watch(
  () => props.abbr,
  () => {
    loadFailed.value = false
  },
)

const handleError = () => {
  loadFailed.value = true
}

const sizeStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))

const fallbackStyle = computed(() => ({
  ...sizeStyle.value,
  fontSize: `${Math.round(props.size * 0.34)}px`,
}))
</script>

<style lang="scss" scoped>
.team-logo {
  display: inline-block;
  object-fit: contain;
  flex-shrink: 0;
  vertical-align: middle;
}

.team-logo-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: $radius-full;
  background: linear-gradient(135deg, $color-nba-blue, $color-nba-red);
  color: #fff;
  font-weight: 700;
  letter-spacing: 0.5px;
  vertical-align: middle;
}
</style>
