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
        // 带上当前路径让登录后回到原页面（否则默认兜底 /dashboard，移动端 401 重登会被送到 PC 工作台）；已在登录页时不带，避免 redirect 指向自身
        const current = window.location.pathname + window.location.search
        window.location.href = window.location.pathname === '/login'
          ? '/login'
          : `/login?redirect=${encodeURIComponent(current)}`
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
      const messages = extractErrorMessages(apiError)
      if (messages.length > 0) return messages.join('；')
    }
  }
  if (error instanceof Error) return error.message
  return '请求失败，请稍后重试'
}

/** 递归提取 DRF 验证错误信息（处理嵌套字段如 items[0].单价） */
function extractErrorMessages(obj: any, prefix = '', arrayIndex = -1): string[] {
  const messages: string[] = []
  for (const [key, value] of Object.entries(obj)) {
    if (key === 'detail') continue

    if (Array.isArray(value)) {
      // 数组可能是错误消息列表，或嵌套对象列表（如 items）
      for (let i = 0; i < value.length; i++) {
        const item = value[i]
        if (typeof item === 'string') {
          // 字符串数组：直接是该字段的错误消息列表
          const fieldLabel = formatFieldLabel(key, prefix, arrayIndex)
          messages.push(`${fieldLabel}: ${item}`)
        } else if (item && typeof item === 'object') {
          // 对象数组：嵌套结构，递归处理
          messages.push(...extractErrorMessages(item, key, i))
        }
      }
    } else if (value && typeof value === 'object') {
      messages.push(...extractErrorMessages(value, key, arrayIndex))
    } else {
      const fieldLabel = formatFieldLabel(key, prefix, arrayIndex)
      messages.push(`${fieldLabel}: ${String(value)}`)
    }
  }
  return messages
}

/** 格式化字段标签，将技术性路径转换为用户友好的中文表述 */
function formatFieldLabel(key: string, prefix: string, arrayIndex: number): string {
  // 处理明细行字段：items[0].单价 → 第1行单价
  if (prefix === 'items' && arrayIndex >= 0) {
    return `第${arrayIndex + 1}行${key}`
  }

  // 其他嵌套字段：保持简洁
  if (prefix) {
    return arrayIndex >= 0 ? `${prefix}[${arrayIndex}].${key}` : `${prefix}.${key}`
  }

  return key
}

export { TOKEN_KEY }
export default request
