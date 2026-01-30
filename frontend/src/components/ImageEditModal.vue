<script setup lang="ts">
/**
 * ImageEditModal 组件 - 图片编辑模态框
 * 编辑图片标签，支持乐观更新和冲突重试
 */
import { ref, watch, computed } from 'vue'
import { X, Save, Loader2 } from 'lucide-vue-next'
import TagInput from './TagInput.vue'
import { useImageApi } from '@/composables/useApi'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useToast } from '@/composables/useToast'
import { useOptimisticUpdate } from '@/composables/useOptimisticUpdate'
import type { MemeImage } from '@/types'

// Props
const props = defineProps<{
  visible: boolean
  image: MemeImage | null
  suggestions?: string[]
}>()

// Emits
const emit = defineEmits<{
  'close': []
  'saved': [image: MemeImage]
  'refresh': []  // 新增：请求刷新数据
}>()

const imageApi = useImageApi()
const globalStore = useGlobalStore()
const toast = useToast()
const { executeWithRetry } = useOptimisticUpdate()

// 状态
const isSaving = ref(false)
const tags = ref<{ text: string; exclude: boolean; synonym: boolean; synonymWords: string[] | null }[]>([])
const originalImage = ref<MemeImage | null>(null)

// 监听图片变化，初始化标签
watch(() => props.image, (newImage) => {
  if (newImage) {
    originalImage.value = { ...newImage }
    const tagStrings = newImage.tags ? newImage.tags.split(' ').filter(t => t.trim()) : []
    tags.value = tagStrings.map(t => ({
      text: t,
      exclude: false,
      synonym: false,
      synonymWords: null,
    }))
  } else {
    tags.value = []
    originalImage.value = null
  }
}, { immediate: true })

// 计算属性
const imageSrc = computed(() =>
  props.image ? `/images/${props.image.filename}` : ''
)

const hasChanges = computed(() => {
  if (!props.image) return false
  const originalTags = props.image.tags ? props.image.tags.split(' ').filter(t => t.trim()) : []
  const currentTags = tags.value.map(t => t.text)
  if (originalTags.length !== currentTags.length) return true
  return !originalTags.every((t, i) => t === currentTags[i])
})

// 保存标签（带冲突重试）
async function save() {
  if (!props.image || !hasChanges.value) return

  isSaving.value = true
  const tagStrings = tags.value.map(t => t.text)

  // 使用冲突重试机制
  const result = await executeWithRetry(
    (clientId, baseVersion) => imageApi.updateImageTags(
      props.image!.id,
      tagStrings,
      clientId,
      baseVersion
    ),
    // 冲突时的回调：可以在这里刷新数据
    async () => {
      // 发出刷新请求，让父组件重新获取最新数据
      emit('refresh')
    }
  )

  isSaving.value = false

  if (result.success && result.data) {
    toast.success('标签已保存')

    // 更新图片对象
    const updatedImage: MemeImage = {
      ...props.image,
      tags: tagStrings.join(' '),
    }
    emit('saved', updatedImage)
    emit('close')
  } else {
    toast.error(result.error || '保存失败')
  }
}

// 关闭
function close() {
  if (!isSaving.value) {
    emit('close')
  }
}

// 键盘快捷键
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
  } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    save()
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩 -->
    <div
      v-if="visible && image"
      class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
      @click.self="close"
      @keydown="handleKeydown"
    >
      <!-- 模态框 -->
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        <!-- 头部 -->
        <div class="flex items-center justify-between p-4 border-b flex-shrink-0">
          <h2 class="text-lg font-bold text-slate-800">编辑图片</h2>
          <button
            class="p-1 text-slate-400 hover:text-slate-600 transition"
            :disabled="isSaving"
            @click="close"
          >
            <X class="w-6 h-6" />
          </button>
        </div>

        <!-- 内容区 -->
        <div class="flex-1 overflow-auto p-4">
          <div class="flex flex-col md:flex-row gap-6">
            <!-- 图片预览 -->
            <div class="md:w-1/2">
              <div class="bg-slate-100 rounded-xl overflow-hidden aspect-square flex items-center justify-center">
                <img
                  :src="imageSrc"
                  :alt="image.filename"
                  class="max-w-full max-h-full object-contain"
                />
              </div>
              <!-- 图片信息 -->
              <div class="mt-3 text-sm text-slate-500 space-y-1">
                <p><span class="font-medium">文件名:</span> {{ image.filename }}</p>
                <p v-if="image.width && image.height">
                  <span class="font-medium">尺寸:</span> {{ image.width }} × {{ image.height }}
                </p>
                <p v-if="image.file_size">
                  <span class="font-medium">大小:</span> {{ (image.file_size / 1024 / 1024).toFixed(2) }} MB
                </p>
              </div>
            </div>

            <!-- 标签编辑 -->
            <div class="md:w-1/2">
              <label class="block text-sm font-medium text-slate-700 mb-2">
                标签
              </label>
              <TagInput
                v-model="tags"
                placeholder="输入标签，空格分隔..."
                theme="purple"
                :suggestions="suggestions"
                auto-focus
              />
              <p class="mt-2 text-xs text-slate-400">
                提示: 空格或回车添加标签，点击标签可编辑，Ctrl+S 保存
              </p>
            </div>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="flex items-center justify-end gap-3 p-4 border-t bg-slate-50 flex-shrink-0">
          <button
            class="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition"
            :disabled="isSaving"
            @click="close"
          >
            取消
          </button>
          <button
            :class="[
              'px-4 py-2 rounded-lg transition flex items-center gap-2',
              hasChanges && !isSaving
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
            ]"
            :disabled="!hasChanges || isSaving"
            @click="save"
          >
            <Loader2 v-if="isSaving" class="w-4 h-4 animate-spin" />
            <Save v-else class="w-4 h-4" />
            {{ isSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
