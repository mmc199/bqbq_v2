<script setup lang="ts">
/**
 * ToastContainer 组件 - 全局通知容器
 * 一比一复刻旧项目样式：白色背景 + 左侧彩色边框
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

function getIconColor(type: ToastMessage['type']) {
  switch (type) {
    case 'success': return 'text-green-500'
    case 'error': return 'text-red-500'
    case 'warning': return 'text-amber-500'
    default: return 'text-blue-500'
  }
}

function getBorderColor(type: ToastMessage['type']) {
  switch (type) {
    case 'success': return 'border-l-green-500'
    case 'error': return 'border-l-red-500'
    case 'warning': return 'border-l-amber-500'
    default: return 'border-l-blue-500'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'toast-item border-l-4',
            getBorderColor(toast.type)
          ]"
        >
          <component :is="getIcon(toast.type)" :class="['w-5 h-5 flex-shrink-0', getIconColor(toast.type)]" />
          <span class="flex-1 text-sm text-slate-700">{{ toast.message }}</span>
          <button
            class="w-6 h-6 rounded-md flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-all flex-shrink-0"
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
