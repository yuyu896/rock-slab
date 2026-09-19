import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { taskId: 't-1' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/inventories', () => ({
  getInventoryTask: vi.fn(),
  getInventoryProgress: vi.fn(),
  checkInventoryItem: vi.fn(),
  checkInventoryInstance: vi.fn(),
  getInventoryChecks: vi.fn(),
  getInventoryReport: vi.fn(),
  submitInventory: vi.fn(),
}))

vi.mock('@/api/assets', () => ({ getAssetStocks: vi.fn() }))

import MobileScan from '@/views/MobileScan.vue'
import { getInventoryTask, getInventoryProgress, getInventoryReport } from '@/api/inventories'

function mockTask(kind: string) {
  vi.mocked(getInventoryTask).mockResolvedValue({
    data: { id: 't-1', name: '测试任务', branch: '北京分公司', inventoryKind: kind },
  } as any)
  vi.mocked(getInventoryProgress).mockResolvedValue({
    data: { totalItems: 10, checkedItems: 3, surplusCount: 0, missingCount: 0 },
  } as any)
  vi.mocked(getInventoryReport).mockResolvedValue({ data: { items: [] } } as any)
}

async function mountPage() {
  const wrapper = mount(MobileScan)
  await flushPromises()
  return wrapper
}

describe('MobileScan 扫码入口按任务类型条件渲染', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('数量盘任务：无摄像头按钮、无不支持提示，编号输入定位保留', async () => {
    mockTask('stock')
    const wrapper = await mountPage()
    expect(wrapper.find('.camera-toggle-btn').exists()).toBe(false)
    expect(wrapper.find('.camera-not-supported').exists()).toBe(false)
    expect(wrapper.find('.scan-input').exists()).toBe(true)
    wrapper.unmount()
  })

  it('实例盘任务（旧路由深链）：摄像头按钮保留，不支持提示照常显示（测试环境无 BarcodeDetector）', async () => {
    mockTask('instance')
    const wrapper = await mountPage()
    expect(wrapper.find('.camera-toggle-btn').exists()).toBe(true)
    expect(wrapper.find('.camera-not-supported').exists()).toBe(true)
    wrapper.unmount()
  })
})
