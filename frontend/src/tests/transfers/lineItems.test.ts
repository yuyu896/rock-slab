import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

import {
  emptyDraft, draftsToItems, draftsFromLines, type LineDraft,
} from '@/views/transfers/components/lineDrafts'
import { transferDocSummary } from '@/types'
import type { TransferLine } from '@/types'
import TransferLinesEditor from '@/views/transfers/components/TransferLinesEditor.vue'

vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn(),
  getAssetStocks: vi.fn(),
}))
vi.mock('@/api/departments', () => ({
  getDepartmentOptions: vi.fn().mockResolvedValue({ data: [] }),
}))
import { getFixedAssets } from '@/api/assets'

const pickedItem = {
  id: 'item-1',
  asset_code: 'NB-001',
  asset_name: '笔记本',
  specification: '14寸',
  unit: '台',
  assetCategory: '固定资产',
  itemCategory: '电脑',
  managementType: 'quantity',
}

function line(overrides: Partial<TransferLine> = {}): TransferLine {
  return {
    id: 'l1', 行号: 1, item: 'item-1', itemCode: 'NB-001', itemName: '笔记本',
    itemSpec: '14寸', unit: '台', assetCategory: '固定资产', itemCategory: '电脑',
    managementType: 'quantity', 数量: 2, ...overrides,
  } as TransferLine
}

describe('lineDrafts 助手', () => {
  it('emptyDraft 生成可增删的空行草稿', () => {
    const a = emptyDraft()
    const b = emptyDraft()
    expect(a.item).toBeNull()
    expect(a.数量).toBe(1)
    expect(a.key).not.toBe(b.key) // key 唯一，v-for 稳定
  })

  it('draftsToItems 忽略未选品目的行并映射行字段', () => {
    const d1 = { ...emptyDraft(), item: pickedItem, 数量: 3, 使用人: '张三' }
    const d2 = emptyDraft() // 未选品目 → 忽略
    const items = draftsToItems([d1, d2])
    expect(items).toEqual([
      expect.objectContaining({ item: 'item-1', 数量: 3, 使用人: '张三' }),
    ])
  })

  it('draftsFromLines 从既有明细行还原编辑草稿', () => {
    const drafts = draftsFromLines([line(), line({ 行号: 2, 数量: 5, 使用人: '李四' })])
    expect(drafts).toHaveLength(2)
    expect(drafts[0].item?.asset_code).toBe('NB-001')
    expect(drafts[0].数量).toBe(2)
    expect(drafts[1].使用人).toBe('李四')
  })
})

describe('transferDocSummary 多行摘要', () => {
  it('单行单据显示品目名与数量', () => {
    const s = transferDocSummary({ 单据编号: 'CG1', lines: [line()] } as any)
    expect(s.name).toBe('笔记本')
    expect(s.qty).toBe(2)
    expect(s.code).toBe('NB-001')
  })

  it('多行单据显示首行 + 等 N 项，数量为合计', () => {
    const s = transferDocSummary({
      单据编号: 'CG2',
      lines: [line(), line({ 行号: 2, itemCode: 'MP-001', itemName: '鼠标', 数量: 4 })],
    } as any)
    expect(s.name).toBe('笔记本 等 2 项')
    expect(s.qty).toBe(6)
  })
})

describe('TransferLinesEditor 增删行与校验', () => {
  function mountEditor() {
    return mount(TransferLinesEditor, {
      props: { modelValue: [], type: 'purchase' },
      global: {
        stubs: { ItemPicker: { template: '<div class="picker-stub" />' } },
      },
    })
  }

  it('初始一行，可添加/删除行（至少保留一行）', async () => {
    const wrapper = mountEditor()
    expect(wrapper.findAll('.lines-row')).toHaveLength(1)
    await wrapper.find('.add-row-btn').trigger('click')
    expect(wrapper.findAll('.lines-row')).toHaveLength(2)
    const removeBtns = wrapper.findAll('.remove-btn')
    await removeBtns[1].trigger('click')
    expect(wrapper.findAll('.lines-row')).toHaveLength(1)
    await wrapper.findAll('.remove-btn')[0].trigger('click')
    expect(wrapper.findAll('.lines-row')).toHaveLength(1) // 不删到空
  })

  it('validate：未选品目或数量<1 的行不通过', async () => {
    const wrapper = mountEditor()
    expect((wrapper.vm as any).validate()).toBe(false) // 空 item
    const drafts = [{ ...emptyDraft(), item: pickedItem, 数量: 2 }]
    await wrapper.setProps({ modelValue: drafts })
    await nextTick()
    expect((wrapper.vm as any).validate()).toBe(true)
    drafts[0].数量 = 0
    expect((wrapper.vm as any).validate()).toBe(false)
  })

  it('采购行金额留空自动 = 单价 × 数量，手填不覆盖，清空回自动', async () => {
    const wrapper = mountEditor()
    const draft: LineDraft = { ...emptyDraft(), item: pickedItem, 数量: 4, 单价: null, 金额: null }
    await wrapper.setProps({ modelValue: [draft] })
    await nextTick()
    const numInputs = wrapper.findAll('input.num') // [单价, 金额]

    await numInputs[0].setValue('12.5')
    await numInputs[0].trigger('change')
    expect(draft.单价).toBe(12.5)
    expect(draft.金额).toBe(50) // 留空自动算

    draft.金额 = 45 // 手填（整批折价）
    await numInputs[0].setValue('13')
    await numInputs[0].trigger('change')
    expect(draft.金额).toBe(45) // 手填优先不被覆盖

    await numInputs[1].setValue('') // 清空金额 → 回到自动
    await numInputs[1].trigger('change')
    expect(draft.金额).toBeNull()
    await numInputs[0].setValue('13')
    await numInputs[0].trigger('change')
    expect(draft.金额).toBe(52)
  })

  it('领用行使用人/部门必填（不分管理方式）', async () => {
    const wrapper = mount(TransferLinesEditor, {
      props: { modelValue: [], type: 'assign', branchId: 'b-1' },
      global: {
        stubs: { ItemPicker: { template: '<div class="picker-stub" />' } },
      },
    })
    const draft: LineDraft = { ...emptyDraft(), item: pickedItem, 数量: 1 }
    await wrapper.setProps({ modelValue: [draft] })
    await nextTick()
    expect((wrapper.vm as any).validate()).toBe(false) // 缺使用人与部门
    draft.使用人 = '张三'
    expect((wrapper.vm as any).validate()).toBe(false) // 仍缺部门
    draft.department = 'dept-1'
    expect((wrapper.vm as any).validate()).toBe(true)
  })

  it('回收行在用数量未知时预检放行（终检在后端台账行锁内）', async () => {
    const wrapper = mount(TransferLinesEditor, {
      props: { modelValue: [], type: 'recovery', branchName: '测试分公司' },
      global: {
        stubs: { ItemPicker: { template: '<div class="picker-stub" />' } },
      },
    })
    const draft: LineDraft = { ...emptyDraft(), item: pickedItem, 数量: 99 }
    await wrapper.setProps({ modelValue: [draft] })
    await nextTick()
    expect((wrapper.vm as any).validate()).toBe(true)
    expect((wrapper.vm as any).validateMessage).toBe('')
  })
})

describe('实例点选跨行去重与面板收口', () => {
  const instItem = { ...pickedItem, managementType: 'instance' as const }
  function inst(i: number) {
    return {
      id: `fa-${i}`, 内部编号: `NB-001-${i}`, 序列号: '', 当前状态: '在库' as const,
      item: 'item-1', itemCode: 'NB-001', itemName: '笔记本', createdAt: '', updatedAt: '',
    }
  }

  function mountAssign(d1: LineDraft, d2: LineDraft) {
    return mount(TransferLinesEditor, {
      props: {
        modelValue: [d1, d2], type: 'assign' as const,
        branchId: 'b-1', branchName: '北京分公司',
      },
      global: { stubs: { ItemPicker: { template: '<div class="picker-stub" />' } } },
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 3, results: [inst(1), inst(2), inst(3)] },
    } as any)
  })

  async function openPicker(wrapper: ReturnType<typeof mountAssign>, rowIndex: number) {
    await wrapper.findAll('.picker-toggle')[rowIndex].trigger('click')
    await flushPromises()
  }

  it('他行已选实例不再出现在候选；取消勾选后回到候选', async () => {
    const d1: LineDraft = { ...emptyDraft(), item: instItem, 数量: 1, 使用人: '张三', department: 'd' }
    const d2: LineDraft = { ...emptyDraft(), item: instItem, 数量: 1, 使用人: '李四', department: 'd' }
    const wrapper = mountAssign(d1, d2)

    await openPicker(wrapper, 0)
    const row1Checks = wrapper.findAll('.picker-panel .picker-row input')
    await row1Checks[0].setValue(true) // 行 1 勾 fa-1
    expect(d1.instances.map((i) => i.id)).toEqual(['fa-1'])

    await openPicker(wrapper, 1) // 展开行 2（同时验证互斥收起行 1）
    const codes2 = wrapper.findAll('.picker-panel .picker-row .row-code').map((c) => c.text())
    expect(codes2).toEqual(['NB-001-2', 'NB-001-3']) // fa-1 被他行排除

    // 行 1 取消勾选（经 UI）→ 行 2 候选恢复 fa-1
    await openPicker(wrapper, 0)
    await wrapper.findAll('.picker-panel .picker-row input')[0].setValue(false)
    await openPicker(wrapper, 1)
    const codes2After = wrapper.findAll('.picker-panel .picker-row .row-code').map((c) => c.text())
    expect(codes2After).toEqual(['NB-001-1', 'NB-001-2', 'NB-001-3'])
  })

  it('本行已选保留勾选回显；完成按钮收起面板；同屏互斥', async () => {
    const d1: LineDraft = { ...emptyDraft(), item: instItem, 数量: 1, 使用人: '张三', department: 'd' }
    const d2: LineDraft = { ...emptyDraft(), item: instItem, 数量: 1, 使用人: '李四', department: 'd' }
    const wrapper = mountAssign(d1, d2)

    await openPicker(wrapper, 0)
    const checks1 = wrapper.findAll('.picker-panel .picker-row input')
    await checks1[0].setValue(true)
    await checks1[1].setValue(true)
    expect(d1.数量).toBe(2) // 数量=勾选台数联动

    // 本行已选保留：重开面板仍勾选
    await wrapper.findAll('.picker-toggle')[0].trigger('click') // 收起
    await openPicker(wrapper, 0)
    const checked = wrapper.findAll('.picker-panel .picker-row input').filter((c) => (c.element as HTMLInputElement).checked)
    expect(checked).toHaveLength(2)

    // 同屏互斥：展开行 2 → 行 1 面板收起
    await openPicker(wrapper, 1)
    expect(wrapper.findAll('.picker-panel')).toHaveLength(1)

    // 完成按钮收起
    await wrapper.find('.picker-panel .picker-done').trigger('click')
    expect(wrapper.findAll('.picker-panel')).toHaveLength(0)
    expect(wrapper.findAll('.picker-toggle')[1].text()).toContain('选择实例')
  })
})
