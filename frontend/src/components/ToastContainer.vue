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
      return 'bg-green-500'
    case 'error':
      return 'bg-red-500'
    default:
      return 'bg-blue-500'
  }
}
</script>

<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'fixed bottom-8 right-8 p-4 rounded-xl shadow-2xl text-white font-bold z-50 transform transition-all duration-300',
          getBg(toast.type)
        ]"
      >
        {{ toast.message }}
      </div>
    </TransitionGroup>
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
