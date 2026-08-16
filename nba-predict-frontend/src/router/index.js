import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      // === v2 新页面 ===
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/home/index.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'game/:gameId',
        name: 'GameDetail',
        component: () => import('@/views/game/detail.vue'),
        meta: { title: '数据页' },
      },
      {
        path: 'predict',
        name: 'Predict',
        component: () => import('@/views/predict/index.vue'),
        meta: { title: '预测' },
      },
      {
        path: 'players',
        name: 'Players',
        component: () => import('@/views/players/index.vue'),
        meta: { title: '球员数据' },
      },
      {
        path: 'teams',
        name: 'Teams',
        component: () => import('@/views/teams/index.vue'),
        meta: { title: '球队数据' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/index.vue'),
        meta: { title: '系统设置' },
      },
      // === 旧路由保留（兼容） ===
      {
        path: 'player/list',
        name: 'PlayerList',
        component: () => import('@/views/player/list.vue'),
        meta: { title: '球员列表' },
      },
      {
        path: 'player/predict',
        name: 'PlayerPredict',
        component: () => import('@/views/player/predict.vue'),
        meta: { title: '球员预测' },
      },
      {
        path: 'team/list',
        name: 'TeamList',
        component: () => import('@/views/team/list.vue'),
        meta: { title: '球队列表' },
      },
      {
        path: 'team/predict',
        name: 'TeamPredict',
        component: () => import('@/views/team/predict.vue'),
        meta: { title: '球队预测' },
      },
      {
        path: 'team/detail/:teamId',
        name: 'TeamDetail',
        component: () => import('@/views/team/detail.vue'),
        meta: { title: '球队详情' },
      },
      {
        path: 'series',
        name: 'Series',
        component: () => import('@/views/series/index.vue'),
        meta: { title: '系列赛' },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '数据看板' },
      },
      {
        path: 'odds',
        name: 'Odds',
        component: () => import('@/views/odds/index.vue'),
        meta: { title: '赔率管理' },
      },
      {
        path: 'record',
        name: 'Record',
        component: () => import('@/views/record/index.vue'),
        meta: { title: '预测记录' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'NBA预测系统'} - NBA预测系统`
  next()
})

export default router
