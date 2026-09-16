import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { toStringMock } = vi.hoisted(() => ({ toStringMock: vi.fn() }))

vi.mock('qrcode', () => ({
  default: { toString: toStringMock },
}))

import AssetPrintDialog from '@/views/assets/AssetPrintDialog.vue'
import dialogSource from '@/views/assets/AssetPrintDialog.vue?raw'

const assets = [
  { id: 'fa-1', 内部编号: 'A-a00008-BJ001-1', 序列号: 'PF3XK2LM', 资产名称: 'ThinkPad T14', 品目编号: 'A-a00008', 分公司: '北京分公司' },
  { id: 'fa-2', 内部编号: 'A-a00008-BJ001-2', 序列号: '', 资产名称: 'ThinkPad T14', 品目编号: 'A-a00008', 分公司: '北京分公司' },
]

let appShell: HTMLDivElement

async function mountInAppShell(props: Record<string, unknown> = {}) {
  appShell = document.createElement('div')
  appShell.id = 'app'
  document.body.appendChild(appShell)
  const wrapper = mount(AssetPrintDialog, {
    props: { visible: true, assets, ...props },
    attachTo: appShell,
  })
  await flushPromises()
  return wrapper
}

describe('AssetPrintDialog 标签规范 V1', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    toStringMock.mockResolvedValue('<svg class="qr-stub"></svg>')
  })

  afterEach(() => {
    document.body.innerHTML = ''
    document.head.querySelectorAll('#label-page-size').forEach(e => e.remove())
  })

  it('标签区 Teleport 到 body，位于 #app 应用壳之外（打印时 #app 整体隐藏）', async () => {
    const wrapper = await mountInAppShell()
    const printArea = document.getElementById('print-area')
    expect(printArea).toBeTruthy()
    expect(appShell.contains(printArea!)).toBe(false)
    wrapper.unmount()
  })

  it('QR 编码内部编号（ECC M），每签一个二维码容器', async () => {
    const wrapper = await mountInAppShell({ visible: false })
    await wrapper.setProps({ visible: true })
    await flushPromises()
    expect(toStringMock).toHaveBeenCalledTimes(2)
    expect(toStringMock).toHaveBeenCalledWith('A-a00008-BJ001-1', {
      type: 'svg', errorCorrectionLevel: 'M', margin: 0,
    })
    expect(toStringMock).toHaveBeenCalledWith('A-a00008-BJ001-2', expect.anything())
    expect(document.querySelectorAll('.qr-box svg').length).toBeGreaterThanOrEqual(2)
    wrapper.unmount()
  })

  it('标签三区文案：内部编号/SN/品目名称/品目·分公司', async () => {
    const wrapper = await mountInAppShell()
    const labels = document.querySelectorAll('.print-label')
    expect(labels).toHaveLength(2)
    const first = labels[0]
    expect(first.querySelector('.label-code')!.textContent).toBe('A-a00008-BJ001-1')
    expect(first.querySelector('.label-sn')!.textContent).toBe('SN: PF3XK2LM')
    expect(first.querySelector('.label-name')!.textContent).toBe('ThinkPad T14')
    expect(first.querySelector('.label-aux')!.textContent).toContain('品目 A-a00008')
    expect(first.querySelector('.label-aux')!.textContent).toContain('北京分公司')
    wrapper.unmount()
  })

  it('序列号为空（待补录）时 SN 行整行不渲染', async () => {
    const wrapper = await mountInAppShell()
    const labels = document.querySelectorAll('.print-label')
    expect(labels[0].querySelector('.label-sn')).toBeTruthy()
    expect(labels[1].querySelector('.label-sn')).toBeNull()
    wrapper.unmount()
  })

  it('纸型默认 60×40、可切换 A4 并记忆，@page 随纸型改写', async () => {
    const wrapper = await mountInAppShell()
    const content = document.querySelector('.modal-content')!
    expect(content.className).toContain('paper-60x40')
    let pageStyle = document.getElementById('label-page-size') as HTMLStyleElement
    expect(pageStyle.textContent).toContain('60mm 40mm')

    const a4Btn = [...document.querySelectorAll<HTMLButtonElement>('.paper-switch button')].find(b => b.textContent === 'A4 双列')!
    a4Btn.click()
    await flushPromises()
    expect(content.className).toContain('paper-a4')
    pageStyle = document.getElementById('label-page-size') as HTMLStyleElement
    expect(pageStyle.textContent).toContain('A4')
    expect(localStorage.getItem('rock_slab_label_paper')).toBe('a4')
    wrapper.unmount()

    const second = await mountInAppShell()
    expect(document.querySelector('.modal-content')!.className).toContain('paper-a4')
    second.unmount()
  })

  it('弹窗常驻「实际大小/100%」打印提示，且打印态隐藏', async () => {
    const wrapper = await mountInAppShell()
    const hint = document.querySelector('.print-hint')!
    expect(hint.textContent).toContain('实际大小')
    expect(dialogSource).toMatch(/\.print-hint\s*\{[^}]*display:\s*none/s)
    wrapper.unmount()
  })

  it('「打印」按钮触发 window.print', async () => {
    const printSpy = vi.fn()
    vi.stubGlobal('print', printSpy)
    const wrapper = await mountInAppShell()
    const btn = [...document.querySelectorAll<HTMLButtonElement>('button')].find(b => b.textContent === '打印')!
    btn.click()
    await Promise.resolve()
    expect(printSpy).toHaveBeenCalled()
    wrapper.unmount()
    vi.unstubAllGlobals()
  })

  it('60×40 版式源码约定：一页一签、固定高度防越界、白底黑字（源码断言）', () => {
    expect(dialogSource).toMatch(/<Teleport to="body">/)
    expect(dialogSource).toMatch(/@page \{ size: 60mm 40mm; margin: 0; \}/)
    expect(dialogSource).toMatch(/break-after:\s*page/)
    expect(dialogSource).toMatch(/height:\s*40mm/)
    expect(dialogSource).toMatch(/#app \{ display: none !important; \}/)
  })
})
