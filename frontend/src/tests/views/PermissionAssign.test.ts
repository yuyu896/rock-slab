import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import PermissionAssign from '@/views/admin/PermissionAssign.vue'

const api = vi.hoisted(() => ({
  getUsers: vi.fn(),
  getRegions: vi.fn(),
  getBranches: vi.fn(),
  getTeams: vi.fn(),
  getOperationCatalog: vi.fn(),
  getEffectivePermissions: vi.fn(),
  getUserAuthorization: vi.fn(),
  saveUserAuthorization: vi.fn(),
  getPositionBaselinePreview: vi.fn(),
  applyPositionBaseline: vi.fn(),
}))

const ui = vi.hoisted(() => ({
  confirm: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}))

vi.mock('@/api/users', () => ({ getUsers: api.getUsers }))
vi.mock('@/api/regions', () => ({ getRegions: api.getRegions }))
vi.mock('@/api/branches', () => ({ getBranches: api.getBranches }))
vi.mock('@/api/teams', () => ({ getTeams: api.getTeams }))
vi.mock('@/api/permissions', () => ({
  getOperationCatalog: api.getOperationCatalog,
  getEffectivePermissions: api.getEffectivePermissions,
  getUserAuthorization: api.getUserAuthorization,
  saveUserAuthorization: api.saveUserAuthorization,
  getPositionBaselinePreview: api.getPositionBaselinePreview,
  applyPositionBaseline: api.applyPositionBaseline,
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: ui.success, error: ui.error },
  ElMessageBox: { confirm: ui.confirm },
}))

const InputStub = defineComponent({
  props: { modelValue: { type: [String, Number], default: '' }, type: { type: String, default: 'text' } },
  emits: ['update:modelValue'],
  setup(_, { emit }) {
    const onInput = (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).value)
    return { onInput }
  },
  template: '<textarea v-if="type === \'textarea\'" :value="modelValue" @input="onInput" /><input v-else :value="modelValue" @input="onInput" />',
})

const SelectStub = defineComponent({
  props: { modelValue: { type: [String, Array], default: '' }, multiple: Boolean },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const onChange = (event: Event) => {
      const select = event.target as HTMLSelectElement
      emit('update:modelValue', props.multiple
        ? Array.from(select.selectedOptions).map(option => option.value)
        : select.value)
    }
    return { onChange }
  },
  template: '<select :multiple="multiple" :value="modelValue" @change="onChange"><slot /></select>',
})

const OptionStub = defineComponent({
  props: { value: { type: [String, Number], default: '' }, label: String },
  template: '<option :value="value">{{ label }}</option>',
})

const TreeSelectStub = defineComponent({
  props: {
    modelValue: { type: Array as () => string[], default: () => [] },
    data: { type: Array as () => any[], default: () => [] },
    props: { type: Object, default: () => ({}) },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const valueKey = (props.props.value as string) || 'value'
    const labelKey = (props.props.label as string) || 'label'
    const childrenKey = (props.props.children as string) || 'children'
    const flatten = (nodes: any[]): any[] => nodes.flatMap(node => [node, ...flatten(node[childrenKey] || [])])
    const onChange = (event: Event) => {
      emit('update:modelValue', Array.from((event.target as HTMLSelectElement).selectedOptions).map(option => option.value))
    }
    return { flatten, valueKey, labelKey, onChange }
  },
  template: '<select multiple :value="modelValue" @change="onChange"><option v-for="node in flatten(data)" :key="node[valueKey]" :value="node[valueKey]">{{ node[labelKey] }}</option></select>',
})

const ButtonStub = defineComponent({
  props: { disabled: Boolean, loading: Boolean },
  emits: ['click'],
  template: '<button :disabled="disabled || loading" @click="$emit(\'click\', $event)"><slot /></button>',
})

const DialogStub = defineComponent({
  props: { modelValue: Boolean, title: String },
  template: '<section v-if="modelValue" role="dialog"><h2>{{ title }}</h2><slot /><slot name="footer" /></section>',
})

const AlertStub = defineComponent({
  template: '<div role="status"><slot /></div>',
})

function authorization(userId: string, operations: string[] = [], mode: 'default' | 'custom' | 'all' = 'default') {
  const users: Record<string, any> = {
    'manager-a': { id: 'manager-a', name: '员工甲', phone: '100', role: 'manager', status: 'active', region: 'r1', branch: 'b1', region_name: '华东', branch_name: '上海分公司' },
    'manager-b': { id: 'manager-b', name: '员工乙', phone: '101', role: 'manager', status: 'active', region: 'r1', branch: 'b1', region_name: '华东', branch_name: '上海分公司' },
    admin: { id: 'admin', name: '系统管理员', phone: '102', role: 'admin', status: 'active', region: null, branch: null, region_name: null, branch_name: null },
  }
  return {
    user: users[userId],
    scope: { mode, nodes: mode === 'custom' ? [{ id: 'r1', type: 'region', name: '华东' }] : [] },
    operations,
  }
}

async function mountPage() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: PermissionAssign },
      { path: '/other', component: defineComponent({ template: '<div />' }) },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(defineComponent({ template: '<router-view />' }), {
    global: {
      plugins: [router],
      stubs: {
        ElInput: InputStub,
        ElSelect: SelectStub,
        ElOption: OptionStub,
        ElTreeSelect: TreeSelectStub,
        ElButton: ButtonStub,
        ElDialog: DialogStub,
        ElAlert: AlertStub,
      },
    },
  })
  return { wrapper, router }
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getUsers.mockResolvedValue({ data: [
    { id: 'manager-a', name: '员工甲', phone: '100', role: 'manager', status: 'active', branch: 'b1', branchName: '上海分公司' },
    { id: 'manager-b', name: '员工乙', phone: '101', role: 'leader', status: 'inactive', branch: 'b2', branchName: '杭州分公司' },
    { id: 'admin', name: '系统管理员', phone: '102', role: 'admin', status: 'active' },
  ] })
  api.getOperationCatalog.mockResolvedValue({ data: [
    { code: 'view_purchase', label: '查看采购入库', module: 'purchase', module_label: '采购入库' },
    { code: 'create_purchase', label: '创建采购入库', module: 'purchase', module_label: '采购入库' },
  ] })
  api.getEffectivePermissions.mockResolvedValue({ data: [
    { user: 'manager-a', operations: ['view_purchase'], legacy_operations: [] },
    { user: 'manager-b', operations: [], legacy_operations: [] },
    { user: 'admin', operations: null, legacy_operations: [] },
  ] })
  api.getRegions.mockResolvedValue({ data: [{ id: 'r1', name: '华东' }, { id: 'r2', name: '华南' }] })
  api.getBranches.mockResolvedValue({ data: [
    { id: 'b1', name: '上海分公司', region: 'r1', team: 't1' },
    { id: 'b2', name: '杭州分公司', region: 'r2' },
  ] })
  api.getTeams.mockResolvedValue({ data: [{ id: 't1', name: '行政组一', region: 'r1' }] })
  api.getUserAuthorization.mockImplementation((id: string) => Promise.resolve({ data: authorization(id) }))
  api.saveUserAuthorization.mockResolvedValue({ data: {} })
  api.getPositionBaselinePreview.mockResolvedValue({ data: {
    fromVersion: null,
    toVersion: 'v1',
    hasChanges: true,
    activeEmployeeCount: 2,
    changedEmployeeCount: 1,
    addedPermissionCount: 1,
    removedPermissionCount: 0,
    legacyPermissionCount: 1,
    inactiveEmployeeCount: 1,
    roleChanges: [{ role: 'leader', roleLabel: '行政组长', added: [{ code: 'view_dashboard', label: '查看工作台' }], removed: [] }],
    employees: [{
      user: 'manager-a', name: '员工甲', phone: '100', role: 'manager', roleLabel: '分公司行政',
      branchName: '上海分公司', added: [{ code: 'view_dashboard', label: '查看工作台' }],
      removed: [], legacyCodes: ['old_permission'], scopePreserved: true,
    }],
    previewToken: 'preview-token',
  } })
  api.applyPositionBaseline.mockResolvedValue({ data: {
    detail: '岗位权限基线已确认并应用', version: 'v1', synchronized_users: 2,
    added_permission_count: 1, removed_permission_count: 0, legacy_permission_count_retained_for_review: 1,
  } })
  ui.confirm.mockResolvedValue('confirm')
})

describe('PermissionAssign', () => {
  it('展示逐员工岗位基线差异并要求预览后确认应用', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('员工权限按实际生效结果显示')
    await wrapper.get('header button').trigger('click')
    await flushPromises()

    expect(api.getPositionBaselinePreview).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('岗位权限基线核对')
    expect(wrapper.text()).toContain('员工甲')
    expect(wrapper.text()).toContain('查看工作台')
    expect(wrapper.text()).toContain('old_permission')

    await wrapper.findAll('button').find(button => button.text().includes('确认应用基线'))?.trigger('click')
    await flushPromises()

    expect(api.applyPositionBaseline).toHaveBeenCalledWith({
      expected_from_version: null,
      preview_token: 'preview-token',
    })
    expect(api.getPositionBaselinePreview).toHaveBeenCalledTimes(2)
    expect(ui.success).toHaveBeenCalledWith('岗位权限基线已确认并应用')
    wrapper.unmount()
  })

  it('目录缺少模块字段时按稳定权限码展示模块名', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'view_purchase', label: '查看采购入库单', module: 'purchase', module_label: '其他权限' },
      { code: 'view_assignment', label: '查看领用出库单' },
      { code: 'manage_assets', label: '管理资产' },
    ] })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.module-heading h4').map(heading => heading.text())).toEqual(['采购入库', '领用出库', '资产管理'])
    expect(wrapper.text()).not.toContain('其他权限')
    wrapper.unmount()
  })

  it('回收权限不再单独列出处置，旧授权显示人工核对说明', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'create_recovery', label: '创建回收单', module: 'recovery', module_label: '回收' },
      { code: 'approve_recovery', label: '审批回收单', module: 'recovery', module_label: '回收', description: '审批重新入库和直接处置的回收单。' },
    ] })
    api.getUserAuthorization.mockResolvedValue({ data: {
      ...authorization('manager-a'),
      legacyOperations: ['dispose_assets'],
      legacyOperationDetails: [{ code: 'dispose_assets', label: '处置回收物资（旧权限，需人工核对）' }],
    } })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()

    const activeLabels = wrapper.findAll('.operation-option strong').map(label => label.text())
    expect(activeLabels).toContain('审批回收单')
    expect(activeLabels).not.toContain('处置回收物资')
    expect(wrapper.find('.legacy-option').text()).toContain('处置回收物资（旧权限，需人工核对）')
    expect(wrapper.find('.legacy-option').text()).toContain('不会自动转成回收单权限')
    wrapper.unmount()
  })

  it('实例管理旧权限显示历史范围且不自动勾选新权限', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'view_instances', label: '查看实例档案', module: 'instances', module_label: '实例档案' },
      { code: 'edit_instances', label: '编辑实例档案', module: 'instances', module_label: '实例档案' },
      { code: 'change_instance_assignee', label: '更换使用人和部门', module: 'instances', module_label: '实例档案' },
      { code: 'print_instance_label', label: '打印实例标签', module: 'instances', module_label: '实例档案' },
    ] })
    api.getUserAuthorization.mockResolvedValue({ data: {
      ...authorization('manager-a'),
      legacyOperations: ['manage_instances'],
      legacyOperationDetails: [{ code: 'manage_instances', label: '管理固定资产实例（旧权限）' }],
    } })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('.legacy-option').text()).toContain('实例资料和图片维护')
    expect(wrapper.find('.legacy-option').text()).toContain('直接更换使用人和部门')
    expect(wrapper.find('.legacy-option').text()).toContain('不会自动变成新目录的查看、编辑、换人或打印权限')
    expect(wrapper.findAll('.operation-option input:checked')).toHaveLength(0)
    wrapper.unmount()
  })

  it('旧台账调整权限说明其历史能力且不自动勾选导入或手工调整', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'import_asset_ledger', label: '导入资产台账', module: 'asset_ledger', module_label: '资产台账' },
      { code: 'adjust_asset_ledger', label: '调整资产台账', module: 'asset_ledger', module_label: '资产台账' },
    ] })
    api.getUserAuthorization.mockResolvedValue({ data: {
      ...authorization('manager-a'),
      legacyOperations: ['adjust_ledger'],
      legacyOperationDetails: [{ code: 'adjust_ledger', label: '台账调整单（旧权限）' }],
    } })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('.legacy-option').text()).toContain('手工创建台账调整单')
    expect(wrapper.find('.legacy-option').text()).toContain('历史台账导入流程也接受该权限')
    expect(wrapper.find('.legacy-option').text()).toContain('不会自动变成“导入资产台账”或“调整资产台账”')
    expect(wrapper.findAll('.operation-option input:checked')).toHaveLength(0)
    wrapper.unmount()
  })

  it('按组织、岗位、账号状态和业务授权状态筛选员工', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()

    expect(wrapper.find('.page-links').exists()).toBe(false)
    expect((wrapper.find('.people-filters').element as HTMLElement).style.display).toBe('none')
    await wrapper.find('.filter-toggle').trigger('click')
    expect((wrapper.find('.people-filters').element as HTMLElement).style.display).not.toBe('none')

    await wrapper.find('[aria-label="按大区筛选"]').setValue('r2')
    await wrapper.find('[aria-label="按分公司筛选"]').setValue('b2')
    await wrapper.find('[aria-label="按岗位筛选"]').setValue('leader')
    await wrapper.find('[aria-label="按账号状态筛选"]').setValue('inactive')
    await wrapper.find('[aria-label="按授权状态筛选"]').setValue('none')

    expect(wrapper.findAll('.person-row')).toHaveLength(1)
    expect(wrapper.find('.filter-count').text()).toBe('5')
    const row = wrapper.find('.person-row')
    expect(row.find('.person-name').text()).toBe('员工乙')
    expect(row.find('.person-branch').text()).toBe('杭州分公司')
    expect(row.text()).not.toContain('101')
    expect(row.text()).not.toContain('未授予业务权限')

    await row.trigger('click')
    await flushPromises()
    expect(wrapper.find('.employee-meta').text()).toContain('101')
    expect(wrapper.find('.authorization-label').text()).toBe('未授予业务权限')
    wrapper.unmount()
  })

  it('筛选面板默认收起，手机号搜索生效且重置筛选保留搜索词', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()

    expect((wrapper.find('.people-filters').element as HTMLElement).style.display).toBe('none')
    await wrapper.find('.filter-toggle').trigger('click')
    await wrapper.find('[aria-label="搜索员工"]').setValue('101')
    await wrapper.find('[aria-label="按大区筛选"]').setValue('r2')

    expect(wrapper.findAll('.person-row')).toHaveLength(1)
    expect(wrapper.find('.person-name').text()).toBe('员工乙')
    expect(wrapper.find('.filter-count').text()).toBe('1')

    await wrapper.find('.filter-reset').trigger('click')

    expect(wrapper.find('.filter-count').exists()).toBe(false)
    expect(wrapper.findAll('.person-row')).toHaveLength(1)
    expect(wrapper.find('.person-name').text()).toBe('员工乙')
    wrapper.unmount()
  })

  it('有未保存草稿时阻止刷新或关闭页面', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    await wrapper.findAll('.operation-option input[type="checkbox"]')[0].setValue(true)

    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    wrapper.unmount()
  })

  it('路由离开时保存草稿后再继续导航', async () => {
    const { wrapper, router } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    await wrapper.findAll('.operation-option input[type="checkbox"]')[0].setValue(true)

    await router.push('/other')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/other')
    expect(api.saveUserAuthorization).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('路由离开时选择关闭确认框会留在页面并保留草稿', async () => {
    ui.confirm.mockRejectedValue('close')
    const { wrapper, router } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    await wrapper.findAll('.operation-option input[type="checkbox"]')[0].setValue(true)

    await router.push('/other')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/')
    expect(api.saveUserAuthorization).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('未保存')
    wrapper.unmount()
  })

  it('系统管理员显示内置全权且不能逐项修改', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[2].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('系统管理员自动拥有全部业务权限和全组织数据范围')
    const checkboxes = wrapper.findAll('.operation-option input[type="checkbox"]')
    expect(checkboxes).toHaveLength(2)
    expect((checkboxes[0].element as HTMLInputElement).checked).toBe(true)
    expect((checkboxes[0].element as HTMLInputElement).disabled).toBe(true)
    expect(wrapper.find('.editor-actions').exists()).toBe(false)
    wrapper.unmount()
  })

  it('按组织树选择数据范围并显示授权模块摘要', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'view_purchase', label: '查看采购入库', module: 'purchase', module_label: '采购入库' },
      { code: 'view_assignment', label: '查看领用出库', module: 'assignment', module_label: '领用出库' },
    ] })
    api.getUserAuthorization.mockResolvedValue({ data: authorization('manager-a', ['view_purchase']) })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    await wrapper.find('input[type="radio"][value="custom"]').setValue()

    expect(wrapper.text()).toContain('1 个已授权模块')
    expect(wrapper.findComponent(TreeSelectStub).props('data')).toEqual(expect.arrayContaining([
      expect.objectContaining({
        key: 'region:r1',
        children: [expect.objectContaining({
          key: 'team:t1',
          children: [expect.objectContaining({ key: 'branch:b1', label: '上海分公司' })],
        })],
      }),
    ]))
    wrapper.unmount()
  })

  it('按目录模块显示快速定位按钮并滚动到对应权限分组', async () => {
    api.getOperationCatalog.mockResolvedValue({ data: [
      { code: 'view_purchase', label: '查看采购入库', module: 'purchase', module_label: '采购入库' },
      { code: 'create_purchase', label: '创建采购入库', module: 'purchase', module_label: '采购入库' },
      { code: 'view_assignment', label: '查看领用出库', module: 'assignment', module_label: '领用出库' },
    ] })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    document.body.appendChild(wrapper.element)

    const quickNav = wrapper.find('[aria-label="权限模块快速定位"]')
    expect(quickNav.findAll('button').map(button => button.text())).toEqual(['采购入库', '领用出库'])
    const target = wrapper.get('#permission-module-assignment').element as HTMLElement
    const scrollIntoView = vi.fn()
    Object.defineProperty(target, 'scrollIntoView', { value: scrollIntoView })

    await quickNav.findAll('button')[1].trigger('click')

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
    wrapper.unmount()
    wrapper.element.remove()
  })

  it('把范围、权限與可选原因通过单个请求统一保存', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()

    await wrapper.findAll('.operation-option input[type="checkbox"]')[1].setValue(true)
    await wrapper.find('input[type="radio"][value="custom"]').setValue()
    await wrapper.find('select[multiple]').setValue(['region:r1'])
    await wrapper.find('.reason-field textarea').setValue('分公司职责调整')
    expect(wrapper.text()).toContain('待保存变更')

    await wrapper.find('.editor-actions button:last-child').trigger('click')
    await flushPromises()

    expect(api.saveUserAuthorization).toHaveBeenCalledTimes(1)
    expect(api.saveUserAuthorization).toHaveBeenCalledWith('manager-a', {
      operations: ['create_purchase'],
      scope: { mode: 'custom', nodes: [{ id: 'r1', type: 'region', name: '华东' }] },
      reason: '分公司职责调整',
    })
    wrapper.unmount()
  })

  it('自定义范围至少选择一个组织节点才能保存', async () => {
    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    await wrapper.find('input[type="radio"][value="custom"]').setValue()

    expect(wrapper.text()).toContain('自定义范围至少选择一个组织节点')
    expect((wrapper.find('.editor-actions button:last-child').element as HTMLButtonElement).disabled).toBe(true)
    expect(api.saveUserAuthorization).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('普通保存保留未选中的旧权限', async () => {
    api.getUserAuthorization.mockResolvedValue({
      data: { ...authorization('manager-a'), legacyOperations: ['old_manage_assets'] },
    })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('1 项旧权限')
    expect(wrapper.text()).toContain('未登记的旧权限')
    expect(wrapper.text()).not.toContain('old_manage_assets')

    await wrapper.findAll('.operation-option input[type="checkbox"]')[0].setValue(true)
    await wrapper.find('.editor-actions button:last-child').trigger('click')
    await flushPromises()

    expect(api.saveUserAuthorization.mock.calls[0][1]).not.toHaveProperty('remove_legacy_operations')
    expect(wrapper.text()).toContain('1 项旧权限')
    expect(wrapper.text()).not.toContain('old_manage_assets')
    wrapper.unmount()
  })

  it('逐项勾选撤销旧权限并在预览与保存请求中列出', async () => {
    api.getUserAuthorization.mockResolvedValue({
      data: { ...authorization('manager-a'), legacyOperations: ['old_manage_assets'] },
    })
    api.saveUserAuthorization.mockRejectedValue({
      isAxiosError: true,
      response: { status: 400, data: { detail: '旧权限码已变化' } },
    })

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await flushPromises()
    await wrapper.findAll('.operation-option input[type="checkbox"]')[0].setValue(true)
    await wrapper.find('.legacy-option input[type="checkbox"]').setValue(true)
    expect(wrapper.text()).toContain('撤销旧权限')

    await wrapper.find('.editor-actions button:last-child').trigger('click')
    await flushPromises()

    expect(api.saveUserAuthorization).toHaveBeenCalledWith('manager-a', expect.objectContaining({
      operations: ['view_purchase'],
      remove_legacy_operations: ['old_manage_assets'],
    }))
    expect(ui.error).toHaveBeenCalledWith('旧权限码已变化')
    expect((wrapper.find('.operation-option input[type="checkbox"]').element as HTMLInputElement).checked).toBe(true)
    expect(wrapper.text()).toContain('未保存')
    wrapper.unmount()
  })

  it('快速切换员工时忽略迟到的授权响应', async () => {
    let resolveFirst!: (value: { data: ReturnType<typeof authorization> }) => void
    api.getUserAuthorization.mockImplementation((id: string) => id === 'manager-a'
      ? new Promise(resolve => { resolveFirst = resolve })
      : Promise.resolve({ data: authorization(id) }))

    const { wrapper } = await mountPage()
    await flushPromises()
    await wrapper.findAll('.person-row')[0].trigger('click')
    await wrapper.findAll('.person-row')[1].trigger('click')
    await flushPromises()
    resolveFirst({ data: authorization('manager-a', ['view_purchase']) })
    await flushPromises()

    expect(wrapper.findAll('.person-row')[1].classes()).toContain('selected')
    expect((wrapper.find('.operation-option input[type="checkbox"]').element as HTMLInputElement).checked).toBe(false)
    wrapper.unmount()
  })
})
