<script setup lang="ts">
/**
 * Gallery 主页面 - 图片画廊
 * 一比一复刻旧项目的所有功能
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

// 功能开关（从 store 读取持久化值）
const isTrashMode = ref(false)
const isExpansionEnabled = computed({
  get: () => globalStore.preferences.isExpansionEnabled,
  set: (val) => globalStore.updatePreference('isExpansionEnabled', val)
})
const isHQMode = computed({
  get: () => globalStore.preferences.isHQMode,
  set: (val) => globalStore.updatePreference('isHQMode', val)
})

// 搜索参数（排序持久化）
const sortBy = computed({
  get: () => globalStore.preferences.sortBy,
  set: (val) => globalStore.updatePreference('sortBy', val)
})
const minTags = ref<number | null>(null)
const maxTags = ref<number | null>(null)

// 临时标签（批量打标）
const tempTags = ref<string[]>([])
const selectedImages = ref<Set<number>>(new Set())

// 批量编辑模式
const isBatchMode = ref(false)

// 膨胀统计
const expandedTagsCount = ref(0)
const originalTagsCount = ref(0)

// 计算属性
const totalPages = computed(() => Math.ceil(totalImages.value / pageSize))
const hasMore = computed(() => currentPage.value < totalPages.value)
const selectedCount = computed(() => selectedImages.value.size)

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
    sort_by: sortBy.value,
    min_tags: minTags.value,
    max_tags: maxTags.value,
    expand: isExpansionEnabled.value,
  })

  isLoading.value = false

  if (result.success && result.data) {
    if (resetPage) {
      images.value = result.data.images
    } else {
      images.value.push(...result.data.images)
    }
    totalImages.value = result.data.total

    // 更新膨胀统计
    originalTagsCount.value = includeTags.length
    expandedTagsCount.value = result.data.expanded_tags?.length || includeTags.length
  }
}

// 加载更多
async function loadMore() {
  if (!hasMore.value || isLoading.value) return
  currentPage.value++
  await searchImages(false)
}

// 加载所有标签（带缓存）
async function loadAllTags(forceRefresh = false) {
  // 检查缓存是否有效
  if (!forceRefresh && globalStore.isTagCacheValid()) {
    allTags.value = globalStore.tagCache
    return
  }

  // 尝试从缓存加载
  const cached = globalStore.loadTagCache()
  if (!forceRefresh && cached) {
    allTags.value = cached
    return
  }

  // 从 API 加载
  const result = await systemApi.getAllTags()
  if (result.success && result.data) {
    const tags = result.data.tags || []
    allTags.value = tags
    globalStore.saveTagCache(tags)
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
    if (!response.ok) throw new Error('获取图片失败')

    const blob = await response.blob()

    // 检查是否支持 ClipboardItem API
    if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
      // 现代浏览器：直接复制原始格式
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ [blob.type]: blob })
        ])
        toast.success('已复制到剪贴板')
        return
      } catch (clipboardErr) {
        // 某些浏览器只支持 PNG 格式
        if (blob.type !== 'image/png') {
          // 转换为 PNG 再复制
          const pngBlob = await convertToPng(blob)
          await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': pngBlob })
          ])
          toast.success('已复制到剪贴板')
          return
        }
        throw clipboardErr
      }
    }

    // 降级方案：使用 canvas 转换为 PNG 并复制
    const pngBlob = await convertToPng(blob)
    if (typeof ClipboardItem !== 'undefined' && navigator.clipboard?.write) {
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': pngBlob })
      ])
      toast.success('已复制到剪贴板')
    } else {
      // 最终降级：提示用户右键复制
      toast.warning('浏览器不支持复制图片，请右键图片选择复制')
    }
  } catch (err) {
    console.error('复制失败:', err)
    toast.error('复制失败，请尝试右键复制')
  }
}

// 将图片转换为 PNG 格式
async function convertToPng(blob: Blob): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('无法创建 canvas context'))
        return
      }
      ctx.drawImage(img, 0, 0)
      canvas.toBlob((pngBlob) => {
        if (pngBlob) {
          resolve(pngBlob)
        } else {
          reject(new Error('转换 PNG 失败'))
        }
      }, 'image/png')
    }
    img.onerror = () => reject(new Error('加载图片失败'))
    img.src = URL.createObjectURL(blob)
  })
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
  loadAllTags(true) // 强制刷新缓存
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
      loadAllTags(true) // 强制刷新缓存
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
  searchImages(true)
}

// 处理 HQ 模式切换
function handleToggleHQ(enabled: boolean) {
  isHQMode.value = enabled
  toast.info(enabled ? 'HQ 高清模式已开启' : 'HQ 高清模式已关闭')
}

// 处理排序更新
function handleUpdateSort(newSortBy: string) {
  sortBy.value = newSortBy
  searchImages(true)
}

// 处理标签数量范围更新
function handleUpdateTagRange(min: number | null, max: number | null) {
  minTags.value = min
  maxTags.value = max
  searchImages(true)
}

// 处理临时标签更新
function handleUpdateTempTags(tags: string[]) {
  tempTags.value = tags
}

// 应用临时标签到选中图片
async function handleApplyTempTags() {
  if (tempTags.value.length === 0) {
    toast.warning('请先添加临时标签')
    return
  }

  if (selectedImages.value.size === 0) {
    // 如果没有选中图片，应用到当前显示的所有图片
    if (!confirm(`将临时标签应用到当前显示的 ${images.value.length} 张图片？`)) return

    let successCount = 0
    for (const image of images.value) {
      const currentTags = image.tags ? image.tags.split(' ').filter(t => t) : []
      const newTags = [...new Set([...currentTags, ...tempTags.value])]

      const result = await imageApi.updateImageTags(
        image.id,
        newTags,
        globalStore.clientId,
        globalStore.rulesVersion
      )

      if (result.success && result.data) {
        globalStore.updateRulesVersion(result.data.new_version)
        successCount++
      }
    }

    toast.success(`已为 ${successCount} 张图片添加标签`)
    searchImages(true)
  } else {
    // 应用到选中的图片
    let successCount = 0
    for (const imageId of selectedImages.value) {
      const image = images.value.find(img => img.id === imageId)
      if (!image) continue

      const currentTags = image.tags ? image.tags.split(' ').filter(t => t) : []
      const newTags = [...new Set([...currentTags, ...tempTags.value])]

      const result = await imageApi.updateImageTags(
        image.id,
        newTags,
        globalStore.clientId,
        globalStore.rulesVersion
      )

      if (result.success && result.data) {
        globalStore.updateRulesVersion(result.data.new_version)
        successCount++
      }
    }

    toast.success(`已为 ${successCount} 张图片添加标签`)
    selectedImages.value.clear()
    searchImages(true)
  }
}

// 刷新
function refresh() {
  searchImages(true)
  loadAllTags(true) // 强制刷新缓存
}

// 清空搜索
function clearSearch() {
  searchTags.value = []
  searchImages(true)
}

// 切换批量编辑模式
function toggleBatchMode() {
  isBatchMode.value = !isBatchMode.value
  if (!isBatchMode.value) {
    selectedImages.value.clear()
  }
  toast.info(isBatchMode.value ? '批量编辑模式已开启，点击图片选择' : '批量编辑模式已关闭')
}

// 切换图片选择
function toggleImageSelection(image: MemeImage) {
  if (selectedImages.value.has(image.id)) {
    selectedImages.value.delete(image.id)
  } else {
    selectedImages.value.add(image.id)
  }
  // 触发响应式更新
  selectedImages.value = new Set(selectedImages.value)
}

// 全选当前页
function selectAllImages() {
  images.value.forEach(img => selectedImages.value.add(img.id))
  selectedImages.value = new Set(selectedImages.value)
  toast.info(`已选择 ${selectedImages.value.size} 张图片`)
}

// 取消全选
function clearSelection() {
  selectedImages.value.clear()
  selectedImages.value = new Set(selectedImages.value)
}

// 批量删除选中图片
async function batchDeleteSelected() {
  if (selectedImages.value.size === 0) {
    toast.warning('请先选择图片')
    return
  }

  if (!confirm(`确定要删除选中的 ${selectedImages.value.size} 张图片吗？`)) return

  let successCount = 0
  for (const imageId of selectedImages.value) {
    const result = await imageApi.deleteImage(imageId)
    if (result.success) {
      successCount++
    }
  }

  toast.success(`已删除 ${successCount} 张图片`)
  selectedImages.value.clear()
  searchImages(true)
}

// 初始化
onMounted(() => {
  globalStore.init()
  searchImages(true)
  loadAllTags()
})
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden bg-slate-50" :class="{ 'trash-mode-active': isTrashMode }">
    <!-- 顶部搜索栏 -->
    <header class="min-h-16 bg-white/90 border-b border-slate-200 flex items-center px-4 z-30 shrink-0 gap-2 shadow-sm">
      <!-- 搜索容器 -->
      <TagInput
        v-model="searchTags"
        placeholder="输入标签搜索，空格分隔，-排除..."
        theme="mixed"
        :enable-excludes="true"
        :suggestions="allTags"
        class="flex-1"
        @submit="handleSearchSubmit"
      />

      <!-- 统计信息 -->
      <div class="text-sm text-slate-500 whitespace-nowrap flex items-center gap-2">
        <span>{{ totalImages }} 张</span>
        <span v-if="isTrashMode" class="text-red-500">回收站</span>
        <!-- 膨胀统计徽章 -->
        <span
          v-if="isExpansionEnabled && expandedTagsCount > originalTagsCount"
          class="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold"
          :title="`${originalTagsCount} 个标签膨胀为 ${expandedTagsCount} 个关键词`"
        >
          膨胀 {{ originalTagsCount }}→{{ expandedTagsCount }}
        </span>
        <span v-else-if="isExpansionEnabled" class="text-emerald-600">膨胀</span>
        <span v-if="isHQMode" class="text-blue-600">HQ</span>
        <span v-if="sortBy !== 'time_desc'" class="text-purple-600">排序</span>
      </div>
    </header>

    <!-- 批量编辑工具栏 -->
    <div
      v-if="isBatchMode"
      class="bg-blue-600 text-white px-4 py-2 flex items-center justify-between z-30 shrink-0"
    >
      <div class="flex items-center gap-4">
        <span class="font-bold">批量编辑模式</span>
        <span class="text-blue-200">已选择 {{ selectedCount }} 张图片</span>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm transition"
          @click="selectAllImages"
        >
          全选当前页
        </button>
        <button
          class="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm transition"
          @click="clearSelection"
        >
          取消选择
        </button>
        <button
          v-if="selectedCount > 0"
          class="px-3 py-1 bg-red-500 hover:bg-red-600 rounded-lg text-sm transition"
          @click="batchDeleteSelected"
        >
          删除选中
        </button>
        <button
          class="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm transition"
          @click="toggleBatchMode"
        >
          退出
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <main class="flex-1 overflow-y-auto p-4 custom-scrollbar relative bg-slate-50">
      <!-- 图片网格 - 使用旧项目的列数配置 -->
      <div
        v-if="images.length > 0"
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-4 pb-40"
      >
        <MemeCard
          v-for="(image, index) in images"
          :key="image.id"
          :image="image"
          :index="index"
          :is-trash="isTrashMode"
          :prefer-h-q="isHQMode"
          :selectable="isBatchMode"
          :selected="selectedImages.has(image.id)"
          @copy="handleCopyImage"
          @delete="handleDeleteImage"
          @click-tag="handleTagClick"
          @edit="handleEditImage"
          @select="toggleImageSelection"
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

      <!-- 加载指示器 -->
      <div v-if="isLoading" class="py-12 text-center text-slate-400">
        <RefreshCw class="w-8 h-8 animate-spin mx-auto" />
      </div>

      <!-- 到底提示 -->
      <div v-if="!hasMore && images.length > 0 && !isLoading" class="py-16 text-center text-sm font-bold text-slate-300">
        - 到底了 -
      </div>

      <!-- 加载更多按钮 -->
      <div v-if="hasMore && !isLoading" class="flex justify-center mt-4 mb-8">
        <button
          class="px-6 py-2 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition"
          @click="loadMore"
        >
          加载更多
        </button>
      </div>
    </main>

    <!-- FAB 悬浮按钮组 -->
    <FloatingButtons
      :is-trash-mode="isTrashMode"
      :is-expansion-enabled="isExpansionEnabled"
      :is-h-q-mode="isHQMode"
      :is-batch-mode="isBatchMode"
      :sort-by="sortBy"
      :min-tags="minTags ?? undefined"
      :max-tags="maxTags ?? undefined"
      :temp-tags="tempTags"
      @upload="showUploadModal = true"
      @open-rules="showRulesPanel = true"
      @export="handleExport"
      @import="handleImport"
      @toggle-trash="handleToggleTrash"
      @toggle-expansion="handleToggleExpansion"
      @toggle-h-q="handleToggleHQ"
      @toggle-batch="toggleBatchMode"
      @search="handleSearchSubmit"
      @refresh="refresh"
      @clear="clearSearch"
      @update-sort="handleUpdateSort"
      @update-tag-range="handleUpdateTagRange"
      @update-temp-tags="handleUpdateTempTags"
      @apply-temp-tags="handleApplyTempTags"
    />

    <!-- 规则树面板 -->
    <RuleTree
      :visible="showRulesPanel"
      @close="showRulesPanel = false"
      @toggle="showRulesPanel = !showRulesPanel"
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
