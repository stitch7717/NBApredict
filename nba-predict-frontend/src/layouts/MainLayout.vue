<template>
  <div class="app-layout">
    <!-- 左侧固定侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-logo" @click="router.push('/')">
        <div class="logo-icon">
          <svg viewBox="0 0 32 32" width="32" height="32">
            <circle cx="16" cy="16" r="14" fill="none" stroke="#1d428a" stroke-width="2" />
            <path d="M16 2 C16 2 8 10 8 18 C8 22 11.5 26 16 26 C20.5 26 24 22 24 18 C24 10 16 2 16 2Z" fill="none" stroke="#c8102e" stroke-width="1.5" />
            <line x1="4" y1="16" x2="28" y2="16" stroke="#1d428a" stroke-width="1" />
          </svg>
        </div>
        <div class="logo-text">
          <span class="logo-title">NBA Predict</span>
          <span class="logo-sub">数据分析平台</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-version">v1.0.0</div>
      </div>
    </aside>

    <!-- 右侧主内容 -->
    <div class="main-wrapper">
      <!-- 顶部导航栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <h1 class="topbar-title">{{ currentTitle }}</h1>
        </div>

        <div class="topbar-right">
          <div class="topbar-actions">
            <button class="action-btn" title="通知">
              <el-icon><Bell /></el-icon>
              <span class="notification-dot"></span>
            </button>
            <button class="action-btn" title="全屏" @click="toggleFullscreen">
              <el-icon><FullScreen /></el-icon>
            </button>
          </div>

          <div class="topbar-user">
            <div class="user-avatar">
              <el-icon><UserFilled /></el-icon>
            </div>
            <div class="user-info" @click="switchRole" title="点击切换身份">
              <span class="user-name">{{ userStore.isAdmin() ? 'Admin' : '访客' }}</span>
              <span class="user-role">{{ userStore.isAdmin() ? '分析师' : '普通用户' }}</span>
            </div>
          </div>
        </div>
      </header>

      <!-- 主内容区 -->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  HomeFilled, User, Trophy, TrendCharts, Setting, Bell, FullScreen,
  DataAnalysis, Money, Document
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 基础菜单（所有角色可见）
const baseMenuItems = [
  { path: '/', label: '首页赛程', icon: HomeFilled },
  { path: '/predict', label: '比赛预测', icon: TrendCharts },
  { path: '/players', label: '球员数据', icon: User },
  { path: '/teams', label: '球队数据', icon: Trophy },
]

// 管理员专属菜单
const adminMenuItems = [
  { path: '/dashboard', label: '数据看板', icon: DataAnalysis },
  { path: '/odds', label: '赔率管理', icon: Money },
  { path: '/record', label: '预测记录', icon: Document },
  { path: '/settings', label: '系统设置', icon: Setting },
]

const menuItems = computed(() =>
  userStore.isAdmin() ? [...baseMenuItems, ...adminMenuItems] : baseMenuItems
)

const switchRole = () => {
  userStore.exit()
  router.push('/entry')
}

const currentTitle = computed(() => {
  const item = menuItems.value.find(m => isActive(m.path))
  return item?.label || 'NBA预测系统'
})

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: $bg-base;
}

// ============================================
// 侧边栏
// ============================================
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: $sidebar-width;
  background: $sidebar-bg;
  display: flex;
  flex-direction: column;
  z-index: 100;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.15);
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 24px;
  cursor: pointer;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);

  .logo-icon {
    flex-shrink: 0;
  }

  .logo-text {
    display: flex;
    flex-direction: column;

    .logo-title {
      font-size: 17px;
      font-weight: 700;
      color: $color-nba-blue;
      line-height: 1.2;
      letter-spacing: -0.3px;
    }

    .logo-sub {
      font-size: 11px;
      color: $sidebar-text-muted;
      margin-top: 2px;
    }
  }
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: $radius-md;
  color: $sidebar-text;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all $transition-fast;
  position: relative;

  .nav-icon {
    font-size: 18px;
    flex-shrink: 0;
  }

  .nav-label {
    flex: 1;
  }

  .nav-badge {
    font-size: 11px;
    font-weight: 700;
    background: $color-nba-red;
    color: #fff;
    padding: 2px 8px;
    border-radius: $radius-full;
    line-height: 1.2;
  }

  &:hover {
    background: $sidebar-hover;
    color: $sidebar-active;
  }

  &.active {
    background: $sidebar-active;
    color: #fff;
    box-shadow:
      3px 3px 8px rgba(29, 66, 138, 0.25),
      -2px -2px 6px rgba(255, 255, 255, 0.5);

    .nav-icon {
      color: #fff;
    }
  }
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.sidebar-version {
  font-size: 11px;
  color: $sidebar-text-muted;
  text-align: center;
}

// ============================================
// 主内容区
// ============================================
.main-wrapper {
  flex: 1;
  margin-left: $sidebar-width;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

// ============================================
// 顶部导航栏
// ============================================
.topbar {
  position: sticky;
  top: 0;
  height: $topbar-height;
  background: rgba($bg-surface, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid $border-dark;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 $space-xl;
  z-index: 50;
}

.topbar-left {
  .topbar-title {
    font-size: 18px;
    font-weight: 700;
    color: $text-primary;
    letter-spacing: -0.3px;
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: $space-lg;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  position: relative;
  width: 38px;
  height: 38px;
  border-radius: $radius-md;
  border: 1px solid $border-dark;
  background: $bg-card;
  color: $text-secondary;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all $transition-fast;
  box-shadow: $neu-flat;

  .el-icon {
    font-size: 16px;
  }

  &:hover {
    color: $text-primary;
    box-shadow: $neu-raised-sm;
    transform: translateY(-1px);
  }

  &:active {
    box-shadow: $neu-pressed;
    transform: translateY(0);
  }

  .notification-dot {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 7px;
    height: 7px;
    background: $color-nba-red;
    border-radius: 50%;
    border: 1.5px solid $bg-card;
  }
}

.topbar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  border-radius: $radius-md;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  .user-avatar {
    width: 36px;
    height: 36px;
    border-radius: $radius-full;
    background: linear-gradient(135deg, $color-nba-blue, color.adjust($color-nba-blue, $lightness: 12%));
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 16px;
  }

  .user-info {
    display: flex;
    flex-direction: column;

    .user-name {
      font-size: 13px;
      font-weight: 600;
      color: $text-primary;
      line-height: 1.2;
    }

    .user-role {
      font-size: 11px;
      color: $text-muted;
    }
  }
}

// ============================================
// 主内容
// ============================================
.main-content {
  flex: 1;
  padding: $space-xl;
  overflow-y: auto;
}

// ============================================
// 页面过渡
// ============================================
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

// ============================================
// 响应式
// ============================================
@media (max-width: $breakpoint-lg) {
  .sidebar {
    width: $sidebar-collapsed;

    .logo-text,
    .nav-label,
    .nav-badge,
    .sidebar-footer {
      display: none;
    }

    .sidebar-logo {
      justify-content: center;
      padding: 20px 12px;
    }

    .nav-item {
      justify-content: center;
      padding: 12px;
    }
  }

  .main-wrapper {
    margin-left: $sidebar-collapsed;
  }
}
</style>
