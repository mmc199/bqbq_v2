<script setup lang="ts">
/**
 * ImageEditModal 组件 - 图片编辑模态框
 * 编辑图片标签，支持乐观更新和冲突重试
 */
import { ref, watch, computed } from 'vue'
import { X, Save, Loader2 } from 'lucide-vue-next'
import TagInput from './TagInput.vue'
import { useImageApi } from '@/composables/useApi'
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
    <!-- 遮罩 - 一比一复刻旧项目 -->
    <div
      v-if="visible && image"
      class="modal-overlay fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="close"
      @keydown="handleKeydown"
    >
      <!-- 模态框 - 双栏布局 -->
      <div class="modal-content bg-white rounded-[20px] shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        <!-- 头部 -->
        <div class="modal-header flex items-center justify-between px-6 py-5 border-b border-slate-200 flex-shrink-0">
          <h3 class="text-lg font-semibold text-slate-800">编辑图片</h3>
          <button
            class="modal-close w-9 h-9 rounded-[10px] bg-slate-100 text-slate-500 flex items-center justify-center hover:bg-red-100 hover:text-red-600 transition-all"
            :disabled="isSaving"
            @click="close"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- 内容区 - 双栏布局 -->
        <div class="modal-body flex-1 overflow-auto p-6">
          <div class="edit-modal-content grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- 图片预览 -->
            <div class="edit-preview aspect-square rounded-xl overflow-hidden bg-slate-800 flex items-center justify-center">
              <img
                :src="imageSrc"
                :alt="image.filename"
                class="max-w-full max-h-full object-contain"
              />
            </div>

            <!-- 编辑表单 -->
            <div class="edit-form flex flex-col gap-4">
              <!-- 文件信息 -->
              <div class="edit-form-group">
                <label class="edit-form-label text-sm font-medium text-slate-500 mb-1.5">文件名</label>
                <div class="text-sm text-slate-700 font-mono bg-slate-50 px-3 py-2 rounded-lg">
                  {{ image.filename }}
                </div>
              </div>

              <!-- 尺寸信息 -->
              <div v-if="image.width && image.height" class="edit-form-group">
                <label class="edit-form-label text-sm font-medium text-slate-500 mb-1.5">尺寸</label>
                <div class="text-sm text-slate-700 bg-slate-50 px-3 py-2 rounded-lg">
                  {{ image.width }} × {{ image.height }} px
                </div>
              </div>

              <!-- 文件大小 -->
              <div v-if="image.file_size" class="edit-form-group">
                <label class="edit-form-label text-sm font-medium text-slate-500 mb-1.5">大小</label>
                <div class="text-sm text-slate-700 bg-slate-50 px-3 py-2 rounded-lg">
                  {{ (image.file_size / 1024).toFixed(1) }} KB
                </div>
              </div>

              <!-- 标签编辑 -->
              <div class="edit-form-group flex-1">
                <label class="edit-form-label text-sm font-medium text-slate-500 mb-1.5">标签</label>
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
        </div>

        <!-- 底部操作 -->
        <div class="modal-footer flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 flex-shrink-0">
          <button
            class="modal-btn secondary px-5 py-2.5 bg-slate-100 text-slate-600 rounded-[10px] hover:bg-slate-200 transition-all font-medium"
            :disabled="isSaving"
            @click="close"
          >
            取消
          </button>
          <button
            :class="[
              'modal-btn px-5 py-2.5 rounded-[10px] transition-all flex items-center gap-2 font-medium',
              hasChanges && !isSaving
                ? 'primary bg-blue-500 text-white hover:bg-blue-600'
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
