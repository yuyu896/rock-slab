import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { computed } from 'vue'

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
}))

vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn(),
  exportFixedAssets: vi.fn(),
  supplementFixedAsset: vi.fn(),
  getFixedAssetTimeline: vi.fn(),
  uploadFixedAssetImage: vi.fn(),
  deleteFixedAssetImage: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [] }),
}))

import FixedAssetList from '@/views/FixedAssetList.vue'
import fixedAssetListSource from '@/views/FixedAssetList.vue?raw'
import { getFixedAssets, uploadFixedAssetImage } from '@/api/assets'
import type { FixedAsset } from '@/types'

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
  'el-dialog': { props: ['modelValue'], template: '<div><slot /></div>' },
  'el-drawer': { props: ['modelValue'], template: '<div><slot /></div>' },
  'el-image': { props: ['src'], template: '<img class="el-image-stub" :src="src" />' },
  'el-form': { template: '<div><slot /></div>' },
  'el-form-item': { template: '<div><slot /></div>' },
  'el-input': { template: '<input />' },
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
    const printBtn = wrapper.findAll('button').find(b => b.text().includes('打印标签（2）'))
    expect(printBtn).toBeTruthy()
    await printBtn!.trigger('click')
    expect(wrapper.find('.print-stub').text()).toBe('2-true')
  })

  it('已挂图显示缩略图、未挂图显示占位', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 2, results: [
        _inst({ id: 'fa-1', 图片: '/media/fixed_assets/a.jpg' }),
        _inst({ id: 'fa-2', 图片: null }),
      ] },
    } as any)
    const wrapper = await _mount()
    const rows = wrapper.findAll('.data-table tbody tr')
    expect(rows[0].find('.row-thumb').exists()).toBe(true)
    expect(rows[0].find('.row-thumb').attributes('src')).toBe('/media/fixed_assets/a.jpg')
    expect(rows[1].find('.row-thumb').exists()).toBe(false)
    expect(rows[1].find('.thumb-empty').text()).toBe('—')
  })

  it('无 manage_instances 权限时图片操作按钮不渲染', async () => {
    mockCan.mockImplementation((code?: string) => code !== 'manage_instances')
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    const wrapper = await _mount()
    const buttons = wrapper.findAll('.action-btn')
    // 图片/补录按钮均不渲染，仅剩生平/打印
    expect(buttons.filter(b => b.attributes('title') === '物品图片').length).toBe(0)
    expect(buttons.filter(b => b.attributes('title') === '补录序列号').length).toBe(0)
    expect(buttons.filter(b => b.attributes('title') === '生平').length).toBe(1)
  })

  it('操作列单元格不得用 flex 破坏表格行布局（行分割线同高对齐）', () => {
    expect(fixedAssetListSource).toMatch(/\.action-col\s*\{[^}]*white-space:\s*nowrap/)
    expect(fixedAssetListSource).not.toMatch(/\.action-col\s*\{[^}]*display:\s*flex/)
  })

  it('上传成功后图片弹窗自动关闭', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 1, results: [_inst({})] },
    } as any)
    vi.mocked(uploadFixedAssetImage).mockResolvedValue({
      data: _inst({ 图片: '/media/fixed_assets/new.jpg' }),
    } as any)
    const wrapper = await _mount()
    await wrapper.findAll('.action-btn').find(b => b.attributes('title') === '物品图片')!.trigger('click')
    expect(wrapper.find('.image-dialog-body').exists()).toBe(true)

    const input = wrapper.find('input[type=file]')
    const file = new File([new Uint8Array(64)], 'photo.jpg', { type: 'image/jpeg' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await flushPromises()

    expect(uploadFixedAssetImage).toHaveBeenCalledWith('fa-1', file)
    expect(wrapper.find('.image-dialog-body').exists()).toBe(false)
    const thumb = wrapper.find('.data-table tbody img')
    expect(thumb.exists()).toBe(true)
    expect(thumb.attributes('src')).toBe('/media/fixed_assets/new.jpg')
  })
})
