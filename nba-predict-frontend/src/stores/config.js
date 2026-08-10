import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi } from '@/api'

export const useConfigStore = defineStore('config', () => {
  const coefficients = ref({})
  const oddsSettings = ref({})
  const loading = ref(false)

  async function fetchCoefficients() {
    loading.value = true
    try {
      const res = await configApi.list({ configGroup: 'COEFFICIENT' })
      coefficients.value = res.data || {}
    } catch (e) {
      console.error('[ConfigStore] fetchCoefficients:', e)
    } finally {
      loading.value = false
    }
  }

  async function updateCoefficient(key, value) {
    try {
      await configApi.update({ configGroup: 'COEFFICIENT', configKey: key, configValue: String(value) })
      coefficients.value[key] = value
    } catch (e) {
      console.error('[ConfigStore] updateCoefficient:', e)
    }
  }

  return { coefficients, oddsSettings, loading, fetchCoefficients, updateCoefficient }
})
