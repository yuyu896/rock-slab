import { describe, it, expect, beforeEach } from 'vitest'
import request from '@/utils/request'

/** 注入 401 响应，触发响应拦截器（吞掉 reject，只关心副作用 location.href） */
function fire401(url: string) {
  request.defaults.adapter = ((config: any) => {
    const err: any = new Error('401')
    err.config = config
    err.response = { status: 401, data: { detail: 'token 无效' }, config, headers: {} }
    return Promise.reject(err)
  }) as any
  return request.get(url).catch(() => undefined)
}

describe('401 响应拦截：登录跳转保留回跳路径', () => {
  beforeEach(() => {
    localStorage.setItem('rock_slab_token', 'stale')
    Object.defineProperty(window, 'location', {
      value: { href: '', pathname: '/mobile/scan', search: '?task=abc' },
      writable: true,
      configurable: true,
    })
  })

  it('普通页面 401 → 跳登录并带 redirect（含 query）', async () => {
    await fire401('/api/assets/')
    expect(window.location.href).toBe('/login?redirect=' + encodeURIComponent('/mobile/scan?task=abc'))
  })

  it('已停在 /login 时 401 → 跳裸 /login，不带指向自身的 redirect', async () => {
    ;(window.location as any).pathname = '/login'
    ;(window.location as any).search = ''
    await fire401('/api/assets/')
    expect(window.location.href).toBe('/login')
  })

  it('登录请求本身的 401 不跳转（由登录页展示错误）', async () => {
    await fire401('/api/auth/login')
    expect(window.location.href).toBe('')
  })

  it('401 清除失效 token（非登录请求）', async () => {
    await fire401('/api/assets/')
    expect(localStorage.getItem('rock_slab_token')).toBeNull()
  })
})
