<script setup lang="ts">
/**
 * Gallery 主页面 - 图片画廊
 * 一比一复刻旧项目的所有功能
 */
import { ref, onMounted, computed, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import TagInput from '@/components/TagInput.vue'
import MemeCard from '@/components/MemeCard.vue'
import RuleTree from '@/components/RuleTree.vue'
import SparkMD5 from 'spark-md5'
import FloatingButtons from '@/components/FloatingButtons.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import { useImageApi, useSystemApi } from '@/composables/useApi'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useToast } from '@/composables/useToast'
import type { MemeImage, RuleGroup } from '@/types'

// API & Store
const imageApi = useImageApi()
const systemApi = useSystemApi()
const globalStore = useGlobalStore()
const toast = useToast()

// 状态
const images = ref<MemeImage[]>([])
const searchTags = ref<{ text: string; exclude: boolean; synonym: boolean; synonymWords: string[] | null }[]>([])
const searchInputRef = ref<InstanceType<typeof TagInput> | null>(null)
const allTags = ref<string[]>([])
const isLoading = ref(false)
const totalImages = ref(0)
const limit = 40
const offset = ref(0)
const hasMore = ref(true)

// 模态框状态
const uploadInputRef = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)
const showRulesPanel = ref(false)
// 功能开关（从 store 读取持久化值）
const isTrashMode = ref(false)
const isExpansionEnabled = computed({
  get: () => globalStore.isExpansionEnabled,
  set: (val) => globalStore.setExpansionEnabled(val)
})
const isHQMode = computed({
  get: () => globalStore.preferHQ,
  set: (val) => globalStore.setPreferHQ(val)
})

// 搜索参数（与旧项目一致）
const sortBy = ref('date_desc')
const minTags = ref(0)
const maxTags = ref(-1)

// 临时标签（批量打标）
const tempTags = ref<string[]>([])
const isTempTagMode = ref(false)

// 图片预览（旧项目无预览，已移除）
const mainRef = ref<HTMLElement | null>(null)

// 膨胀统计
const expandedTagsCount = ref(0)
const originalTagsCount = ref(0)

// 计算属性

const SUPPORTED_EXTENSIONS = ['gif', 'png', 'jpg', 'webp']

function isExtensionTag(text: string) {
  if (!text.startsWith('.')) return false
  const ext = text.slice(1).toLowerCase()
  return SUPPORTED_EXTENSIONS.includes(ext)
}

function expandSingleKeyword(inputText: string): string[] {
  if (!isExpansionEnabled.value) {
    return [inputText]
  }
  if (!globalStore.rulesTree || !globalStore.rulesTree.groups) {
    return [inputText]
  }

  const uniqueKeywords = new Set<string>()
  uniqueKeywords.add(inputText)

  const recursivelyCollectKeywords = (node: RuleGroup) => {
    if (!node.enabled) return
    node.keywords
      .filter(k => k.enabled)
      .forEach(k => uniqueKeywords.add(k.keyword))
    node.children.forEach(recursivelyCollectKeywords)
  }

  const traverseAndMatch = (nodes: RuleGroup[]) => {
    nodes.forEach(node => {
      if (!node.enabled) return
      if (node.name === inputText) {
        recursivelyCollectKeywords(node)
        return
      }
      const matchedKeyword = node.keywords.find(k => k.keyword === inputText && k.enabled)
      if (matchedKeyword) {
        recursivelyCollectKeywords(node)
        return
      }
      traverseAndMatch(node.children)
    })
  }

  traverseAndMatch(globalStore.rulesTree.groups)
  return Array.from(uniqueKeywords)
}

function expandKeywordsToGroups(inputs: string[]) {
  return inputs.map(input => expandSingleKeyword(input))
}

// 搜索图片
async function searchImages(resetPage = true) {
  if (resetPage) {
    offset.value = 0
    images.value = []
    hasMore.value = true
  }

  if (!hasMore.value && !resetPage) return

  isLoading.value = true

  // 分离标签类型（旧项目逻辑）
  const extensionIncludes = searchTags.value
    .filter(t => !t.exclude && !t.synonym && isExtensionTag(t.text))
    .map(t => t.text.slice(1).toLowerCase())

  const extensionExcludes = searchTags.value
    .filter(t => t.exclude && !t.synonym && isExtensionTag(t.text))
    .map(t => t.text.slice(1).toLowerCase())

  const normalIncludes = searchTags.value
    .filter(t => !t.exclude && !t.synonym && !isExtensionTag(t.text))
    .map(t => t.text)
  const synonymIncludes = searchTags.value.filter(t => !t.exclude && t.synonym)
  const normalExcludes = searchTags.value
    .filter(t => t.exclude && !t.synonym && !isExtensionTag(t.text))
    .map(t => t.text)
  const synonymExcludes = searchTags.value.filter(t => t.exclude && t.synonym)

  if (isTrashMode.value) {
    normalIncludes.push('trash_bin')
  } else {
    normalExcludes.push('trash_bin')
  }

  const expandedNormalIncludes = expandKeywordsToGroups(normalIncludes)

  const synonymIncludeGroups = synonymIncludes.map(t => {
    const expandedWords = (t.synonymWords || []).flatMap(word => expandSingleKeyword(word))
    return [...new Set(expandedWords)]
  })

  const expandedIncludesGroups = [...expandedNormalIncludes, ...synonymIncludeGroups]

  const expandedNormalExcludes = expandKeywordsToGroups(normalExcludes)

  const synonymExcludeAndGroups = synonymExcludes.map(t => {
    return (t.synonymWords || []).map(word => {
      const expanded = expandSingleKeyword(word)
      return [...new Set(expanded)]
    })
  })

  const expandedExcludesGroups = [...expandedNormalExcludes]

  const totalExpandedIncludes = expandedIncludesGroups.reduce((sum, g) => sum + g.length, 0)
  const totalExpandedExcludes = expandedExcludesGroups.reduce((sum, g) => sum + g.length, 0)
  const totalExpandedAndExcludes = synonymExcludeAndGroups.reduce((sum, capsule) =>
    sum + capsule.reduce((s, g) => s + g.length, 0), 0
  )

  const totalOriginalIncludes = normalIncludes.length + synonymIncludes.reduce((sum, t) => sum + (t.synonymWords || []).length, 0)
  const totalOriginalExcludes = normalExcludes.length + synonymExcludes.reduce((sum, t) => sum + (t.synonymWords || []).length, 0)

  const totalOriginal = totalOriginalIncludes + totalOriginalExcludes
  const totalExpanded = totalExpandedIncludes + totalExpandedExcludes + totalExpandedAndExcludes

  const result = await imageApi.advancedSearch({
    offset: offset.value,
    limit,
    sort_by: sortBy.value,
    keywords: expandedIncludesGroups,
    excludes: expandedExcludesGroups,
    excludes_and: synonymExcludeAndGroups,
    extensions: extensionIncludes,
    exclude_extensions: extensionExcludes,
    min_tags: minTags.value,
    max_tags: maxTags.value,
  })

  isLoading.value = false

  if (result.success && result.data) {
    const mapped = result.data.results.map(item => ({
      id: item.id,
      md5: item.md5,
      filename: item.filename,
      tags: item.tags.join(' '),
      file_size: item.file_size,
      width: item.width,
      height: item.height,
      created_at: '',
    }))

    if (resetPage) {
      images.value = mapped
    } else {
      images.value.push(...mapped)
    }
    totalImages.value = result.data.total
    offset.value += result.data.results.length
    hasMore.value = result.data.results.length >= limit

    originalTagsCount.value = totalOriginal
    expandedTagsCount.value = totalExpanded
  }
}

watch(searchTags, (tags) => {
  const hasTrashTag = tags.some(t => t.text === 'trash_bin' && !t.exclude)
  if (isTrashMode.value !== hasTrashTag) {
    isTrashMode.value = hasTrashTag
  }
}, { deep: true })

// 加载更多
async function loadMore() {
  if (!hasMore.value || isLoading.value) return
  await searchImages(false)
}

function handleMainScroll() {
  const el = mainRef.value
  if (!el || isLoading.value || !hasMore.value) return
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 200) {
    loadMore()
  }
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

function focusSearchInput() {
  searchInputRef.value?.focus()
  mainRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

// 处理复制标签（旧项目行为）
async function handleCopyImage(image: MemeImage) {
  const tagsText = (image.tags || '').trim()
  if (!tagsText) {
    toast.warning('无标签可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(tagsText)
    toast.success('标签已复制')
  } catch (err) {
    console.error('复制失败:', err)
    toast.error('复制失败，请手动复制')
  }
}

// 处理删除图片（旧项目：切换 trash_bin 标签）
async function handleDeleteImage(image: MemeImage) {
  const currentTags = (image.tags || '').split(' ').filter(t => t)
  const hasTrash = currentTags.includes('trash_bin')
  const nextTags = hasTrash
    ? currentTags.filter(t => t !== 'trash_bin')
    : [...currentTags, 'trash_bin']

  const result = await imageApi.updateImageTags(
    image.id,
    nextTags,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    const idx = images.value.findIndex(img => img.id === image.id)
    if (idx !== -1) {
      const updated = { ...images.value[idx], tags: nextTags.join(' ') }
      if (isTrashMode.value && !updated.tags.includes('trash_bin')) {
        images.value.splice(idx, 1)
      } else if (!isTrashMode.value && updated.tags.includes('trash_bin')) {
        images.value.splice(idx, 1)
      } else {
        images.value[idx] = updated
      }
    }
    toast.success(hasTrash ? '已恢复' : '已移入回收站')
  } else {
    toast.error('操作失败')
  }
}

async function handleUpdateTags(image: MemeImage, nextTags: string[]) {
  const index = images.value.findIndex(img => img.id === image.id)
  const oldTags = (index !== -1 ? images.value[index]?.tags : image.tags) || ''
  const nextText = nextTags.join(' ')

  if (index !== -1) {
    const existing = images.value[index]
    if (existing) {
      images.value[index] = { ...existing, tags: nextText }
    }
  }

  const result = await imageApi.updateImageTags(
    image.id,
    nextTags,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    const nowTrash = nextTags.includes('trash_bin')
    if (index !== -1) {
      if (isTrashMode.value && !nowTrash) {
        images.value.splice(index, 1)
      } else if (!isTrashMode.value && nowTrash) {
        images.value.splice(index, 1)
      }
    }
  } else {
    if (index !== -1) {
      const existing = images.value[index]
      if (existing) {
        images.value[index] = { ...existing, tags: oldTags }
      }
    }
    toast.error('保存标签失败')
  }
}

function triggerUpload() {
  uploadInputRef.value?.click()
}

async function checkMD5Exists(md5: string, refreshTime: boolean) {
  const response = await fetch('/api/check_md5', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ md5, refresh_time: refreshTime }),
  })
  return await response.json()
}

async function uploadFiles(files: FileList | null) {
  if (!files || files.length === 0) return
  isUploading.value = true

  try {
    for (const file of Array.from(files)) {
      const buffer = await file.arrayBuffer()
      const md5 = SparkMD5.ArrayBuffer.hash(buffer)

      const checkResult = await checkMD5Exists(md5, true)
      if (checkResult.exists) {
        toast.info(`图片已存在：${file.name}${checkResult.time_refreshed ? '（已更新时间戳）' : ''}`)
        continue
      }

      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()
      if (result.success) {
        toast.success(`上传成功：${file.name}`)
      } else {
        toast.error(`上传失败：${result.error || '未知错误'}`)
      }
    }

    refresh()
  } catch (err) {
    console.error('上传出错:', err)
    toast.error('上传出错，请重试')
  } finally {
    isUploading.value = false
  }
}

function handleUploadChange(e: Event) {
  const input = e.target as HTMLInputElement
  uploadFiles(input.files)
  if (input) {
    input.value = ''
  }
}

// 处理导出
async function handleExport() {
  toast.info('正在导出数据...')
  const result = await systemApi.exportData()
  if (result.success && result.data) {
    const url = URL.createObjectURL(result.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `bqbq_export_${Date.now()}.json`
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
      const added = result.data?.imported_images ?? 0
      const skipped = result.data?.skipped_images ?? 0
      toast.success(`导入成功！新增 ${added} 张，跳过 ${skipped} 张`)
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
  const hasTrashTag = searchTags.value.some(t => t.text === 'trash_bin' && !t.exclude)
  if (isTrash && !hasTrashTag) {
    searchTags.value.push({ text: 'trash_bin', exclude: false, synonym: false, synonymWords: null })
  } else if (!isTrash && hasTrashTag) {
    searchTags.value = searchTags.value.filter(t => !(t.text === 'trash_bin' && !t.exclude))
  }
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
  searchImages(true)
}

// 处理排序更新
function handleUpdateSort(newSortBy: string) {
  sortBy.value = newSortBy
  searchImages(true)
}

// 处理标签数量范围更新
function handleUpdateTagRange(min: number | null, max: number | null) {
  minTags.value = typeof min === 'number' && min > 0 ? min : 0
  maxTags.value = typeof max === 'number' && max >= 0 ? max : -1
  searchImages(true)
}

// 处理临时标签更新
function handleUpdateTempTags(tags: string[]) {
  tempTags.value = tags
}

function handleToggleTempMode(enabled: boolean) {
  isTempTagMode.value = enabled
  toast.info(enabled ? '批量打标模式已开启' : '批量打标模式已关闭')
}

async function handleCardTempApply(image: MemeImage) {
  if (tempTags.value.length === 0) {
    toast.warning('请先添加临时标签')
    return
  }

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
    const idx = images.value.findIndex(img => img.id === image.id)
    if (idx !== -1) {
      const existing = images.value[idx]
      if (existing) {
        images.value[idx] = { ...existing, tags: newTags.join(' ') }
      }
    }
    toast.success('已应用临时标签')
  } else {
    toast.error('批量打标失败')
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
  isTrashMode.value = false
  searchImages(true)
}

// 切换批量编辑模式

// 初始化
onMounted(() => {
  globalStore.init()
  searchImages(true)
  loadAllTags()
})
</script>

<template>
  <div class="h-screen flex flex-col bg-slate-50 overflow-hidden" :class="{ 'trash-mode-active': isTrashMode }">
    <!-- 顶部搜索栏 - 旧项目结构 -->
    <header
      id="app-header"
      class="min-h-16 bg-white/90 border-b border-slate-200 flex items-center px-4 z-30 shrink-0 gap-2 shadow-sm"
    >
      <TagInput
        ref="searchInputRef"
        id="header-search-bar"
        v-model="searchTags"
        title="输入标签搜索图片，支持同义词组(逗号分隔)和排除标签(-前缀)"
        placeholder="输入标签搜索，空格分隔，-排除..."
        theme="mixed"
        :enable-excludes="true"
        :suggestions="allTags"
        @submit="handleSearchSubmit"
      />
    </header>

    <!-- 主内容区 - 图片网格 -->
    <main
      ref="mainRef"
      class="flex-1 overflow-y-auto p-4 custom-scrollbar relative bg-slate-50"
      @scroll="handleMainScroll"
    >
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
          :temp-mode="isTempTagMode"
          @copy="handleCopyImage"
          @delete="handleDeleteImage"
          @apply-temp-tags="handleCardTempApply"
          @update-tags="handleUpdateTags"
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
      <div v-if="isLoading" class="flex justify-center py-8">
        <div class="w-8 h-8 border-4 border-slate-200 border-t-blue-500 rounded-full animate-spin"></div>
      </div>

      <!-- 到底提示 -->
      <div v-if="!hasMore && images.length > 0 && !isLoading" class="py-12 text-center text-sm font-semibold text-slate-300">
        - 到底了 -
      </div>

    </main>

    <!-- FAB 悬浮按钮组 -->
    <FloatingButtons
      :is-trash-mode="isTrashMode"
      :is-expansion-enabled="isExpansionEnabled"
      :is-h-q-mode="isHQMode"
      :is-temp-tag-mode="isTempTagMode"
      :sort-by="sortBy"
      :min-tags="minTags"
      :max-tags="maxTags"
      :temp-tags="tempTags"
      :expanded-original="originalTagsCount"
      :expanded-total="expandedTagsCount"
      :is-uploading="isUploading"
      @upload="triggerUpload"
      @export="handleExport"
      @import="handleImport"
      @toggle-trash="handleToggleTrash"
      @toggle-expansion="handleToggleExpansion"
      @toggle-h-q="handleToggleHQ"
      @toggle-temp-mode="handleToggleTempMode"
      @focus-search="focusSearchInput"
      @refresh="refresh"
      @clear="clearSearch"
      @update-sort="handleUpdateSort"
      @update-tag-range="handleUpdateTagRange"
      @update-temp-tags="handleUpdateTempTags"
    />

    <!-- 规则树面板 -->
    <RuleTree
      :visible="showRulesPanel"
      @close="showRulesPanel = false"
      @toggle="showRulesPanel = !showRulesPanel"
      @update="loadAllTags"
    />

    <!-- Toast 通知容器 -->
    <ToastContainer />

    <datalist id="tag-suggestions">
      <option v-for="tag in allTags" :key="tag" :value="tag" />
    </datalist>

    <input
      ref="uploadInputRef"
      type="file"
      class="hidden"
      multiple
      accept="image/*"
      @change="handleUploadChange"
    />
  </div>
</template>
