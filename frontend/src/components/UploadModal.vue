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

interface UploadItem {
  id: number
  file: File
  status: 'pending' | 'uploading' | 'success' | 'error' | 'duplicate'
  message?: string
  preview?: string
}

let nextId = 0

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
    <!-- 遮罩 -->
    <div
      v-if="visible"
      class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      @click.self="close"
    >
      <!-- 模态框 -->
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <!-- 头部 -->
        <div class="flex items-center justify-between p-4 border-b">
          <h2 class="text-lg font-bold text-slate-800">上传图片</h2>
          <button
            class="p-1 text-slate-400 hover:text-slate-600 transition"
            :disabled="isUploading"
            @click="close"
          >
            <X class="w-6 h-6" />
          </button>
        </div>

        <!-- 拖拽区域 -->
        <div
          :class="[
            'm-4 p-8 border-2 border-dashed rounded-xl transition-colors text-center',
            isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
          ]"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
        >
          <Upload class="w-12 h-12 mx-auto mb-4 text-slate-400" />
          <p class="text-slate-600 mb-2">拖拽图片到此处，或</p>
          <label class="inline-block px-4 py-2 bg-blue-500 text-white rounded-lg cursor-pointer hover:bg-blue-600 transition">
            选择文件
            <input
              type="file"
              multiple
              accept="image/*"
              class="hidden"
              @change="handleFileSelect"
            />
          </label>
          <p class="text-sm text-slate-400 mt-2">支持 GIF、PNG、JPG、WebP 格式</p>
        </div>

        <!-- 上传队列 -->
        <div v-if="uploadQueue.length > 0" class="flex-1 overflow-auto px-4">
          <div class="space-y-2 pb-4">
            <div
              v-for="item in uploadQueue"
              :key="item.id"
              class="flex items-center gap-3 p-2 bg-slate-50 rounded-lg"
            >
              <!-- 预览图 -->
              <div class="w-12 h-12 rounded overflow-hidden bg-slate-200 flex-shrink-0">
                <img
                  v-if="item.preview"
                  :src="item.preview"
                  class="w-full h-full object-cover"
                />
                <Image v-else class="w-full h-full p-2 text-slate-400" />
              </div>

              <!-- 文件名 -->
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-700 truncate">{{ item.file.name }}</p>
                <p class="text-xs text-slate-400">
                  {{ (item.file.size / 1024).toFixed(1) }} KB
                  <span v-if="item.message" class="ml-2">· {{ item.message }}</span>
                </p>
              </div>

              <!-- 状态图标 -->
              <div class="flex-shrink-0">
                <Loader2 v-if="item.status === 'uploading'" class="w-5 h-5 text-blue-500 animate-spin" />
                <CheckCircle v-else-if="item.status === 'success'" class="w-5 h-5 text-green-500" />
                <XCircle v-else-if="item.status === 'error'" class="w-5 h-5 text-red-500" />
                <span v-else-if="item.status === 'duplicate'" class="text-xs text-orange-500 font-medium">已存在</span>
                <button
                  v-else
                  class="p-1 text-slate-400 hover:text-red-500 transition"
                  @click="removeItem(item.id)"
                >
                  <X class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部操作 -->
        <div class="flex items-center justify-between p-4 border-t bg-slate-50 rounded-b-2xl">
          <div class="text-sm text-slate-500">
            {{ uploadQueue.length }} 个文件，{{ pendingCount }} 个待上传
          </div>
          <div class="flex gap-2">
            <button
              class="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition"
              :disabled="isUploading"
              @click="clearQueue"
            >
              清空
            </button>
            <button
              :class="[
                'px-4 py-2 rounded-lg transition flex items-center gap-2',
                canUpload
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
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
