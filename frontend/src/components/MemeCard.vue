<script setup lang="ts">
/**
 * MemeCard 组件 - 图片卡片
 * 显示图片、标签、操作按钮（下载、复制、删除）
 */
import { ref, computed } from 'vue'
import { Download, Copy, Trash2, RefreshCw, Check } from 'lucide-vue-next'
import type { MemeImage } from '@/types'

// Props
const props = defineProps<{
  image: MemeImage
  preferHQ?: boolean
}>()

// Emits
const emit = defineEmits<{
  'copy': [image: MemeImage]
  'delete': [image: MemeImage]
  'clickTag': [tag: string]
  'edit': [image: MemeImage]
}>()

// 状态
const isLoading = ref(false)
const copySuccess = ref(false)
const imageError = ref(false)

// 计算属性
const imageSrc = computed(() => `/images/${props.image.filename}`)
const thumbnailSrc = computed(() => `/thumbnails/${props.image.filename}`)
// 暂时默认使用原图，因为后端未配置缩略图服务
const currentSrc = computed(() => imageSrc.value)

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
  emit('edit', props.image)
}

function handleImageError() {
  imageError.value = true
}

function handleImageLoad() {
  isLoading.value = false
  imageError.value = false
}
</script>

<template>
  <div
    class="meme-card group relative bg-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-lg aspect-square cursor-pointer"
    @click="handleCardClick"
  >
    <!-- 图片 -->
    <img
      :src="currentSrc"
      :alt="image.filename"
      class="w-full h-full object-contain"
      loading="lazy"
      @load="handleImageLoad"
      @error="handleImageError"
    />

    <!-- 加载指示器 -->
    <div
      v-if="isLoading"
      class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white drop-shadow-md z-10"
    >
      <RefreshCw class="w-8 h-8 animate-spin" />
    </div>

    <!-- 错误提示 -->
    <div
      v-if="imageError"
      class="absolute inset-0 flex items-center justify-center bg-slate-300 text-slate-500"
    >
      <span class="text-sm">加载失败</span>
    </div>

    <!-- 顶部工具栏 -->
    <div
      class="absolute top-0 left-0 right-0 p-2 flex justify-between items-start hidden group-hover:flex z-30"
    >
      <!-- 下载按钮 -->
      <a
        :href="imageSrc"
        :download="image.filename"
        class="p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition"
        @click.stop
      >
        <Download class="w-5 h-5" />
      </a>

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

    <!-- 底部信息栏 -->
    <div
      class="absolute bottom-0 left-0 right-0 p-3 pt-8 flex flex-col justify-end text-white bg-gradient-to-t from-black/60 to-transparent"
    >
      <!-- 文件信息 -->
      <div class="text-xs font-mono opacity-80 mb-1 leading-tight">
        <span>{{ fileExt }}</span>
        <template v-if="dimensions">
          <br />
          <span>{{ dimensions }}</span>
        </template>
        <template v-if="fileSize">
          <br />
          <span>{{ fileSize }}</span>
        </template>
      </div>

      <!-- 标签 -->
      <div class="flex flex-wrap gap-1">
        <template v-if="tags.length > 0">
          <span
            v-for="tag in tags"
            :key="tag"
            class="px-2 py-0.5 bg-white/20 rounded-full text-xs hover:bg-white/30 transition cursor-pointer"
            @click.stop="handleTagClick(tag)"
          >
            {{ tag }}
          </span>
        </template>
        <span v-else class="text-sm opacity-60 italic">无标签</span>
      </div>
    </div>
  </div>
</template>
