<script setup lang="ts">
/**
 * MemeCard 组件 - 图片卡片
 * 复刻旧项目：覆盖层标签编辑、复制标签、回收站软删除、原图加载
 */
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { Download, Copy, Trash2, RefreshCw } from 'lucide-vue-next'
import TagInput from '@/components/TagInput.vue'
import type { MemeImage } from '@/types'

const props = defineProps<{
  image: MemeImage
  preferHQ?: boolean
  isTrash?: boolean
  index?: number
  tempMode?: boolean
}>()

const emit = defineEmits<{
  'copy': [image: MemeImage]
  'delete': [image: MemeImage]
  'applyTempTags': [image: MemeImage]
  'updateTags': [image: MemeImage, tags: string[]]
}>()

const isOriginalLoading = ref(false)
const imageError = ref(false)
const currentSrcType = ref<'thumbnail' | 'original'>(props.preferHQ ? 'original' : 'thumbnail')

const isEditingTags = ref(false)
const editTags = ref<string[]>([])
const editInputValue = ref('')
const tagInputRef = ref<InstanceType<typeof TagInput> | null>(null)
const editorRef = ref<HTMLElement | null>(null)
const cardRef = ref<HTMLElement | null>(null)

const EAGER_LOAD_COUNT = 4

const imageSrc = computed(() => `/images/${props.image.filename}`)
const thumbnailSrc = computed(() => `/thumbnails/${props.image.md5}_thumbnail.jpg`)

const currentSrc = computed(() => {
  return currentSrcType.value === 'original' ? imageSrc.value : thumbnailSrc.value
})

const loadingStrategy = computed(() => {
  return (props.index ?? 0) < EAGER_LOAD_COUNT ? 'eager' : 'lazy'
})

const tags = computed(() => {
  if (!props.image.tags) return []
  return props.image.tags.split(' ').filter(t => t.trim())
})

const isTempMode = computed(() => !!props.tempMode)

const isTrashImage = computed(() => tags.value.includes('trash_bin'))

const extLabel = computed(() => {
  const parts = props.image.filename.split('.')
  const ext = parts.length > 1 ? parts[parts.length - 1] : ''
  return ext ? ext.toUpperCase() : ''
})

const sizeLabel = computed(() => {
  if (!props.image.file_size) return ''
  return (props.image.file_size / (1024 * 1024)).toFixed(3) + 'MB'
})

const dimensionLabel = computed(() => {
  if (!props.image.width || !props.image.height) return ''
  return `${props.image.width}x${props.image.height}`
})

watch(() => props.preferHQ, (newVal) => {
  if (newVal && currentSrcType.value === 'thumbnail') {
    loadOriginalImage()
  }
})

function handleImageClick() {
  if (isTempMode.value) {
    emit('applyTempTags', props.image)
    return
  }
  loadOriginalImage()
}

function handleCopy() {
  emit('copy', props.image)
}

function handleDelete() {
  emit('delete', props.image)
}

function handleImageError() {
  if (currentSrcType.value === 'thumbnail') {
    // 缩略图失败时不自动切换，等待点击加载原图
    return
  }
  imageError.value = true
  isOriginalLoading.value = false
}

function handleImageLoad() {
  if (currentSrcType.value === 'original') {
    isOriginalLoading.value = false
    imageError.value = false
  }
}

function loadOriginalImage() {
  if (currentSrcType.value === 'original' && !imageError.value) return
  imageError.value = false
  isOriginalLoading.value = true

  const tempImg = new Image()
  tempImg.onload = () => {
    currentSrcType.value = 'original'
    isOriginalLoading.value = false
    imageError.value = false
  }
  tempImg.onerror = () => {
    isOriginalLoading.value = false
    imageError.value = true
  }
  tempImg.src = imageSrc.value
}

function openEditor() {
  if (isEditingTags.value) return
  editTags.value = [...tags.value]
  editInputValue.value = ''
  isEditingTags.value = true
  nextTick(() => {
    setTimeout(() => {
      document.addEventListener('click', handleOutsideClick)
    }, 0)
  })
}

function handleOutsideClick(e: MouseEvent) {
  const editorEl = editorRef.value
  if (editorEl && editorEl.contains(e.target as Node)) return
  finishEdit()
}

function finishEdit() {
  document.removeEventListener('click', handleOutsideClick)

  const pending = editInputValue.value.trim()
  if (pending) {
    tagInputRef.value?.addTag(pending)
  }

  const nextTags = [...editTags.value]
  const current = [...tags.value]
  const changed = nextTags.join(' ') !== current.join(' ')

  isEditingTags.value = false

  if (changed) {
    emit('updateTags', props.image, nextTags)
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<template>
  <div
    ref="cardRef"
    :class="[
      'meme-card group relative rounded-xl overflow-hidden shadow-md aspect-square',
      isTrashImage && !isTrash ? 'is-trash' : 'bg-white',
      imageError ? 'load-failed' : '',
      isTempMode ? 'temp-mode-card' : ''
    ]"
  >
    <div v-if="isTempMode" class="temp-mode-pill">批量打标</div>

    <img
      class="image-element w-full h-full object-cover cursor-pointer"
      :src="currentSrc"
      alt=""
      :loading="loadingStrategy"
      @click="handleImageClick"
      @load="handleImageLoad"
      @error="handleImageError"
    />

    <!-- Loader for original load -->
    <div
      v-if="isOriginalLoading"
      class="loader-element absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white drop-shadow-md z-10"
    >
      <RefreshCw class="w-7 h-7 animate-spin-fast" />
    </div>

    <!-- Error Overlay -->
    <div
      v-if="imageError"
      class="error-overlay absolute inset-0 text-red-500 flex flex-col items-center justify-center text-center p-4 z-20 cursor-pointer rounded-xl transition-opacity hover:opacity-90"
      @click.stop="loadOriginalImage"
    >
      加载失败
      <span class="text-xs text-slate-400 mt-1">点击重试</span>
    </div>

    <!-- 顶部工具栏 -->
    <div class="top-toolbar absolute top-0 left-0 right-0 p-2 flex justify-between items-start hidden group-hover:flex z-30">
      <a
        :href="imageSrc"
        :download="image.filename"
        class="p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition"
        @click.stop
      >
        <Download class="w-5 h-5" />
      </a>
      <div class="flex gap-2">
        <button
          class="copy-btn p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition"
          @click.stop="handleCopy"
        >
          <Copy class="w-5 h-5" />
        </button>
        <button
          :class="[
            'delete-btn p-2 rounded-lg hover:bg-black/60 transition',
            isTrashImage ? 'bg-red-500 text-white' : 'bg-black/40 text-white'
          ]"
          @click.stop="handleDelete"
        >
          <RefreshCw v-if="isTrashImage" class="w-5 h-5" />
          <Trash2 v-else class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- 底部覆盖层 -->
    <div class="image-overlay absolute bottom-0 left-0 right-0 p-3 pt-8 flex flex-col justify-end text-white transition-opacity duration-300">
      <div class="image-info text-[12px] font-mono opacity-80 mb-1 leading-tight">
        <span v-if="extLabel">{{ extLabel }}</span>
        <br v-if="extLabel && (dimensionLabel || sizeLabel)" />
        <span v-if="dimensionLabel">{{ dimensionLabel }}</span>
        <br v-if="dimensionLabel && sizeLabel" />
        <span v-if="sizeLabel">{{ sizeLabel }}</span>
      </div>

      <div
        v-if="!isEditingTags"
        class="tags-container-element flex flex-wrap gap-1 cursor-pointer"
        @click.stop="openEditor"
      >
        <template v-if="tags.length > 0">
          <span
            v-for="tag in tags"
            :key="tag"
            class="overlay-tag px-2 py-1 rounded text-sm font-medium shadow-sm"
          >
            {{ tag }}
          </span>
        </template>
        <span v-else class="text-sm opacity-60 italic">&nbsp;</span>
      </div>

      <div v-else ref="editorRef">
        <TagInput
          ref="tagInputRef"
          v-model="editTags"
          suggestions-id="tag-suggestions"
          placeholder="添加标签..."
          theme="blue"
          :enable-excludes="false"
          :auto-focus="true"
          container-class="tag-editor-container w-full bg-white/95 rounded p-1 flex flex-wrap gap-1 items-center animate-in fade-in slide-in-from-bottom-2 border border-blue-300 shadow-lg text-slate-800"
          @submit="finishEdit"
          @input-update="editInputValue = $event"
        />
      </div>
    </div>
  </div>
</template>
