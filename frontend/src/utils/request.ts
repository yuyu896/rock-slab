/* 磐盘 - Rock Slab Axios 请求实例 */
import axios from 'axios'
import type { ApiError } from '@/types'

const TOKEN_KEY = 'rock_slab_token'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器：注入 token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      // 只在非登录请求时重定向，登录页的 401 错误需要正常处理以显示错误提示
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      if (!isLoginRequest) {
        // 检查是否是 Token 过期
        const detail = error.response?.data?.detail || ''
        if (detail.includes('过期')) {
          sessionStorage.setItem('token_expired', 'true')
        }
        window.location.href = '/login'
      }
    }
    if (error.response?.status === 429) {
      // 请求过于频繁 - 由调用方处理
    }
    return Promise.reject(error)
  },
)

/** 从 DRF 错误响应中提取可读错误信息 */
export function handleApiError(error: unknown): string {
  if (axios.isAxiosError(error) && error.response) {
    const data = error.response.data
    // 非 JSON 响应（如 5xx 的 HTML 错误页）：返回可读提示，避免逐字符乱码
    if (typeof data === 'string') {
      return `服务器错误（HTTP ${error.response.status}），请稍后重试或联系管理员`
    }
    if (data && typeof data === 'object') {
      const apiError = data as ApiError
      if (apiError.detail) return apiError.detail
      const messages = Object.entries(apiError)
        .filter(([key]) => key !== 'detail')
        .flatMap(([, value]) => (Array.isArray(value) ? value : [String(value)]))
      if (messages.length > 0) return messages.join('；')
    }
  }
  if (error instanceof Error) return error.message
  return '请求失败，请稍后重试'
}

export { TOKEN_KEY }
export default request
