import { type Ref, onBeforeUnmount } from 'vue'

const focusableSelectors = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  '[tabindex]:not([tabindex="-1"])'
].join(',')

type FocusTrapOptions = {
  initialFocusSelector?: string
}

export function useFocusTrap(
  containerRef: Ref<HTMLElement | null>,
  options: FocusTrapOptions = {}
) {
  const { initialFocusSelector } = options
  let isActive = false
  let focusTimer: ReturnType<typeof setTimeout> | null = null

  const getFocusableElements = (): HTMLElement[] => {
    if (!containerRef.value) return []
    return Array.from(
      containerRef.value.querySelectorAll<HTMLElement>(focusableSelectors)
    ).filter((el) =>
      el.offsetParent !== null &&
      window.getComputedStyle(el).visibility !== 'hidden'
    )
  }

  const handleKeydown = (e: KeyboardEvent) => {
    if (!isActive || e.key !== 'Tab' || !containerRef.value) return
    const focusables = getFocusableElements()
    if (focusables.length === 0) return

    const first = focusables[0]
    const last = focusables[focusables.length - 1]

    if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
      return
    }

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    }
  }

  const focusFirst = () => {
    if (!containerRef.value) return
    const focusables = getFocusableElements()
    if (focusables.length > 0) {
      if (initialFocusSelector) {
        const initial = containerRef.value.querySelector<HTMLElement>(initialFocusSelector)
        if (initial) {
          initial.focus()
          return
        }
      }
      focusables[0].focus()
    }
  }

  const activateTrap = () => {
    if (isActive) return
    isActive = true
    document.addEventListener('keydown', handleKeydown)
    // 延迟聚焦以确保 DOM 已更新
    focusTimer = setTimeout(focusFirst, 10)
  }

  const deactivateTrap = () => {
    if (!isActive) return
    isActive = false
    document.removeEventListener('keydown', handleKeydown)
    if (focusTimer) {
      clearTimeout(focusTimer)
      focusTimer = null
    }
  }

  // 组件卸载时自动清理，防止事件监听器泄漏
  onBeforeUnmount(() => {
    deactivateTrap()
  })

  return { activateTrap, deactivateTrap, focusFirst }
}
