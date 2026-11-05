import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
  ElSelect: { name: 'ElSelect', props: ['modelValue', 'filterable', 'clearable', 'placeholder'], emits: ['update:modelValue', 'clear'], template: '<div class="el-select-stub" />' },
  ElOption: { name: 'ElOption', props: ['value', 'label'], template: '<div class="el-option-stub" />' },
}))

const api = vi.hoisted(() => ({
  getTransfers: vi.fn().mockResolvedValue({ data: { count: 0, results: [] } }),
  exportTransfers: vi.fn(),
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
  generateTransferTemplate: vi.fn(),
}))
vi.mock('@/api/transfers', () => ({
  getTransfers: api.getTransfers,
  exportTransfers: api.exportTransfers,
}))
vi.mock('@/api/branches', () => ({ getBranches: api.getBranches }))
vi.mock('@/utils/importTemplate', () => ({ generateTransferTemplate: api.generateTransferTemplate }))

const permissionCodes = vi.hoisted(() => ({ codes: null as string[] | null }))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    can: (code: string) => permissionCodes.codes === null || permissionCodes.codes.includes(code),
  }),
}))

import PurchaseList from '@/views/transfers/PurchaseList.vue'

beforeEach(() => {
  vi.clearAllMocks()
  permissionCodes.codes = null
  api.getTransfers.mockResolvedValue({ data: { count: 0, results: [] } })
  api.getBranches.mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] })
})

describe('PurchaseList 入库分公司筛选', () => {
  it('选中分公司后请求携带 toBranch（入库分公司口径）', async () => {
    const wrapper = mount(PurchaseList, {
      global: {
        stubs: {
          BranchFilterSelect: {
            name: 'BranchFilterSelect',
            props: ['modelValue', 'options', 'allLabel'],
            emits: ['update:modelValue'],
            template: '<button class="stub-branch" @click="$emit(\'update:modelValue\', [\'北京分公司\'])" />',
          },
        },
      },
    })
    await flushPromises()
    await wrapper.find('.stub-branch').trigger('click')
    await flushPromises()

    const calls = api.getTransfers.mock.calls
    const lastCall = calls[calls.length - 1]?.[0] as Record<string, unknown>
    expect(lastCall.toBranch).toBe('北京分公司')
  })
})

describe('PurchaseList 编辑权限', () => {
  it('编辑权限满足查看前置时开放单据列表和批量导入', async () => {
    permissionCodes.codes = ['edit_purchase', 'view_purchase', 'view_categories']
    const wrapper = mount(PurchaseList)
    await flushPromises()

    expect(api.getTransfers).toHaveBeenCalled()
    expect(api.getBranches).toHaveBeenCalled()
    expect(wrapper.find('table').exists()).toBe(true)
    const importButton = wrapper.findAll('button').find(button => button.text().includes('批量导入'))
    expect(importButton).toBeDefined()

    await importButton!.trigger('click')
    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
    const templateButton = wrapper.findAll('button').find(button => button.text().includes('下载模板'))
    expect(templateButton).toBeDefined()
    await templateButton!.trigger('click')
    expect(api.generateTransferTemplate).toHaveBeenCalledWith(expect.any(String), 'purchase')
  })

  it('缺少采购单查看权时仅凭编辑和品目查看权不加载列表或显示写操作', async () => {
    permissionCodes.codes = ['edit_purchase', 'view_categories']
    const wrapper = mount(PurchaseList)
    await flushPromises()

    expect(api.getTransfers).not.toHaveBeenCalled()
    expect(api.getBranches).not.toHaveBeenCalled()
    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.findAll('button').some(button => button.text().includes('批量导入'))).toBe(false)
    expect(wrapper.findAll('button').some(button => button.text().includes('新建入库'))).toBe(false)
  })

  it('缺少品目查看权时不提供新建或批量导入入口', async () => {
    permissionCodes.codes = ['edit_purchase', 'view_purchase']
    const wrapper = mount(PurchaseList)
    await flushPromises()

    expect(api.getTransfers).toHaveBeenCalled()
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.findAll('button').some(button => button.text().includes('批量导入'))).toBe(false)
    expect(wrapper.findAll('button').some(button => button.text().includes('新建入库'))).toBe(false)
  })
})

describe('PurchaseList 直渲服务端序（排序已下沉后端）', () => {
  it('行序与接口返回序一致，前端不再重排', async () => {
    api.getTransfers.mockResolvedValue({
      data: {
        count: 3, next: null, previous: null,
        results: [
          { id: 'a', 审批状态: '待审批', 调入分公司: 'A公司', 调拨日期: '2026-09-14', lines: [] } as any,
          { id: 'b', 审批状态: '已入库', 调入分公司: 'Z公司', 调拨日期: '2026-09-01', lines: [] } as any,
          { id: 'c', 审批状态: '草稿', 调入分公司: 'B公司', 调拨日期: '2026-09-13', lines: [] } as any,
        ],
      },
    } as any)
    const wrapper = mount(PurchaseList, {
      global: { stubs: { BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    const codes = wrapper.findAll('tbody tr .doc-number').map(n => n.text())
    expect(codes).toEqual(['a', 'b', 'c'])
  })
})
