import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElSelect, ElOption } from 'element-plus'
import BranchFilterSelect from '@/components/BranchFilterSelect.vue'

const OPTIONS = [
  { value: '杭州二分', label: '杭州二分' },
  { value: '北京分公司', label: '北京分公司' },
  { value: '杭州分公司', label: '杭州分公司' },
]

function mountPicker(props: Record<string, unknown> = {}): ReturnType<typeof mount> {
  return mount(BranchFilterSelect, {
    props: { modelValue: [] as string[], options: OPTIONS, ...props },
  })
}

describe('BranchFilterSelect 分公司筛选（多选）', () => {
  it('多选模式：选项按名称拼音排序、无空值哨兵项', () => {
    const wrapper = mountPicker()
    const select = wrapper.getComponent(ElSelect)
    expect(select.props('multiple')).toBe(true)
    const opts = wrapper.findAllComponents(ElOption)
    const values = opts.map((o) => o.props('value'))
    expect(values).toEqual(['北京分公司', '杭州二分', '杭州分公司']) // 拼音序，无 ''
  })

  it('allLabel 定制占位文案', () => {
    const wrapper = mountPicker({ allLabel: '调出分公司' })
    expect(wrapper.getComponent(ElSelect).props('placeholder')).toBe('调出分公司')
  })

  it('开启 filterable/clearable，值数组双向透传', async () => {
    const wrapper = mountPicker({ modelValue: ['北京分公司'] })
    const select = wrapper.getComponent(ElSelect)
    expect(select.props('filterable')).toBe(true)
    expect(select.props('clearable')).toBe(true)
    expect(select.props('modelValue')).toEqual(['北京分公司'])

    await select.vm.$emit('update:modelValue', ['北京分公司', '杭州二分'])
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([['北京分公司', '杭州二分']])
  })

  it('清空归一为空数组（=全部）', async () => {
    const wrapper = mountPicker({ modelValue: ['北京分公司'] })
    const select = wrapper.getComponent(ElSelect)
    await select.vm.$emit('update:modelValue', undefined)
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([[]])
    await select.vm.$emit('clear')
    expect(wrapper.emitted('update:modelValue')![1]).toEqual([[]])
  })
})
