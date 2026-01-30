<script setup lang="ts">
/**
 * MemeCard 组件 - 图片卡片
 * 复刻旧项目的视觉效果：标签文字阴影、回收站样式、缩略图/HQ模式等
 */
import { ref, computed, watch } from 'vue'
import { Download, Copy, Trash2, RefreshCw, Check, RotateCw, CheckCircle2 } from 'lucide-vue-next'
import type { MemeImage } from '@/types'

// Props
const props = defineProps<{
  image: MemeImage
  preferHQ?: boolean
  isTrash?: boolean
  index?: number
  selectable?: boolean
  selected?: boolean
  tempMode?: boolean
}>()

// Emits
const emit = defineEmits<{
  'copy': [image: MemeImage]
  'delete': [image: MemeImage]
  'clickTag': [tag: string]
  'edit': [image: MemeImage]
  'select': [image: MemeImage]
  'preview': [image: MemeImage]
  'applyTempTags': [image: MemeImage]
}>()

// 状态
const isLoading = ref(true)
const copySuccess = ref(false)
const imageError = ref(false)
const isLoadingHQ = ref(false)
const currentSrcType = ref<'thumbnail' | 'original'>('thumbnail')

// 右键菜单状态
const showContextMenu = ref(false)
const contextMenuPos = ref({ x: 0, y: 0 })

// 首屏前 4 张图片使用 eager 加载
const EAGER_LOAD_COUNT = 4

// 计算属性
const imageSrc = computed(() => `/images/${props.image.filename}`)
const thumbnailSrc = computed(() => {
  // 缩略图使用 md5_thumbnail.jpg 格式
  const md5 = props.image.md5
  return `/thumbnails/${md5}_thumbnail.jpg`
})

// 当前显示的图片源
const currentSrc = computed(() => {
  if (props.preferHQ || currentSrcType.value === 'original') {
    return imageSrc.value
  }
  return thumbnailSrc.value
})

// 图片加载策略
const loadingStrategy = computed(() => {
  return (props.index ?? 0) < EAGER_LOAD_COUNT ? 'eager' : 'lazy'
})

const fileSize = computed(() => {
  if (!props.image.file_size) return ''
  return (props.image.file_size / (1024 * 1024)).toFixed(3) + 'MB'
})

const tags = computed(() => {
  if (!props.image.tags) return []
  return props.image.tags.split(' ').filter(t => t.trim())
})

const isTempMode = computed(() => !!props.tempMode)

// 判断是否为回收站图片
const isTrashImage = computed(() => {
  return tags.value.includes('trash_bin')
})

// 监听 preferHQ 变化
watch(() => props.preferHQ, (newVal) => {
  if (newVal && currentSrcType.value === 'thumbnail') {
    loadOriginalImage()
  }
})

// 方法
function handleCopy() {
  emit('copy', props.image)
  copySuccess.value = true
  setTimeout(() => {
    copySuccess.value = false
  }, 1500)
}

function handleDelete() {
  emit('delete', props.image)
}

function handleTagClick(tag: string) {
  emit('clickTag', tag)
}

function handleCardClick() {
  if (isTempMode.value) {
    emit('applyTempTags', props.image)
    return
  }
  if (props.selectable) {
    emit('select', props.image)
  } else {
    emit('edit', props.image)
  }
}

// 右键菜单
function handleContextMenu(e: MouseEvent) {
  e.preventDefault()
  contextMenuPos.value = { x: e.clientX, y: e.clientY }
  showContextMenu.value = true

  // 点击其他地方关闭菜单
  const closeMenu = () => {
    showContextMenu.value = false
    document.removeEventListener('click', closeMenu)
  }
  setTimeout(() => {
    document.addEventListener('click', closeMenu)
  }, 0)
}

function handlePreview() {
  showContextMenu.value = false
  emit('preview', props.image)
}

function handleContextEdit() {
  showContextMenu.value = false
  emit('edit', props.image)
}

function handleContextCopy() {
  showContextMenu.value = false
  handleCopy()
}

function handleContextDelete() {
  showContextMenu.value = false
  handleDelete()
}

async function handleDownload() {
  showContextMenu.value = false
  try {
    const response = await fetch(imageSrc.value)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.image.filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('下载失败:', err)
  }
}

function handleImageError() {
  // 如果缩略图加载失败，尝试加载原图
  if (currentSrcType.value === 'thumbnail') {
    currentSrcType.value = 'original'
  } else {
    imageError.value = true
    isLoading.value = false
  }
}

function handleImageLoad() {
  isLoading.value = false
  isLoadingHQ.value = false
  imageError.value = false
}

function loadOriginalImage() {
  if (currentSrcType.value === 'original') return
  isLoadingHQ.value = true
  currentSrcType.value = 'original'
}
</script>

<template>
  <div
    :class="[
      'meme-card group relative rounded-xl overflow-hidden shadow-md cursor-pointer aspect-square transition-all duration-200 hover:-translate-y-1 hover:shadow-xl',
      isTrashImage && !isTrash ? 'is-trash' : 'bg-white',
      selected ? 'ring-4 ring-blue-500 ring-offset-2' : '',
      isTempMode ? 'temp-mode-card' : ''
    ]"
    @click="handleCardClick"
    @contextmenu="handleContextMenu"
    @dblclick.prevent="handlePreview"
  >
    <!-- 选择指示器 -->
    <div
      v-if="selectable"
      :class="[
        'absolute top-2 left-2 z-40 w-7 h-7 rounded-full flex items-center justify-center transition-all',
        selected ? 'bg-blue-500 text-white' : 'bg-black/30 text-white/70 hover:bg-black/50'
      ]"
    >
      <CheckCircle2 v-if="selected" class="w-5 h-5" />
      <div v-else class="w-4 h-4 rounded-full border-2 border-white/70" />
    </div>

    <div
      v-if="isTempMode"
      class="temp-mode-pill"
    >
      批量打标
    </div>

    <!-- 图片 -->
    <img
      :src="currentSrc"
      :alt="image.filename"
      class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      :loading="loadingStrategy"
      @load="handleImageLoad"
      @error="handleImageError"
    />

    <!-- 加载指示器 -->
    <div
      v-if="isLoading && !imageError"
      class="absolute inset-0 flex items-center justify-center bg-slate-100"
    >
      <RefreshCw class="w-8 h-8 text-slate-400 animate-spin" />
    </div>

    <!-- HQ 加载指示器 -->
    <div
      v-if="isLoadingHQ"
      class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white drop-shadow-md z-10"
    >
      <RotateCw class="w-8 h-8 animate-spin" />
    </div>

    <!-- 错误提示 -->
    <div
      v-if="imageError"
      class="load-failed absolute inset-0 flex items-center justify-center text-slate-400 text-xs"
    >
      加载失败
    </div>

    <!-- 顶部工具栏 - 悬停显示 -->
    <div
      class="card-toolbar absolute top-0 left-0 right-0 p-2 flex justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-30"
      style="background: linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, transparent 100%);"
    >
      <!-- 下载按钮 -->
      <button
        class="w-8 h-8 rounded-lg bg-white/90 text-slate-600 flex items-center justify-center hover:bg-white hover:scale-110 transition-all"
        title="下载"
        @click="handleDownload"
      >
        <Download class="w-4 h-4" />
      </button>

      <!-- 复制按钮 -->
      <button
        class="w-8 h-8 rounded-lg bg-white/90 text-slate-600 flex items-center justify-center hover:bg-white hover:scale-110 transition-all"
        title="复制"
        @click.stop="handleCopy"
      >
        <Check v-if="copySuccess" class="w-4 h-4 text-green-500" />
        <Copy v-else class="w-4 h-4" />
      </button>

      <!-- 删除按钮 -->
      <button
        class="w-8 h-8 rounded-lg bg-white/90 text-slate-600 flex items-center justify-center hover:bg-red-100 hover:text-red-600 hover:scale-110 transition-all"
        title="删除"
        @click.stop="handleDelete"
      >
        <Trash2 class="w-4 h-4" />
      </button>
    </div>

    <!-- 底部信息栏 - 渐变背景 -->
    <div
      class="card-info absolute bottom-0 left-0 right-0 px-2.5 py-2 pt-6 text-white"
      style="background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.6) 60%, transparent 100%);"
    >
      <!-- 文件信息 -->
      <div class="file-info text-[11px] font-mono opacity-80 mb-1" style="text-shadow: 0 1px 2px rgba(0,0,0,0.5);">
        <span>{{ image.filename }}</span>
        <template v-if="fileSize">
          <span class="mx-1">·</span>
          <span>{{ fileSize }}</span>
        </template>
      </div>

      <!-- 标签 -->
      <div class="tags-row flex flex-wrap gap-1">
        <template v-if="tags.length > 0">
          <span
            v-for="tag in tags"
            :key="tag"
            class="overlay-tag px-2 py-0.5 rounded-full text-[11px] font-medium cursor-pointer transition-all hover:scale-105"
            @click.stop="handleTagClick(tag)"
          >
            {{ tag }}
          </span>
        </template>
        <span v-else class="text-[11px] opacity-60 italic">无标签</span>
      </div>
    </div>

    <!-- 右键菜单 -->
    <Teleport to="body">
      <Transition name="context-menu">
        <div
          v-if="showContextMenu"
          class="fixed z-[5000] bg-white rounded-xl shadow-2xl border border-slate-200 py-2 min-w-[160px]"
          :style="{ left: contextMenuPos.x + 'px', top: contextMenuPos.y + 'px' }"
        >
          <button
            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-600 flex items-center gap-3 transition-colors"
            @click="handlePreview"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            预览
          </button>
          <button
            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-600 flex items-center gap-3 transition-colors"
            @click="handleContextEdit"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            编辑标签
          </button>
          <button
            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-600 flex items-center gap-3 transition-colors"
            @click="handleContextCopy"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
            复制图片
          </button>
          <button
            class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-600 flex items-center gap-3 transition-colors"
            @click="handleDownload"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            下载
          </button>
          <div class="border-t border-slate-100 my-1" />
          <button
            class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors"
            @click="handleContextDelete"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            删除
          </button>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.context-menu-enter-active,
.context-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.context-menu-enter-from,
.context-menu-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
