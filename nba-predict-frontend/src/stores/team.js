import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { teamApi } from '@/api'

export const useTeamStore = defineStore('team', () => {
  const teams = ref([])
  const loading = ref(false)
  const lastFetch = ref(null)

  const teamMap = computed(() => {
    const map = {}
    teams.value.forEach(t => { map[t.teamId] = t })
    return map
  })

  const teamOptions = computed(() =>
    teams.value.map(t => ({ value: t.teamId, label: t.teamName }))
  )

  async function fetchTeams(force = false) {
    if (!force && teams.value.length && lastFetch.value) {
      const age = Date.now() - lastFetch.value
      if (age < 5 * 60 * 1000) return // 5 分钟缓存
    }
    loading.value = true
    try {
      const res = await teamApi.getList()
      teams.value = res.data || []
      lastFetch.value = Date.now()
    } catch (e) {
      console.error('[TeamStore] fetchTeams:', e)
    } finally {
      loading.value = false
    }
  }

  return { teams, loading, teamMap, teamOptions, fetchTeams }
})
