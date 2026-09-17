import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { toStringMock } = vi.hoisted(() => ({ toStringMock: vi.fn() }))
const { renderLabelDataUrlMock } = vi.hoisted(() => ({ renderLabelDataUrlMock: vi.fn() }))

vi.mock('qrcode', () => ({
  default: { toString: toStringMock },
}))

vi.mock('@/utils/labelImage', () => ({
  renderLabelDataUrl: renderLabelDataUrlMock,
  labelFileName: (a: Record<string, any>) => `标签_${a.内部编号}.png`,
}))

import AssetPrintDialog from '@/views/assets/AssetPrintDialog.vue'
import dialogSource from '@/views/assets/AssetPrintDialog.vue?raw'

const assets = [
  { id: 'fa-1', 内部编号: 'A-a00008-BJ001-1', 序列号: 'PF3XK2LM', 资产名称: 'ThinkPad T14', 品目编号: 'A-a00008', 分公司: '北京分公司', 供应商: '小熊', 采购日期: '2026-09-16' },
  { id: 'fa-2', 内部编号: 'A-a00008-BJ001-2', 序列号: '', 资产名称: 'ThinkPad T14', 品目编号: 'A-a00008', 分公司: '北京分公司', 供应商: '', 采购日期: '' },
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

  it('QR 生成失败不再静默：显示占位并报 console.error', async () => {
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    toStringMock.mockRejectedValue(new Error('qrcode module broken'))
    const wrapper = await mountInAppShell({ visible: false })
    await wrapper.setProps({ visible: true })
    await flushPromises()
    const fallbacks = document.querySelectorAll('.qr-box .qr-fallback')
    expect(fallbacks).toHaveLength(2)
    expect(fallbacks[0].textContent).toContain('QR 生成失败')
    expect(errSpy).toHaveBeenCalled()
    errSpy.mockRestore()
    wrapper.unmount()
  })

  it('标签 V3 五行英文前缀文案：无品目编号行，供应商/日期行显隐', async () => {
    const wrapper = await mountInAppShell()
    const labels = document.querySelectorAll('.print-label')
    expect(labels).toHaveLength(2)
    const first = labels[0]
    expect(first.querySelector('.label-code')!.textContent).toContain('NO:')
    expect(first.querySelector('.label-code')!.textContent).toContain('A-a00008-BJ001-1')
    expect(first.querySelector('.label-sn')!.textContent).toContain('SN:')
    expect(first.querySelector('.label-name')!.textContent).toContain('ITEM:')
    const auxTexts = [...first.querySelectorAll('.label-aux')].map(e => (e.textContent || '').trim())
    expect(auxTexts).toHaveLength(2)
    expect(auxTexts[0]).toContain('BRANCH:')
    expect(auxTexts[0]).toContain('北京分公司')
    expect(auxTexts[1]).toContain('VENDOR:')
    expect(auxTexts[1]).toContain('小熊')
    expect(auxTexts[1]).toContain('DATE:')
    expect(auxTexts[1]).toContain('2026-09-16')
    expect(first.textContent).not.toContain('品目')

    const second = labels[1]
    const secondAux = [...second.querySelectorAll('.label-aux')].map(e => (e.textContent || '').trim())
    expect(secondAux).toHaveLength(1)
    expect(secondAux[0]).toContain('BRANCH:')
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

describe('AssetPrintDialog 导出图片（第二通道）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    toStringMock.mockResolvedValue('<svg class="qr-stub"></svg>')
    renderLabelDataUrlMock.mockImplementation(async (a: Record<string, any>) => `data:image/png;base64,${a.id}`)
  })

  afterEach(() => {
    document.body.innerHTML = ''
    document.head.querySelectorAll('#label-page-size').forEach(e => e.remove())
  })

  async function mountDialog() {
    appShell = document.createElement('div')
    appShell.id = 'app'
    document.body.appendChild(appShell)
    const wrapper = mount(AssetPrintDialog, {
      props: { visible: true, assets },
      attachTo: appShell,
    })
    await flushPromises()
    return wrapper
  }

  it('点「导出图片」进入导出视图：每签一张图 + 下载按钮 + App 原尺寸提示', async () => {
    const wrapper = await mountDialog()
    const exportBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '导出图片')!
    await exportBtn.click()
    await flushPromises()

    expect(renderLabelDataUrlMock).toHaveBeenCalledTimes(2)
    expect(renderLabelDataUrlMock).toHaveBeenCalledWith(expect.objectContaining({ 内部编号: 'A-a00008-BJ001-1' }))
    const view = document.querySelector('.export-view')!
    expect(view).toBeTruthy()
    expect(view.querySelector('.print-hint')!.textContent).toContain('原尺寸')
    expect(document.querySelectorAll('.export-item img')).toHaveLength(2)
    expect(document.querySelectorAll('.export-item img')[0].getAttribute('src')).toBe('data:image/png;base64,fa-1')
    const dlBtns = [...document.querySelectorAll<HTMLButtonElement>('.export-item button')]
    expect(dlBtns.map(b => b.textContent)).toEqual(['下载', '下载'])
    wrapper.unmount()
  })

  it('单张下载：触发 a[download] 点击、文件名含内部编号', async () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const wrapper = await mountDialog()
    const exportBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '导出图片')!
    await exportBtn.click()
    await flushPromises()
    const first = [...document.querySelectorAll<HTMLButtonElement>('.export-item button')][0]
    await first.click()
    expect(clickSpy).toHaveBeenCalledTimes(1)
    const anchor = clickSpy.mock.instances[0] as unknown as HTMLAnchorElement
    expect(anchor.download).toBe('标签_A-a00008-BJ001-1.png')
    clickSpy.mockRestore()
    wrapper.unmount()
  })

  it('「全部下载」逐张触发、「返回打印」回到打印预览', async () => {
    vi.useFakeTimers()
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const wrapper = await mountDialog()
    const exportBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '导出图片')!
    await exportBtn.click()
    await flushPromises()

    const allBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '全部下载')!
    await allBtn.click()
    vi.advanceTimersByTime(1000)
    expect(clickSpy).toHaveBeenCalledTimes(2)

    const backBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '返回打印')!
    await backBtn.click()
    await flushPromises()
    expect(document.querySelector('.export-view')).toBeNull()
    expect(document.getElementById('print-area')).toBeTruthy()
    clickSpy.mockRestore()
    vi.useRealTimers()
    wrapper.unmount()
  })
})
