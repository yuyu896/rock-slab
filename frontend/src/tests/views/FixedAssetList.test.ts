import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
  ElSelect: { name: 'ElSelect', props: ['modelValue', 'filterable', 'clearable', 'placeholder'], emits: ['update:modelValue', 'clear'], template: '<div class="el-select-stub" />' },
  ElOption: { name: 'ElOption', props: ['value', 'label'], template: '<div class="el-option-stub" />' },
}))

const mockCan = vi.fn((_code?: string) => true)
vi.mock('@/hooks/usePermission', () => ({
  usePermission: () => ({ can: mockCan }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn(),
  getFixedAssetAssigneeTargets: vi.fn(),
  getFixedAssetEditTargets: vi.fn(),
  exportFixedAssets: vi.fn(),
  supplementFixedAsset: vi.fn(),
  getFixedAssetTimeline: vi.fn(),
  changeFixedAssetAssignee: vi.fn(),
  uploadFixedAssetImage: vi.fn(),
  deleteFixedAssetImage: vi.fn(),
  batchUpdateFixedAssets: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))
vi.mock('@/api/departments', () => ({
  getDepartmentOptions: vi.fn().mockResolvedValue({
    data: [
      { id: 'd1', name: '行政部' },
      { id: 'd2', name: '技术部' },
    ],
  }),
  getAssigneeDepartmentOptions: vi.fn().mockResolvedValue({
    data: [
      { id: 'd1', name: '行政部' },
      { id: 'd2', name: '技术部' },
    ],
  }),
}))
vi.mock('@/api/suppliers', () => ({
  getInstanceSupplierOptions: vi.fn().mockResolvedValue({
    data: [
      { id: 's1', name: '小熊U租' },
      { id: 's2', name: '易点云' },
    ],
  }),
}))

import FixedAssetList from '@/views/FixedAssetList.vue'
import fixedAssetListSource from '@/views/FixedAssetList.vue?raw'
import { getFixedAssets, getFixedAssetAssigneeTargets, getFixedAssetEditTargets, uploadFixedAssetImage, changeFixedAssetAssignee, getFixedAssetTimeline, supplementFixedAsset, batchUpdateFixedAssets } from '@/api/assets'
import { getAssigneeDepartmentOptions } from '@/api/departments'
import { getInstanceSupplierOptions } from '@/api/suppliers'
import type { FixedAsset } from '@/types'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function _inst(overrides: Partial<FixedAsset>): FixedAsset {
  return {
    id: 'fa-1',
    内部编号: 'NB-001-1',
    序列号: '',
    当前状态: '在库',
    item: 'i1',
    itemCode: 'NB-001',
    itemName: 'ThinkPad T14',
    createdAt: '',
    updatedAt: '',
    ...overrides,
  }
}

const stubs = {
  BasePagination: { template: '<div />' },
  StatusBadge: { props: ['status'], template: '<span>{{ status }}</span>' },
  AssetPrintDialog: { props: ['assets', 'visible'], template: '<div class="print-stub">{{ assets.length }}-{{ visible }}</div>' },
  'el-dialog': { props: ['modelValue', 'title', 'width'], template: `<div v-if="modelValue" class="el-dialog" :data-width="width"><div class="dlg-title">{{ title }}</div><slot /><slot name="footer" /></div>` },
  'el-drawer': { props: ['modelValue'], template: '<div><slot /></div>' },
  'el-image': {
    props: ['src', 'previewSrcList', 'lazy'],
    template: '<img class="el-image-stub" :src="src" :data-preview-src="previewSrcList?.[0]" :loading="lazy ? \'lazy\' : \'eager\'" />',
  },
  'el-form': { template: '<div><slot /></div>' },
  'el-form-item': { props: ['label'], template: '<div><span v-if="label">{{ label }}</span><slot /></div>' },
  'el-input': { props: ['modelValue'], emits: ['update:modelValue'], template: `<input class="el-input-stub" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />` },
  'el-date-picker': { name: 'ElDatePicker', props: ['modelValue'], emits: ['update:modelValue'], template: `<input class="el-date-picker-stub" :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />` },
  'el-select': { name: 'ElSelect', props: ['modelValue', 'placeholder'], emits: ['update:modelValue', 'clear'], template: `<div class="el-select-stub" :data-ph="placeholder" />` },
  'el-option': { name: 'ElOption', props: ['value', 'label'], template: '<div class="el-option-stub" />' },
  'el-button': { template: '<button><slot /></button>' },
}

async function _mount() {
  const wrapper = mount(FixedAssetList, { global: { stubs } })
  await flushPromises()
  return wrapper
}

describe('FixedAssetList 物品图片', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCan.mockReturnValue(true)
  })

  it('图片列置于序号列后', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({ 图片: '/media/fixed_assets/a.jpg' })] },
    } as any)
    const wrapper = await _mount()
    const headers = wrapper.findAll('.data-table thead th').map(th => th.text())
    expect(headers[0]).toBe('') // 勾选列
    expect(headers[1]).toBe('序号')
    expect(headers[2]).toBe('图片')
  })

  it('上传前将大于 1MB 的图片压缩为 WebP，并拒绝超过 10MB 的文件', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    vi.mocked(uploadFixedAssetImage).mockResolvedValue({ data: _inst({ 图片: '/media/new.jpg' }) } as any)
    const wrapper = await _mount()
    await wrapper.findAll('.action-btn').find(b => b.attributes('title') === '编辑')!.trigger('click')

    const canvas = {
      width: 0,
      height: 0,
      getContext: vi.fn(() => ({ drawImage: vi.fn() })),
      toBlob: vi.fn((callback: BlobCallback, type?: string) => callback(new Blob(['compressed'], { type }))),
    }
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue({ width: 1600, height: 1200, close: vi.fn() }))
    const createElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation(((tagName: string, options?: ElementCreationOptions) => {
      if (tagName === 'canvas') return canvas as unknown as HTMLCanvasElement
      return createElement(tagName, options)
    }) as typeof document.createElement)

    const input = wrapper.find('input[type=file]')
    const allowedFile = new File([new Uint8Array(3 * 1024 * 1024)], 'phone-photo.jpg', { type: 'image/jpeg' })
    Object.defineProperty(input.element, 'files', { value: [allowedFile], configurable: true })
    await input.trigger('change')
    await flushPromises()
    expect(canvas.toBlob).toHaveBeenCalledWith(expect.any(Function), 'image/webp', 0.82)
    expect(uploadFixedAssetImage).toHaveBeenCalledWith('fa-1', expect.objectContaining({ type: 'image/webp', name: 'phone-photo.webp' }))

    const rejectedFile = new File([new Uint8Array(11 * 1024 * 1024)], 'large-photo.jpg', { type: 'image/jpeg' })
    Object.defineProperty(input.element, 'files', { value: [rejectedFile], configurable: true })
    await input.trigger('change')
    expect(uploadFixedAssetImage).toHaveBeenCalledTimes(1)
    expect(ElMessage.error).toHaveBeenCalledWith('图片大小不能超过 10MB')
  })

  it('小于 1MB 但最长边超过 2048px 时压缩，压缩失败时阻止上传', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    vi.mocked(uploadFixedAssetImage).mockResolvedValue({ data: _inst({ 图片: '/media/new.webp' }) } as any)
    const wrapper = await _mount()
    await wrapper.findAll('.action-btn').find(b => b.attributes('title') === '编辑')!.trigger('click')
    const input = wrapper.find('input[type=file]')
    const canvas = {
      width: 0,
      height: 0,
      getContext: vi.fn(() => ({ drawImage: vi.fn() })),
      toBlob: vi.fn((callback: BlobCallback, type?: string) => callback(new Blob(['compressed'], { type }))),
    }
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue({ width: 3000, height: 2000, close: vi.fn() }))
    const createElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation(((tagName: string, options?: ElementCreationOptions) => {
      if (tagName === 'canvas') return canvas as unknown as HTMLCanvasElement
      return createElement(tagName, options)
    }) as typeof document.createElement)

    const smallFile = new File([new Uint8Array(512 * 1024)], 'wide.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [smallFile], configurable: true })
    await input.trigger('change')
    await flushPromises()
    expect(canvas.width).toBe(2048)
    expect(canvas.height).toBe(1365)
    expect(uploadFixedAssetImage).toHaveBeenCalledWith('fa-1', expect.objectContaining({ type: 'image/webp' }))

    vi.mocked(uploadFixedAssetImage).mockClear()
    vi.mocked(ElMessage.error).mockClear()
    vi.mocked(createImageBitmap).mockRejectedValueOnce(new Error('decode error'))
    const nextFile = new File([new Uint8Array(2 * 1024 * 1024)], 'broken.jpg', { type: 'image/jpeg' })
    Object.defineProperty(input.element, 'files', { value: [nextFile], configurable: true })
    await input.trigger('change')
    await flushPromises()
    expect(uploadFixedAssetImage).not.toHaveBeenCalled()
    expect(ElMessage.error).toHaveBeenCalledWith('无法读取图片，请重新选择文件')
  })

  it('小于 1MB 且最长边不超过 2048px 时保留原文件', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    vi.mocked(uploadFixedAssetImage).mockResolvedValue({ data: _inst({ 图片: '/media/new.jpg' }) } as any)
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue({ width: 1600, height: 1200, close: vi.fn() }))
    const wrapper = await _mount()
    await wrapper.findAll('.action-btn').find(b => b.attributes('title') === '编辑')!.trigger('click')

    const file = new File([new Uint8Array(512 * 1024)], 'small.jpg', { type: 'image/jpeg' })
    const input = wrapper.find('input[type=file]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(uploadFixedAssetImage).toHaveBeenCalledWith('fa-1', file)
  })

  it('勾选实例后批量打印标签（弹窗收多项）', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 2, results: [
        _inst({ id: 'fa-1', 图片: null }),
        _inst({ id: 'fa-2', 图片: null }),
      ] },
    } as any)
    const wrapper = await _mount()
    const checks = wrapper.findAll('tbody .check-col input[type=checkbox]')
    expect(checks).toHaveLength(2)
    await checks[0].setValue(true)
    await checks[1].setValue(true)
    const batchBtn = wrapper.findAll('button').find(b => b.text().includes('批量操作（2）'))
    expect(batchBtn).toBeTruthy()
    await batchBtn!.trigger('click')
    const printBtn = wrapper.find('.batch-menu').findAll('button').find(b => b.text() === '打印标签')
    expect(printBtn).toBeTruthy()
    await printBtn!.trigger('click')
    expect(wrapper.find('.print-stub').text()).toBe('2-true')
  })

  it('列表懒加载缩略图，预览使用主图；缺少缩略图时回退主图，无图显示占位', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 2, results: [
        _inst({ id: 'fa-1', 图片: '/media/fixed_assets/a.webp', 缩略图: '/media/fixed_assets/a-thumb.webp' }),
        _inst({ id: 'fa-2', 图片: '/media/fixed_assets/b.jpg', 缩略图: null }),
        _inst({ id: 'fa-3', 图片: null, 缩略图: null }),
      ] },
    } as any)
    const wrapper = await _mount()
    const rows = wrapper.findAll('.data-table tbody tr')
    expect(rows[0].find('.row-thumb').exists()).toBe(true)
    expect(rows[0].find('.row-thumb').attributes('src')).toBe('/media/fixed_assets/a-thumb.webp')
    expect(rows[0].find('.row-thumb').attributes('data-preview-src')).toBe('/media/fixed_assets/a.webp')
    expect(fixedAssetListSource).toMatch(/<el-image\s+v-if="item\.图片"[\s\S]*?:lazy="true"/)
    expect(rows[1].find('.row-thumb').attributes('src')).toBe('/media/fixed_assets/b.jpg')
    expect(rows[1].find('.row-thumb').attributes('data-preview-src')).toBe('/media/fixed_assets/b.jpg')
    expect(rows[2].find('.row-thumb').exists()).toBe(false)
    expect(rows[2].find('.thumb-empty').text()).toBe('—')
  })

  it('无实例编辑和打印权限时实例维护与交接入口不渲染', async () => {
    mockCan.mockImplementation((code?: string) => !['edit_instances', 'change_instance_assignee', 'print_instance_label'].includes(code || ''))
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    const wrapper = await _mount()
    const buttons = wrapper.findAll('.action-btn')
    // 无维护或打印授权时，维护和打印入口均不可见
    expect(buttons.filter(b => b.attributes('title') === '编辑').length).toBe(0)
    expect(buttons.filter(b => b.attributes('title') === '物品图片').length).toBe(0)
    expect(buttons.filter(b => b.attributes('title') === '补录序列号').length).toBe(0)
    expect(buttons.filter(b => b.attributes('title') === '生平').length).toBe(0)
    expect(buttons.filter(b => b.attributes('title') === '打印标签').length).toBe(0)
    expect(wrapper.find('.batch-wrap').exists()).toBe(false)
  })

  it('有档案查看和打印权限时显示单项和批量打印，不显示实例维护操作', async () => {
    mockCan.mockImplementation((code?: string) => ['view_instances', 'print_instance_label'].includes(code || ''))
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    const wrapper = await _mount()

    expect(wrapper.findAll('.action-btn').filter(b => b.attributes('title') === '打印标签')).toHaveLength(1)
    expect(wrapper.findAll('.action-btn').filter(b => b.attributes('title') === '编辑')).toHaveLength(0)
    await wrapper.find('tbody .check-col input[type=checkbox]').setValue(true)
    await wrapper.findAll('button').find(b => b.text().includes('批量操作'))!.trigger('click')
    const menu = wrapper.find('.batch-menu')
    expect(menu.findAll('button').map(button => button.text())).toEqual(['打印标签'])
    await menu.find('button').trigger('click')
    expect(wrapper.find('.print-stub').text()).toBe('1-true')
  })

  it('操作列单元格不得用 flex 破坏表格行布局（行分割线同高对齐）', () => {
    expect(fixedAssetListSource).toMatch(/\.action-col\s*\{[^}]*white-space:\s*nowrap/)
    expect(fixedAssetListSource).not.toMatch(/\.action-col\s*\{[^}]*display:\s*flex/)
  })

  it('编辑弹窗：上传图片即时生效，序列号/备注走补录接口，规格/供应商走 batch-update', async () => {
    const { batchUpdateFixedAssets, supplementFixedAsset } = await import('@/api/assets')
    vi.mocked(supplementFixedAsset).mockResolvedValue({ data: _inst({}) } as any)
    vi.mocked(batchUpdateFixedAssets).mockResolvedValue({
      data: { updated: 1, results: ['NB-001-1'], errors: [] },
    } as any)
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({ 图片: '/media/fixed_assets/fa-1/old.jpg?v=1' })] },
    } as any)
    vi.mocked(uploadFixedAssetImage).mockResolvedValue({
      data: _inst({ 图片: '/media/fixed_assets/fa-1/new.jpg?v=2' }),
    } as any)
    const wrapper = await _mount()
    const editBtn = wrapper.findAll('.action-btn').find(b => b.attributes('title') === '编辑')
    expect(editBtn).toBeTruthy()
    await editBtn!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('编辑实例')

    // 图片上传（编辑弹窗内隐藏 input）
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue({ width: 1600, height: 1200, close: vi.fn() }))
    const input = wrapper.find('input[type=file]')
    const file = new File([new Uint8Array(64)], 'photo.jpg', { type: 'image/jpeg' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()
    expect(uploadFixedAssetImage).toHaveBeenCalledWith('fa-1', file)
    expect(wrapper.findAll('.el-image-stub').map(image => image.attributes('src'))).toEqual([
      '/media/fixed_assets/fa-1/new.jpg?v=2',
      '/media/fixed_assets/fa-1/new.jpg?v=2',
    ])

    // 保存：序列号/备注经 supplement（可清空+查重），规格/供应商经 batch-update
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()
    expect(supplementFixedAsset).toHaveBeenCalledWith('fa-1', {
      序列号: expect.any(String),
      备注: expect.any(String),
    })
    expect(batchUpdateFixedAssets).toHaveBeenCalledWith(expect.objectContaining({
      ids: ['fa-1'],
      规格: expect.any(String),
      供应商: expect.any(String),
    }))
    expect(vi.mocked(batchUpdateFixedAssets).mock.calls[0][0]).not.toHaveProperty('序列号列表')
  })
})

describe('实例批量操作', () => {
  it('勾选后批量菜单保留维护操作，供应商弹窗提交 batch-update', async () => {
    const { batchUpdateFixedAssets } = await import('@/api/assets')
    vi.mocked(batchUpdateFixedAssets).mockResolvedValue({
      data: { updated: 2, results: ['A-1', 'A-2'], errors: [] },
    } as any)
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 2, results: [
        _inst({ id: 'fa-1', 图片: null }), _inst({ id: 'fa-2', 图片: null }),
      ] },
    } as any)
    const wrapper = await _mount()
    const checks = wrapper.findAll('tbody .check-col input[type=checkbox]')
    await checks[0].setValue(true)
    await checks[1].setValue(true)
    const batchBtn = wrapper.findAll('button').find(b => b.text().includes('批量操作（2）'))
    expect(batchBtn).toBeTruthy()
    await batchBtn!.trigger('click')
    const menu = wrapper.find('.batch-menu')
    expect(menu.exists()).toBe(true)
    expect(menu.text()).toContain('修改供应商')
    expect(menu.text()).toContain('补录序列号')

    await menu.findAll('button').find(b => b.text() === '修改供应商')!.trigger('click')
    expect(wrapper.find('.el-dialog').exists() || wrapper.text()).toBeTruthy()
    // 供应商已收口为字典下拉：经 ElSelect 桩 emit 选中值
    const selectStub = wrapper.findAllComponents({ name: 'ElSelect' })
      .find(c => c.props('placeholder') === '统一设置的供应商')
    expect(selectStub).toBeTruthy()
    await selectStub!.vm.$emit('update:modelValue', '小熊U租')
    await wrapper.findAll('button').find(b => b.text().includes('应用（2 台）'))!.trigger('click')
    await flushPromises()
    expect(batchUpdateFixedAssets).toHaveBeenCalledWith(
      expect.objectContaining({ ids: ['fa-1', 'fa-2'], 供应商: '小熊U租' }),
    )
  })
})

describe('实例更换使用人', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCan.mockReturnValue(true)
    vi.mocked(getFixedAssetTimeline).mockResolvedValue({
      data: { instance: _inst({ 当前状态: '在用' }), birth: null, timeline: [] },
    } as any)
    vi.mocked(getAssigneeDepartmentOptions).mockResolvedValue({
      data: [
        { id: 'd1', name: '行政部' },
        { id: 'd2', name: '技术部' },
      ],
    } as any)
    vi.mocked(supplementFixedAsset).mockResolvedValue({ data: _inst({}) } as any)
    vi.mocked(batchUpdateFixedAssets).mockResolvedValue({
      data: { updated: 1, results: [], errors: [] },
    } as any)
  })

  async function openEditDialog(asset: FixedAsset = _inst({ 当前状态: '在用', 使用人: '张三', department: 'd1', departmentName: '行政部' })) {
    vi.mocked(getFixedAssets).mockResolvedValue({ data: { count: 1, results: [asset] } } as any)
    const wrapper = await _mount()
    await wrapper.findAll('.action-btn').find(button => button.attributes('title') === '编辑')!.trigger('click')
    await flushPromises()
    return wrapper
  }

  async function fillAssigneeForm(wrapper: ReturnType<typeof mount>, name = '李四', department = 'd2', reason = '') {
    await wrapper.find('input[placeholder="请输入使用人姓名"]').setValue(name)
    if (reason) await wrapper.find('input[placeholder="填写交接原因"]').setValue(reason)
    const select = wrapper.findAllComponents({ name: 'ElSelect' })
      .find(component => component.props('placeholder') === '请选择部门')
    await select!.vm.$emit('update:modelValue', department)
  }

  it('点击编辑页保存后更新档案和使用人部门，无需额外确认按钮', async () => {
    const original = _inst({ id: 'fa-1', 内部编号: 'NB-001-1', 当前状态: '在用', 使用人: '张三', department: 'd1', departmentName: '行政部' })
    const updated = _inst({ ...original, 使用人: '李四', department: 'd2', departmentName: '技术部' })
    vi.mocked(changeFixedAssetAssignee).mockResolvedValue({ data: { asset: updated, changed: true } } as any)
    vi.mocked(getFixedAssetTimeline).mockResolvedValueOnce({
      data: { instance: original, birth: null, timeline: [] },
    } as any)
    const wrapper = await openEditDialog(original)
    expect(getAssigneeDepartmentOptions).toHaveBeenCalledOnce()
    expect(getFixedAssetTimeline).toHaveBeenCalledOnce()
    expect(wrapper.find('.timeline-pane').exists()).toBe(true)
    expect(wrapper.find('.timeline-table tbody .empty-cell').text()).toBe('暂无流转记录')
    expect(wrapper.find('.assignee-section input[placeholder="请输入使用人姓名"]').exists()).toBe(true)
    expect(wrapper.find('.assignee-section .el-select-stub[data-ph="请选择部门"]').exists()).toBe(true)
    expect(wrapper.findAll('button').some(button => button.text() === '确认更换使用人')).toBe(false)
    await fillAssigneeForm(wrapper, '李四', 'd2', '岗位调整')

    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(ElMessageBox.confirm).not.toHaveBeenCalled()
    expect(supplementFixedAsset).toHaveBeenCalledWith('fa-1', { 序列号: '', 备注: '' })
    expect(batchUpdateFixedAssets).toHaveBeenCalledOnce()
    expect(changeFixedAssetAssignee).toHaveBeenCalledWith('fa-1', {
      使用人: '李四',
      department: 'd2',
      原因: '岗位调整',
    })
    expect(wrapper.text()).toContain('李四')
    expect(wrapper.text()).toContain('技术部')
    expect(wrapper.findAll('.data-table tbody tr')[0].text()).toContain('李四')
    expect(wrapper.find('.asset-edit-dialog').exists()).toBe(false)
    expect(getFixedAssetTimeline).toHaveBeenCalledOnce()
  })

  it('姓名为空或部门不属于完整部门字典时不提交', async () => {
    const wrapper = await openEditDialog()
    await fillAssigneeForm(wrapper, '  ', 'd2')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    expect(ElMessage.warning).toHaveBeenCalledWith('请输入使用人姓名')

    await fillAssigneeForm(wrapper, '李四', 'unknown')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    expect(ElMessage.warning).toHaveBeenCalledWith('请选择有效部门')
    expect(changeFixedAssetAssignee).not.toHaveBeenCalled()
    expect(supplementFixedAsset).not.toHaveBeenCalled()
  })

  it('非在用实例显示使用人和部门不可变更说明，且不能提交交接', async () => {
    const wrapper = await openEditDialog(_inst({
      id: 'fa-2', 内部编号: 'NB-001-2', 当前状态: '在库', 使用人: '张三', departmentName: '行政部',
    }))
    expect(wrapper.find('.assignee-readonly-hint').exists()).toBe(true)
    expect(wrapper.text()).toContain('仅在用实例可更换使用人和部门')
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('行政部')
    expect(wrapper.find('input[placeholder="请输入使用人姓名"]').exists()).toBe(false)
    expect(wrapper.findAll('button').some(button => button.text() === '确认更换使用人')).toBe(false)
    expect(getAssigneeDepartmentOptions).not.toHaveBeenCalled()
    expect(changeFixedAssetAssignee).not.toHaveBeenCalled()
  })

  it('没有使用人变更时，保存其他档案字段不会调用交接接口', async () => {
    const wrapper = await openEditDialog()
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(changeFixedAssetAssignee).not.toHaveBeenCalled()
    expect(wrapper.find('.asset-edit-dialog').exists()).toBe(false)
  })

  it('有档案编辑权限但无更换使用人权限时，使用人和部门只读且保存不调用交接接口', async () => {
    mockCan.mockImplementation((code?: string) => ['view_instances', 'edit_instances'].includes(code || ''))
    const wrapper = await openEditDialog()

    expect(wrapper.find('input[placeholder="请输入使用人姓名"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('当前账号没有更换使用人和部门权限')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(changeFixedAssetAssignee).not.toHaveBeenCalled()
  })

  it('只有换人权限时可进入换人表单，保存不调用档案维护接口', async () => {
    mockCan.mockImplementation((code?: string) => ['view_instances', 'change_instance_assignee'].includes(code || ''))
    const original = _inst({ 当前状态: '在用', 使用人: '张三', department: 'd1', departmentName: '行政部' })
    const updated = _inst({ ...original, 使用人: '李四', department: 'd2', departmentName: '技术部' })
    vi.mocked(changeFixedAssetAssignee).mockResolvedValue({ data: { asset: updated, changed: true } } as any)
    const wrapper = await openEditDialog(original)

    expect(wrapper.find('.action-col button[title="编辑"]').exists()).toBe(true)
    expect(wrapper.find('input[placeholder="扫码或手工录入；清空=回到待补录"]').exists()).toBe(false)
    await fillAssigneeForm(wrapper, '李四', 'd2')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(changeFixedAssetAssignee).toHaveBeenCalledWith('fa-1', expect.objectContaining({ 使用人: '李四', department: 'd2' }))
    expect(supplementFixedAsset).not.toHaveBeenCalled()
    expect(batchUpdateFixedAssets).not.toHaveBeenCalled()
  })

  it('仅有换人权限时只读取数据范围内的必要实例信息，不加载档案或生平', async () => {
    mockCan.mockImplementation((code?: string) => code === 'change_instance_assignee')
    vi.mocked(getFixedAssetAssigneeTargets).mockResolvedValue({
      data: {
        count: 1,
        results: [{
          id: 'fa-1', 内部编号: 'NB-001-1', 序列号: 'SN-001', 当前状态: '在用',
          使用人: '张三', department: 'd1', departmentName: '行政部',
          branch: 'b1', branchName: '北京分公司', itemCode: 'NB-001', itemName: 'ThinkPad T14',
        }],
      },
    } as any)
    vi.mocked(changeFixedAssetAssignee).mockResolvedValue({
      data: {
        changed: true,
        asset: {
          id: 'fa-1', 内部编号: 'NB-001-1', 序列号: 'SN-001', 当前状态: '在用',
          使用人: '李四', department: 'd2', departmentName: '技术部',
          branch: 'b1', branchName: '北京分公司', itemCode: 'NB-001', itemName: 'ThinkPad T14',
        },
      },
    } as any)

    const wrapper = await _mount()
    expect(getFixedAssetAssigneeTargets).toHaveBeenCalledOnce()
    expect(getFixedAssets).not.toHaveBeenCalled()
    expect(getFixedAssetTimeline).not.toHaveBeenCalled()
    expect(wrapper.find('.assignee-target-table').exists()).toBe(true)
    expect(wrapper.find('.header-actions').findAll('button')).toHaveLength(0)
    expect(wrapper.find('.assignee-target-table').text()).toContain('北京分公司')
    expect(wrapper.find('.assignee-target-table').text()).toContain('SN-001')

    await wrapper.find('.assignee-target-table button[title="更换使用人"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('.assignee-only').exists()).toBe(true)
    expect(wrapper.find('.timeline-pane').exists()).toBe(false)
    expect(wrapper.find('input[placeholder="扫码或手工录入；清空=回到待补录"]').exists()).toBe(false)
    expect(getAssigneeDepartmentOptions).toHaveBeenCalledOnce()

    await fillAssigneeForm(wrapper, '李四', 'd2')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(changeFixedAssetAssignee).toHaveBeenCalledWith('fa-1', expect.objectContaining({ 使用人: '李四', department: 'd2' }))
    expect(supplementFixedAsset).not.toHaveBeenCalled()
    expect(batchUpdateFixedAssets).not.toHaveBeenCalled()
    expect(getFixedAssetTimeline).not.toHaveBeenCalled()
  })

  it('仅有实例编辑权限时通过受限列表进入编辑，不读取完整档案、使用人或生平', async () => {
    mockCan.mockImplementation((code?: string) => code === 'edit_instances')
    vi.mocked(getFixedAssetEditTargets).mockResolvedValue({
      data: {
        count: 1,
        results: [{
          id: 'fa-1', 内部编号: 'NB-001-1', 序列号: 'SN-001', 当前状态: '在库',
          branch: 'b1', branchName: '北京分公司', itemCode: 'NB-001', itemName: 'ThinkPad T14',
          itemSpec: '14 英寸', 供应商: '小熊U租', 采购日期: '2026-01-10', 备注: '旧备注', 图片: null,
        }],
      },
    } as any)
    vi.mocked(supplementFixedAsset).mockResolvedValue({ data: _inst({}) } as any)
    vi.mocked(batchUpdateFixedAssets).mockResolvedValue({
      data: { updated: 1, results: ['NB-001-1'], errors: [] },
    } as any)

    const wrapper = await _mount()

    expect(getFixedAssetEditTargets).toHaveBeenCalledWith(expect.objectContaining({ page: 1, pageSize: 50 }))
    expect(getFixedAssets).not.toHaveBeenCalled()
    expect(getFixedAssetAssigneeTargets).not.toHaveBeenCalled()
    expect(getFixedAssetTimeline).not.toHaveBeenCalled()
    expect(wrapper.find('.page-title').text()).toBe('实例维护')
    expect(wrapper.find('.assignee-target-table').exists()).toBe(true)
    expect(wrapper.find('.header-actions').findAll('button')).toHaveLength(0)

    await wrapper.find('.assignee-target-table button[title="编辑"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('.dlg-title').text()).toBe('编辑实例')
    expect(wrapper.find('input[placeholder="扫码或手工录入；清空=回到待补录"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('规格')
    expect(wrapper.text()).toContain('供应商')
    expect(wrapper.find('.assignee-section').exists()).toBe(false)
    expect(wrapper.find('.timeline-pane').exists()).toBe(false)
    expect(getInstanceSupplierOptions).toHaveBeenCalledOnce()

    await wrapper.findAll('button').find(button => button.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(supplementFixedAsset).toHaveBeenCalledWith('fa-1', { 序列号: 'SN-001', 备注: '旧备注' })
    expect(batchUpdateFixedAssets).toHaveBeenCalledWith(expect.objectContaining({
      ids: ['fa-1'], 规格: '14 英寸', 供应商: '小熊U租', 采购日期: '2026-01-10',
    }))
    expect(changeFixedAssetAssignee).not.toHaveBeenCalled()
  })

  it('档案字段部分保存失败时不提交使用人变更', async () => {
    vi.mocked(batchUpdateFixedAssets).mockResolvedValueOnce({
      data: { updated: 0, results: [], errors: ['供应商更新失败'] },
    } as any)
    const wrapper = await openEditDialog()
    await fillAssigneeForm(wrapper, '李四', 'd2', '岗位调整')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(changeFixedAssetAssignee).not.toHaveBeenCalled()
    expect(ElMessage.warning).toHaveBeenCalledWith('保存部分失败：供应商更新失败；使用人和部门未变更')
    expect(wrapper.find('.asset-edit-dialog').exists()).toBe(true)
    expect((wrapper.find('.assignee-section .el-input-stub').element as HTMLInputElement).value).toBe('李四')
  })

  it('接口失败时保留交接表单并显示错误', async () => {
    vi.mocked(changeFixedAssetAssignee).mockRejectedValue(new Error('实例已被待审批流转单占用'))
    const wrapper = await openEditDialog()
    await fillAssigneeForm(wrapper, '李四', 'd2', '岗位调整')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(changeFixedAssetAssignee).toHaveBeenCalledWith('fa-1', expect.objectContaining({ 使用人: '李四', department: 'd2' }))
    expect(ElMessage.error).toHaveBeenCalledWith('档案信息已保存，但使用人和部门变更失败：实例已被待审批流转单占用')
    expect(wrapper.find('.assignee-section').exists()).toBe(true)
    expect((wrapper.find('.assignee-section .el-input-stub').element as HTMLInputElement).value).toBe('李四')
    expect((wrapper.findAll('.assignee-section .el-input-stub')[1].element as HTMLInputElement).value).toBe('岗位调整')
  })

  it('交接失败后刷新档案基线，重试清空采购日期仍提交空值', async () => {
    const original = _inst({ 当前状态: '在用', 使用人: '张三', department: 'd1', 采购日期: null })
    const persisted = _inst({ ...original, 采购日期: '2026-10-20' })
    vi.mocked(getFixedAssets)
      .mockResolvedValueOnce({ data: { count: 1, results: [original] } } as any)
    vi.mocked(changeFixedAssetAssignee)
      .mockRejectedValueOnce(new Error('实例已被待审批流转单占用'))
      .mockResolvedValueOnce({ data: { asset: _inst({ ...persisted, 使用人: '李四', department: 'd2', departmentName: '技术部' }), changed: true } } as any)
    const wrapper = await openEditDialog(original)
    vi.mocked(getFixedAssets).mockResolvedValueOnce({ data: { count: 1, results: [persisted] } } as any)
    await fillAssigneeForm(wrapper, '李四', 'd2')
    const dateInput = wrapper.find('input.el-date-picker-stub')
    await dateInput.setValue('2026-10-20')

    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()
    expect(batchUpdateFixedAssets).toHaveBeenNthCalledWith(1, expect.objectContaining({ 采购日期: '2026-10-20' }))
    expect(wrapper.find('.asset-edit-dialog').exists()).toBe(true)

    await dateInput.setValue('')
    await wrapper.findAll('button').find(b => b.text() === '保存')!.trigger('click')
    await flushPromises()

    expect(batchUpdateFixedAssets).toHaveBeenNthCalledWith(2, expect.objectContaining({ 采购日期: '' }))
    expect(changeFixedAssetAssignee).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.asset-edit-dialog').exists()).toBe(false)
  })

  it('批量菜单不再提供使用人交接', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 2, results: [_inst({ id: 'fa-1' }), _inst({ id: 'fa-2' })] },
    } as any)
    const wrapper = await _mount()
    for (const checkbox of wrapper.findAll('tbody .check-col input[type=checkbox]')) await checkbox.setValue(true)
    await wrapper.findAll('button').find(button => button.text().includes('批量操作'))!.trigger('click')
    expect(wrapper.find('.batch-menu').text()).not.toContain('更换使用人')
  })

  it('编辑和生平共用加宽弹窗，生平以原表格展示流转和使用人变更', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({ 当前状态: '在用' })] },
    } as any)
    vi.mocked(getFixedAssetTimeline).mockResolvedValue({
      data: {
        instance: _inst({ 当前状态: '在用' }),
        birth: null,
        timeline: [
          {
            kind: 'transfer', event_id: 'flow-1', transferId: 't1', 单据编号: 'CG20260911-020',
            actionType: 'assign', 日期: '2026-10-01', 时间: '2026-10-01T09:00:00', 行号: 1,
            品目编号: 'NB-001', 数量: 1, 使用人: '张三', 部门: '行政部', 本批规格: '', 审批状态: '已通过',
          },
          {
            kind: 'assignee_change', event_id: 'handoff-1', 时间: '2026-10-20T10:30:00',
            旧使用人: '张三', 新使用人: '李四', 旧部门: '行政部', 新部门: '技术部',
            操作账号: 'admin@example.com', 操作人: '管理员', 原因: '岗位调整',
          },
        ],
      },
    } as any)
    const wrapper = await openEditDialog(_inst({ 当前状态: '在用' }))
    expect(getFixedAssetTimeline).toHaveBeenCalledOnce()
    const editDialog = wrapper.find('.asset-edit-dialog')
    expect(editDialog.exists()).toBe(true)
    expect(editDialog.attributes('data-width')).toBe('min(1240px, calc(100vw - 32px))')
    const timeline = wrapper.find('.timeline-pane')
    expect(timeline.exists()).toBe(true)
    const table = timeline.find('.timeline-table')
    expect(table.exists()).toBe(true)
    expect(table.findAll('thead th').map(header => header.text())).toEqual(['日期', '单据', '类型', '使用人', '状态'])
    const rows = table.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('CG20260911-020')
    expect(rows[0].findAll('td')[1].classes()).toContain('timeline-document-cell')
    expect(rows[0].findAll('td')[2].text()).toBe('领用出库')
    expect(rows[0].findAll('td')[3].text()).toContain('张三 / 行政部')
    expect(rows[1].findAll('td')[0].text()).toBe('2026-10-20')
    expect(rows[1].findAll('td')[2].text()).toBe('使用人变更')
    expect(rows[1].findAll('td')[3].text()).toBe('李四 / 技术部')
    expect(rows[1].findAll('td')[4].text()).toBe('已生效')
    expect(fixedAssetListSource).toMatch(/\.timeline-table th:first-child\s*\{\s*width:\s*108px/)
    expect(fixedAssetListSource).toMatch(/\.timeline-document-cell\s*\{[^}]*white-space:\s*nowrap/)
  })

  it('生平请求失败时保留视图并允许重试', async () => {
    const asset = _inst({ 当前状态: '在用' })
    vi.mocked(getFixedAssets).mockResolvedValue({ data: { count: 1, results: [asset] } } as any)
    vi.mocked(getFixedAssetTimeline)
      .mockRejectedValueOnce(new Error('network error'))
      .mockResolvedValueOnce({
        data: {
          instance: asset,
          birth: null,
          timeline: [{
            kind: 'transfer', event_id: 'flow-1', 日期: '2026-10-01',
            actionType: 'assign', 使用人: '张三', 部门: '行政部', 审批状态: '已通过',
          }],
        },
      } as any)

    const wrapper = await openEditDialog(asset)

    const timeline = wrapper.find('.timeline-pane')
    expect(timeline.exists()).toBe(true)
    expect(timeline.text()).toContain('重试')
    await timeline.findAll('button').find(button => button.text() === '重试')!.trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.timeline-table tbody tr')).toHaveLength(1)
    expect(getFixedAssetTimeline).toHaveBeenCalledTimes(2)
  })
})

describe('勾选随筛选重置', () => {
  it('筛选变化清空勾选，批量计数不残留', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 2, results: [
        _inst({ id: 'fa-1', 图片: null }), _inst({ id: 'fa-2', 图片: null }),
      ] },
    } as any)
    const wrapper = await _mount()
    const checks = wrapper.findAll('tbody .check-col input[type=checkbox]')
    await checks[0].setValue(true)
    await checks[1].setValue(true)
    expect(wrapper.findAll('button').find(b => b.text().includes('批量操作（2）'))).toBeTruthy()

    // 筛选变化（关键字）→ 刷新数据 + 勾选清空
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({ id: 'fa-9', 图片: null })] },
    } as any)
    const search = wrapper.find('input[placeholder^="搜索内部编号"]')
    await search.setValue('电脑')
    await flushPromises()
    const btn = wrapper.findAll('button').find(b => b.text().includes('批量操作'))
    expect(btn!.text()).not.toContain('（')
    // 新页勾选框为未选中态
    const newChecks = wrapper.findAll('tbody .check-col input[type=checkbox]')
    expect((newChecks[0].element as HTMLInputElement).checked).toBe(false)
  })
})

describe('实例档案供应商只准选（instance-supplier-dict-select）', () => {
  it('行编辑与批量供应商均为字典下拉，自由输入退役，含继承语义项', () => {
    expect(fixedAssetListSource).toContain('<el-select v-model="editForm.供应商"')
    expect(fixedAssetListSource).not.toContain('el-input v-model="editForm.供应商"')
    expect(fixedAssetListSource).toContain('继承出生单（清空覆盖）')
    expect(fixedAssetListSource).toContain('设为继承（清空覆盖，回落出生单供应商，可能为空）')
    expect(fixedAssetListSource).toContain('for="sp in supplierOptions"')
  })

  it('批量供应商提交前确认影响行数与回落语义', () => {
    expect(fixedAssetListSource).toContain('ElMessageBox.confirm(`将更新 ${ids.length} 台实例的供应商')
  })
})
