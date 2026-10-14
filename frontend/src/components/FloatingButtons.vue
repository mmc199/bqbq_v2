<script setup lang="ts">
/**
 * FloatingButtons 组件 - FAB 悬浮按钮组 
 * 完全复刻旧项目的顺序和样式，包含 FAB 按钮排列、面板控制、规则样式
 */
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Search, RefreshCw, X, Download, Upload, Trash2,
  TreePine, ImagePlus, ChevronsRight, ChevronsLeft, Loader2,
  ArrowUpDown,
  Hash, Stamp, FileText
} from 'lucide-vue-next'
import * as noUiSlider from 'nouislider'
import 'nouislider/dist/nouislider.css'
import TagInput from '@/components/TagInput.vue'
import { useGlobalStore } from '@/stores/useGlobalStore'

const SLIDER_MAX_VISUAL = 6
const INFINITY_DISPLAY = '∞'
const DEFAULT_MINI_TOP = 256
const DRAG_THRESHOLD = 5

const props = defineProps<{
  isTrashMode?: boolean
  isExpansionEnabled?: boolean
  isHQMode?: boolean
  isTempTagMode?: boolean
  sortBy?: string
  minTags?: number | null
  maxTags?: number | null
  tempTags?: string[]
  expandedOriginal?: number
  expandedTotal?: number
  isUploading?: boolean
}>()

const emit = defineEmits<{
  upload: []
  export: []
  import: []
  toggleTrash: [isTrash: boolean]
  toggleExpansion: [enabled: boolean]
  toggleHQ: [enabled: boolean]
  toggleTempMode: [enabled: boolean]
  focusSearch: []
  refresh: []
  clear: []
  updateSort: [sortBy: string]
  updateTagRange: [min: number | null, max: number | null]
  updateTempTags: [tags: string[]]
  tempInputUpdate: [value: string]
}>()

const globalStore = useGlobalStore()
const isTrashMode = computed(() => !!props.isTrashMode)
const isExpansionEnabled = computed(() => !!props.isExpansionEnabled)
const isHQMode = computed(() => !!props.isHQMode)

const isCollapsed = computed({
  get: () => globalStore.fabCollapsed,
  set: (val) => globalStore.setFabCollapsed(val)
})

const showSortMenu = ref(false)
const showTagCountPanel = ref(false)
const showTempTagsPanel = ref(false)
const sortMenuRef = ref<HTMLElement | null>(null)
const sortButtonRef = ref<HTMLElement | null>(null)

const sortBy = computed(() => props.sortBy ?? 'date_desc')

const appliedMin = computed(() => (typeof props.minTags === 'number' && props.minTags > 0 ? props.minTags : 0))
const appliedMax = computed(() => (typeof props.maxTags === 'number' && props.maxTags >= 0 ? props.maxTags : -1))
const normalizedMinPayload = computed<number | null>(() =>
  typeof props.minTags === 'number' && props.minTags > 0 ? props.minTags : null
)
const normalizedMaxPayload = computed<number | null>(() =>
  typeof props.maxTags === 'number' && props.maxTags >= 0 ? props.maxTags : null
)
const isTagRangeApplied = computed(() => appliedMin.value > 0 || appliedMax.value >= 0)
const appliedRangeText = computed(() => `${appliedMin.value}-${appliedMax.value < 0 ? INFINITY_DISPLAY : appliedMax.value}`)

const expandedOriginal = computed(() => props.expandedOriginal ?? 0)
const expandedTotal = computed(() => props.expandedTotal ?? 0)
const showExpansionBadge = computed(() =>
  isExpansionEnabled.value && expandedTotal.value > expandedOriginal.value && expandedOriginal.value > 0
)
const expansionBadgeText = computed(() => `${expandedOriginal.value}→${expandedTotal.value}`)

const localMinTags = ref(appliedMin.value)
const localMaxTags = ref(appliedMax.value)
const minInputValue = ref(localMinTags.value.toString())
const maxInputValue = ref(localMaxTags.value < 0 ? INFINITY_DISPLAY : localMaxTags.value.toString())

watch(appliedMin, (val) => {
  localMinTags.value = val
  minInputValue.value = val.toString()
  nextTick(syncSliderHandles)
})

watch(appliedMax, (val) => {
  localMaxTags.value = val
  maxInputValue.value = val < 0 ? INFINITY_DISPLAY : val.toString()
  nextTick(syncSliderHandles)
})

watch(localMinTags, (val) => {
  minInputValue.value = val.toString()
})

watch(localMaxTags, (val) => {
  maxInputValue.value = val < 0 ? INFINITY_DISPLAY : val.toString()
})

const tagSliderRef = ref<HTMLElement | null>(null)
const sliderInstance = ref<noUiSlider.API | null>(null)
let sliderSyncing = false
let tagRangeDebounceTimer: number | null = null

function initTagSlider() {
  if (!tagSliderRef.value || sliderInstance.value) return
  sliderInstance.value = noUiSlider.create(tagSliderRef.value, {
    start: [
      Math.min(localMinTags.value, SLIDER_MAX_VISUAL),
      localMaxTags.value < 0 || localMaxTags.value > SLIDER_MAX_VISUAL ? SLIDER_MAX_VISUAL : localMaxTags.value
    ],
    connect: true,
    step: 1,
    range: { min: 0, max: SLIDER_MAX_VISUAL }
  })

  sliderInstance.value.on('update', (values: Array<string | number>, handle: number) => {
    if (sliderSyncing) return
    const current = values[handle]
    const parsed = Math.round(parseFloat((current ?? 0).toString()))
    if (Number.isNaN(parsed)) return
    if (handle === 0) {
      localMinTags.value = parsed
    } else {
      if (parsed < SLIDER_MAX_VISUAL) {
        localMaxTags.value = parsed
      } else {
        const currentVal = parseInt(maxInputValue.value, 10)
        if (!Number.isNaN(currentVal) && currentVal > SLIDER_MAX_VISUAL) {
          localMaxTags.value = currentVal
        } else {
          localMaxTags.value = -1
        }
      }
    }
  })

  sliderInstance.value.on('change', () => {
    emitCurrentRangeDebounced()
  })

  syncSliderHandles()
}

function syncSliderHandles() {
  if (!sliderInstance.value) return
  sliderSyncing = true
  sliderInstance.value.set([
    Math.min(localMinTags.value, SLIDER_MAX_VISUAL),
    localMaxTags.value < 0 || localMaxTags.value > SLIDER_MAX_VISUAL ? SLIDER_MAX_VISUAL : localMaxTags.value
  ])
  requestAnimationFrame(() => {
    sliderSyncing = false
  })
}

function normalizeMaxInput(raw: string) {
  const trimmed = raw.trim()
  if (!trimmed || trimmed === INFINITY_DISPLAY || trimmed.toLowerCase() === 'inf') {
    return { value: -1, display: INFINITY_DISPLAY }
  }
  const parsed = parseInt(trimmed, 10)
  if (Number.isNaN(parsed) || parsed < 0) {
    return { value: -1, display: INFINITY_DISPLAY }
  }
  return { value: parsed, display: parsed.toString() }
}

function emitCurrentRange() {
  const nextMin = localMinTags.value > 0 ? localMinTags.value : null
  const currentMin = normalizedMinPayload.value
  const nextMax = localMaxTags.value >= 0 ? localMaxTags.value : null
  const currentMax = normalizedMaxPayload.value
  if (nextMin === currentMin && nextMax === currentMax) return
  emit('updateTagRange', nextMin, nextMax)
}

function emitCurrentRangeDebounced() {
  if (tagRangeDebounceTimer !== null) {
    window.clearTimeout(tagRangeDebounceTimer)
  }
  tagRangeDebounceTimer = window.setTimeout(() => {
    emitCurrentRange()
    tagRangeDebounceTimer = null
  }, 300)
}

function handleMinInputChange() {
  let parsed = parseInt(minInputValue.value, 10)
  if (Number.isNaN(parsed) || parsed < 0) parsed = 0
  localMinTags.value = parsed
  minInputValue.value = parsed.toString()
  emitCurrentRange()
  syncSliderHandles()
}

function handleMaxInputChange() {
  const normalized = normalizeMaxInput(maxInputValue.value)
  localMaxTags.value = normalized.value
  maxInputValue.value = normalized.display
  emitCurrentRange()
  syncSliderHandles()
}

const tempTagInputRef = ref<InstanceType<typeof TagInput> | null>(null)
const localTempTags = ref<string[]>([...(props.tempTags || [])])

watch(
  () => props.tempTags,
  (tags) => {
    localTempTags.value = [...(tags || [])]
  },
  { immediate: true }
)

watch(localTempTags, (tags) => {
  emit('updateTempTags', [...tags])
}, { deep: true })

function handleTempInputUpdate(value: string) {
  emit('tempInputUpdate', value)
}

const isDragging = ref(false)
const hasMoved = ref(false)
const dragStartY = ref(0)
const dragStartTop = ref(0)
const miniStripTop = ref(DEFAULT_MINI_TOP)
const miniStripRef = ref<HTMLElement | null>(null)
const dragHandleRef = ref<HTMLElement | null>(null)

function handlePointerDown(e: PointerEvent) {
  const handle = (e.target as HTMLElement).closest('[data-drag-handle]') as HTMLElement | null
  if (!handle) return
  isDragging.value = true
  hasMoved.value = false
  dragStartY.value = e.clientY
  dragStartTop.value = miniStripTop.value
  dragHandleRef.value = handle
  handle.setPointerCapture(e.pointerId)
  e.preventDefault()
}

function handlePointerMove(e: PointerEvent) {
  if (!isDragging.value) return
  const deltaY = e.clientY - dragStartY.value
  if (!hasMoved.value && Math.abs(deltaY) <= DRAG_THRESHOLD) return
  if (!hasMoved.value) {
    hasMoved.value = true
  }
  let newTop = dragStartTop.value + deltaY
  const minTop = 80
  const stripHeight = miniStripRef.value?.offsetHeight ?? 200
  const maxTop = window.innerHeight - stripHeight - 16
  newTop = Math.max(minTop, Math.min(maxTop, newTop))
  miniStripTop.value = newTop
}

function handlePointerUp(e: PointerEvent) {
  if (!isDragging.value) return
  isDragging.value = false
  if (hasMoved.value) {
    globalStore.setFabMiniPosition(Math.round(miniStripTop.value))
  } else {
    toggleCollapse()
  }
  hasMoved.value = false
  if (dragHandleRef.value) {
    dragHandleRef.value.releasePointerCapture(e.pointerId)
  }
  dragHandleRef.value = null
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  // 记下"刚刚展开"的时刻，供 HQ 按钮防穿透使用（见 shouldIgnoreGhostClick）
  if (!isCollapsed.value) {
    lastExpandAt = Date.now()
  }
}

/**
 * 展开动画后，同一次触摸的"尾随点击"会穿透到刚渲染出来的 #fab-hq 上。
 *
 * 【成因】#fab-expand-btn 的展开动作由 pointerup 触发（拖拽逻辑里
 * preventDefault 掉了原生 click）。pointerup 时 #fab-container 立刻从
 * hidden 变可见，#fab-hq 恰好落在手指原本的位置；浏览器随后补发的那次
 * click 就落到了 HQ 上，顺带触发 handleToggleHQ -> searchImages 重新搜索。
 *
 * 【修法】不改拖拽逻辑，只在这里按"距上次展开的时间"做一层拦截：
 * 展开后极短窗口内的 HQ 点击一律视为穿透，直接丢弃。
 */
const GHOST_CLICK_WINDOW_MS = 350
let lastExpandAt = 0

function shouldIgnoreGhostClick(): boolean {
  // 仅在"已展开"状态下拦截；收起时的正常点击不受影响
  if (isCollapsed.value) return false
  if (lastExpandAt === 0) return false
  return Date.now() - lastExpandAt < GHOST_CLICK_WINDOW_MS
}

function toggleTrashMode() {
  emit('toggleTrash', !props.isTrashMode)
}

function toggleExpansion() {
  emit('toggleExpansion', !props.isExpansionEnabled)
}

function toggleHQMode() {
  // 丢弃"展开后尾随点击"造成的误触（详见 shouldIgnoreGhostClick 注释）
  if (shouldIgnoreGhostClick()) return
  emit('toggleHQ', !props.isHQMode)
}

function toggleTempMode() {
  emit('toggleTempMode', !props.isTempTagMode)
}

function toggleSortPanel() {
  const next = !showSortMenu.value
  closeAllPanels()
  showSortMenu.value = next
}

function toggleTagCountPanel() {
  const next = !showTagCountPanel.value
  closeAllPanels()
  showTagCountPanel.value = next
  if (next) {
    nextTick(() => {
      initTagSlider()
      syncSliderHandles()
    })
  }
}

function toggleTempPanel() {
  const next = !showTempTagsPanel.value
  closeAllPanels()
  showTempTagsPanel.value = next
  if (next) {
    nextTick(() => tempTagInputRef.value?.focus())
  }
}

function selectSort(value: string) {
  emit('updateSort', value)
  showSortMenu.value = false
}

function clearTempTags() {
  localTempTags.value = []
}

function closeAllPanels() {
  showSortMenu.value = false
  showTagCountPanel.value = false
  showTempTagsPanel.value = false
}

function handleSortOutsideClick(e: MouseEvent) {
  const target = e.target as Node
  if (sortMenuRef.value?.contains(target)) return
  if (sortButtonRef.value?.contains(target)) return
  showSortMenu.value = false
}

onMounted(() => {
  initTagSlider()
  const saved = globalStore.fabMiniPosition
  if (typeof saved === 'number' && !Number.isNaN(saved)) {
    miniStripTop.value = saved
  } else {
    miniStripTop.value = DEFAULT_MINI_TOP
  }
})

watch(tagSliderRef, () => initTagSlider())

watch(showSortMenu, (val) => {
  if (val) {
    document.addEventListener('click', handleSortOutsideClick)
  } else {
    document.removeEventListener('click', handleSortOutsideClick)
  }
})

onBeforeUnmount(() => {
  if (sliderInstance.value) {
    sliderInstance.value.destroy()
    sliderInstance.value = null
  }
  if (tagRangeDebounceTimer !== null) {
    window.clearTimeout(tagRangeDebounceTimer)
    tagRangeDebounceTimer = null
  }
  document.removeEventListener('click', handleSortOutsideClick)
})
</script>

<template>
  <div>
    <div
      id="tag-count-panel"
      :class="[
        'fixed top-24 right-44 bg-white rounded-xl shadow-2xl border border-slate-200 p-3 z-40 w-52 origin-top-right flex-col',
        showTagCountPanel ? 'flex' : 'hidden'
      ]"
      title="按标签数量筛选图片"
      @click.stop
    >
      <div id="tag-count-header" class="flex items-center justify-between gap-1 mb-2">
        <input
          v-model="minInputValue"
          type="number"
          min="0"
          id="input-min-tags"
          class="w-12 px-1 py-0.5 text-xs border border-slate-200 rounded text-center focus:ring-1 focus:ring-cyan-300 focus:border-cyan-400 outline-none text-slate-600"
          title="最少标签数"
          @change="handleMinInputChange"
        />
        <span
          id="tag-count-title"
          class="text-xs font-bold text-slate-600 flex-1 text-center"
          title="筛选指定标签数量范围的图片"
        >标签数</span>
        <input
          v-model="maxInputValue"
          type="text"
          id="input-max-tags"
          class="w-12 px-1 py-0.5 text-xs border border-slate-200 rounded text-center focus:ring-1 focus:ring-cyan-300 focus:border-cyan-400 outline-none text-slate-600"
          title="最多标签数 (∞ 表示无限制)"
          @change="handleMaxInputChange"
        />
        <span
          id="close-tag-count-panel"
          class="cursor-pointer text-slate-400 hover:text-red-500 text-base ml-1"
          title="关闭标签数量筛选面板"
          @click="showTagCountPanel = false"
        >&times;</span>
      </div>
      <div
        ref="tagSliderRef"
        id="tag-slider"
        class="mx-1"
        title="拖动滑块调整标签数量范围"
      />
      <span id="tag-count-display" class="hidden">
        {{ localMinTags }} - {{ localMaxTags }}
      </span>
    </div>

    <div
      id="temp-tag-panel"
      :class="[
        'fixed top-24 right-44 bg-white rounded-xl shadow-2xl border border-slate-200 p-3 z-40 w-64 origin-top-right flex-col gap-2 transform transition-all duration-200',
        showTempTagsPanel ? 'flex' : 'hidden'
      ]"
      @click.stop
    >
      <div class="text-xs font-bold text-slate-500 mb-1 flex items-center gap-2">
        <span id="temp-panel-title" title="在此输入标签，然后点击图片快速粘贴">临时标签 (点击粘贴到图片)</span>
        <button
          id="clear-temp-tags"
          class="text-xs text-blue-600 hover:underline"
          title="清空所有临时标签"
          @click="clearTempTags"
        >
          清空
        </button>
        <span
          id="close-temp-panel"
          class="cursor-pointer hover:text-red-500 ml-auto text-base leading-none"
          title="隐藏临时标签面板"
          @click="showTempTagsPanel = false"
        >&minus;</span>
      </div>
      <TagInput
        ref="tempTagInputRef"
        id="temp-tag-input-container"
        v-model="localTempTags"
        suggestions-id="tag-suggestions"
        placeholder="输入临时标签..."
        title="输入要批量粘贴的标签"
        theme="purple"
        :enable-excludes="false"
        container-class="flex flex-wrap gap-1 bg-slate-50 p-2 rounded border border-slate-200 min-h-[40px] cursor-text"
        @input-update="handleTempInputUpdate"
      />
    </div>

    <div
      id="sort-menu"
      :class="[
        'fixed top-24 right-44 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-40 w-40 origin-top-right flex-col',
        showSortMenu ? 'flex' : 'hidden'
      ]"
      ref="sortMenuRef"
      @click.stop
    >
      <button
        id="sort-date-desc"
        data-sort="date_desc"
        class="sort-option px-4 py-2 text-sm text-left hover:bg-slate-50 transition-colors"
        :class="sortBy === 'date_desc' ? 'bg-slate-50 text-blue-600 font-bold' : 'text-slate-600'"
        title="按添加时间降序排列"
        @click="selectSort('date_desc')"
      >📅 最新添加</button>
      <button
        id="sort-date-asc"
        data-sort="date_asc"
        class="sort-option px-4 py-2 text-sm text-left hover:bg-slate-50 transition-colors"
        :class="sortBy === 'date_asc' ? 'bg-slate-50 text-blue-600 font-bold' : 'text-slate-600'"
        title="按添加时间升序排列"
        @click="selectSort('date_asc')"
      >📅 最早添加</button>
      <button
        id="sort-size-desc"
        data-sort="size_desc"
        class="sort-option px-4 py-2 text-sm text-left hover:bg-slate-50 transition-colors"
        :class="sortBy === 'size_desc' ? 'bg-slate-50 text-blue-600 font-bold' : 'text-slate-600'"
        title="按文件大小降序排列"
        @click="selectSort('size_desc')"
      >💾 文件很大</button>
      <button
        id="sort-size-asc"
        data-sort="size_asc"
        class="sort-option px-4 py-2 text-sm text-left hover:bg-slate-50 transition-colors"
        :class="sortBy === 'size_asc' ? 'bg-slate-50 text-blue-600 font-bold' : 'text-slate-600'"
        title="按文件大小升序排列"
        @click="selectSort('size_asc')"
      >💾 文件很小</button>
      <button
        id="sort-resolution-desc"
        data-sort="resolution_desc"
        class="sort-option px-4 py-2 text-sm text-left hover:bg-slate-50 transition-colors"
        :class="sortBy === 'resolution_desc' ? 'bg-slate-50 text-blue-600 font-bold' : 'text-slate-600'"
        title="按分辨率(像素数)降序排列"
        @click="selectSort('resolution_desc')"
      >📐 高分辨率</button>
      <button
        id="sort-resolution-asc"
        data-sort="resolution_asc"
        class="sort-option px-4 py-2 text-sm text-left hover:bg-slate-50 transition-colors"
        :class="sortBy === 'resolution_asc' ? 'bg-slate-50 text-blue-600 font-bold' : 'text-slate-600'"
        title="按分辨率(像素数)升序排列"
        @click="selectSort('resolution_asc')"
      >📐 低分辨率</button>
    </div>

    <!-- FAB 展开状态：2×5 网格布局（旧项目） -->
    <div
      id="fab-container"
      :class="[
        'fixed right-4 grid grid-cols-2 gap-3 z-50 top-[7rem] transition-all duration-300',
        isCollapsed ? 'hidden' : ''
      ]"
    >
        <!-- Export JSON -->
        <button
          id="fab-export"
          class="w-14 h-14 bg-white hover:bg-amber-50 text-amber-600 border border-amber-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative group"
          title="导出数据"
          @click="emit('export')"
        >
          <Download class="w-6 h-6" />
          <span class="absolute right-full mr-3 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap pointer-events-none">导出JSON</span>
        </button>

        <!-- Import JSON -->
        <button
          id="fab-import"
          class="w-14 h-14 bg-white hover:bg-indigo-50 text-indigo-600 border border-indigo-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative group"
          title="导入数据"
          @click="emit('import')"
        >
          <Upload class="w-6 h-6" />
          <span class="absolute right-full mr-3 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap pointer-events-none">导入JSON</span>
        </button>

        <!-- Tag Count Filter -->
        <button
          id="fab-tag-count"
          :class="[
            'w-14 h-14 bg-white hover:bg-cyan-50 text-cyan-600 border border-cyan-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center flex-col relative group',
            isTagRangeApplied ? 'bg-cyan-100 border-cyan-300' : ''
          ]"
          title="标签数量筛选"
          @click.stop="toggleTagCountPanel"
        >
          <Hash class="w-5 h-5" />
          <span
            id="tag-count-badge"
            :class="[
              'absolute -top-1 -right-1 bg-cyan-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full',
              isTagRangeApplied ? '' : 'hidden'
            ]"
          >
            {{ appliedRangeText }}
          </span>
        </button>

        <!-- Temp Tags Trigger + Satellite -->
        <div id="temp-tags-btn-group" class="relative group">
          <button
            id="fab-temp-tags"
            :class="[
              'w-14 h-14 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative z-20 border',
              props.isTempTagMode
                ? 'bg-purple-100 border-purple-400 text-purple-700'
                : 'bg-white border-purple-100 text-purple-600 hover:bg-purple-50'
            ]"
            :title="props.isTempTagMode ? '批量打标粘贴模式：已开启（点击关闭）' : '批量打标粘贴模式：已关闭（点击开启）'"
            @click="toggleTempMode"
          >
            <Stamp class="w-6 h-6" />
            <div
              id="fab-temp-tags-slash"
              :class="[
                'absolute inset-0 items-center justify-center pointer-events-none',
                props.isTempTagMode ? 'hidden' : 'flex'
              ]"
            >
              <div class="w-10 h-0.5 bg-red-500 rotate-45 rounded-full shadow-sm"></div>
            </div>
            <span class="absolute right-full mr-3 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap pointer-events-none">批量打标</span>
          </button>
          <button
            id="toggle-temp-panel-btn"
            class="absolute -top-2 -right-2 w-8 h-8 bg-white text-slate-600 border border-slate-200 rounded-full shadow-md flex items-center justify-center hover:bg-purple-50 hover:text-purple-600 transition-all z-30"
            title="显示/隐藏临时标签面板"
            @click.stop="toggleTempPanel"
          >
            <FileText class="w-4 h-4" />
          </button>
        </div>

        <!-- Sort Trigger -->
        <button
          ref="sortButtonRef"
          id="fab-sort"
          class="w-14 h-14 bg-white hover:bg-slate-50 text-slate-600 border border-slate-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative group"
          title="排序"
          @click.stop="toggleSortPanel"
        >
          <ArrowUpDown class="w-6 h-6" />
        </button>

        <!-- HQ Toggle -->
        <button
          id="fab-hq"
          :class="[
            'w-14 h-14 bg-white hover:bg-slate-50 border border-slate-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center flex-col relative group',
            isHQMode ? 'text-blue-600 border-blue-200' : 'text-slate-400'
          ]"
          title="HQ 原图模式"
          @click="toggleHQMode"
        >
          <span class="text-[10px] font-black leading-none mb-0.5">HQ</span>
          <div id="hq-status-dot" :class="['w-2 h-2 rounded-full transition-colors', isHQMode ? 'bg-blue-600' : 'bg-slate-300']"></div>
        </button>

        <!-- Trash Bin Toggle -->
        <button
          id="fab-trash"
          :class="[
            'w-14 h-14 bg-white hover:bg-red-50 border border-slate-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative group',
            isTrashMode ? 'text-red-500 bg-red-50 border-red-200' : 'text-slate-400'
          ]"
          title="显示回收站内容"
          @click="toggleTrashMode"
        >
          <Trash2 class="w-6 h-6" />
          <div
            id="trash-active-dot"
            :class="[
              'absolute top-3 right-3 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white',
              isTrashMode ? '' : 'hidden'
            ]"
          ></div>
        </button>

        <!-- Upload -->
        <button
          id="fab-upload"
          class="w-14 h-14 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center group relative"
          title="上传新图片"
          @click="emit('upload')"
        >
          <Loader2 v-if="props.isUploading" class="w-7 h-7 animate-spin" />
          <ImagePlus v-else class="w-7 h-7" />
        </button>

        <!-- Main Search + Satellites -->
        <div id="search-btn-group" class="relative group">
          <button
            id="fab-search"
            class="w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl shadow-xl hover:shadow-2xl hover:scale-105 transition-all flex items-center justify-center z-20 relative"
            title="执行搜索"
            @click="emit('focusSearch')"
          >
            <Search class="w-7 h-7" />
          </button>

          <button
            id="fab-toggle-btn"
            class="absolute -top-2 -left-2 w-8 h-8 bg-white text-slate-600 border border-slate-200 rounded-full shadow-md flex items-center justify-center hover:bg-slate-100 hover:text-blue-600 transition-all z-30"
            title="折叠悬浮按钮组"
            @click="toggleCollapse"
          >
            <ChevronsRight class="w-4 h-4" />
          </button>

          <button
            id="clear-search-btn"
            class="absolute -top-2 -right-2 w-8 h-8 bg-white text-slate-600 border border-slate-200 rounded-full shadow-md flex items-center justify-center hover:bg-red-50 hover:text-red-500 transition-all z-30 group-hover:opacity-100"
            title="清空标签"
            @click="emit('clear')"
          >
            <X class="w-4 h-4" />
          </button>

          <button
            id="reload-search-btn"
            class="absolute -bottom-2 -right-2 w-8 h-8 bg-white text-slate-600 border border-slate-200 rounded-full shadow-md flex items-center justify-center hover:bg-slate-100 hover:text-blue-600 transition-all z-30"
            title="刷新"
            @click="emit('refresh')"
          >
            <RefreshCw class="w-4 h-4" />
          </button>
        </div>

        <!-- Expansion / Rules -->
        <button
          id="fab-tree"
          :class="[
            'w-14 h-14 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative group border',
            isExpansionEnabled
              ? 'bg-green-100 hover:bg-green-50 text-green-700 border-green-400'
              : 'bg-white hover:bg-green-50 text-yellow-600 border-yellow-300'
          ]"
          :title="isExpansionEnabled ? '同义词膨胀：已开启（点击关闭）' : '同义词膨胀：已关闭（点击开启）'"
          @click="toggleExpansion"
        >
          <TreePine class="w-6 h-6" />
          <div
            id="fab-tree-slash"
            :class="[
              'absolute inset-0 items-center justify-center pointer-events-none',
              isExpansionEnabled ? 'hidden' : 'flex'
            ]"
          >
            <div class="w-10 h-0.5 bg-red-500 rotate-45 rounded-full shadow-sm"></div>
          </div>
          <span
            id="expansion-badge"
            :class="[
              'absolute -top-1 -right-1 bg-purple-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full whitespace-nowrap',
              showExpansionBadge ? '' : 'hidden'
            ]"
            :title="`原始 ${expandedOriginal} 个标签已膨胀为 ${expandedTotal} 个关键词`"
          >
            {{ expansionBadgeText }}
          </span>
        </button>
    </div>

    <!-- Collapsed FAB Mini Strip -->
    <div
      id="fab-mini-strip"
      :class="['fixed z-50', isCollapsed ? '' : 'hidden']"
      :style="{ top: miniStripTop + 'px', right: '0px' }"
      ref="miniStripRef"
      @pointerdown="handlePointerDown"
      @pointermove="handlePointerMove"
      @pointerup="handlePointerUp"
      @pointercancel="handlePointerUp"
    >
        <div class="bg-white/80 backdrop-blur-sm border-l border-y border-slate-200 rounded-l-lg shadow-lg py-2 pl-1" style="width: 24px;">
          <div class="flex flex-col gap-1.5" style="margin-left: -16px;">
            <button
              id="fab-expand-btn"
              class="w-8 h-8 bg-white hover:bg-blue-50 text-slate-500 hover:text-blue-600 border border-slate-200 rounded-full shadow-md flex items-center justify-center cursor-grab active:cursor-grabbing touch-none"
              title="拖拽调整位置 / 点击展开"
              data-drag-handle
            >
              <ChevronsLeft class="w-4 h-4" />
            </button>

            <button
              id="fab-mini-clear"
              class="w-8 h-8 bg-white hover:bg-red-50 text-slate-500 hover:text-red-500 border border-slate-200 rounded-full shadow-md flex items-center justify-center"
              title="清空标签"
              @click="emit('clear')"
            >
              <X class="w-4 h-4" />
            </button>

            <button
              id="fab-mini-reload"
              class="w-8 h-8 bg-white hover:bg-slate-100 text-slate-500 hover:text-blue-600 border border-slate-200 rounded-full shadow-md flex items-center justify-center"
              title="刷新"
              @click="emit('refresh')"
            >
              <RefreshCw class="w-4 h-4" />
            </button>

            <button
              id="fab-mini-search"
              class="w-8 h-8 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-md flex items-center justify-center"
              title="搜索"
              @click="emit('focusSearch')"
            >
              <Search class="w-4 h-4" />
            </button>
          </div>
        </div>
    </div>
  </div>
</template>
