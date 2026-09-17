import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { toCanvasMock } = vi.hoisted(() => ({ toCanvasMock: vi.fn() }))
vi.mock('qrcode', () => ({ default: { toCanvas: toCanvasMock } }))

import InstallQrCard from '@/components/InstallQrCard.vue'

describe('InstallQrCard 工作台安装二维码卡片', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    toCanvasMock.mockResolvedValue(undefined)
  })

  it('运行时生成二维码，内容为 当前域名/install', async () => {
    const wrapper = mount(InstallQrCard)
    await flushPromises()
    expect(toCanvasMock).toHaveBeenCalledTimes(1)
    const canvas = toCanvasMock.mock.calls[0][0]
    expect(canvas).toBeInstanceOf(HTMLCanvasElement)
    expect(toCanvasMock.mock.calls[0][1]).toBe(`${location.origin}/install`)
    wrapper.unmount()
  })

  it('卡片文案含引导语与步骤提示', async () => {
    const wrapper = mount(InstallQrCard)
    await flushPromises()
    expect(wrapper.text()).toContain('移动端安装')
    expect(wrapper.text()).toContain('手机扫码')
    expect(wrapper.text()).toContain('安卓两下 · iPhone 四下')
    expect(wrapper.text()).toContain('/install')
    wrapper.unmount()
  })

  it('二维码生成失败静默（不崩页面）', async () => {
    toCanvasMock.mockRejectedValue(new Error('canvas unavailable'))
    const wrapper = mount(InstallQrCard)
    await flushPromises()
    expect(wrapper.find('.install-qr-card').exists()).toBe(true)
    wrapper.unmount()
  })
})
