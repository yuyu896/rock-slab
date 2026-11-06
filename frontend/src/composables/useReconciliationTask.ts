import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReconciliationTasks, getReconciliationTask } from '@/api/reconciliation'
import type { ReconciliationTask } from '@/api/reconciliation'

// Module-level refs — shared state across all component instances (singleton pattern)
const currentTaskId = ref('')
const currentTask = ref<ReconciliationTask | null>(null)
const taskOptions = ref<Array<{ value: string; label: string }>>([])
// Guard: track whether we've already restored from URL so it only runs once per session
let restoredFromUrl = false

export function useReconciliationTask() {
  const route = useRoute()
  const router = useRouter()

  async function loadTaskOptions() {
    try {
      const { data } = await getReconciliationTasks()
      taskOptions.value = (data.results ?? []).map((task) => ({
        value: task.id,
        label: `${task.supplierName} ${task.period}`,
      }))
    } catch {
      // silently ignore — caller decides error handling
    }
  }

  async function setTask(id: string) {
    if (!id) return
    currentTaskId.value = id
    try {
      router.replace({ query: { ...route.query, task: id } })
    } catch {
      // ignore navigation errors
    }
    try {
      const { data } = await getReconciliationTask(id)
      currentTask.value = data
    } catch {
      // silently ignore — caller decides error handling
    }
  }

  function clearTask() {
    currentTaskId.value = ''
    currentTask.value = null
  }

  // Fix 1: initialise from route.query.task on first call (once per session)
  if (!restoredFromUrl && currentTaskId.value === '') {
    restoredFromUrl = true
    const queryTask = route.query.task
    if (typeof queryTask === 'string' && queryTask) {
      setTask(queryTask)
    }
  }

  return {
    currentTaskId,
    currentTask,
    taskOptions,
    loadTaskOptions,
    setTask,
    clearTask,
  }
}
