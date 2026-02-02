<script setup lang="ts">
/**
 * Gallery 主页面 - 图片画廊
 * 一比一复刻旧项目的所有功能
 */
import { ref, onMounted, computed, watch } from 'vue'
import { Loader2 } from 'lucide-vue-next'
import TagInput from '@/components/TagInput.vue'
import MemeCard from '@/components/MemeCard.vue'
import RuleTree from '@/components/RuleTree.vue'
import SparkMD5 from 'spark-md5'
import FloatingButtons from '@/components/FloatingButtons.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import { useImageApi, useRulesApi, useSystemApi } from '@/composables/useApi'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useToast } from '@/composables/useToast'
import type { MemeImage, RuleGroup } from '@/types'

// API & Store
const imageApi = useImageApi()
const rulesApi = useRulesApi()
const systemApi = useSystemApi()
const globalStore = useGlobalStore()
const toast = useToast()

// 状态
const images = ref<MemeImage[]>([])
type SearchTag = { text: string; exclude: boolean; synonym: boolean; synonymWords: string[] | null }
const searchTags = ref<Array<SearchTag | string>>([])
const searchInputRef = ref<InstanceType<typeof TagInput> | null>(null)
const allTags = ref<string[]>([])
const baseTags = ref<string[]>([])
const tagInputQuery = ref('')
const filteredTagSuggestions = ref<string[]>([])
const isLoading = ref(false)
const totalImages = ref(0)
const limit = 40
const offset = ref(0)
const hasMore = ref(true)

// 模态框状态
const uploadInputRef = ref<HTMLInputElement | null>(null)
const importInputRef = ref<HTMLInputElement | null>(null)
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
const TAG_SUGGESTION_LIMIT = 4
const MD5_ID_LEN = 8

function md5ToId(md5: string) {
  if (!md5) return 0
  const slice = md5.slice(0, MD5_ID_LEN)
  const parsed = Number.parseInt(slice, 16)
  return Number.isNaN(parsed) ? 0 : parsed
}

function normalizeSearchTags(tags: Array<SearchTag | string>): SearchTag[] {
  return tags
    .map((tag) => {
      if (typeof tag === 'string') {
        return { text: tag, exclude: false, synonym: false, synonymWords: null }
      }
      return tag
    })
    .filter((tag) => tag.text)
}

function collectRuleKeywords(): string[] {
  const tree = globalStore.rulesTree
  if (!tree || !tree.groups) return []
  const keywords = new Set<string>()
  const stack = [...tree.groups]

  while (stack.length > 0) {
    const node = stack.pop()
    if (!node) continue
    if (typeof node.name === 'string') {
      keywords.add(node.name)
    }
    node.keywords.forEach((kw) => {
      if (typeof kw.keyword === 'string') {
        keywords.add(kw.keyword)
      }
    })
    if (node.children && node.children.length > 0) {
      node.children.forEach(child => stack.push(child))
    }
  }
  return Array.from(keywords)
}

function buildAllSuggestions(tags: string[]): string[] {
  const unique = new Set<string>()
  tags.forEach((tag) => {
    if (typeof tag === 'string') {
      unique.add(tag)
    }
  })
  collectRuleKeywords().forEach((tag) => unique.add(tag))
  return Array.from(unique)
}

function filterAndUpdateDatalist(currentInput: string) {
  const source = allTags.value
  if (!source.length) {
    filteredTagSuggestions.value = []
    return
  }

  const isExclude = currentInput.startsWith('-')
  const prefix = isExclude ? '-' : ''
  const searchText = isExclude ? currentInput.slice(1) : currentInput

  if (searchText.startsWith('.')) {
    const partialExt = searchText.slice(1).toLowerCase()
    filteredTagSuggestions.value = SUPPORTED_EXTENSIONS
      .filter(ext => ext.startsWith(partialExt))
      .map(ext => `${prefix}.${ext}`)
    return
  }

  const filtered = source.filter(tag =>
    tag.toLowerCase().includes(searchText.toLowerCase())
  )
  const limited = filtered.slice(0, TAG_SUGGESTION_LIMIT)
  filteredTagSuggestions.value = limited.map(tag => `${prefix}${tag}`)
}

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

  const normalizedTags = normalizeSearchTags(searchTags.value)

  // 分离标签类型（旧项目逻辑）
  const extensionIncludes = normalizedTags
    .filter(t => !t.exclude && !t.synonym && isExtensionTag(t.text))
    .map(t => t.text.slice(1).toLowerCase())

  const extensionExcludes = normalizedTags
    .filter(t => t.exclude && !t.synonym && isExtensionTag(t.text))
    .map(t => t.text.slice(1).toLowerCase())

  const normalIncludes = normalizedTags
    .filter(t => !t.exclude && !t.synonym && !isExtensionTag(t.text))
    .map(t => t.text)
  const synonymIncludes = normalizedTags.filter(t => !t.exclude && t.synonym)
  const normalExcludes = normalizedTags
    .filter(t => t.exclude && !t.synonym && !isExtensionTag(t.text))
    .map(t => t.text)
  const synonymExcludes = normalizedTags.filter(t => t.exclude && t.synonym)

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
    const rawResults = result.data.results
    const visibleResults = isTrashMode.value
      ? rawResults
      : rawResults.filter(item => !item.is_trash && !item.tags.includes('trash_bin'))

    const mapped = visibleResults.map(item => ({
      id: md5ToId(item.md5),
      md5: item.md5,
      filename: item.filename,
      tags: item.tags.join(' '),
      file_size: item.size,
      width: item.w,
      height: item.h,
      created_at: '',
    }))

    if (resetPage) {
      images.value = mapped
    } else {
      images.value.push(...mapped)
    }
    totalImages.value = result.data.total
    offset.value += rawResults.length
    hasMore.value = rawResults.length >= limit

    originalTagsCount.value = totalOriginal
    expandedTagsCount.value = totalExpanded
  }
}

watch(searchTags, (tags) => {
  const normalized = normalizeSearchTags(tags)
  const hasTrashTag = normalized.some(t => t.text === 'trash_bin' && !t.exclude)
  if (isTrashMode.value !== hasTrashTag) {
    isTrashMode.value = hasTrashTag
  }
}, { deep: true })

watch(() => globalStore.rulesTree, () => {
  allTags.value = buildAllSuggestions(baseTags.value)
  filterAndUpdateDatalist(tagInputQuery.value)
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
    baseTags.value = [...globalStore.tagCache]
    allTags.value = buildAllSuggestions(baseTags.value)
    filterAndUpdateDatalist('')
    return
  }

  // 尝试从缓存加载
  const cached = globalStore.loadTagCache()
  if (!forceRefresh && cached) {
    baseTags.value = [...cached]
    allTags.value = buildAllSuggestions(baseTags.value)
    filterAndUpdateDatalist('')
    return
  }

  // 从 API 加载
  const result = await systemApi.getAllTags()
  if (result.success && result.data) {
    const tags = result.data.tags || []
    baseTags.value = [...tags]
    allTags.value = buildAllSuggestions(baseTags.value)
    globalStore.saveTagCache(tags)
    filterAndUpdateDatalist('')
  }
}


// 处理搜索提交
function handleSearchSubmit() {
  searchImages(true)
}

function handleSearchInputUpdate(value: string) {
  tagInputQuery.value = value
  filterAndUpdateDatalist(value)
}

function handleTempInputUpdate(value: string) {
  tagInputQuery.value = value
  filterAndUpdateDatalist(value)
}


function focusSearchInput() {
  searchInputRef.value?.focus()
  mainRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

// 处理复制标签（旧项目行为）


// 处理删除图片（旧项目：切换 trash_bin 标签）
async function handleDeleteImage(image: MemeImage) {
  const currentTags = (image.tags || '').split(' ').filter(t => t)
  const hasTrash = currentTags.includes('trash_bin')
  const nextTags = hasTrash
    ? currentTags.filter(t => t !== 'trash_bin')
    : [...currentTags, 'trash_bin']

  const idx = images.value.findIndex(img => img.md5 === image.md5)
  const oldTags = idx !== -1 ? (images.value[idx]?.tags ?? image.tags) : image.tags

  if (idx !== -1) {
    const existing = images.value[idx]
    if (existing) {
      images.value[idx] = { ...existing, tags: nextTags.join(' ') }
    }
  }

  const result = await systemApi.updateTags(image.md5, nextTags)
  const ok = result.success && (result.data?.success ?? true)

  if (!ok && idx !== -1) {
    const existing = images.value[idx]
    if (existing) {
      images.value[idx] = { ...existing, tags: oldTags || '' }
    }
  }
}


async function handleUpdateTags(image: MemeImage, nextTags: string[]) {
  const index = images.value.findIndex(img => img.md5 === image.md5)
  const oldTags = (index !== -1 ? images.value[index]?.tags : image.tags) || ''
  const nextText = nextTags.join(' ')

  if (index !== -1) {
    const existing = images.value[index]
    if (existing) {
      images.value[index] = { ...existing, tags: nextText }
    }
  }

  const result = await systemApi.updateTags(image.md5, nextTags)
  const ok = result.success && (result.data?.success ?? true)

  if (!ok && index !== -1) {
    const existing = images.value[index]
    if (existing) {
      images.value[index] = { ...existing, tags: oldTags }
    }
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
        toast.error(`上传失败：${result.error}`)
      }
    }

    refresh()
  } catch (err) {
    console.error('上传出错:', err)
    const message = err instanceof Error ? err.message : '未知错误'
    toast.error(`上传出错：${message}`)
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
    const payload = result.data as Record<string, unknown>
    const dataStr = JSON.stringify(payload, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bqbq_export_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    const imagesCount = Array.isArray((payload as { images?: unknown }).images)
      ? (payload as { images?: unknown[] }).images?.length ?? 0
      : 0
    toast.success(`导出成功！（${imagesCount} 张图片）`)
  } else {
    toast.error(`导出失败：${result.error}`)
  }
}

// 处理导入
async function handleImport() {
  if (!importInputRef.value) return
  importInputRef.value.value = ''
  importInputRef.value.click()
}

async function handleJsonImportChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return

  toast.info('正在导入数据...')
  const result = await systemApi.importData(file)
  const ok = result.success && (result.data?.success ?? true)
  if (ok) {
    const added = result.data?.imported_images ?? 0
    const skipped = result.data?.skipped_images ?? 0
    toast.success(`导入成功！新增 ${added} 张，跳过 ${skipped} 张`)
    await refreshRulesTree()
    searchImages(true)
  } else {
    const message = result.success ? result.data?.error : result.error
    toast.error(`导入失败：${message}`)
  }
}

// 处理回收站模式切换
function handleToggleTrash(isTrash: boolean) {
  isTrashMode.value = isTrash
  const hasTrashTag = normalizeSearchTags(searchTags.value).some(t => t.text === 'trash_bin' && !t.exclude)
  if (isTrash && !hasTrashTag) {
    searchTags.value.push({ text: 'trash_bin', exclude: false, synonym: false, synonymWords: null })
  } else if (!isTrash && hasTrashTag) {
    searchTags.value = normalizeSearchTags(searchTags.value)
      .filter(t => !(t.text === 'trash_bin' && !t.exclude))
  }
  searchImages(true)
}


// 处理关键词膨胀切换
function handleToggleExpansion(enabled: boolean) {
  isExpansionEnabled.value = enabled
  if (enabled) {
    toast.success('同义词膨胀已开启')
  } else {
    toast.info('同义词膨胀已关闭')
  }
  if (searchTags.value.length > 0) {
    searchImages(true)
  }
}


// 处理 HQ 模式切换
function handleToggleHQ(enabled: boolean) {
  isHQMode.value = enabled
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
  toast[enabled ? 'success' : 'info'](enabled ? '已进入批量打标模式' : '已退出批量打标模式')
}


async function handleCardTempApply(image: MemeImage) {
  if (tempTags.value.length === 0) return

  const currentTags = image.tags ? image.tags.split(' ').filter(t => t) : []
  const nextTags = [...currentTags]
  let changed = false

  tempTags.value.forEach((tag) => {
    if (!nextTags.includes(tag)) {
      nextTags.push(tag)
      changed = true
    }
  })

  if (!changed) return

  const idx = images.value.findIndex(img => img.md5 === image.md5)
  const oldTags = idx !== -1 ? (images.value[idx]?.tags ?? image.tags) : image.tags

  if (idx !== -1) {
    const existing = images.value[idx]
    if (existing) {
      images.value[idx] = { ...existing, tags: nextTags.join(' ') }
    }
  }

  const result = await systemApi.updateTags(image.md5, nextTags)
  const ok = result.success && (result.data?.success ?? true)

  if (!ok && idx !== -1) {
    const existing = images.value[idx]
    if (existing) {
      images.value[idx] = { ...existing, tags: oldTags || '' }
    }
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

async function refreshRulesTree() {
  const result = await rulesApi.getRulesTree()
  if (result.success && result.data) {
    globalStore.setRulesTree(result.data)
  }
}
</script>

<template>
  <div class="h-screen flex flex-col bg-slate-50 text-slate-800 overflow-hidden" :class="{ 'trash-mode-active': isTrashMode }">
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
        placeholder="输入关键词 (空格生成胶囊)..."
        theme="mixed"
        :enable-excludes="true"
        :suggestions="allTags"
        @submit="handleSearchSubmit"
        @input-update="handleSearchInputUpdate"
      />
    </header>

    <!-- 主内容区 - 图片网格 -->
    <main
      id="gallery-container"
      ref="mainRef"
      class="flex-1 overflow-y-auto p-4 custom-scrollbar relative bg-slate-50"
      @scroll="handleMainScroll"
    >
      <!-- 图片网格 - 使用旧项目的列数配置 -->
      <div
        id="meme-grid"
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-4 pb-40"
      >
        <MemeCard
          v-for="(image, index) in images"
          :key="image.md5"
          :image="image"
          :index="index"
          :is-trash="isTrashMode"
          :prefer-h-q="isHQMode"
          :temp-mode="isTempTagMode"
          @delete="handleDeleteImage"
          @apply-temp-tags="handleCardTempApply"
          @update-tags="handleUpdateTags"
        />
      </div>

      <!-- 加载指示器 -->
      <div
        id="loading-indicator"
        :class="['py-12 text-center text-slate-400', isLoading ? '' : 'hidden']"
      >
        <Loader2 class="w-8 h-8 animate-spin mx-auto" />
      </div>

      <!-- 到底提示 -->
      <div
        id="end-indicator"
        :class="[
          'py-16 text-center text-sm font-bold text-slate-300',
          (!hasMore && images.length > 0 && !isLoading) ? '' : 'hidden'
        ]"
      >
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
      @temp-input-update="handleTempInputUpdate"
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
      <option v-for="tag in filteredTagSuggestions" :key="tag" :value="tag" />
    </datalist>

    <input
      id="file-upload"
      ref="uploadInputRef"
      type="file"
      class="hidden"
      multiple
      accept="image/*"
      @change="handleUploadChange"
    />

    <input
      id="json-import-input"
      ref="importInputRef"
      type="file"
      class="hidden"
      accept=".json"
      @change="handleJsonImportChange"
    />
  </div>
</template>
