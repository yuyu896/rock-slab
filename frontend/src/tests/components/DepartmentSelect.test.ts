import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DepartmentSelect from '@/components/DepartmentSelect.vue'

vi.mock('@/api/departments', () => ({
  getDepartmentOptions: vi.fn().mockResolvedValue({
    data: [
      { id: 'd1', name: '行政部', branch: 'b1', branchName: '分公司A' },
      { id: 'd2', name: '仓库', branch: 'b1', branchName: '分公司A' },
    ],
  }),
}))

import { getDepartmentOptions } from '@/api/departments'

describe('DepartmentSelect（P1 部门字典版）', () => {
  it('按分公司拉取字典选项渲染 datalist', async () => {
    const wrapper = mount(DepartmentSelect, {
      props: { modelValue: '', branch: '分公司A' },
    })
    await flushPromises()
    expect(getDepartmentOptions).toHaveBeenCalledWith({ branch: '分公司A' })
    const options = wrapper.findAll('datalist option')
    expect(options.map(o => o.attributes('value'))).toEqual(['行政部', '仓库'])
  })

  it('输入自定义部门时更新 v-model（P1 允许字典外新值）', async () => {
    const wrapper = mount(DepartmentSelect, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('市场部')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['市场部'])
  })

  it('回显已有值', () => {
    const wrapper = mount(DepartmentSelect, { props: { modelValue: '市场部' } })
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('市场部')
  })
})
