import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

import InstallGuide from '@/views/InstallGuide.vue'

function setUa(ua: string) {
  Object.defineProperty(window.navigator, 'userAgent', { value: ua, configurable: true })
}

async function mountGuide() {
  const wrapper = mount(InstallGuide)
  await flushPromises()
  return wrapper
}

describe('InstallGuide 环境自适应', () => {
  const realUa = navigator.userAgent

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    setUa(realUa)
  })

  it('微信内：显示跳浏览器引导，不显示安装按钮', async () => {
    setUa('Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 MicroMessenger/8.0.49')
    const wrapper = await mountGuide()
    expect(wrapper.text()).toContain('微信内')
    expect(wrapper.text()).toContain('在浏览器打开')
    expect(wrapper.find('.install-big-btn').exists()).toBe(false)
    wrapper.unmount()
  })

  it('iPhone：显示分享→添加到主屏幕三步', async () => {
    setUa('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1')
    const wrapper = await mountGuide()
    expect(wrapper.text()).toContain('iPhone 安装')
    expect(wrapper.text()).toContain('添加到主屏幕')
    expect(wrapper.find('.install-big-btn').exists()).toBe(false)
    wrapper.unmount()
  })

  it('安卓无安装事件：显示菜单图文兜底', async () => {
    setUa('Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36')
    const wrapper = await mountGuide()
    expect(wrapper.text()).toContain('安卓安装')
    expect(wrapper.text()).toContain('添加到主屏幕')
    wrapper.unmount()
  })

  it('安卓且安装事件触发：出【安装磐盘】按钮并可 prompt', async () => {
    setUa('Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36')
    const wrapper = await mountGuide()
    const promptMock = vi.fn()
    const ev = new Event('beforeinstallprompt')
    ;(ev as any).prompt = promptMock
    ;(ev as any).userChoice = Promise.resolve({ outcome: 'accepted' })
    window.dispatchEvent(ev)
    await flushPromises()
    const btn = wrapper.find('.install-big-btn')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    await flushPromises()
    expect(promptMock).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('PC 桌面：提示用手机扫码打开', async () => {
    setUa('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36')
    const wrapper = await mountGuide()
    expect(wrapper.text()).toContain('请在手机上打开本页')
    wrapper.unmount()
  })

  it('「打开磐盘」跳转扫码页', async () => {
    const wrapper = await mountGuide()
    await wrapper.find('.open-btn').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/mobile/scan')
    wrapper.unmount()
  })
})
