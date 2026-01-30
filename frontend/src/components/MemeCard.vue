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
}>()

// Emits
const emit = defineEmits<{
  'copy': [image: MemeImage]
  'delete': [image: MemeImage]
  'clickTag': [tag: string]
  'edit': [image: MemeImage]
  'select': [image: MemeImage]
}>()

// 状态
const isLoading = ref(true)
const copySuccess = ref(false)
const imageError = ref(false)
const isLoadingHQ = ref(false)
const currentSrcType = ref<'thumbnail' | 'original'>('thumbnail')

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

const fileExt = computed(() => {
  const parts = props.image.filename.split('.')
  return (parts[parts.length - 1] || '').toUpperCase()
})

const fileSize = computed(() => {
  if (!props.image.file_size) return ''
  return (props.image.file_size / (1024 * 1024)).toFixed(3) + 'MB'
})

const dimensions = computed(() => {
  if (!props.image.width || !props.image.height) return ''
  return `${props.image.width}x${props.image.height}`
})

const tags = computed(() => {
  if (!props.image.tags) return []
  return props.image.tags.split(' ').filter(t => t.trim())
})

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
  if (props.selectable) {
    emit('select', props.image)
  } else {
    emit('edit', props.image)
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

function handleDownload(e: Event) {
  e.stopPropagation()
  // 下载原图
  const link = document.createElement('a')
  link.href = imageSrc.value
  link.download = props.image.filename
  link.click()
}
</script>

<template>
  <div
    :class="[
      'meme-card group relative rounded-xl overflow-hidden shadow-sm hover:shadow-lg aspect-square cursor-pointer transition-all',
      isTrashImage && !isTrash ? 'is-trash' : 'bg-slate-200',
      selected ? 'ring-4 ring-blue-500 ring-offset-2' : ''
    ]"
    @click="handleCardClick"
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

    <!-- 图片 -->
    <img
      :src="currentSrc"
      :alt="image.filename"
      class="w-full h-full object-contain"
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
      class="absolute inset-0 flex items-center justify-center bg-slate-300 text-slate-500 load-failed"
    >
      <span class="text-sm">加载失败</span>
    </div>

    <!-- 顶部工具栏 - 悬停显示（旧项目用 hidden/flex） -->
    <div
      class="absolute top-0 left-0 right-0 p-2 hidden group-hover:flex justify-between items-start z-30 top-toolbar"
    >
      <!-- 下载按钮 -->
      <button
        class="p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition"
        @click="handleDownload"
      >
        <Download class="w-5 h-5" />
      </button>

      <!-- 右侧按钮组 -->
      <div class="flex gap-2">
        <!-- 复制按钮 -->
        <button
          class="p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition"
          @click.stop="handleCopy"
        >
          <Check v-if="copySuccess" class="w-5 h-5 text-green-400" />
          <Copy v-else class="w-5 h-5" />
        </button>

        <!-- 删除按钮 -->
        <button
          class="p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition"
          @click.stop="handleDelete"
        >
          <Trash2 class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- 底部信息栏 - 渐变背景（旧项目渐变更强 0.85） -->
    <div
      class="absolute bottom-0 left-0 right-0 p-3 pt-8 flex flex-col justify-end text-white"
      style="background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.0) 0%, transparent 100%);"
    >
      <!-- 文件信息 - 带文字阴影（旧项目 opacity-80） -->
      <div class="text-[12px] font-mono opacity-80 mb-1.5 leading-tight image-info">
        <span>{{ fileExt }}</span>
        <template v-if="dimensions">
          <span class="mx-1">·</span>
          <span>{{ dimensions }}</span>
        </template>
        <template v-if="fileSize">
          <span class="mx-1">·</span>
          <span>{{ fileSize }}</span>
        </template>
      </div>

      <!-- 标签 - 使用 overlay-tag 样式 -->
      <div class="flex flex-wrap gap-1">
        <template v-if="tags.length > 0">
          <span
            v-for="tag in tags"
            :key="tag"
            class="overlay-tag px-2 py-0.5 rounded-full text-xs hover:bg-white/30 transition cursor-pointer tag-capsule"
            @click.stop="handleTagClick(tag)"
          >
            {{ tag }}
          </span>
        </template>
        <span v-else class="text-sm opacity-60 italic image-info">无标签</span>
      </div>
    </div>
  </div>
</template>
