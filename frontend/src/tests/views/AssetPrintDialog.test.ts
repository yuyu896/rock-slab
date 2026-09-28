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

    const a4Btn = [...document.querySelectorAll<HTMLButtonElement>('.paper-switch button')].find(b => b.textContent === 'A4 三列')!
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

  it('切纸型后缩号按新纸型重算：fit 在 DOM class 更新后执行，旧 inline 字号被清除', async () => {
    // jsdom 无真实布局：动态桩——60×40 视为超宽（触发缩号）、A4 视为不超宽（应清除 inline 字号）
    const fontSizeOf = () => (document.querySelector('.modal-content')?.classList.contains('paper-a4') ? '14px' : '12px')
    const gcSpy = vi.spyOn(window, 'getComputedStyle').mockImplementation(
      () => ({ fontSize: fontSizeOf() }) as unknown as CSSStyleDeclaration,
    )
    // jsdom 将 scrollWidth/clientWidth 定义在 Element.prototype（不同版本有差异），在所属原型上替换并恢复
    const owningProto = (prop: string) =>
      [HTMLElement.prototype, Element.prototype].find(p => Object.getOwnPropertyDescriptor(p, prop))!
    const swProto = owningProto('scrollWidth')
    const cwProto = owningProto('clientWidth')
    const origSW = Object.getOwnPropertyDescriptor(swProto, 'scrollWidth')!
    const origCW = Object.getOwnPropertyDescriptor(cwProto, 'clientWidth')!
    Object.defineProperty(swProto, 'scrollWidth', { configurable: true, get: () => 200 })
    Object.defineProperty(cwProto, 'clientWidth', {
      configurable: true,
      get: () => (document.querySelector('.modal-content')?.classList.contains('paper-a4') ? 300 : 100),
    })
    try {
      const wrapper = await mountInAppShell({ visible: false })
      await wrapper.setProps({ visible: true })
      await flushPromises()
      const line = document.querySelector('.print-label .label-name') as HTMLElement
      expect(line.style.fontSize).not.toBe('')

      const a4Btn = [...document.querySelectorAll<HTMLButtonElement>('.paper-switch button')].find(b => b.textContent === 'A4 三列')!
      a4Btn.click()
      await flushPromises()
      expect(document.querySelector('.modal-content')!.classList.contains('paper-a4')).toBe(true)
      document.querySelectorAll<HTMLElement>('.print-label .fit').forEach(el => {
        expect(el.style.fontSize).toBe('')
      })
      wrapper.unmount()
    } finally {
      gcSpy.mockRestore()
      Object.defineProperty(swProto, 'scrollWidth', origSW)
      Object.defineProperty(cwProto, 'clientWidth', origCW)
    }
  })

  it('switchPaper 源码契约：await nextTick 先于 fitLabelLines', () => {
    expect(dialogSource).toMatch(/async function switchPaper[\s\S]*?await nextTick\(\)\s*\n\s*fitLabelLines\(\)/)
  })

  it('弹窗三段式布局与打印态复位（源码契约）：仅内容区滚动，打印恢复块级文档流', () => {
    expect(dialogSource).toMatch(/\.modal-content \{[^}]*display:\s*flex;\s*flex-direction:\s*column;/s)
    expect(dialogSource).toMatch(/\.modal-header \{[^}]*flex-shrink:\s*0;/s)
    expect(dialogSource).toMatch(/\.modal-footer \{[^}]*flex-shrink:\s*0;/s)
    expect(dialogSource).toMatch(/\.modal-body \{[^}]*flex:\s*1;[^}]*overflow-y:\s*auto;/s)
    expect(dialogSource).toMatch(/@media print[\s\S]*?\.modal-content \{[^}]*display:\s*block;/s)
    expect(dialogSource).toMatch(/@media print[\s\S]*?\.modal-body \{[^}]*overflow:\s*visible;/s)
  })

  it('A4 三列成品纸版式（源码契约）：三列 63.8×38、列距 3、边距 15.5/6、打印态行距 0；60×40 通道不受影响', () => {
    expect(dialogSource).toMatch(/@page \{ size: A4; margin: 15\.5mm 6mm; \}/)
    expect(dialogSource).toMatch(/grid-template-columns:\s*repeat\(3,\s*63\.8mm\)/)
    expect(dialogSource).toMatch(/\.paper-a4 \.print-labels \{[^}]*column-gap:\s*3mm;/s)
    expect(dialogSource).toMatch(/\.paper-a4 \.print-label \{[^}]*width:\s*63\.8mm;[^}]*height:\s*38mm;/s)
    expect(dialogSource).toMatch(/@media print[\s\S]*?\.paper-a4 \.print-labels \{[^}]*row-gap:\s*0;/s)
    /* 预览与打印行距同为 0（成品纸贴格，所见即所得）——基础规则不得引入 row-gap */
    const a4LabelsRule = dialogSource.match(/\.paper-a4 \.print-labels \{[^}]*\}/s)![0]
    expect(a4LabelsRule).not.toContain('row-gap')
    expect(dialogSource).toMatch(/@page \{ size: 60mm 40mm; margin: 0; \}/)
    expect(dialogSource).toMatch(/\.paper-60x40 \.print-label \{[^}]*width:\s*60mm;[^}]*height:\s*40mm;/s)
    expect(dialogSource).not.toContain('18mm')
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

  async function mountDialog(assetsArg: Array<Record<string, any>> = assets) {
    appShell = document.createElement('div')
    appShell.id = 'app'
    document.body.appendChild(appShell)
    const wrapper = mount(AssetPrintDialog, {
      props: { visible: true, assets: assetsArg },
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

  it('导出图片失败：停留导出视图、展示失败提示并 console.error，重试后恢复', async () => {
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    renderLabelDataUrlMock.mockRejectedValue(new Error('canvas broken'))
    const wrapper = await mountDialog()
    const exportBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '导出图片')!
    await exportBtn.click()
    await flushPromises()

    expect(document.querySelector('.export-view')).toBeTruthy()
    const errBox = document.querySelector('.export-error')!
    expect(errBox.textContent).toContain('渲染失败')
    expect(errSpy).toHaveBeenCalled()

    renderLabelDataUrlMock.mockResolvedValue('data:image/png;base64,retry')
    const retryBtn = [...document.querySelectorAll<HTMLButtonElement>('.export-error button')]
      .find(b => b.textContent === '重试')!
    await retryBtn.click()
    await flushPromises()
    expect(document.querySelector('.export-error')).toBeNull()
    expect(document.querySelectorAll('.export-item img')).toHaveLength(2)
    errSpy.mockRestore()
    wrapper.unmount()
  })

  it('导出列表以实例 id 为键：两个空内部编号实例文件名相同也不冲突', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const unnamed = [
      { id: 'fa-x1', 内部编号: '', 序列号: '', 资产名称: '未编号设备', 分公司: '', 供应商: '', 采购日期: '' },
      { id: 'fa-x2', 内部编号: '', 序列号: '', 资产名称: '未编号设备', 分公司: '', 供应商: '', 采购日期: '' },
    ]
    const wrapper = await mountDialog(unnamed)
    const exportBtn = [...document.querySelectorAll<HTMLButtonElement>('.modal-footer button')]
      .find(b => b.textContent === '导出图片')!
    await exportBtn.click()
    await flushPromises()
    expect(document.querySelectorAll('.export-item img')).toHaveLength(2)
    expect(warnSpy.mock.calls.some(c => String(c[0]).includes('Duplicate keys'))).toBe(false)
    warnSpy.mockRestore()
    wrapper.unmount()
  })
})
