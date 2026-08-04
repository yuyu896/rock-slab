import { describe, it, expect } from 'vitest'
import { AxiosError } from 'axios'
import { handleApiError } from '@/utils/request'

function makeErr(status: number, data: unknown): AxiosError {
  return new AxiosError(
    'err', String(status), undefined, undefined,
    { status, statusText: '', data, headers: {}, config: {} as any } as any,
  )
}

describe('handleApiError', () => {
  it('非 JSON（HTML 错误页）响应返回可读提示，不逐字符乱码', () => {
    const msg = handleApiError(makeErr(500, '<html><body>Server Error</body></html>'))
    expect(msg).toBe('服务器错误（HTTP 500），请稍后重试或联系管理员')
    expect(msg).not.toContain('<')
  })

  it('DRF 字段错误正常提取（不回归）', () => {
    const msg = handleApiError(makeErr(400, { code: ['分公司编码 SH001 已存在'] }))
    expect(msg).toBe('分公司编码 SH001 已存在')
  })

  it('detail 字段直接返回', () => {
    const msg = handleApiError(makeErr(403, { detail: '无权操作' }))
    expect(msg).toBe('无权操作')
  })
})
