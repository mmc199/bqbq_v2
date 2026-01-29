/**
 * Toast 通知 composable
 */
import { ref } from 'vue'

export interface ToastMessage {
  id: number
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
}

const toasts = ref<ToastMessage[]>([])
let nextId = 0

export function useToast() {
  function show(message: string, type: ToastMessage['type'] = 'info', duration = 3000) {
    const id = nextId++
    toasts.value.push({ id, message, type })

    setTimeout(() => {
      remove(id)
    }, duration)

    return id
  }

  function remove(id: number) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function success(message: string, duration?: number) {
    return show(message, 'success', duration)
  }

  function error(message: string, duration?: number) {
    return show(message, 'error', duration)
  }

  function info(message: string, duration?: number) {
    return show(message, 'info', duration)
  }

  function warning(message: string, duration?: number) {
    return show(message, 'warning', duration)
  }

  return {
    toasts,
    show,
    remove,
    success,
    error,
    info,
    warning,
  }
}
