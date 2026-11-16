import { defineStore } from 'pinia'
import { ref } from 'vue'

// 路由守卫读的是 ROLE_KEY（'guest' | 'admin'），与后端 role（ADMIN | USER）区分开
const ROLE_KEY = 'nba-predict-role'
const TOKEN_KEY = 'nba-predict-token'
const USER_KEY = 'nba-predict-user'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const role = ref(localStorage.getItem(ROLE_KEY) || null) // null | 'guest' | 'admin'
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const userInfo = ref(readUser())

  /**
   * 登录/注册成功后写入登录态
   * @param {object} auth  后端 AuthResponse
   * @param {'guest'|'admin'} roleKey  入口页选择的身份
   */
  function applyAuth(auth, roleKey) {
    token.value = auth.token
    userInfo.value = {
      userId: auth.userId,
      username: auth.username,
      nickname: auth.nickname,
    }
    role.value = roleKey
    localStorage.setItem(TOKEN_KEY, auth.token)
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo.value))
    localStorage.setItem(ROLE_KEY, roleKey)
  }

  function logout() {
    role.value = null
    token.value = ''
    userInfo.value = null
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const isAdmin = () => role.value === 'admin'
  const isGuest = () => role.value === 'guest'
  const isLoggedIn = () => !!token.value

  return { role, token, userInfo, applyAuth, logout, isAdmin, isGuest, isLoggedIn }
})
