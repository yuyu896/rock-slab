import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MobileLayout from '@/layouts/MobileLayout.vue'

const state = vi.hoisted(() => ({
  pages: {} as Record<string, boolean>,
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/mobile/scan' }),
  useRouter: () => ({ push: state.push }),
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    canAccessPage: (page: string) => state.pages[page] === true,
  }),
}))

describe('MobileLayout permission navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    state.pages = {}
  })

  it('shows only tabs allowed by the backend page directory', () => {
    state.pages = { mobile_scan: true, mobile_approvals: true }

    const wrapper = mount(MobileLayout, {
      global: { stubs: { RouterView: true } },
    })

    expect(wrapper.findAll('.tab-label').map(label => label.text())).toEqual(['扫码', '审批', '我的'])
    wrapper.unmount()
  })

  it('shows the inventory tab only when its page key is allowed', async () => {
    state.pages = { mobile_inventory: true }
    const wrapper = mount(MobileLayout, {
      global: { stubs: { RouterView: true } },
    })

    const inventoryTab = wrapper.findAll('.tab-item').find(tab => tab.text().includes('盘点任务'))
    expect(inventoryTab).toBeDefined()
    await inventoryTab!.trigger('click')
    expect(state.push).toHaveBeenCalledWith('/mobile/inventory')
    wrapper.unmount()
  })
})
