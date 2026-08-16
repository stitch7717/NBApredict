import { defineStore } from 'pinia'
import { ref } from 'vue'

const ROLE_KEY = 'nba-predict-role'

export const useUserStore = defineStore('user', () => {
  const role = ref(localStorage.getItem(ROLE_KEY) || null) // null | 'guest' | 'admin'

  function enterAs(newRole) {
    role.value = newRole
    localStorage.setItem(ROLE_KEY, newRole)
  }

  function exit() {
    role.value = null
    localStorage.removeItem(ROLE_KEY)
  }

  const isAdmin = () => role.value === 'admin'
  const isGuest = () => role.value === 'guest'

  return { role, enterAs, exit, isAdmin, isGuest }
})
