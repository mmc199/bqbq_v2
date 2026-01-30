<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { X, ChevronLeft, ChevronRight, Download, Copy, ZoomIn, ZoomOut, RotateCw } from 'lucide-vue-next'
import type { MemeImage } from '@/types'
import { useToast } from '@/composables/useToast'

const props = defineProps<{
  image: MemeImage | null
  currentIndex: number
  totalCount: number
}>()

const emit = defineEmits<{
  'close': []
  'navigate': [direction: 'prev' | 'next']
}>()

const toast = useToast()

// 缩放和旋转状态
const scale = ref(1)
const rotation = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const position = ref({ x: 0, y: 0 })

// 图片 URL
const imageUrl = computed(() => {
  if (!props.image) return ''
  return `/images/${props.image.filename}`
})

// 重置变换
function resetTransform() {
  scale.value = 1
  rotation.value = 0
  position.value = { x: 0, y: 0 }
}

// 缩放
function zoomIn() {
  scale.value = Math.min(scale.value * 1.25, 5)
}

function zoomOut() {
  scale.value = Math.max(scale.value / 1.25, 0.25)
}

// 旋转
function rotate() {
  rotation.value = (rotation.value + 90) % 360
}

// 下载图片
async function downloadImage() {
  if (!props.image) return
  try {
    const response = await fetch(imageUrl.value)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.image.filename
    a.click()
    URL.revokeObjectURL(url)
    toast.success('下载成功')
  } catch {
    toast.error('下载失败')
  }
}

// 复制图片
async function copyImage() {
  if (!props.image) return
  try {
    const response = await fetch(imageUrl.value)
    const blob = await response.blob()
    await navigator.clipboard.write([
      new ClipboardItem({ [blob.type]: blob })
    ])
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败')
  }
}

// 拖拽移动
function handleMouseDown(e: MouseEvent) {
  if (scale.value <= 1) return
  isDragging.value = true
  dragStart.value = { x: e.clientX - position.value.x, y: e.clientY - position.value.y }
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  position.value = {
    x: e.clientX - dragStart.value.x,
    y: e.clientY - dragStart.value.y
  }
}

function handleMouseUp() {
  isDragging.value = false
}

// 滚轮缩放
function handleWheel(e: WheelEvent) {
  e.preventDefault()
  if (e.deltaY < 0) {
    zoomIn()
  } else {
    zoomOut()
  }
}

// 键盘导航
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('close')
  } else if (e.key === 'ArrowLeft') {
    emit('navigate', 'prev')
  } else if (e.key === 'ArrowRight') {
    emit('navigate', 'next')
  }
}

// 切换图片时重置变换
watch(() => props.image, () => {
  resetTransform()
})

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="preview">
      <div
        v-if="image"
        class="fixed inset-0 z-[4000] bg-black/90 flex items-center justify-center"
        @click.self="emit('close')"
        @wheel="handleWheel"
      >
        <!-- 顶部工具栏 -->
        <div class="absolute top-0 left-0 right-0 h-16 bg-gradient-to-b from-black/60 to-transparent flex items-center justify-between px-6 z-10">
          <div class="text-white/80 text-sm">
            <span class="font-medium">{{ image.filename }}</span>
            <span class="ml-4 text-white/50">{{ currentIndex + 1 }} / {{ totalCount }}</span>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all"
              title="缩小"
              @click="zoomOut"
            >
              <ZoomOut class="w-5 h-5" />
            </button>
            <span class="text-white/60 text-sm min-w-[50px] text-center">{{ Math.round(scale * 100) }}%</span>
            <button
              class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all"
              title="放大"
              @click="zoomIn"
            >
              <ZoomIn class="w-5 h-5" />
            </button>
            <button
              class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all"
              title="旋转"
              @click="rotate"
            >
              <RotateCw class="w-5 h-5" />
            </button>
            <div class="w-px h-6 bg-white/20 mx-2" />
            <button
              class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all"
              title="下载"
              @click="downloadImage"
            >
              <Download class="w-5 h-5" />
            </button>
            <button
              class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all"
              title="复制"
              @click="copyImage"
            >
              <Copy class="w-5 h-5" />
            </button>
            <div class="w-px h-6 bg-white/20 mx-2" />
            <button
              class="p-2 rounded-lg text-white/70 hover:text-white hover:bg-red-500/20 transition-all"
              title="关闭 (Esc)"
              @click="emit('close')"
            >
              <X class="w-5 h-5" />
            </button>
          </div>
        </div>

        <!-- 图片容器 -->
        <div
          class="relative max-w-[90vw] max-h-[85vh] overflow-hidden"
          :class="{ 'cursor-grab': scale > 1, 'cursor-grabbing': isDragging }"
          @mousedown="handleMouseDown"
        >
          <img
            :src="imageUrl"
            :alt="image.filename"
            class="max-w-full max-h-[85vh] object-contain select-none transition-transform duration-150"
            :style="{
              transform: `translate(${position.x}px, ${position.y}px) scale(${scale}) rotate(${rotation}deg)`,
            }"
            draggable="false"
          />
        </div>

        <!-- 左右导航按钮 -->
        <button
          v-if="currentIndex > 0"
          class="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-all"
          title="上一张 (←)"
          @click="emit('navigate', 'prev')"
        >
          <ChevronLeft class="w-8 h-8" />
        </button>
        <button
          v-if="currentIndex < totalCount - 1"
          class="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-all"
          title="下一张 (→)"
          @click="emit('navigate', 'next')"
        >
          <ChevronRight class="w-8 h-8" />
        </button>

        <!-- 底部信息栏 -->
        <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-6 pt-12">
          <div class="flex flex-wrap gap-2">
            <span
              v-for="tag in image.tags.split(' ').filter(t => t)"
              :key="tag"
              class="px-3 py-1 bg-white/20 text-white text-sm rounded-full"
            >
              {{ tag }}
            </span>
          </div>
          <div class="mt-2 text-white/50 text-xs">
            {{ image.width }}×{{ image.height }} · {{ image.file_size ? Math.round(image.file_size / 1024) + ' KB' : '' }}
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.preview-enter-active,
.preview-leave-active {
  transition: opacity 0.2s ease;
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
}
</style>
