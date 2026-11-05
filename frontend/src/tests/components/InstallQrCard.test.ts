import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { toCanvasMock } = vi.hoisted(() => ({ toCanvasMock: vi.fn() }))
vi.mock('qrcode', () => ({ default: { toCanvas: toCanvasMock } }))

import InstallQrCard from '@/components/InstallQrCard.vue'

describe('InstallQrCard 工作台移动端盘点入口二维码卡片', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    toCanvasMock.mockResolvedValue(undefined)
  })

  it('运行时生成二维码，内容为 当前域名/mobile/inventory', async () => {
    const wrapper = mount(InstallQrCard)
    await flushPromises()
    expect(toCanvasMock).toHaveBeenCalledTimes(1)
    const canvas = toCanvasMock.mock.calls[0][0]
    expect(canvas).toBeInstanceOf(HTMLCanvasElement)
    expect(canvas.width).toBe(88)
    expect(canvas.height).toBe(88)
    expect(toCanvasMock.mock.calls[0][1]).toBe(`${location.origin}/mobile/inventory`)
    expect(toCanvasMock.mock.calls[0][2].width).toBe(88)
    wrapper.unmount()
  })

  it('显示移动端盘点说明，不暴露安装话术或内部地址', async () => {
    const wrapper = mount(InstallQrCard)
    await flushPromises()
    expect(wrapper.text()).toContain('移动端盘点')
    expect(wrapper.find('.qr-heading').exists()).toBe(true)
    expect(wrapper.text()).toContain('微信扫码使用移动端进行盘点')
    expect(wrapper.text()).toContain('首次使用需登录，登录后选择盘点任务')
    const contentChildren = Array.from(wrapper.get('.qr-content').element.children)
    expect(contentChildren[0].classList.contains('qr-info')).toBe(true)
    expect(contentChildren[1].classList.contains('qr-box')).toBe(true)
    expect(wrapper.text()).not.toContain('安装')
    expect(wrapper.text()).not.toContain('/mobile/inventory')
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
