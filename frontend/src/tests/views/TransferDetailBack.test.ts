import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import TransferDetailLayout from '@/views/transfers/components/TransferDetailLayout.vue'

const props = {
  title: '采购入库详情',
  backPath: '/transfers/purchase',
  doc: null,
  type: 'purchase' as const,
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/transfers/purchase', component: { template: '<div />' } },
    ],
  })
}

describe('单据详情返回保留列表筛选（query 持久化配套）', () => {
  it('有来路（history.state.back）时返回走 router.back，回到带 query 的列表', async () => {
    const router = makeRouter()
    await router.push('/transfers/purchase')
    await router.isReady()
    const backSpy = vi.spyOn(router, 'back').mockImplementation(() => {})
    window.history.replaceState({ back: '/transfers/purchase?status=pending' }, '')
    const wrapper = mount(TransferDetailLayout, { props, global: { plugins: [router] } })
    await wrapper.find('.back-btn').trigger('click')
    expect(backSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
    backSpy.mockRestore()
    window.history.replaceState(null, '')
  })

  it('直达详情无来路时回退 push(backPath)', async () => {
    const router = makeRouter()
    await router.push('/')
    await router.isReady()
    const pushSpy = vi.spyOn(router, 'push').mockResolvedValue(undefined as never)
    window.history.replaceState({}, '')
    const wrapper = mount(TransferDetailLayout, { props, global: { plugins: [router] } })
    await wrapper.find('.back-btn').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/transfers/purchase')
    wrapper.unmount()
    pushSpy.mockRestore()
    window.history.replaceState(null, '')
  })
})
