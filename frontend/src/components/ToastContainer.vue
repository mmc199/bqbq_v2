<script setup lang="ts">
/**
 * ToastContainer 组件 - 全局通知容器
 * 复刻旧项目样式：右下角彩色块、文字加粗、滑入滑出
 */
import { useToast, type ToastMessage } from '@/composables/useToast'

const { toasts } = useToast()

function getBg(type: ToastMessage['type']) {
  switch (type) {
    case 'success':
      return 'bg-emerald-500'
    case 'error':
      return 'bg-red-500'
    case 'warning':
      return 'bg-amber-500'
    default:
      return 'bg-blue-500'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-8 right-8 z-50 flex flex-col gap-3">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'px-4 py-3 rounded-xl shadow-2xl text-white font-bold transform transition-all duration-300',
            getBg(toast.type)
          ]"
        >
          {{ toast.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
