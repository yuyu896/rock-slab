import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }), useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { name: '张三' } }) }))
vi.mock('@/api/transfers', () => ({
  transferAsset: vi.fn().mockResolvedValue({ data: { id: 't-1' } }),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [
    { id: 'b-1', name: '北京分公司' },
    { id: 'b-2', name: '上海分公司' },
  ] }),
}))
vi.mock('@/api/users', () => ({
  getUsers: vi.fn().mockResolvedValue({ data: [
    { id: 'u-1', name: '员工甲' }, { id: 'u-2', name: '员工乙' },
  ] }),
}))

import TransferCreate from '@/views/transfers/TransferCreate.vue'
import { transferAsset } from '@/api/transfers'
import { getUsers } from '@/api/users'

const validDrafts = [{
  key: 1, item: { id: 'item-1' }, 数量: 2, 本批规格: '', 行供应商: '',
  单价: null, 金额: null, 使用人: '', department: null, 存放位置: '', instances: [],
}]

const editorStub = {
  name: 'TransferLinesEditor',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  methods: { validate: () => true },
  template: `<button class="stub-editor" @click="$emit('update:modelValue', drafts)" />`,
  data: () => ({ drafts: validDrafts }),
}

function mountPage() {
  return mount(TransferCreate, {
    global: { stubs: { TransferLinesEditor: editorStub as any, DepartmentSelect: { template: '<div />' } } },
  })
}

/** selects.form-select 顺序：0=调出分公司 1=调入分公司 2=调入负责人 */
function selects(wrapper: any) {
  return wrapper.findAll('select.form-select')
}

async function fillAndSubmit(wrapper: any) {
  await wrapper.find('input[type="date"]').setValue('2026-09-23')
  const s = selects(wrapper)
  await s.at(0)!.setValue('b-1')
  await s.at(1)!.setValue('b-2')
  await flushPromises()
  await wrapper.find('.stub-editor').trigger('click')
  await wrapper.findAll('button').find((b: any) => b.text() === '确定提交')!.trigger('click')
  await flushPromises()
}

describe('transfer-responsible-unify：调出负责人退役', () => {
  beforeEach(() => vi.clearAllMocks())

  it('页面无调出负责人字段，提交 payload 不携带', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).not.toContain('调出负责人')
    await fillAndSubmit(wrapper)
    expect(transferAsset).toHaveBeenCalledTimes(1)
    const payload = vi.mocked(transferAsset).mock.calls[0][0] as Record<string, unknown>
    expect('调出负责人' in payload).toBe(false)
  })
})

describe('transfer-responsible-unify：调入负责人按调入分公司员工纯下拉', () => {
  beforeEach(() => vi.clearAllMocks())

  it('未选调入分公司时下拉禁用', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(selects(wrapper).at(2)!.attributes('disabled')).toBeDefined()
  })

  it('选定调入分公司后拉取该公司员工为选项', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const s = selects(wrapper)
    await s.at(0)!.setValue('b-1')
    await s.at(1)!.setValue('b-2')
    await flushPromises()
    expect(getUsers).toHaveBeenCalledWith(expect.objectContaining({ branch: 'b-2' }))
    const options = selects(wrapper).at(2)!.findAll('option')
    expect(options.map((o: any) => o.text())).toContain('员工甲')
    expect(options.map((o: any) => o.text())).toContain('员工乙')
    expect(selects(wrapper).at(2)!.attributes('disabled')).toBeUndefined()
  })

  it('切换调入分公司清空已选并重拉员工', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const s = selects(wrapper)
    await s.at(0)!.setValue('b-1')
    await s.at(1)!.setValue('b-2')
    await flushPromises()
    await s.at(2)!.setValue('员工甲')
    expect((s.at(2)!.element as HTMLSelectElement).value).toBe('员工甲')

    await s.at(1)!.setValue('b-1')
    await flushPromises()
    expect((s.at(2)!.element as HTMLSelectElement).value).toBe('')
    expect(getUsers).toHaveBeenCalledTimes(2)
  })

  it('选定调入负责人提交，payload 携带姓名快照与经办人', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('input[type="date"]').setValue('2026-09-23')
    const s = selects(wrapper)
    await s.at(0)!.setValue('b-1')
    await s.at(1)!.setValue('b-2')
    await flushPromises()
    await s.at(2)!.setValue('员工乙')
    await wrapper.find('.stub-editor').trigger('click')
    await wrapper.findAll('button').find((b: any) => b.text() === '确定提交')!.trigger('click')
    await flushPromises()
    const payload = vi.mocked(transferAsset).mock.calls[0][0] as Record<string, unknown>
    expect(payload.调入负责人).toBe('员工乙')
    expect(payload.经办人).toBe('张三')
  })
})
