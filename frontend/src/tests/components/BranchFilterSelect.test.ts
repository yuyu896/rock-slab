import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElSelect, ElOption } from 'element-plus'
import BranchFilterSelect from '@/components/BranchFilterSelect.vue'

const OPTIONS = [
  { value: '北京分公司', label: '北京分公司' },
  { value: '杭州分公司', label: '杭州分公司' },
  { value: '杭州二分', label: '杭州二分' },
]

function mountPicker(props: Record<string, unknown> = {}) {
  return mount(BranchFilterSelect, {
    props: { modelValue: '', options: OPTIONS, ...props },
  })
}

describe('BranchFilterSelect 分公司筛选', () => {
  it('内置「全部分公司」空值项 + 透传选项', () => {
    const wrapper = mountPicker()
    const opts = wrapper.findAllComponents(ElOption)
    const values = opts.map((o) => o.props('value'))
    expect(values).toEqual(['', '北京分公司', '杭州分公司', '杭州二分'])
    expect(opts[0].props('label')).toBe('全部分公司')
  })

  it('allLabel 定制空值项与占位文案', () => {
    const wrapper = mountPicker({ allLabel: '调出分公司' })
    const opts = wrapper.findAllComponents(ElOption)
    expect(opts[0].props('label')).toBe('调出分公司')
    expect(wrapper.getComponent(ElSelect).props('placeholder')).toBe('调出分公司')
  })

  it('开启 filterable/clearable，值双向透传', async () => {
    const wrapper = mountPicker({ modelValue: '北京分公司' })
    const select = wrapper.getComponent(ElSelect)
    expect(select.props('filterable')).toBe(true)
    expect(select.props('clearable')).toBe(true)
    expect(select.props('modelValue')).toBe('北京分公司')

    await select.vm.$emit('update:modelValue', '杭州二分')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['杭州二分'])
  })

  it('清空/未定义值归一为空串', async () => {
    const wrapper = mountPicker({ modelValue: '北京分公司' })
    const select = wrapper.getComponent(ElSelect)
    await select.vm.$emit('update:modelValue', undefined)
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([''])
    await select.vm.$emit('clear')
    expect(wrapper.emitted('update:modelValue')![1]).toEqual([''])
  })
})
