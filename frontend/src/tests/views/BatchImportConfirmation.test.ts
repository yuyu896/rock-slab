import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount, shallowMount } from '@vue/test-utils'
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

function installFileOnInput(input: HTMLInputElement, fileNameOrFile: string | File = 'import.xlsx') {
  const file = typeof fileNameOrFile === 'string'
    ? new File(['content'], fileNameOrFile)
    : fileNameOrFile
  const selection = new DataTransfer()
  selection.items.add(file)
  input.files = selection.files
  return file
}

enableAutoUnmount(afterEach)

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
  async function mountImport() {
    const wrapper = shallowMount(Inventory)
    await flushPromises()
    const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
    const input = wrapper.find('input[type="file"]')
    const element = input.element as HTMLInputElement
    const open = async (id = 'task-1') => {
      await taskList.vm.$emit('import', { id, name: id, status: 'in_progress' })
    }
    const choose = async (fileNameOrFile: string | File = 'import.xlsx') => {
      const file = installFileOnInput(element, fileNameOrFile)
      // dispatchEvent also exercises handler guards against duplicate native events.
      element.dispatchEvent(new Event('change'))
      await flushPromises()
      return file
    }
    const expectReady = () => {
      expect(taskList.props('importBusy')).toBe(false)
      expect(element.disabled).toBe(false)
      expect(element.value).toBe('')
      expect(element.files?.length).toBe(0)
    }
    return { wrapper, taskList, input, element, open, choose, expectReady }
  }

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

  it.each(['ledger', 'instance'])('imports the original %s task after waiting in the file picker', async (inventoryKind) => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      const wrapper = shallowMount(Inventory)
      await flushPromises()
      const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
      const task = { id: `task-${inventoryKind}`, name: 'Task 1', inventoryKind }
      await taskList.vm.$emit('import', task)
      vi.advanceTimersByTime(150)
      await flushPromises()

      const input = wrapper.find('input[type="file"]')
      const file = installFileOnInput(input.element as HTMLInputElement)
      const confirmation = deferred<'confirm'>()
      vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise as any)
      await input.trigger('change')
      await flushPromises()

      expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
      expect(importInventoryResult).not.toHaveBeenCalled()
      confirmation.resolve('confirm')
      await flushPromises()
      expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith(task.id, file)
      expect(input.attributes('disabled')).toBeUndefined()
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })

  it('clears a cancelled native picker without relying on an elapsed timer', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      const wrapper = shallowMount(Inventory)
      await flushPromises()
      const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
      await taskList.vm.$emit('import', { id: 'task-1', name: 'Task 1' })
      const input = wrapper.find('input[type="file"]')
      await input.trigger('cancel')

      expect(input.attributes('disabled')).toBeUndefined()
      expect(taskList.props('importBusy')).toBe(false)
      installFileOnInput(input.element as HTMLInputElement)
      await input.trigger('change')
      await flushPromises()
      expect(ElMessageBox.confirm).not.toHaveBeenCalled()
      expect(importInventoryResult).not.toHaveBeenCalled()
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })

  it('can reopen for another task when the browser sends no cancel event', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      const wrapper = shallowMount(Inventory)
      await flushPromises()
      const taskList = wrapper.findComponent({ name: 'InventoryTaskList' })
      const input = wrapper.find('input[type="file"]')
      const openPicker = vi.spyOn(input.element as HTMLInputElement, 'click')
      await taskList.vm.$emit('import', { id: 'task-1', name: 'Task 1' })
      // A cancelled picker need not dispatch cancel in every browser.
      await taskList.vm.$emit('import', { id: 'task-2', name: 'Task 2' })

      expect(openPicker).toHaveBeenCalledTimes(2)
      const file = installFileOnInput(input.element as HTMLInputElement)
      vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
      await input.trigger('change')
      await flushPromises()
      expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-2', file)
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
    }
  })

  it('keeps the file input usable while waiting for selection and switches tasks after explicit cancel', async () => {
    const { taskList, input, element, open, choose, expectReady } = await mountImport()
    await open('task-1')
    expect(element.disabled).toBe(false)
    expect(taskList.props('importBusy')).toBe(false)
    await input.trigger('cancel')
    expectReady()
    expect(ElMessageBox.confirm).not.toHaveBeenCalled()
    expect(importInventoryResult).not.toHaveBeenCalled()

    await open('task-2')
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    const file = await choose()
    expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-2', file)
    expectReady()
  })

  it.each(['cancel', 'close'])('can select the same file again after confirmation %s', async (reason) => {
    const { open, choose, expectReady } = await mountImport()
    const file = new File(['content'], 'same.xlsx')
    vi.mocked(ElMessageBox.confirm).mockRejectedValueOnce(reason)
    await open()
    await choose(file)
    expect(importInventoryResult).not.toHaveBeenCalled()
    expect(ElMessage.error).not.toHaveBeenCalled()
    expectReady()

    vi.mocked(ElMessageBox.confirm).mockResolvedValueOnce('confirm' as any)
    await open()
    await choose(file)
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(2)
    expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-1', file)
    expectReady()
  })

  it('can select a valid file after an invalid extension without losing the target', async () => {
    const { open, choose, expectReady } = await mountImport()
    await open()
    await choose('invalid.csv')
    expect(ElMessage.warning).toHaveBeenCalledWith(expect.stringContaining('Excel'))
    expect(ElMessageBox.confirm).not.toHaveBeenCalled()
    expect(importInventoryResult).not.toHaveBeenCalled()
    expectReady()

    await open('task-2')
    vi.mocked(ElMessageBox.confirm).mockResolvedValueOnce('confirm' as any)
    const file = await choose()
    expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-2', file)
    expectReady()
  })

  it.each(['success', 'network error', 'whole-file rejection'])('can reselect the same file after %s', async (outcome) => {
    const { open, choose, expectReady } = await mountImport()
    const file = new File(['content'], 'same.xlsx')
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    if (outcome === 'network error') {
      vi.mocked(importInventoryResult).mockRejectedValueOnce(new Error('Network Error'))
    } else if (outcome === 'whole-file rejection') {
      vi.mocked(importInventoryResult).mockRejectedValueOnce(Object.assign(new Error('Bad Request'), {
        response: {
          data: {
            detail: '文件存在错误，已驳回，未导入任何盘点结果',
            imported: 0,
            errors: ['第 3 行: 资产编号 NOT-IN-TASK 不在盘点范围内'],
          },
        },
      }))
    }
    await open()
    await choose(file)
    expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-1', file)
    if (outcome === 'success') {
      expect(ElMessage.success).toHaveBeenCalledWith(expect.stringContaining('导入成功'))
    } else if (outcome === 'network error') {
      expect(ElMessage.error).toHaveBeenCalledWith('Network Error')
    } else {
      expect(ElMessageBox.alert).toHaveBeenCalledWith(
        '整份文件未导入。有 1 条记录不属于本次盘点清单。请核对盘点表后重新上传。',
        '盘点结果未导入',
        expect.objectContaining({ type: 'error' }),
      )
    }
    expectReady()

    await open()
    await choose(file)
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(2)
    expect(importInventoryResult).toHaveBeenCalledTimes(2)
    expect(importInventoryResult).toHaveBeenNthCalledWith(2, 'task-1', file)
    expectReady()
  })

  it('preserves the original task and File through duplicate events during confirmation and upload', async () => {
    const { taskList, input, element, open, choose, expectReady } = await mountImport()
    const confirmation = deferred<'confirm'>()
    vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise as any)
    const request = deferred<any>()
    vi.mocked(importInventoryResult).mockReturnValue(request.promise as any)
    await open('task-1')
    const originalFile = await choose('original.xlsx')
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
    expect(importInventoryResult).not.toHaveBeenCalled()
    expect(taskList.props('importBusy')).toBe(true)
    expect(element.disabled).toBe(true)

    await open('task-2')
    await choose('replacement.xlsx')
    await input.trigger('cancel')
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
    expect(importInventoryResult).not.toHaveBeenCalled()
    expect(taskList.props('importBusy')).toBe(true)
    expect(element.disabled).toBe(true)

    confirmation.resolve('confirm')
    await flushPromises()
    expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-1', originalFile)
    expect(taskList.props('importBusy')).toBe(true)
    expect(element.disabled).toBe(true)

    await open('task-3')
    await choose('another.xlsx')
    await input.trigger('cancel')
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(1)
    expect(importInventoryResult).toHaveBeenCalledExactlyOnceWith('task-1', originalFile)
    expect(taskList.props('importBusy')).toBe(true)
    expect(element.disabled).toBe(true)

    request.resolve({ data: { imported: 1, errors: [] } })
    await flushPromises()
    expectReady()
  })

  it.each(['file selection', 'confirmation'])('does not upload after leaving the page during %s', async (phase) => {
    const { wrapper, element, open, choose } = await mountImport()
    const confirmation = deferred<'confirm'>()
    vi.mocked(ElMessageBox.confirm).mockReturnValue(confirmation.promise as any)
    await open()
    if (phase === 'confirmation') {
      await choose()
    } else {
      installFileOnInput(element)
    }

    wrapper.unmount()
    expect(element.value).toBe('')
    expect(element.files?.length).toBe(0)
    confirmation.resolve('confirm')
    element.dispatchEvent(new Event('change'))
    await flushPromises()
    expect(ElMessageBox.confirm).toHaveBeenCalledTimes(phase === 'confirmation' ? 1 : 0)
    expect(importInventoryResult).not.toHaveBeenCalled()
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

  it.each(['400 rejection', 'legacy 200 errors'])('summarizes five out-of-scope records in a %s without listing rows or codes', async (responseType) => {
    const { open, choose, expectReady } = await mountImport()
    const errors = [
      '第 3 行: 资产编号 "ASSET-A" 不在盘点范围内',
      '第 4 行: 内部编号 "INSTANCE-B" 不在盘点范围内',
      '第 5 行: 资产编号 "ASSET-C" 不在盘点范围内',
      '第 6 行: 内部编号 "INSTANCE-D" 不在盘点范围内',
      '第 7 行: 资产编号 "ASSET-E" 不在盘点范围内',
    ]
    const data = { detail: '文件存在错误，已驳回，未导入任何盘点结果', imported: 0, errors }
    if (responseType === '400 rejection') {
      vi.mocked(importInventoryResult).mockRejectedValueOnce(Object.assign(new Error('Bad Request'), {
        response: { status: 400, data },
      }))
    } else {
      vi.mocked(importInventoryResult).mockResolvedValueOnce({ data } as any)
    }
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    await open()
    await choose()

    expect(ElMessageBox.alert).toHaveBeenCalledExactlyOnceWith(
      '整份文件未导入。有 5 条记录不属于本次盘点清单。请核对盘点表后重新上传。',
      '盘点结果未导入',
      expect.objectContaining({ type: 'error' }),
    )
    const message = String(vi.mocked(ElMessageBox.alert).mock.calls[0]?.[0])
    expect(message).not.toMatch(/第 \d+ 行|ASSET-|INSTANCE-/)
    expect(ElMessage.success).not.toHaveBeenCalled()
    expect(ElMessage.warning).not.toHaveBeenCalled()
    expectReady()
  })

  it('groups mixed inventory errors by reason and count without exposing row details', async () => {
    const { open, choose, expectReady } = await mountImport()
    vi.mocked(importInventoryResult).mockRejectedValueOnce(Object.assign(new Error('Bad Request'), {
      response: {
        status: 400,
        data: {
          imported: 0,
          errors: [
            '第 3 行: 资产编号 "ASSET-A" 不在盘点范围内',
            '第 4 行: 内部编号 "INSTANCE-B" 不在盘点范围内',
            '第 5 行: 实盘数量必须为整数 "1.2"',
            '第 6 行: 实盘数量必须为整数 "invalid"',
            '第 7 行: 核对结果须为「已找到/未找到」，实际 "待定"',
            '第 8 行: 核对结果须为「已找到/未找到」，实际 "未知"',
            '第 9 行: 无法识别填写内容 "PRIVATE-VALUE"',
            '第 10 行: 其他未知错误 "PRIVATE-CODE"',
          ],
        },
      },
    }))
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    await open()
    await choose()

    expect(ElMessageBox.alert).toHaveBeenCalledTimes(1)
    const message = String(vi.mocked(ElMessageBox.alert).mock.calls[0]?.[0])
    expect(message).toContain('整份文件未导入。')
    expect(message).toContain('有 2 条记录不属于本次盘点清单。')
    expect(message).toContain('有 2 条记录的实盘数量格式不正确。')
    expect(message).toContain('有 2 条记录的核对结果格式不正确。')
    expect(message).toContain('有 2 条记录存在其他填写错误。')
    expect(message).toContain('请核对盘点表后重新上传。')
    expect(message).not.toMatch(/第 \d+ 行|ASSET-|INSTANCE-|PRIVATE-|1\.2|invalid|待定|未知/)
    expect(ElMessage.success).not.toHaveBeenCalled()
    expectReady()
  })

  it.each(['400 rejection', 'legacy 200 errors'])('preserves the empty-checklist hint once with the %s summary', async (responseType) => {
    const { open, choose } = await mountImport()
    const hint = '本次盘点清单为空，请核对任务范围后重新开始盘点。'
    const data = {
      imported: 0,
      errors: ['第 3 行: 资产编号 "NOT-IN-TASK" 不在盘点范围内'],
      hint,
    }
    if (responseType === '400 rejection') {
      vi.mocked(importInventoryResult).mockRejectedValueOnce(Object.assign(new Error('Bad Request'), {
        response: { status: 400, data },
      }))
    } else {
      vi.mocked(importInventoryResult).mockResolvedValueOnce({ data } as any)
    }
    vi.mocked(ElMessageBox.confirm).mockResolvedValue('confirm' as any)
    await open()
    await choose()

    expect(ElMessageBox.alert).toHaveBeenCalledTimes(1)
    const message = String(vi.mocked(ElMessageBox.alert).mock.calls[0]?.[0])
    expect(message).toContain('有 1 条记录不属于本次盘点清单。')
    const displayedMessages = [
      message,
      ...vi.mocked(ElMessage.warning).mock.calls.map(call => String(call[0])),
    ].join('\n')
    expect(displayedMessages.split(hint)).toHaveLength(2)
    expect(message).not.toMatch(/第 3 行|NOT-IN-TASK/)
    if (responseType === 'legacy 200 errors') {
      expect(ElMessage.warning).toHaveBeenCalledExactlyOnceWith(hint)
    } else {
      expect(ElMessage.warning).not.toHaveBeenCalled()
    }
    expect(ElMessage.success).not.toHaveBeenCalled()
  })
})
