import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/api/inventories', () => ({
  getInventoryTasks: vi.fn().mockResolvedValue({ data: { count: 0 } }),
}))

vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn(),
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({ isAdmin: false }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/dashboard' }),
  useRouter: () => ({ push: vi.fn() }),
}))

import SidebarNav from '@/components/layout/SidebarNav.vue'
import { getFixedAssets } from '@/api/assets'

function mountNav() {
  const wrapper = mount(SidebarNav, { props: { isCollapsed: false } })
  return wrapper
}

function findInstanceItem(wrapper: ReturnType<typeof mountNav>) {
  return wrapper.findAll('.nav-submenu-item').find(a => a.text().includes('实例档案'))
}

describe('SidebarNav 实例档案待补录徽标（P3 刀三）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('有待补录时子项显示计数徽标，请求带 pending_serial=1', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 5, next: null, previous: null, results: [] },
    } as any)
    const wrapper = mountNav()
    await flushPromises()

    expect(getFixedAssets).toHaveBeenCalledWith(
      expect.objectContaining({ pending_serial: '1', pageSize: 1 }),
    )
    const item = findInstanceItem(wrapper)!
    const badge = item.find('.nav-badge')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('5')
  })

  it('无待补录不显示徽标', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 0, next: null, previous: null, results: [] },
    } as any)
    const wrapper = mountNav()
    await flushPromises()

    expect(findInstanceItem(wrapper)!.find('.nav-badge').exists()).toBe(false)
  })

  it('接口失败静默按 0 处理，导航不受影响', async () => {
    vi.mocked(getFixedAssets).mockRejectedValue(new Error('network'))
    const wrapper = mountNav()
    await flushPromises()

    expect(findInstanceItem(wrapper)).toBeTruthy()
    expect(findInstanceItem(wrapper)!.find('.nav-badge').exists()).toBe(false)
  })
})
