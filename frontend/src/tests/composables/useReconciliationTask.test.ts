import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'

// Mutable mock state so each test can configure route.query / api responses independently.
// vi.hoisted keeps the object reference stable across vi.resetModules() re-evaluations.
const mockState = vi.hoisted(() => ({
  route: { query: {} as Record<string, unknown> },
  replace: vi.fn(),
  tasksResponse: { results: [] as unknown[], suppliers: [] as unknown[] },
  taskResponse: null as unknown,
}))

vi.mock('vue-router', () => ({
  useRoute: () => mockState.route,
  useRouter: () => ({ replace: mockState.replace }),
}))

vi.mock('@/api/reconciliation', () => ({
  getReconciliationTasks: vi.fn(async () => ({ data: mockState.tasksResponse })),
  getReconciliationTask: vi.fn(async () => ({ data: mockState.taskResponse })),
}))

async function importComposable() {
  const mod = await import('@/composables/useReconciliationTask')
  return mod.useReconciliationTask
}

describe('useReconciliationTask', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.resetModules()
    mockState.route = { query: {} }
    mockState.tasksResponse = { results: [], suppliers: [] }
    mockState.taskResponse = null
  })

  it('exposes currentTaskId ref', async () => {
    const useReconciliationTask = await importComposable()
    const { currentTaskId } = useReconciliationTask()
    expect(currentTaskId.value).toBe('')
  })

  it('setTask updates currentTaskId', async () => {
    const useReconciliationTask = await importComposable()
    const { currentTaskId, setTask } = useReconciliationTask()
    setTask('abc')
    expect(currentTaskId.value).toBe('abc')
  })

  it('initializes currentTaskId from route.query.task on first call', async () => {
    mockState.route = { query: { task: 'abc' } }
    mockState.taskResponse = { id: 'abc', supplierName: '测试', period: '2026-09' }
    const useReconciliationTask = await importComposable()
    const { currentTaskId } = useReconciliationTask()
    await flushPromises()
    expect(currentTaskId.value).toBe('abc')
  })
})
