import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, shallowMount } from '@vue/test-utils'
import { defineComponent } from 'vue'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: {
    confirm: vi.fn(),
    prompt: vi.fn(),
    alert: vi.fn(),
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('@/composables/useQueryFilters', () => ({
  useQueryFilters: vi.fn(),
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    can: (code: string) => permissionState.codes === null || permissionState.codes.includes(code),
  }),
}))

vi.mock('@/store/inventory', () => ({
  useInventoryStore: () => ({ deleteTask: vi.fn() }),
}))

vi.mock('@/utils/importTemplate', () => ({
  generateTransferTemplate: vi.fn(),
  generateCategoryTemplate: vi.fn(),
}))

vi.mock('@/api/transfers', () => ({
  getTransfers: vi.fn(),
  approveTransfer: vi.fn(),
  rejectTransfer: vi.fn(),
  importTransfers: vi.fn(),
  exportTransfers: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn(),
}))

vi.mock('@/api/categories', () => ({
  importCategories: vi.fn(),
  getCategories: vi.fn(),
}))

vi.mock('@/api/inventories', () => ({
  getInventoryTasks: vi.fn(),
  startInventory: vi.fn(),
  cancelInventory: vi.fn(),
  approveInventory: vi.fn(),
  rejectInventory: vi.fn(),
  recountInventory: vi.fn(),
  getInventoryReport: vi.fn(),
  getInventoryChecks: vi.fn(),
  exportInventoryReport: vi.fn(),
  submitInventory: vi.fn(),
  downloadInventoryTemplate: vi.fn(),
  importInventoryResult: vi.fn(),
  checkInventoryInstance: vi.fn(),
  checkInventoryItem: vi.fn(),
}))

import { ElMessage, ElMessageBox } from 'element-plus'
import { generateTransferTemplate } from '@/utils/importTemplate'
import { getTransfers, importTransfers } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { getCategories, importCategories } from '@/api/categories'
import {
  getInventoryTasks,
  importInventoryResult,
} from '@/api/inventories'
import { useTransferList } from '@/composables/useTransferList'
import CategoryImportDialog from '@/views/categories/CategoryImportDialog.vue'
import Inventory from '@/views/Inventory.vue'
import InventoryTaskList from '@/views/inventory/InventoryTaskList.vue'

const permissionState = vi.hoisted(() => ({ codes: null as string[] | null }))

const emptyTransferPage = {
  data: { count: 0, next: null, previous: null, results: [] },
}

const emptyInventoryPage = {
  data: { count: 0, next: null, previous: null, results: [] },
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function fileEvent(fileName = 'import.xlsx') {
  return {
    target: {
      files: [new File(['content'], fileName)],
      value: fileName,
    },
  } as unknown as Event
}

function installFileOnInput(input: HTMLInputElement, fileName = 'import.xlsx') {
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: [new File(['content'], fileName)],
  })
}

function mountTransferComposable() {
  return mount(defineComponent({
    setup() {
      return { state: useTransferList('assign') }
    },
    template: '<div />',
  }))
}

beforeEach(() => {
  vi.clearAllMocks()
  permissionState.codes = null
  vi.mocked(getTransfers).mockResolvedValue(emptyTransferPage as any)
  vi.mocked(getBranches).mockResolvedValue({ data: [] } as any)
  vi.mocked(getCategories).mockResolvedValue({ data: { results: [] } } as any)
  vi.mocked(importTransfers).mockResolvedValue({
    data: { imported: 1, errors: [] },
  } as any)
  vi.mocked(importCategories).mockResolvedValue({
    data: { imported: 1, errors: [] },
  } as any)
  vi.mocked(getInventoryTasks).mockResolvedValue(emptyInventoryPage as any)
  vi.mocked(importInventoryResult).mockResolvedValue({
    data: { imported: 1, errors: [] },
  } as any)
})

describe('transfer batch import confirmation', () => {
  it('allows template download and import with merged edit and view prerequisites', async () => {
    permissionState.codes = ['view_assignment', 'edit_assignment', 'view_asset_ledger']
    const wrapper = mountTransferComposable()
    await flushPromises()
    const state = wrapper.vm.state as any

    expect(state.canDownloadTemplate.value).toBe(true)
    expect(state.canImport.value).toBe(true)
    state.openImportModal()
    expect(state.showImportModal.value).toBe(true)

    state.handleDownloadTemplate()
    expect(generateTransferTemplate).toHaveBeenCalledWith(expect.any(String), 'assign')
  })

  it('blocks template and import when module view is missing even if edit and ledger view are held', async () => {
    permissionState.codes = ['edit_assignment', 'view_asset_ledger']
    const wrapper = mountTransferComposable()
    await flushPromises()
    const state = wrapper.vm.state as any

    expect(state.canDownloadTemplate.value).toBe(false)
    expect(state.canImport.value).toBe(false)
    state.openImportModal()
    expect(state.showImportModal.value).toBe(false)

    const event = fileEvent()
    await state.handleImportFile(event)
    expect(ElMessageBox.confirm).not.toHaveBeenCalled()
    expect(importTransfers).not.toHaveBeenCalled()
    expect((event.target as HTMLInputElement).value).toBe('')
  })

  it('does not write before confirmation and submits exactly once after confirmation', async () => {
    const wrapper = mountTransferComposable()
    await flushPromises()
    const state = wrapper.vm.state as any
    state.openImportModal()

    const confirmation = deferred<'confirm'>()
    vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise as any)
    const event = fileEvent()
    const pending = state.handleImportFile(event)

    await flushPromises()
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
    expect(importTransfers).not.toHaveBeenCalled()
    expect(state.importBusy.value).toBe(true)

    confirmation.resolve('confirm')
    await pending
    await flushPromises()

    expect(importTransfers).toHaveBeenCalledTimes(1)
    expect(importTransfers).toHaveBeenCalledWith(
      (event.target as HTMLInputElement).files?.[0],
      'assign',
    )
  })

  it('cancelling transfer import clears the selection without writing', async () => {
    const wrapper = mountTransferComposable()
    await flushPromises()
    const state = wrapper.vm.state as any
    state.openImportModal()
    vi.mocked(ElMessageBox.confirm).mockRejectedValue('cancel')

    const event = fileEvent()
    await state.handleImportFile(event)

    expect(importTransfers).not.toHaveBeenCalled()
    expect((event.target as HTMLInputElement).value).toBe('')
    expect(state.importBusy.value).toBe(false)
  })

  it('locks the transfer modal while the confirmed request is pending', async () => {
    const wrapper = mountTransferComposable()
    await flushPromises()
    const state = wrapper.vm.state as any
    state.openImportModal()
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    const request = deferred<any>()
    vi.mocked(importTransfers).mockReturnValue(request.promise as any)

    const event = fileEvent()
    const pending = state.handleImportFile(event)
    await flushPromises()

    expect(importTransfers).toHaveBeenCalledTimes(1)
    expect(state.importBusy.value).toBe(true)
    state.closeImportModal()
    expect(state.showImportModal.value).toBe(true)

    await state.handleImportFile(fileEvent('second.xlsx'))
    expect(importTransfers).toHaveBeenCalledTimes(1)

    request.resolve({ data: { imported: 1, errors: ['row error'] } })
    await pending
    expect(state.importBusy.value).toBe(false)
  })

  it('shows row errors returned with a whole-file rejection', async () => {
    const wrapper = mountTransferComposable()
    await flushPromises()
    const state = wrapper.vm.state as any
    state.openImportModal()
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    vi.mocked(importTransfers).mockRejectedValue(Object.assign(new Error('Bad Request'), {
      response: {
        data: {
          detail: '文件存在错误，已驳回，未导入任何单据',
          imported: 0,
          imported_lines: 0,
          errors: ['第 3 行: 资产编号 NOT-REGISTERED 未在品目字典登记'],
        },
      },
    }))

    await state.handleImportFile(fileEvent())

    expect(state.importResult.value).toEqual({
      imported: 0,
      errors: ['第 3 行: 资产编号 NOT-REGISTERED 未在品目字典登记'],
      rejected: true,
    })
  })
})

describe('category batch import confirmation', () => {
  it('waits for confirmation and does not write when the user cancels', async () => {
    const wrapper = mount(CategoryImportDialog, { props: { visible: true } })
    const input = wrapper.find('input[type="file"]')
    installFileOnInput(input.element as HTMLInputElement)
    const confirmation = deferred<'confirm'>()
    vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise as any)

    await input.trigger('change')
    await flushPromises()
    expect(importCategories).not.toHaveBeenCalled()
    expect(input.attributes('disabled')).toBeDefined()

    confirmation.reject('cancel')
    await flushPromises()
    expect(importCategories).not.toHaveBeenCalled()
    expect(input.attributes('disabled')).toBeUndefined()
  })

  it('submits once after category import confirmation and locks the dialog during the request', async () => {
    const wrapper = mount(CategoryImportDialog, { props: { visible: true } })
    const input = wrapper.find('input[type="file"]')
    installFileOnInput(input.element as HTMLInputElement)
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    const request = deferred<any>()
    vi.mocked(importCategories).mockReturnValue(request.promise as any)

    await input.trigger('change')
    await flushPromises()
    expect(importCategories).toHaveBeenCalledTimes(1)
    expect(input.attributes('disabled')).toBeDefined()
    expect(wrapper.find('.modal-close').attributes('disabled')).toBeDefined()

    await input.trigger('change')
    expect(importCategories).toHaveBeenCalledTimes(1)

    request.resolve({ data: { imported: 1, errors: [] } })
    await flushPromises()
    expect(wrapper.emitted('success')).toHaveLength(1)
    expect(input.attributes('disabled')).toBeUndefined()
  })
})

describe('inventory result batch import confirmation', () => {
  it('editing users load the regular task list while imports remain part of edit access', async () => {
    permissionState.codes = ['view_inventory', 'edit_inventory']
    const task = {
      id: 'task-importable',
      name: '10 月盘点',
      status: 'in_progress',
      branch: 'branch-1',
      branchName: '北京分公司',
    }
    vi.mocked(getInventoryTasks).mockResolvedValue({
      data: { count: 1, next: null, previous: null, results: [task] },
    } as any)

    const wrapper = shallowMount(Inventory)
    await flushPromises()

    expect(getInventoryTasks).toHaveBeenCalledWith(expect.objectContaining({
      page: 1,
      pageSize: 50,
      status: undefined,
      branchId: undefined,
    }))
    expect(getBranches).not.toHaveBeenCalled()
    expect(getCategories).not.toHaveBeenCalled()

    const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
    expect(taskList.props('importOnly')).toBe(false)
    expect(taskList.props('tasks')).toEqual([task])
  })

  it('编辑权限下的任务列表保留常规信息并允许导入进行中的任务', async () => {
    permissionState.codes = ['view_inventory', 'edit_inventory']
    const task = { id: 'task-1', name: '10 月盘点', status: 'in_progress', branch: 'branch-1' }
    const wrapper = mount(InventoryTaskList, {
      props: {
        loading: false,
        tasks: [task],
        stats: { total: 1, pending: 0, inProgress: 1, pendingReview: 0 },
        filters: { status: '', branch: [], keyword: '' },
        branchOptions: [],
        importBusy: false,
        importOnly: false,
      },
    })

    expect(wrapper.find('.quick-stats').exists()).toBe(true)
    expect(wrapper.find('.filter-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('10 月盘点')
    await wrapper.findAll('.cell-actions button').find(button => button.text() === '导入盘点表')!.trigger('click')
    expect(wrapper.emitted('import')?.[0]?.[0]).toEqual(task)
  })

  it('clears the pending task when the native file picker is cancelled', async () => {
    vi.useFakeTimers()
    try {
      const wrapper = shallowMount(Inventory)
      await flushPromises()
      const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
      await taskList.vm.$emit('import', { id: 'task-1', name: 'Task 1' })

      const input = wrapper.find('input[type="file"]')
      expect(input.attributes('disabled')).toBeDefined()

      vi.runOnlyPendingTimers()
      await flushPromises()
      expect(input.attributes('disabled')).toBeUndefined()
    } finally {
      vi.useRealTimers()
    }
  })

  it('requires confirmation and keeps the inventory import locked until the request completes', async () => {
    const wrapper = shallowMount(Inventory)
    await flushPromises()
    const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
    const task = { id: 'task-1', name: 'Task 1' }
    await taskList.vm.$emit('import', task)

    const input = wrapper.find('input[type="file"]')
    installFileOnInput(input.element as HTMLInputElement)
    const confirmation = deferred<'confirm'>()
    vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise as any)
    const request = deferred<any>()
    vi.mocked(importInventoryResult).mockReturnValue(request.promise as any)
    const event = new Event('change')
    input.element.dispatchEvent(event)

    await flushPromises()
    expect(importInventoryResult).not.toHaveBeenCalled()
    expect(input.attributes('disabled')).toBeDefined()

    confirmation.resolve('confirm')
    await flushPromises()
    expect(importInventoryResult).toHaveBeenCalledTimes(1)
    expect(importInventoryResult).toHaveBeenCalledWith('task-1', expect.any(File))
    expect(input.attributes('disabled')).toBeDefined()

    await taskList.vm.$emit('import', { id: 'task-2', name: 'Task 2' })
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
    expect(input.attributes('disabled')).toBeDefined()

    request.resolve({ data: { imported: 1, errors: [] } })
    await flushPromises()
    expect(input.attributes('disabled')).toBeUndefined()
  })

  it('reports an inventory row error as a whole-file rejection', async () => {
    const wrapper = shallowMount(Inventory)
    await flushPromises()
    const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
    await taskList.vm.$emit('import', { id: 'task-1', name: 'Task 1' })

    const input = wrapper.find('input[type="file"]')
    installFileOnInput(input.element as HTMLInputElement)
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    vi.mocked(importInventoryResult).mockRejectedValue(Object.assign(new Error('Bad Request'), {
      response: {
        data: {
          detail: '文件存在错误，已驳回，未导入任何盘点结果',
          imported: 0,
          errors: ['第 3 行: 资产编号 NOT-IN-TASK 不在盘点范围内'],
        },
      },
    }))

    input.element.dispatchEvent(new Event('change'))
    await flushPromises()

    expect(ElMessageBox.alert).toHaveBeenCalledWith(
      expect.stringContaining('文件存在错误，已驳回'),
      '盘点结果未导入',
      expect.objectContaining({ type: 'error' }),
    )
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })
})
