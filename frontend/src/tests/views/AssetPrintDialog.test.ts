import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('jsbarcode', () => ({ default: vi.fn() }))

import AssetPrintDialog from '@/views/assets/AssetPrintDialog.vue'
import dialogSource from '@/views/assets/AssetPrintDialog.vue?raw'

const assets = [
  { id: 'fa-1', 资产编号: 'NB-001', 资产名称: 'ThinkPad T14', 分公司: '杭州分公司' },
  { id: 'fa-2', 资产编号: 'NB-002', 资产名称: '戴尔 U2723 显示器', 分公司: '宁波分公司' },
]

let appShell: HTMLDivElement

function mountInAppShell() {
  appShell = document.createElement('div')
  appShell.id = 'app'
  document.body.appendChild(appShell)
  return mount(AssetPrintDialog, {
    props: { visible: true, assets },
    attachTo: appShell,
  })
}

describe('AssetPrintDialog 打印输出隔离', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('标签区 Teleport 到 body，位于 #app 应用壳之外（打印时 #app 整体隐藏）', () => {
    const wrapper = mountInAppShell()
    const printArea = document.getElementById('print-area')
    expect(printArea).toBeTruthy()
    expect(appShell.contains(printArea!)).toBe(false)
    wrapper.unmount()
  })

  it('渲染与资产等量的标签及编号/名称/分公司文案', () => {
    const wrapper = mountInAppShell()
    const labels = document.querySelectorAll('.print-label')
    expect(labels).toHaveLength(2)
    expect(labels[0].querySelector('.label-code')!.textContent).toBe('NB-001')
    expect(labels[0].querySelector('.label-name')!.textContent).toBe('ThinkPad T14')
    expect(labels[0].querySelector('.label-branch')!.textContent).toBe('杭州分公司')
    wrapper.unmount()
  })

  it('「打印」按钮触发 window.print', async () => {
    const printSpy = vi.fn()
    vi.stubGlobal('print', printSpy)
    const wrapper = mountInAppShell()
    const btn = [...document.querySelectorAll('button')].find(b => b.textContent === '打印')!
    btn.click()
    await Promise.resolve()
    expect(printSpy).toHaveBeenCalled()
    wrapper.unmount()
    vi.unstubAllGlobals()
  })

  it('打印样式约定：Teleport 挂 body、标签防跨页切断、@media print 隐藏 #app（源码断言）', () => {
    expect(dialogSource).toMatch(/<Teleport to="body">/)
    expect(dialogSource).toMatch(/break-inside:\s*avoid/)
    expect(dialogSource).toMatch(/@media print\s*\{[^}]*#app\s*\{\s*display:\s*none/)
  })
})
