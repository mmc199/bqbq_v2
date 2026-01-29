<script setup lang="ts">
/**
 * Gallery 主页面 - 图片画廊
 */
import { ref, onMounted, computed } from 'vue'
import { Search, RefreshCw } from 'lucide-vue-next'
import TagInput from '@/components/TagInput.vue'
import MemeCard from '@/components/MemeCard.vue'
import RuleTree from '@/components/RuleTree.vue'
import UploadModal from '@/components/UploadModal.vue'
import ImageEditModal from '@/components/ImageEditModal.vue'
import FloatingButtons from '@/components/FloatingButtons.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import { useImageApi, useSystemApi } from '@/composables/useApi'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useToast } from '@/composables/useToast'
import type { MemeImage } from '@/types'

// API & Store
const imageApi = useImageApi()
const systemApi = useSystemApi()
const globalStore = useGlobalStore()
const toast = useToast()

// 状态
const images = ref<MemeImage[]>([])
const searchTags = ref<{ text: string; exclude: boolean; synonym: boolean; synonymWords: string[] | null }[]>([])
const allTags = ref<string[]>([])
const isLoading = ref(false)
const currentPage = ref(1)
const totalImages = ref(0)
const pageSize = 20

// 模态框状态
const showUploadModal = ref(false)
const showRulesPanel = ref(false)
const showEditModal = ref(false)
const editingImage = ref<MemeImage | null>(null)

// 功能开关
const isTrashMode = ref(false)
const isExpansionEnabled = ref(true)

// 计算属性
const totalPages = computed(() => Math.ceil(totalImages.value / pageSize))
const hasMore = computed(() => currentPage.value < totalPages.value)

// 搜索图片
async function searchImages(resetPage = true) {
  if (resetPage) {
    currentPage.value = 1
    images.value = []
  }

  isLoading.value = true

  // 分离包含和排除标签
  const includeTags: string[] = []
  const excludeTags: string[] = []

  searchTags.value.forEach(tag => {
    if (tag.exclude) {
      if (tag.synonym && tag.synonymWords) {
        excludeTags.push(...tag.synonymWords)
      } else {
        excludeTags.push(tag.text)
      }
    } else {
      if (tag.synonym && tag.synonymWords) {
        includeTags.push(...tag.synonymWords)
      } else {
        includeTags.push(tag.text)
      }
    }
  })

  // 回收站模式
  if (isTrashMode.value) {
    includeTags.push('trash_bin')
  } else {
    excludeTags.push('trash_bin')
  }

  const result = await imageApi.searchImages({
    include_tags: includeTags,
    exclude_tags: isTrashMode.value ? [] : excludeTags,
    page: currentPage.value,
    page_size: pageSize,
  })

  isLoading.value = false

  if (result.success && result.data) {
    if (resetPage) {
      images.value = result.data.images
    } else {
      images.value.push(...result.data.images)
    }
    totalImages.value = result.data.total
  }
}

// 加载更多
async function loadMore() {
  if (!hasMore.value || isLoading.value) return
  currentPage.value++
  await searchImages(false)
}

// 加载所有标签
async function loadAllTags() {
  const result = await systemApi.getAllTags()
  if (result.success && result.data) {
    allTags.value = result.data
  }
}

// 处理搜索提交
function handleSearchSubmit() {
  searchImages(true)
}

// 处理标签点击（从卡片）
function handleTagClick(tag: string) {
  const exists = searchTags.value.some(t => t.text === tag && !t.exclude)
  if (!exists) {
    searchTags.value.push({
      text: tag,
      exclude: false,
      synonym: false,
      synonymWords: null,
    })
    searchImages(true)
  }
}

// 处理复制图片
async function handleCopyImage(image: MemeImage) {
  try {
    const response = await fetch(`/images/${image.filename}`)
    const blob = await response.blob()
    await navigator.clipboard.write([
      new ClipboardItem({ [blob.type]: blob })
    ])
    toast.success('已复制到剪贴板')
  } catch (err) {
    console.error('复制失败:', err)
    toast.error('复制失败')
  }
}

// 处理删除图片
async function handleDeleteImage(image: MemeImage) {
  if (!confirm(`确定要删除图片 ${image.filename} 吗？`)) return

  const result = await imageApi.deleteImage(image.id)
  if (result.success) {
    images.value = images.value.filter(img => img.id !== image.id)
    totalImages.value--
    toast.success('图片已删除')
  } else {
    toast.error('删除失败')
  }
}

// 处理编辑图片
function handleEditImage(image: MemeImage) {
  editingImage.value = image
  showEditModal.value = true
}

// 处理图片保存后
function handleImageSaved(updatedImage: MemeImage) {
  const index = images.value.findIndex(img => img.id === updatedImage.id)
  if (index !== -1) {
    images.value[index] = updatedImage
  }
}

// 处理上传完成
function handleUploaded() {
  searchImages(true)
  loadAllTags()
}

// 处理导出
async function handleExport() {
  toast.info('正在导出数据...')
  const result = await systemApi.exportData()
  if (result.success && result.data) {
    const url = URL.createObjectURL(result.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `bqbq_export_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('导出成功')
  } else {
    toast.error('导出失败')
  }
}

// 处理导入
async function handleImport() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return

    toast.info('正在导入数据...')
    const result = await systemApi.importData(file)
    if (result.success) {
      toast.success('导入成功')
      searchImages(true)
      loadAllTags()
    } else {
      toast.error('导入失败')
    }
  }
  input.click()
}

// 处理回收站模式切换
function handleToggleTrash(isTrash: boolean) {
  isTrashMode.value = isTrash
  toast.info(isTrash ? '已进入回收站模式' : '已退出回收站模式')
  searchImages(true)
}

// 处理关键词膨胀切换
function handleToggleExpansion(enabled: boolean) {
  isExpansionEnabled.value = enabled
  toast.info(enabled ? '关键词膨胀已开启' : '关键词膨胀已关闭')
}

// 刷新
function refresh() {
  searchImages(true)
  loadAllTags()
}

// 初始化
onMounted(() => {
  globalStore.init()
  searchImages(true)
  loadAllTags()
})
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <!-- 顶部搜索栏 -->
    <header class="sticky top-0 z-40 bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-3">
        <div class="flex items-center gap-4">
          <!-- Logo -->
          <h1 class="text-xl font-bold text-slate-800 whitespace-nowrap">
            BQBQ
            <span v-if="isTrashMode" class="text-red-500 text-sm ml-1">回收站</span>
          </h1>

          <!-- 搜索框 -->
          <div class="flex-1">
            <TagInput
              v-model="searchTags"
              placeholder="输入标签搜索，空格分隔，-排除..."
              theme="mixed"
              :enable-excludes="true"
              :suggestions="allTags"
              @submit="handleSearchSubmit"
            />
          </div>

          <!-- 搜索按钮 -->
          <button
            class="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
            @click="handleSearchSubmit"
          >
            <Search class="w-5 h-5" />
          </button>

          <!-- 刷新按钮 -->
          <button
            class="p-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition"
            :class="{ 'animate-spin': isLoading }"
            @click="refresh"
          >
            <RefreshCw class="w-5 h-5" />
          </button>
        </div>

        <!-- 统计信息 -->
        <div class="mt-2 text-sm text-slate-500">
          共 {{ totalImages }} 张图片
          <span v-if="searchTags.length > 0">（已筛选）</span>
          <span v-if="isExpansionEnabled" class="ml-2 text-emerald-600">· 膨胀开启</span>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <!-- 图片网格 -->
      <div
        v-if="images.length > 0"
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
      >
        <MemeCard
          v-for="image in images"
          :key="image.id"
          :image="image"
          @copy="handleCopyImage"
          @delete="handleDeleteImage"
          @click-tag="handleTagClick"
          @edit="handleEditImage"
        />
      </div>

      <!-- 空状态 -->
      <div
        v-else-if="!isLoading"
        class="flex flex-col items-center justify-center py-20 text-slate-400"
      >
        <Search class="w-16 h-16 mb-4" />
        <p class="text-lg">没有找到图片</p>
        <p class="text-sm mt-2">尝试修改搜索条件或上传新图片</p>
      </div>

      <!-- 加载更多 -->
      <div v-if="hasMore" class="flex justify-center mt-8">
        <button
          class="px-6 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition"
          :disabled="isLoading"
          @click="loadMore"
        >
          {{ isLoading ? '加载中...' : '加载更多' }}
        </button>
      </div>

      <!-- 加载指示器 -->
      <div v-if="isLoading && images.length === 0" class="flex justify-center py-20">
        <RefreshCw class="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    </main>

    <!-- FAB 悬浮按钮组 -->
    <FloatingButtons
      @upload="showUploadModal = true"
      @open-rules="showRulesPanel = true"
      @export="handleExport"
      @import="handleImport"
      @toggle-trash="handleToggleTrash"
      @toggle-expansion="handleToggleExpansion"
    />

    <!-- 规则树面板 -->
    <RuleTree
      :visible="showRulesPanel"
      @close="showRulesPanel = false"
      @update="loadAllTags"
    />

    <!-- 上传模态框 -->
    <UploadModal
      :visible="showUploadModal"
      @close="showUploadModal = false"
      @uploaded="handleUploaded"
    />

    <!-- 图片编辑模态框 -->
    <ImageEditModal
      :visible="showEditModal"
      :image="editingImage"
      :suggestions="allTags"
      @close="showEditModal = false"
      @saved="handleImageSaved"
    />

    <!-- Toast 通知容器 -->
    <ToastContainer />
  </div>
</template>
