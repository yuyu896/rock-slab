import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const state = vi.hoisted(() => ({
  getFixedAssets: vi.fn(),
  requestGet: vi.fn(),
}))

vi.mock('@/api/assets', () => ({ getFixedAssets: state.getFixedAssets }))
vi.mock('@/utils/request', () => ({ default: { get: state.requestGet } }))

import InstancePicker from '@/components/InstancePicker.vue'

function mountPicker(type: string) {
  return mount(InstancePicker, {
    props: {
      itemCode: 'IT-001',
      type,
      status: '在库',
      branchName: '测试分公司',
      modelValue: [],
    },
  })
}

describe('InstancePicker permission context', () => {
  beforeEach(() => {
    state.getFixedAssets.mockReset().mockResolvedValue({
      data: { results: [], next: null },
    })
    state.requestGet.mockReset().mockResolvedValue({ data: [] })
  })

  it('sends the document type with the occupancy request', async () => {
    const wrapper = mountPicker('assign')

    await wrapper.find('.picker-toggle').trigger('click')
    await flushPromises()

    expect(state.requestGet).toHaveBeenCalledWith(
      '/api/transfers/instance-occupancy',
      { params: { branch: '测试分公司', asset_code: 'IT-001', type: 'assign' } },
    )
  })
})
