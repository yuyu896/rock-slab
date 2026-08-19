import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DepartmentSelect from '@/components/DepartmentSelect.vue'
import { DEPARTMENT_PRESETS } from '@/constants'

describe('DepartmentSelect', () => {
  it('渲染预置部门选项（datalist）', () => {
    const wrapper = mount(DepartmentSelect, { props: { modelValue: '' } })
    const options = wrapper.findAll('datalist option')
    expect(options.map(o => o.attributes('value'))).toEqual(DEPARTMENT_PRESETS)
  })

  it('输入自定义部门时更新 v-model', async () => {
    const wrapper = mount(DepartmentSelect, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('市场部')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['市场部'])
  })

  it('回显已有自定义值', () => {
    const wrapper = mount(DepartmentSelect, { props: { modelValue: '市场部' } })
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('市场部')
    // 回显时预置选项仍可用
    expect(wrapper.findAll('datalist option').length).toBe(DEPARTMENT_PRESETS.length)
  })
})
