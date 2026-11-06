import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ replace: vi.fn() }),
}))

vi.mock('@/api/reconciliation', () => ({
  getReconciliationTasks: vi.fn().mockResolvedValue({ data: { results: [], suppliers: [] } }),
  getReconciliationTask: vi.fn().mockResolvedValue({ data: null }),
}))

import { useReconciliationTask } from '@/composables/useReconciliationTask'

describe('useReconciliationTask', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('exposes currentTaskId ref', () => {
    const { currentTaskId } = useReconciliationTask()
    expect(currentTaskId.value).toBe('')
  })

  it('setTask updates currentTaskId', () => {
    const { currentTaskId, setTask } = useReconciliationTask()
    setTask('abc')
    expect(currentTaskId.value).toBe('abc')
  })
})
