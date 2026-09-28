import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, ref, watch, onMounted } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { useQueryFilters } from '@/composables/useQueryFilters'

/** 宿主组件复刻列表页结构：filters → useQueryFilters（恢复先于 watch）→ fetch-watch → onMounted 拉取 */
const Host = defineComponent({
  setup() {
    const filters = ref({ status: '', branch: [] as string[], keyword: '', flag: false })
    const pagination = ref({ page: 1, pageSize: 50, total: 0 })
    useQueryFilters(filters, pagination, { arrayKeys: ['branch'], boolKeys: ['flag'] })
    const fetchCount = ref(0)
    watch(filters, () => { pagination.value.page = 1; fetchCount.value++ }, { deep: true })
    onMounted(() => { fetchCount.value++ })
    return { filters, pagination, fetchCount }
  },
})

async function mountHost(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: Host }],
  })
  await router.push({ path: '/', query })
  await router.isReady()
  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('useQueryFilters 列表筛选路由持久化', () => {
  it('带 query 挂载：筛选/页码恢复且仅拉取一次（恢复不触发 watch、页码不重置）', async () => {
    const { wrapper, router } = await mountHost({ status: 'pending', branch: '杭州,北京', keyword: 'a00008', flag: '1', page: '3' })
    expect(wrapper.vm.filters).toMatchObject({ status: 'pending', keyword: 'a00008', flag: true })
    expect((wrapper.vm.filters as any).branch).toEqual(['杭州', '北京'])
    expect(wrapper.vm.pagination.page).toBe(3)
    expect(wrapper.vm.fetchCount).toBe(1)
    expect(router.currentRoute.value.query).toMatchObject({ status: 'pending', page: '3' })
    wrapper.unmount()
  })

  it('用户变更筛选：触发一次拉取、query 同步（数组逗号拼接、有值才写）', async () => {
    const { wrapper, router } = await mountHost()
    ;(wrapper.vm.filters as any).status = 'approved'
    ;(wrapper.vm.filters as any).branch = ['杭州']
    await flushPromises()
    expect(wrapper.vm.fetchCount).toBe(2)
    expect(router.currentRoute.value.query).toEqual({ status: 'approved', branch: '杭州' })
    wrapper.unmount()
  })

  it('清空筛选：对应 query 键移除', async () => {
    const { wrapper, router } = await mountHost({ status: 'pending' })
    ;(wrapper.vm.filters as any).status = ''
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
    wrapper.unmount()
  })

  it('手动重置（全空+页码归一）：query 清空', async () => {
    const { wrapper, router } = await mountHost({ status: 'pending', page: '4' })
    Object.assign(wrapper.vm.filters, { status: '', branch: [], keyword: '', flag: false })
    wrapper.vm.pagination.page = 1
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
    wrapper.unmount()
  })

  it('脏 query 容错：page 非法回退 1、未知键忽略、布尔仅认 1', async () => {
    const { wrapper } = await mountHost({ page: 'abc', foo: 'bar', flag: 'yes' })
    expect(wrapper.vm.pagination.page).toBe(1)
    expect(wrapper.vm.filters).toMatchObject({ flag: false, status: '' })
    wrapper.unmount()
  })

  it('页码仅大于 1 时写入 query', async () => {
    const { wrapper, router } = await mountHost({ status: 'pending' })
    wrapper.vm.pagination.page = 5
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ status: 'pending', page: '5' })
    wrapper.vm.filters.keyword = 'x'
    await flushPromises()
    expect(wrapper.vm.pagination.page).toBe(1)
    expect(router.currentRoute.value.query).toEqual({ status: 'pending', keyword: 'x' })
    wrapper.unmount()
  })
})
