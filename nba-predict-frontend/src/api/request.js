import axios from 'axios'
import { ElMessage, ElLoading } from 'element-plus'

const service = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

let loadingInstance = null
let requestCount = 0

const showLoading = () => {
  requestCount++
  if (requestCount === 1) {
    loadingInstance = ElLoading.service({
      lock: true,
      text: '数据加载中...',
      background: 'rgba(18, 18, 18, 0.8)',
    })
  }
}

const hideLoading = () => {
  requestCount--
  if (requestCount <= 0) {
    requestCount = 0
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
  }
}

service.interceptors.request.use(
  (config) => {
    showLoading()
    config.headers['X-Request-Source'] = 'nba-predict-frontend'
    config._retryCount = config._retryCount ?? 2
    return config
  },
  (error) => {
    hideLoading()
    return Promise.reject(error)
  }
)

const statusMsg = {
  400: '请求参数错误',
  401: '未授权访问',
  403: '禁止访问',
  404: '资源不存在',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂不可用',
}

service.interceptors.response.use(
  (response) => {
    hideLoading()
    const res = response.data
    if (res.code !== undefined) {
      if (res.code === 200) return res
      if (!response.config.silent) {
        ElMessage.error(res.message || '请求失败')
      }
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  async (error) => {
    hideLoading()
    const config = error.config
    if (config && config._retryCount > 0 && !config._retried) {
      config._retried = true
      config._retryCount--
      await new Promise(r => setTimeout(r, 1000))
      return service(config)
    }
    const msg = statusMsg[error.response?.status] || (error.code === 'ECONNABORTED' ? '请求超时' : '网络异常')
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

// Python 算法层专用实例（无 /api 前缀，直连 localhost:8000）
export const pythonRequest = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

export default service
