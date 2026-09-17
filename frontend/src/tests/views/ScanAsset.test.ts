import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

vi.mock('jsqr', () => ({ default: vi.fn() }))

const routeQuery = ref<Record<string, string>>({})
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery.value }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/assets', () => ({
  getAssetStocks: vi.fn(),
  getFixedAssets: vi.fn(),
}))

vi.mock('@/api/inventories', () => ({
  getInventoryTasks: vi.fn(),
  getInventoryReport: vi.fn(),
  checkInventoryInstance: vi.fn(),
}))

import { ref } from 'vue'
import ScanAsset from '@/views/mobile/ScanAsset.vue'
import { getAssetStocks, getFixedAssets } from '@/api/assets'
import { checkInventoryInstance, getInventoryReport, getInventoryTasks } from '@/api/inventories'
import { ElMessage } from 'element-plus'

const items = [
  { instance: 'i-1', instanceCode: 'A-a00008-BJ001-1', serialNumber: 'SN1', assetName: '笔记本电脑', holder: '张三', result: 'pending' },
  { instance: 'i-2', instanceCode: 'A-a00008-BJ001-2', serialNumber: 'SN2', assetName: '笔记本电脑', holder: '', result: 'pending' },
]

async function mountScanner() {
  const wrapper = mount(ScanAsset)
  await flushPromises()
  return wrapper
}

describe('ScanAsset 统一扫码器', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeQuery.value = {}
    vi.mocked(getInventoryTasks).mockResolvedValue({
      data: { results: [{ id: 't-1', name: '年度盘点', inventoryKind: 'instance' }] },
    } as any)
    vi.mocked(getInventoryReport).mockResolvedValue({ data: { items } } as any)
    vi.mocked(getAssetStocks).mockResolvedValue({ data: { results: [] } } as any)
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { results: [{ id: 'fa-1', 内部编号: 'A-a00008-BJ001-1', itemName: '笔记本电脑', 当前状态: '在用', 使用人: '张三', branchName: '北京分公司' }] },
    } as any)
  })

  it('默认查询模式；有进行中实例盘任务时露出盘点开关', async () => {
    const wrapper = await mountScanner()
    expect(wrapper.find('.mode-btn.active').text()).toBe('查询')
    expect(wrapper.findAll('.mode-btn').map(b => b.text())).toEqual(['查询', '盘点'])
    wrapper.unmount()
  })

  it('未点开始扫码时摄像头不启动（无 video 流、有开始按钮）', async () => {
    const wrapper = await mountScanner()
    expect(wrapper.find('.start-btn').exists()).toBe(true)
    expect(wrapper.find('video').attributes('srcobject')).toBeUndefined()
    wrapper.unmount()
  })

  it('查询模式：手输回车出资产卡片', async () => {
    const wrapper = await mountScanner()
    const input = wrapper.find('.manual-input')
    await input.setValue('A-a00008-BJ001-1')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    const card = wrapper.find('.asset-card')
    expect(card.exists()).toBe(true)
    expect(card.text()).toContain('A-a00008-BJ001-1')
    expect(card.text()).toContain('笔记本电脑')
    expect(card.text()).toContain('北京分公司')
    wrapper.unmount()
  })

  it('盘点模式：清单内打钩、重复不重交、清单外警告', async () => {
    const wrapper = await mountScanner()
    await wrapper.findAll('.mode-btn').find(b => b.text() === '盘点')!.trigger('click')
    await flushPromises()
    // 只有一个任务时点击盘点自动锁定
    expect(wrapper.find('.inv-progress').exists()).toBe(true)

    const input = wrapper.find('.manual-input')
    await input.setValue('A-a00008-BJ001-1')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(checkInventoryInstance).toHaveBeenCalledWith('t-1', { instanceId: 'i-1', found: true })
    expect(wrapper.find('.flow-item.ok').text()).toContain('A-a00008-BJ001-1')

    // 重复扫
    await input.setValue('A-a00008-BJ001-1')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(checkInventoryInstance).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.flow-item.dup').exists()).toBe(true)

    // 清单外
    await input.setValue('NOT-IN-LIST')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(checkInventoryInstance).toHaveBeenCalledTimes(1)
    expect(ElMessage.warning).toHaveBeenCalled()
    expect(wrapper.find('.flow-item.unknown').exists()).toBe(true)
    wrapper.unmount()
  })

  it('?task= 直达锁定盘点模式', async () => {
    routeQuery.value = { task: 't-1' }
    const wrapper = await mountScanner()
    await flushPromises()
    expect(wrapper.find('.mode-btn.active').text()).toBe('盘点')
    expect(wrapper.find('.inv-name').text()).toBe('年度盘点')
    wrapper.unmount()
  })
})
