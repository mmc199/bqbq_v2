<script setup lang="ts">
/**
 * FloatingButtons 组件 - FAB 悬浮按钮组 
 * 完全复刻旧项目的顺序和样式，包含 FAB 按钮排列、面板控制、规则样式
 */
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Search, RefreshCw, X, Download, Upload, Trash2,
  TreeDeciduous, TreePine, ImagePlus, ChevronsRight, ChevronsLeft,
  ArrowUpDown, Zap, Plus, Check, CheckSquare,
  FileType, Hash, Stamp, FileText
} from 'lucide-vue-next'
import * as noUiSlider from 'nouislider'
import 'nouislider/dist/nouislider.css'
import { useGlobalStore } from '@/stores/useGlobalStore'

const SLIDER_MAX_VISUAL = 6
const INFINITY_DISPLAY = '∞'
const STORAGE_KEY = 'bqbq_fab_mini_position'
const AVAILABLE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']

const props = defineProps<{
  isTrashMode?: boolean
  isExpansionEnabled?: boolean
  isHQMode?: boolean
  isBatchMode?: boolean
  isTempTagMode?: boolean
  sortBy?: string
  minTags?: number | null
  maxTags?: number | null
  tempTags?: string[]
  extensions?: string[]
  excludeExtensions?: string[]
}>()

const emit = defineEmits<{
  upload: []
  openRules: []
  export: []
  import: []
  toggleTrash: [isTrash: boolean]
  toggleExpansion: [enabled: boolean]
  toggleHQ: [enabled: boolean]
  toggleBatch: []
  toggleTempMode: [enabled: boolean]
  search: []
  refresh: []
  clear: []
  updateSort: [sortBy: string]
  updateTagRange: [min: number | null, max: number | null]
  updateTempTags: [tags: string[]]
  applyTempTags: []
  updateExtensions: [extensions: string[], excludeExtensions: string[]]
}>()

const globalStore = useGlobalStore()
const isTrashMode = computed(() => !!props.isTrashMode)
const isExpansionEnabled = computed(() => !!props.isExpansionEnabled)
const isHQMode = computed(() => !!props.isHQMode)
const isBatchMode = computed(() => !!props.isBatchMode)

const isCollapsed = computed({
  get: () => globalStore.preferences.fabCollapsed,
  set: (val) => globalStore.updatePreference('fabCollapsed', val)
})

const showSortMenu = ref(false)
const showTagCountPanel = ref(false)
const showTempTagsPanel = ref(false)
const showExtensionPanel = ref(false)
const isAnyPanelOpen = computed(() =>
  showSortMenu.value || showTagCountPanel.value || showTempTagsPanel.value || showExtensionPanel.value
)

const sortBy = computed(() => props.sortBy ?? 'time_desc')

const sortOptions = [
  { value: 'time_desc', label: '最新添加', hint: '按添加时间降序' },
  { value: 'time_asc', label: '最早添加', hint: '按添加时间升序' },
  { value: 'tags_desc', label: '标签数量多', hint: '按标签数量降序' },
  { value: 'tags_asc', label: '标签数量少', hint: '按标签数量升序' },
  { value: 'size_desc', label: '文件体积大', hint: '按文件大小降序' },
  { value: 'size_asc', label: '文件体积小', hint: '按文件大小升序' },
  { value: 'resolution_desc', label: '分辨率高', hint: '按分辨率降序' },
  { value: 'resolution_asc', label: '分辨率低', hint: '按分辨率升序' }
]

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
      localMaxTags.value = parsed >= SLIDER_MAX_VISUAL ? SLIDER_MAX_VISUAL : parsed
      if (parsed >= SLIDER_MAX_VISUAL && maxInputValue.value === INFINITY_DISPLAY) {
        localMaxTags.value = -1
      }
    }
  })

  sliderInstance.value.on('change', () => {
    emitCurrentRange()
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

const tempTagInput = ref('')
const tempTagInputEl = ref<HTMLInputElement | null>(null)
const localTempTags = ref<string[]>([...(props.tempTags || [])])

watch(
  () => props.tempTags,
  (tags) => {
    localTempTags.value = [...(tags || [])]
  },
  { immediate: true }
)

const localExtensions = ref<string[]>([...(props.extensions || [])])
const localExcludeExtensions = ref<string[]>([...(props.excludeExtensions || [])])

watch(
  () => props.extensions,
  (exts) => {
    localExtensions.value = [...(exts || [])]
  },
  { immediate: true }
)

watch(
  () => props.excludeExtensions,
  (exts) => {
    localExcludeExtensions.value = [...(exts || [])]
  },
  { immediate: true }
)

const isExtensionFilterActive = computed(
  () => localExtensions.value.length > 0 || localExcludeExtensions.value.length > 0
)

const isDragging = ref(false)
const dragStartY = ref(0)
const dragStartTop = ref(0)
const miniStripTop = ref(112)

function handlePointerDown(e: PointerEvent) {
  if ((e.target as HTMLElement).closest('button')) return
  isDragging.value = true
  dragStartY.value = e.clientY
  dragStartTop.value = miniStripTop.value
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  e.preventDefault()
}

function handlePointerMove(e: PointerEvent) {
  if (!isDragging.value) return
  const deltaY = e.clientY - dragStartY.value
  let newTop = dragStartTop.value + deltaY
  const minTop = 64
  const maxTop = window.innerHeight - 250
  newTop = Math.max(minTop, Math.min(maxTop, newTop))
  miniStripTop.value = newTop
}

function handlePointerUp(e: PointerEvent) {
  if (!isDragging.value) return
  isDragging.value = false
  localStorage.setItem(STORAGE_KEY, miniStripTop.value.toString())
  ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function toggleTrashMode() {
  emit('toggleTrash', !props.isTrashMode)
}

function toggleExpansion() {
  emit('toggleExpansion', !props.isExpansionEnabled)
}

function toggleHQMode() {
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
    nextTick(() => tempTagInputEl.value?.focus())
  }
}

function toggleExtensionPanel() {
  const next = !showExtensionPanel.value
  closeAllPanels()
  showExtensionPanel.value = next
}

function selectSort(value: string) {
  emit('updateSort', value)
  showSortMenu.value = false
}

function addTempTag() {
  const tag = tempTagInput.value.trim()
  if (tag && !localTempTags.value.includes(tag)) {
    localTempTags.value.push(tag)
    emit('updateTempTags', [...localTempTags.value])
  }
  tempTagInput.value = ''
}

function removeTempTag(index: number) {
  localTempTags.value.splice(index, 1)
  emit('updateTempTags', [...localTempTags.value])
}

function applyTempTags() {
  if (localTempTags.value.length === 0) return
  emit('applyTempTags')
}

function clearTempTags() {
  localTempTags.value = []
  emit('updateTempTags', [])
}

function toggleExtension(ext: string) {
  const idx = localExtensions.value.indexOf(ext)
  if (idx >= 0) {
    localExtensions.value.splice(idx, 1)
  } else {
    const exIdx = localExcludeExtensions.value.indexOf(ext)
    if (exIdx >= 0) {
      localExcludeExtensions.value.splice(exIdx, 1)
    }
    localExtensions.value.push(ext)
  }
}

function toggleExcludeExtension(ext: string) {
  const idx = localExcludeExtensions.value.indexOf(ext)
  if (idx >= 0) {
    localExcludeExtensions.value.splice(idx, 1)
  } else {
    const incIdx = localExtensions.value.indexOf(ext)
    if (incIdx >= 0) {
      localExtensions.value.splice(incIdx, 1)
    }
    localExcludeExtensions.value.push(ext)
  }
}

function applyExtensionFilter() {
  emit('updateExtensions', [...localExtensions.value], [...localExcludeExtensions.value])
  showExtensionPanel.value = false
}

function clearExtensionFilter() {
  localExtensions.value = []
  localExcludeExtensions.value = []
  emit('updateExtensions', [], [])
  showExtensionPanel.value = false
}

function getExtensionState(ext: string): 'include' | 'exclude' | 'none' {
  if (localExtensions.value.includes(ext)) return 'include'
  if (localExcludeExtensions.value.includes(ext)) return 'exclude'
  return 'none'
}

function closeAllPanels() {
  showSortMenu.value = false
  showTagCountPanel.value = false
  showTempTagsPanel.value = false
  showExtensionPanel.value = false
}

onMounted(() => {
  initTagSlider()
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    const pos = parseInt(saved, 10)
    if (!Number.isNaN(pos) && pos >= 64 && pos <= window.innerHeight - 200) {
      miniStripTop.value = pos
    }
  }
})

watch(tagSliderRef, () => initTagSlider())

onBeforeUnmount(() => {
  if (sliderInstance.value) {
    sliderInstance.value.destroy()
    sliderInstance.value = null
  }
})
</script>

<template>
  <div>
    <div
      v-if="isAnyPanelOpen"
      class="fixed inset-0 z-40"
      @click="closeAllPanels"
    />

    <div
      v-show="showTagCountPanel"
      class="fixed top-24 right-44 bg-white rounded-xl shadow-2xl border border-slate-200 p-3 z-50 w-52 origin-top-right flex flex-col gap-3"
      @click.stop
    >
      <div class="flex items-center justify-between gap-1">
        <input
          v-model="minInputValue"
          type="number"
          min="0"
          class="w-12 px-1 py-0.5 text-xs border border-slate-200 rounded text-center focus:ring-1 focus:ring-cyan-300 focus:border-cyan-400 outline-none text-slate-600"
          title="最少标签数"
          @change="handleMinInputChange"
        />
        <span class="text-xs font-bold text-slate-600 flex-1 text-center">标签数</span>
        <input
          v-model="maxInputValue"
          type="text"
          class="w-12 px-1 py-0.5 text-xs border border-slate-200 rounded text-center focus:ring-1 focus:ring-cyan-300 focus:border-cyan-400 outline-none text-slate-600"
          title="最多标签数 (∞ 表示无限制)"
          @change="handleMaxInputChange"
        />
        <button
          class="text-slate-400 hover:text-red-500 text-base leading-none"
          title="关闭"
          @click="showTagCountPanel = false"
        >
          &times;
        </button>
      </div>
      <div
        ref="tagSliderRef"
        id="tag-slider"
        title="拖动滑块调整标签数量范围"
      />
      <div class="text-xs text-slate-500 text-center">
        {{ localMinTags }} - {{ localMaxTags < 0 ? '∞' : localMaxTags }}
      </div>
    </div>

    <div
      v-show="showTempTagsPanel"
      class="fixed top-24 right-44 bg-white rounded-xl shadow-2xl border border-slate-200 p-6 z-50 w-64 origin-top-right flex flex-col gap-4"
      @click.stop
    >
      <div class="flex items-center justify-between">
        <div class="text-base font-semibold text-slate-800">临时标签</div>
        <button
          class="w-7 h-7 text-slate-400 hover:text-red-500 rounded-full hover:bg-red-50 transition"
          @click="showTempTagsPanel = false"
        >
          <X class="w-4 h-4 mx-auto" />
        </button>
      </div>
      <div class="flex gap-2">
        <input
          ref="tempTagInputEl"
          v-model="tempTagInput"
          placeholder="输入标签..."
          class="flex-1 px-4 py-2.5 text-sm border-2 border-slate-200 rounded-xl focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all"
          @keydown.enter.prevent="addTempTag"
        />
        <button
          class="px-4 py-2.5 bg-purple-500 text-white rounded-xl hover:bg-purple-600 transition"
          @click="addTempTag"
        >
          <Plus class="w-5 h-5" />
        </button>
      </div>
      <div class="flex flex-wrap gap-2 p-3 bg-slate-50 border-2 border-slate-200 rounded-xl min-h-[48px] max-h-[120px] overflow-y-auto">
        <span
          v-for="(tag, index) in localTempTags"
          :key="`temp-${tag}-${index}`"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 text-purple-700 text-sm font-medium rounded-full border border-purple-200"
        >
          {{ tag }}
          <button class="hover:text-purple-900 transition-colors" @click="removeTempTag(index)">
            <X class="w-3.5 h-3.5" />
          </button>
        </span>
        <span v-if="localTempTags.length === 0" class="text-sm text-slate-400 italic">暂无临时标签</span>
      </div>
      <div class="flex gap-3">
        <button
          class="flex-1 px-4 py-2.5 text-sm bg-slate-100 text-slate-600 rounded-[10px] hover:bg-slate-200 font-medium transition"
          @click="clearTempTags"
        >
          清空
        </button>
        <button
          class="flex-1 px-4 py-2.5 text-sm bg-purple-500 text-white rounded-[10px] hover:bg-purple-600 font-medium transition flex items-center justify-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="localTempTags.length === 0"
          @click="applyTempTags"
        >
          <Check class="w-4 h-4" />
          应用
        </button>
      </div>
    </div>

    <div
      v-show="showSortMenu"
      class="fixed top-24 right-44 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50 w-40 origin-top-right flex flex-col"
      @click.stop
    >
      <button
        v-for="opt in sortOptions"
        :key="opt.value"
        class="sort-option px-4 py-2 text-sm text-left transition-colors"
        :class="sortBy === opt.value ? 'bg-blue-50 text-blue-600 font-bold' : 'text-slate-700 hover:bg-slate-50'"
        @click="selectSort(opt.value)"
      >
        <div class="font-medium">{{ opt.label }}</div>
        <div class="text-xs text-slate-400">{{ opt.hint }}</div>
      </button>
    </div>

    <Transition name="fab-main">
      <div
        v-show="!isCollapsed"
        class="fixed right-4 grid grid-cols-2 gap-3 z-50 top-[7rem] transition-all duration-300"
      >
        <button
          class="fab-btn bg-white hover:bg-amber-50 text-amber-600 border border-amber-200"
          title="导出数据"
          @click="emit('export')"
        >
          <Download class="w-6 h-6" />
        </button>

        <button
          class="fab-btn bg-white hover:bg-indigo-50 text-indigo-600 border border-indigo-200"
          title="导入数据"
          @click="emit('import')"
        >
          <Upload class="w-6 h-6" />
        </button>

        <button
          :class="[
            'fab-btn border',
            isHQMode
              ? 'bg-cyan-100 text-cyan-700 border-cyan-300'
              : 'bg-white hover:bg-cyan-50 text-cyan-600 border-cyan-200'
          ]"
          title="HQ 高清模式（优先加载原图）"
          @click="toggleHQMode"
        >
          <Zap class="w-6 h-6" />
          <div
            v-if="isHQMode"
            class="absolute top-3 right-3 w-2 h-2 bg-cyan-500 rounded-full"
          />
        </button>

        <button
          class="fab-btn bg-white hover:bg-orange-50 text-orange-600 border border-orange-200"
          title="排序方式"
          @click.stop="toggleSortPanel"
        >
          <ArrowUpDown class="w-6 h-6" />
        </button>

        <button
          :class="[
            'fab-btn border',
            isTrashMode
              ? 'bg-red-50 text-red-600 border-red-300'
              : 'bg-white hover:bg-red-50 text-slate-400 border-slate-200'
          ]"
          title="显示回收站内容"
          @click="toggleTrashMode"
        >
          <Trash2 class="w-6 h-6" />
          <div
            v-if="isTrashMode"
            class="absolute top-3 right-3 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white"
          />
        </button>

        <button
          class="fab-btn bg-emerald-500 hover:bg-emerald-600 text-white"
          title="上传新图片"
          @click="emit('upload')"
        >
          <ImagePlus class="w-7 h-7" />
        </button>

        <div class="relative group">
          <button
            class="fab-btn bg-blue-600 hover:bg-blue-700 text-white z-20 relative"
            title="执行搜索"
            @click="emit('search')"
          >
            <Search class="w-7 h-7" />
          </button>

          <button
            class="fab-satellite -top-2 -left-2 bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-blue-600"
            title="折叠悬浮按钮组"
            @click="toggleCollapse"
          >
            <ChevronsRight class="w-4 h-4" />
          </button>

          <button
            class="fab-satellite -top-2 -right-2 bg-red-50 text-red-500 hover:bg-red-100"
            title="清空标签"
            @click="emit('clear')"
          >
            <X class="w-4 h-4" />
          </button>

          <button
            :class="[
              'fab-satellite -bottom-2 -right-2',
              isExpansionEnabled
                ? 'bg-green-100 text-green-600 hover:bg-green-200'
                : 'bg-white text-slate-400 hover:bg-slate-100'
            ]"
            :title="isExpansionEnabled ? '同义词膨胀：已开启' : '同义词膨胀：已关闭'"
            @click="toggleExpansion"
          >
            <TreePine class="w-4 h-4" />
            <div v-if="!isExpansionEnabled" class="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div class="w-5 h-0.5 bg-red-500 rotate-45 rounded-full" />
            </div>
          </button>
        </div>

        <button
          :class="[
            'fab-btn border',
            isTagRangeApplied
              ? 'bg-cyan-100 text-cyan-700 border-cyan-300'
              : 'bg-white hover:bg-cyan-50 text-cyan-600 border-cyan-200'
          ]"
          title="标签数量筛选"
          @click.stop="toggleTagCountPanel"
        >
          <Hash class="w-6 h-6" />
          <span
            v-if="isTagRangeApplied"
            class="fab-badge bg-cyan-500 text-white"
          >
            {{ appliedRangeText }}
          </span>
        </button>

        <div class="relative">
          <button
            :class="[
              'fab-btn border',
              props.isTempTagMode
                ? 'bg-purple-100 text-purple-700 border-purple-300'
                : 'bg-white hover:bg-purple-50 text-purple-600 border-purple-100'
            ]"
            title="临时标签/批量打标"
            @click="toggleTempMode"
          >
            <Stamp class="w-6 h-6" />
            <div
              v-if="!props.isTempTagMode"
              class="absolute inset-0 flex items-center justify-center pointer-events-none"
            >
              <div class="w-10 h-0.5 bg-red-500 rotate-45 rounded-full shadow-sm" />
            </div>
            <span
              v-if="localTempTags.length > 0"
              class="fab-badge bg-purple-500 text-white"
            >
              {{ localTempTags.length }}
            </span>
          </button>
          <button
            class="fab-satellite -bottom-2 -left-2 bg-purple-50 text-purple-500 hover:bg-purple-100"
            title="显示临时标签面板"
            @click.stop="toggleTempPanel"
          >
            <FileText class="w-4 h-4" />
          </button>
        </div>

        <button
          class="fab-btn bg-amber-100 hover:bg-amber-200 text-amber-700 border border-amber-300"
          title="同义词规则树"
          @click="emit('openRules')"
        >
          <TreeDeciduous class="w-6 h-6" />
        </button>

        <div class="relative">
          <button
            :class="[
              'fab-btn border',
              isExtensionFilterActive
                ? 'bg-teal-100 text-teal-700 border-teal-300'
                : 'bg-white hover:bg-teal-50 text-teal-600 border-teal-200'
            ]"
            title="扩展名筛选"
            @click.stop="toggleExtensionPanel"
          >
            <FileType class="w-6 h-6" />
            <span
              v-if="isExtensionFilterActive"
              class="fab-badge bg-teal-500 text-white"
            >
              {{ localExtensions.length + localExcludeExtensions.length }}
            </span>
          </button>
          <div
            v-if="showExtensionPanel"
            class="absolute right-full mr-3 top-0 bg-white rounded-2xl shadow-2xl border p-5 min-w-[280px] z-50"
            style="box-shadow: 0 20px 40px rgba(0,0,0,0.2);"
            @click.stop
          >
            <div class="text-base font-semibold text-slate-800 mb-4 text-center">扩展名筛选</div>
            <div class="text-xs text-slate-500 mb-3 text-center">点击选中，双击排除</div>
            <div class="grid grid-cols-3 gap-2 mb-4">
              <button
                v-for="ext in AVAILABLE_EXTENSIONS"
                :key="ext"
                :class="[
                  'px-3 py-2 text-sm font-medium rounded-lg border-2 transition-all',
                  getExtensionState(ext) === 'include'
                    ? 'bg-teal-100 text-teal-700 border-teal-400'
                    : getExtensionState(ext) === 'exclude'
                      ? 'bg-red-100 text-red-600 border-red-400'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-teal-300'
                ]"
                @click="toggleExtension(ext)"
                @dblclick.prevent="toggleExcludeExtension(ext)"
              >
                .{{ ext }}
              </button>
            </div>
            <div class="flex gap-3">
              <button
                class="flex-1 px-4 py-2.5 text-sm bg-slate-100 text-slate-600 rounded-[10px] hover:bg-slate-200 font-medium transition"
                @click="clearExtensionFilter"
              >
                重置
              </button>
              <button
                class="flex-1 px-4 py-2.5 text-sm bg-teal-500 text-white rounded-[10px] hover:bg-teal-600 font-medium transition"
                @click="applyExtensionFilter"
              >
                应用
              </button>
            </div>
          </div>
        </div>

        <button
          :class="[
            'fab-btn border',
            isBatchMode
              ? 'bg-indigo-100 text-indigo-700 border-indigo-300'
              : 'bg-white hover:bg-indigo-50 text-indigo-600 border-indigo-200'
          ]"
          title="批量编辑模式"
          @click="emit('toggleBatch')"
        >
          <CheckSquare class="w-6 h-6" />
          <div
            v-if="isBatchMode"
            class="absolute top-3 right-3 w-2.5 h-2.5 bg-indigo-500 rounded-full border-2 border-white"
          />
        </button>
      </div>
    </Transition>

    <Transition name="fab-mini">
      <div
        v-show="isCollapsed"
        class="fab-mini-strip"
        :class="{ 'cursor-grabbing': isDragging, 'cursor-grab': !isDragging }"
        :style="{ top: miniStripTop + 'px' }"
        @pointerdown="handlePointerDown"
        @pointermove="handlePointerMove"
        @pointerup="handlePointerUp"
        @pointercancel="handlePointerUp"
      >
        <div class="fab-mini-bg">
          <div class="flex flex-col gap-1.5 items-center">
            <button
              class="fab-mini-btn bg-white hover:bg-blue-50 text-slate-500 hover:text-blue-600 border border-slate-200"
              title="展开"
              @click="toggleCollapse"
            >
              <ChevronsLeft class="w-4 h-4" />
            </button>

            <button
              class="fab-mini-btn bg-blue-600 hover:bg-blue-700 text-white"
              title="搜索"
              @click="emit('search')"
            >
              <Search class="w-4 h-4" />
            </button>

            <button
              class="fab-mini-btn bg-white hover:bg-red-50 text-slate-500 hover:text-red-500 border border-slate-200"
              title="清空标签"
              @click="emit('clear')"
            >
              <X class="w-4 h-4" />
            </button>

            <button
              class="fab-mini-btn bg-white hover:bg-slate-100 text-slate-500 hover:text-blue-600 border border-slate-200"
              title="刷新"
              @click="emit('refresh')"
            >
              <RefreshCw class="w-4 h-4" />
            </button>

            <button
              :class="[
                'fab-mini-btn border',
                isExpansionEnabled
                  ? 'bg-purple-100 text-purple-600 border-purple-300'
                  : 'bg-white text-slate-400 border-slate-200 hover:bg-purple-50 hover:text-purple-600'
              ]"
              :title="isExpansionEnabled ? '膨胀：开' : '膨胀：关'"
              @click="toggleExpansion"
            >
              <TreePine class="w-4 h-4" />
              <div v-if="!isExpansionEnabled" class="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div class="w-4 h-0.5 bg-red-500 rotate-45 rounded-full" />
              </div>
            </button>

            <button
              class="fab-mini-btn bg-emerald-500 hover:bg-emerald-600 text-white"
              title="上传"
              @click="emit('upload')"
            >
              <ImagePlus class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
