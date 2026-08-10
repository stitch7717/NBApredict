import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/HomeView.vue') },
  { path: '/predict', name: 'Predict', component: () => import('../views/PredictView.vue') },
  { path: '/teams', name: 'Teams', component: () => import('../views/TeamsView.vue') },
  { path: '/teams/:id', name: 'TeamDetail', component: () => import('../views/TeamDetailView.vue') },
  { path: '/players', name: 'Players', component: () => import('../views/PlayersView.vue') },
  { path: '/players/:id', name: 'PlayerDetail', component: () => import('../views/PlayerDetailView.vue') },
  { path: '/model', name: 'Model', component: () => import('../views/ModelView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
