<script setup lang="ts">
/**
 * ToastContainer 组件 - 全局通知容器
 */
import { useToast, type ToastMessage } from '@/composables/useToast'
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-vue-next'

const { toasts, remove } = useToast()

function getIcon(type: ToastMessage['type']) {
  switch (type) {
    case 'success': return CheckCircle
    case 'error': return XCircle
    case 'warning': return AlertTriangle
    default: return Info
  }
}

function getBgColor(type: ToastMessage['type']) {
  switch (type) {
    case 'success': return 'bg-green-500'
    case 'error': return 'bg-red-500'
    case 'warning': return 'bg-orange-500'
    default: return 'bg-blue-500'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-8 right-8 z-[100] flex flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-white font-medium min-w-[280px] max-w-[400px]',
            getBgColor(toast.type)
          ]"
        >
          <component :is="getIcon(toast.type)" class="w-5 h-5 flex-shrink-0" />
          <span class="flex-1">{{ toast.message }}</span>
          <button
            class="p-1 hover:bg-white/20 rounded transition-colors flex-shrink-0"
            @click="remove(toast.id)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
