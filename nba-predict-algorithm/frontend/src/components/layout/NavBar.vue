<template>
  <nav class="fixed top-0 left-0 right-0 z-50 glass">
    <div class="max-w-[1200px] mx-auto px-6 h-14 flex items-center justify-between">
      <!-- Logo -->
      <router-link to="/" class="flex items-center gap-2.5 group">
        <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10"/>
            <path d="M12 2c3 2.5 5 6 5 10s-2 7.5-5 10"/>
            <path d="M2 12h20"/>
          </svg>
        </div>
        <div>
          <div class="text-sm font-bold text-text leading-none">NBA Analysis</div>
          <div class="text-[10px] text-text-muted font-medium">RIDGE v2</div>
        </div>
      </router-link>

      <!-- 导航链接 -->
      <div class="flex items-center gap-1">
        <router-link
          v-for="link in links"
          :key="link.path"
          :to="link.path"
          class="relative px-3 py-1.5 rounded-lg text-[13px] font-medium transition-all duration-200"
          :class="isActive(link.path)
            ? 'text-white bg-white/[0.08]'
            : 'text-text-secondary hover:text-text hover:bg-white/[0.04]'"
        >
          {{ link.label }}
          <span
            v-if="isActive(link.path)"
            class="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-primary rounded-full"
          ></span>
        </router-link>
      </div>

      <!-- 右侧状态 -->
      <div class="flex items-center gap-3">
        <div class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface border border-border text-[11px] text-text-muted">
          <span class="w-1.5 h-1.5 rounded-full bg-win animate-pulse"></span>
          MODEL ACTIVE
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const links = [
  { path: '/', label: '分析总览' },
  { path: '/predict', label: '预测' },
  { path: '/teams', label: '球队' },
  { path: '/players', label: '球员' },
  { path: '/model', label: '模型' },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>
