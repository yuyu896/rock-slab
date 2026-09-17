import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'

vi.mock('jsqr', () => ({ default: vi.fn() }))

import { shouldAcceptCode, useBarcodeScanner } from '@/composables/useBarcodeScanner'

describe('shouldAcceptCode 同码冷却', () => {
  it('同码在冷却窗口内拒绝', () => {
    expect(shouldAcceptCode('A-1', 'A-1', 1000, 1500, 1000)).toBe(false)
  })

  it('同码超出冷却窗口放行', () => {
    expect(shouldAcceptCode('A-1', 'A-1', 1000, 2100, 1000)).toBe(true)
  })

  it('不同码立即放行', () => {
    expect(shouldAcceptCode('A-2', 'A-1', 1000, 1100, 1000)).toBe(true)
  })
})

describe('useBarcodeScanner 引擎选择与生命周期', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('无 BarcodeDetector 时引擎为 jsqr', () => {
    const scanner = useBarcodeScanner(ref(null), { onDetect: vi.fn() })
    expect(scanner.engine).toBe('jsqr')
  })

  it('取流失败时置错误且不进入会话', async () => {
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    const scanner = useBarcodeScanner(ref(null), { onDetect: vi.fn() })
    await scanner.start()
    expect(scanner.active.value).toBe(false)
    expect(scanner.error.value).toContain('摄像头')
  })

  it('start 建立会话、stop 停流清理', async () => {
    const track = { stop: vi.fn() }
    vi.stubGlobal('navigator', {
      mediaDevices: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [track] }) },
    })
    const video = document.createElement('video')
    video.play = vi.fn().mockResolvedValue(undefined)
    // happy-dom 校验 srcObject 类型，覆写为普通属性以便断言赋值/清理
    Object.defineProperty(video, 'srcObject', { value: null, writable: true, configurable: true })
    const scanner = useBarcodeScanner(ref(video), { onDetect: vi.fn() })
    await scanner.start()
    expect(scanner.active.value).toBe(true)
    expect(video.srcObject).toBeTruthy()
    scanner.stop()
    expect(scanner.active.value).toBe(false)
    expect(track.stop).toHaveBeenCalled()
    expect(video.srcObject).toBeNull()
  })
})
