import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import PermissionMatrix from '@/views/admin/PermissionMatrix.vue'

const api = vi.hoisted(() => ({
  getEffectivePermissions: vi.fn(),
  getOperationCatalog: vi.fn(),
  getPermissionMatrixOrganizations: vi.fn(),
}))

const message = vi.hoisted(() => ({ error: vi.fn() }))

vi.mock('@/api/permissions', () => ({
  getEffectivePermissions: api.getEffectivePermissions,
  getOperationCatalog: api.getOperationCatalog,
  getPermissionMatrixOrganizations: api.getPermissionMatrixOrganizations,
}))
vi.mock('element-plus', () => ({ ElMessage: message }))

const InputStub = defineComponent({
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue', 'keyup', 'clear'],
  setup(_, { emit }) {
    const onInput = (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).value)
    return { onInput, emit }
  },
  template: '<input :value="modelValue" @input="onInput" @keyup.enter="$emit(\'keyup\', $event)" />',
})

const SelectStub = defineComponent({
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue', 'change'],
  setup(_, { emit }) {
    const onChange = (event: Event) => {
      const value = (event.target as HTMLSelectElement).value
      emit('update:modelValue', value)
      emit('change', value)
    }
    return { onChange }
  },
  template: '<select :value="modelValue" @change="onChange"><option value="">全部</option><slot /></select>',
})

const OptionStub = defineComponent({
  props: { value: { type: String, default: '' }, label: String },
  template: '<option :value="value">{{ label }}</option>',
})

const ButtonStub = defineComponent({
  emits: ['click'],
  template: '<button @click="$emit(\'click\', $event)"><slot /></button>',
})

const rows = [
  {
    user: 'user-1', name: '李四', phone: '100', role: 'manager', region: 'r1', branch: 'b1', region_name: '华东', branch_name: '上海分公司',
    scope: { mode: 'custom' as const, nodes: [{ id: 'r1', type: 'region' as const, name: '华东' }] },
    operations: ['view_purchase', 'create_purchase'], legacy_operations: ['old_purchase_role'],
  },
  {
    user: 'admin', name: '系统管理员', phone: '101', role: 'admin', region_name: null, branch_name: null,
    scope: { mode: 'all' as const, nodes: [] }, operations: null,
  },
]

function mountPage() {
  return mount(PermissionMatrix, {
    global: {
      stubs: {
        ElInput: InputStub,
        ElSelect: SelectStub,
        ElOption: OptionStub,
        ElButton: ButtonStub,
      },
    },
  })
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getOperationCatalog.mockResolvedValue({ data: [
    { code: 'view_purchase', label: '查看采购入库', module: 'purchase', module_label: '采购入库' },
    { code: 'create_purchase', label: '创建采购入库', module: 'purchase', module_label: '采购入库' },
  ] })
  api.getPermissionMatrixOrganizations.mockResolvedValue({ data: {
    regions: [{ id: 'r1', name: '华东' }, { id: 'r2', name: '华南' }],
    branches: [
      { id: 'b1', name: '上海分公司', region: 'r1' },
      { id: 'b2', name: '广州分公司', region: 'r2' },
    ],
  } })
  api.getEffectivePermissions.mockResolvedValue({ data: rows })
})

describe('PermissionMatrix', () => {
  it('展示员工当前实际权限和范围，系统管理员标记为内置全权', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('.page-links').exists()).toBe(false)
    expect(wrapper.text()).toContain('查看采购入库、创建采购入库')
    expect(wrapper.text()).toContain('华东')
    expect(wrapper.text()).toContain('1 项旧权限待迁移')
    expect(wrapper.text()).toContain('全部业务权限')
    expect(wrapper.findAll('select')[0].find('option[value="r1"]').exists()).toBe(true)
    expect(wrapper.findAll('select')[1].find('option[value="b1"]').exists()).toBe(true)
    expect(api.getEffectivePermissions).toHaveBeenCalledWith({})
    wrapper.unmount()
  })

  it('组织筛选选项来自组织目录，即使组织暂无员工也能筛选', async () => {
    api.getEffectivePermissions.mockResolvedValue({ data: [] })
    const wrapper = mountPage()
    await flushPromises()

    const selects = wrapper.findAll('select')
    expect(selects[0].find('option[value="r2"]').exists()).toBe(true)
    expect(selects[1].find('option[value="b2"]').exists()).toBe(true)
    expect(api.getPermissionMatrixOrganizations).toHaveBeenCalledOnce()
    wrapper.unmount()
  })

  it('模块筛选和操作筛选显示简体中文名称且不出现 undefined', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'view_purchase', label: '查看采购入库', module: 'purchase', module_label: 'purchase' },
      { code: 'create_purchase', label: '创建采购入库', module: 'purchase' },
    ] })
    const wrapper = mountPage()
    await flushPromises()

    const selects = wrapper.findAll('select')
    expect(selects[2].text()).toContain('采购入库')
    expect(selects[2].text()).not.toContain('purchase')
    expect(selects[3].text()).toContain('采购入库 · 查看采购入库')
    expect(selects[3].text()).not.toContain('undefined')
    expect(wrapper.text()).not.toContain('undefined')
    wrapper.unmount()
  })

  it('提交姓名、组织、模块与操作筛选条件', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('.filter-bar input').setValue('李四')
    await wrapper.find('.filter-bar button').trigger('click')
    await flushPromises()

    expect(api.getEffectivePermissions).toHaveBeenLastCalledWith({
      keyword: '李四', region: undefined, branch: undefined, module: undefined, operation: undefined,
    })
    wrapper.unmount()
  })
})
