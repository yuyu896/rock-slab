import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BasePagination from '@/components/BasePagination.vue'

const ElPaginationStub = {
  name: 'ElPagination',
  props: ['total', 'currentPage', 'pageSize', 'pageSizes', 'layout', 'background'],
  template: '<div class="el-pagination-stub" />',
}

function mountPagination(props: Record<string, unknown> = {}) {
  return mount(BasePagination, {
    props: { total: 120, currentPage: 1, ...props },
    global: { stubs: { ElPagination: ElPaginationStub } },
  })
}

describe('BasePagination 共享分页组件', () => {
  it('未显式传入 pageSize 时默认每页 50 条', () => {
    const wrapper = mountPagination()
    const el = wrapper.findComponent(ElPaginationStub)
    expect(el.props('pageSize')).toBe(50)
    expect(el.props('pageSizes')).toEqual([10, 20, 50, 100])
  })

  it('显式传入 pageSize 时以传入值为准', () => {
    const wrapper = mountPagination({ pageSize: 20 })
    expect(wrapper.findComponent(ElPaginationStub).props('pageSize')).toBe(20)
  })
})
