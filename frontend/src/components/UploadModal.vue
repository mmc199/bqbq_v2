<script setup lang="ts">
/**
 * UploadModal 组件 - 图片上传模态框
 * 支持拖拽上传、多文件上传、MD5 去重
 */
import { ref, computed } from 'vue'
import { X, Upload, Image, Loader2, CheckCircle, XCircle } from 'lucide-vue-next'
import SparkMD5 from 'spark-md5'
import { useToast } from '@/composables/useToast'

// Props
const props = defineProps<{
  visible: boolean
}>()

// Emits
const emit = defineEmits<{
  'close': []
  'uploaded': []
}>()

const toast = useToast()

// 状态
const isDragging = ref(false)
const isUploading = ref(false)
const uploadQueue = ref<UploadItem[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)

interface UploadItem {
  id: number
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error' | 'duplicate'
  message?: string
  preview?: string
}

let nextId = 0

function triggerFilePicker() {
  fileInputRef.value?.click()
}

// 计算 MD5
async function calculateMD5(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const spark = new SparkMD5.ArrayBuffer()
      spark.append(e.target?.result as ArrayBuffer)
      resolve(spark.end())
    }
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

// 检查 MD5 是否存在
async function checkMD5Exists(md5: string): Promise<{ exists: boolean }> {
  try {
    const response = await fetch(`/api/images/check-md5/${md5}`)
    return await response.json()
  } catch {
    return { exists: false }
  }
}

// 上传单个文件
async function uploadFile(item: UploadItem) {
  item.status = 'uploading'

  try {
    // 计算 MD5
    const md5 = await calculateMD5(item.file)

    // 检查是否已存在
    const checkResult = await checkMD5Exists(md5)
    if (checkResult.exists) {
      item.status = 'duplicate'
      item.message = '图片已存在'
      return
    }

    // 上传文件
    const formData = new FormData()
    formData.append('file', item.file)

    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    })

    const result = await response.json()

    if (result.success) {
      item.status = 'success'
      item.message = '上传成功'
    } else {
      item.status = 'error'
      item.message = result.error || '上传失败'
    }
  } catch (err) {
    item.status = 'error'
    item.message = err instanceof Error ? err.message : '上传失败'
  }
}

// 添加文件到队列
function addFiles(files: FileList | File[]) {
  const imageFiles = Array.from(files).filter(f =>
    f.type.startsWith('image/') || /\.(gif|png|jpg|jpeg|webp)$/i.test(f.name)
  )

  for (const file of imageFiles) {
    const item: UploadItem = {
      id: nextId++,
      file,
      status: 'pending',
      preview: URL.createObjectURL(file),
    }
    uploadQueue.value.push(item)
  }
}

// 开始上传
async function startUpload() {
  const pendingItems = uploadQueue.value.filter(item => item.status === 'pending')
  if (pendingItems.length === 0) return

  isUploading.value = true

  for (const item of pendingItems) {
    await uploadFile(item)
  }

  isUploading.value = false

  // 统计结果
  const successCount = uploadQueue.value.filter(i => i.status === 'success').length
  const duplicateCount = uploadQueue.value.filter(i => i.status === 'duplicate').length
  const errorCount = uploadQueue.value.filter(i => i.status === 'error').length

  if (successCount > 0) {
    toast.success(`上传成功 ${successCount} 张图片`)
    emit('uploaded')
  }
  if (duplicateCount > 0) {
    toast.info(`${duplicateCount} 张图片已存在`)
  }
  if (errorCount > 0) {
    toast.error(`${errorCount} 张图片上传失败`)
  }
}

// 移除队列项
function removeItem(id: number) {
  const index = uploadQueue.value.findIndex(i => i.id === id)
  if (index !== -1) {
    const item = uploadQueue.value[index]
    if (item && item.preview) {
      URL.revokeObjectURL(item.preview)
    }
    uploadQueue.value.splice(index, 1)
  }
}

// 清空队列
function clearQueue() {
  uploadQueue.value.forEach(item => {
    if (item.preview) {
      URL.revokeObjectURL(item.preview)
    }
  })
  uploadQueue.value = []
}

// 关闭模态框
function close() {
  if (!isUploading.value) {
    clearQueue()
    emit('close')
  }
}

// 拖拽处理
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  if (e.dataTransfer?.files) {
    addFiles(e.dataTransfer.files)
  }
}

// 文件选择
function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    addFiles(input.files)
    input.value = '' // 重置以允许选择相同文件
  }
}

// 计算属性
const pendingCount = computed(() =>
  uploadQueue.value.filter(i => i.status === 'pending').length
)

const canUpload = computed(() =>
  pendingCount.value > 0 && !isUploading.value
)
</script>

<template>
  <Teleport to="body">
    <!-- 遮罩 - 一比一复刻旧项目 -->
    <div
      v-if="visible"
      class="modal-overlay fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="close"
    >
      <!-- 模态框 -->
      <div class="modal-content bg-white rounded-[20px] shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <!-- 头部 -->
        <div class="modal-header flex items-center justify-between px-6 py-5 border-b border-slate-200">
          <h3 class="text-lg font-semibold text-slate-800">上传图片</h3>
          <button
            class="modal-close w-9 h-9 rounded-[10px] bg-slate-100 text-slate-500 flex items-center justify-center hover:bg-red-100 hover:text-red-600 transition-all"
            :disabled="isUploading"
            @click="close"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- 拖拽区域 - 使用 upload-zone 样式 -->
        <div
          :class="[
            'upload-zone m-6 p-12 border-2 border-dashed rounded-2xl transition-all text-center cursor-pointer',
            isDragging ? 'dragover border-blue-500 bg-blue-100' : 'border-slate-300 bg-slate-50 hover:border-blue-500 hover:bg-blue-50'
          ]"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
          @click="triggerFilePicker"
        >
          <Upload class="w-12 h-12 mx-auto mb-4 text-slate-400" />
          <p class="text-base text-slate-600 mb-2">拖拽图片到此处，或点击选择</p>
          <p class="text-sm text-slate-400">支持 GIF、PNG、JPG、WebP 格式</p>
          <input
            ref="fileInputRef"
            type="file"
            multiple
            accept="image/*"
            class="hidden"
            @change="handleFileSelect"
          />
        </div>

        <!-- 上传队列预览 -->
        <div v-if="uploadQueue.length > 0" class="modal-body flex-1 overflow-auto px-6 pb-4">
          <div class="upload-preview-list grid grid-cols-4 gap-3">
            <div
              v-for="item in uploadQueue"
              :key="item.id"
              :class="[
                'upload-preview-item relative aspect-square rounded-xl overflow-hidden bg-slate-200 group',
                item.status === 'duplicate' ? 'ring-2 ring-amber-500' : '',
                item.status === 'error' ? 'ring-2 ring-red-500' : '',
                item.status === 'success' ? 'ring-2 ring-green-500' : ''
              ]"
            >
              <!-- 预览图 -->
              <img
                v-if="item.preview"
                :src="item.preview"
                class="w-full h-full object-cover"
              />
              <Image v-else class="w-full h-full p-4 text-slate-400" />

              <!-- 状态覆盖层 -->
              <div
                v-if="item.status !== 'pending'"
                class="absolute inset-0 flex items-center justify-center bg-black/40"
              >
                <Loader2 v-if="item.status === 'uploading'" class="w-8 h-8 text-white animate-spin" />
                <CheckCircle v-else-if="item.status === 'success'" class="w-8 h-8 text-green-400" />
                <XCircle v-else-if="item.status === 'error'" class="w-8 h-8 text-red-400" />
                <span v-else-if="item.status === 'duplicate'" class="px-2 py-1 bg-amber-500 text-white text-xs font-bold rounded">重复</span>
              </div>

              <!-- 删除按钮 -->
              <button
                v-if="item.status === 'pending'"
                class="absolute top-1 right-1 w-6 h-6 rounded-full bg-red-500/90 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                @click="removeItem(item.id)"
              >
                <X class="w-3.5 h-3.5" />
              </button>

              <!-- 文件名 -->
              <div class="absolute bottom-0 left-0 right-0 px-2 py-1 bg-black/60 text-white text-[10px] truncate">
                {{ item.file.name }}
              </div>
            </div>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="modal-footer flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50">
          <div class="text-sm text-slate-500">
            {{ uploadQueue.length }} 个文件，{{ pendingCount }} 个待上传
          </div>
          <div class="flex gap-3">
            <button
              class="modal-btn secondary px-5 py-2.5 bg-slate-100 text-slate-600 rounded-[10px] hover:bg-slate-200 transition-all"
              :disabled="isUploading"
              @click="clearQueue"
            >
              清空
            </button>
            <button
              :class="[
                'modal-btn px-5 py-2.5 rounded-[10px] transition-all flex items-center gap-2 font-medium',
                canUpload
                  ? 'primary bg-blue-500 text-white hover:bg-blue-600'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              ]"
              :disabled="!canUpload"
              @click="startUpload"
            >
              <Loader2 v-if="isUploading" class="w-4 h-4 animate-spin" />
              <Upload v-else class="w-4 h-4" />
              {{ isUploading ? '上传中...' : '开始上传' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
