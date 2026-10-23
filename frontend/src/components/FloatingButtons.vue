<script setup lang="ts">
/**
 * FloatingButtons 组件 - FAB 悬浮按钮组 
 * 完全复刻旧项目的顺序和样式，包含 FAB 按钮排列、面板控制、规则样式
 */
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Search, RefreshCw, X, Trash2,
  TreePine, ImagePlus, ChevronsRight, ChevronsLeft, Loader2,
  ArrowUpDown,
  Hash, Stamp, FileText,
  Bird, ShoppingCart
} from 'lucide-vue-next'
import * as noUiSlider from 'nouislider'
import 'nouislider/dist/nouislider.css'
import TagInput from '@/components/TagInput.vue'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useAuthApi, useCartApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { getThumbBlobUrl, preloadThumbnails } from '@/composables/useThumbBatch'

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

// ===========================================================================
//  登录（QQ 验证码）
// ===========================================================================
//
// 【为什么用面板而不是 toast】验证码有效期 5 分钟，toast 几秒就消失，
// 用户去 QQ 发完消息回来就看不见了。面板可以一直显示并带倒计时。

const toast = useToast()
const authApi = useAuthApi()
const cartApi = useCartApi()

const showLoginPanel = ref(false)
const showCartPanel = ref(false)

const isLoggedIn = computed(() => globalStore.authGranted)
const loginCode = ref('')
const loginRemaining = ref(0)
const loginPending = ref(false)

let loginPollTimer: number | null = null
let loginCountdownTimer: number | null = null

function stopLoginTimers() {
  if (loginPollTimer !== null) {
    window.clearInterval(loginPollTimer)
    loginPollTimer = null
  }
  if (loginCountdownTimer !== null) {
    window.clearInterval(loginCountdownTimer)
    loginCountdownTimer = null
  }
}

/** 申请验证码并开始倒计时 / 轮询 */
async function startLogin() {
  stopLoginTimers()
  loginPending.value = true

  const r = await authApi.requestCode(globalStore.clientId)
  if (!r.success || !r.data?.success) {
    toast.error(r.data?.error || r.error || '申请验证码失败')
    loginPending.value = false
    return
  }

  // 已经登录过了
  if (r.data.granted) {
    globalStore.setAuthGranted(true)
    loginPending.value = false
    toast.success('已登录')
    return
  }

  loginCode.value = r.data.code || ''
  loginRemaining.value = r.data.expires_in ?? 300

  // 倒计时
  loginCountdownTimer = window.setInterval(() => {
    loginRemaining.value -= 1
    if (loginRemaining.value <= 0) {
      stopLoginTimers()
      loginPending.value = false
      loginCode.value = ''
    }
  }, 1000)

  // 每 2 秒查一次登录态
  loginPollTimer = window.setInterval(async () => {
    const me = await authApi.checkMe(globalStore.clientId)
    if (me.success && me.data?.granted) {
      stopLoginTimers()
      globalStore.setAuthGranted(true)
      loginPending.value = false
      loginCode.value = ''
      toast.success('登录成功')
    }
  }, 2000)
}

/** 退出登录 */
async function logout() {
  await authApi.logout(globalStore.clientId)
  globalStore.setAuthGranted(false)
  stopLoginTimers()
  loginCode.value = ''
  loginPending.value = false
  toast.info('已退出登录')
}

function toggleLoginPanel() {
  const next = !showLoginPanel.value
  closeAllPanels()
  showLoginPanel.value = next
  if (next && !isLoggedIn.value && !loginCode.value) {
    startLogin()
  }
}

// ===========================================================================
//  购物车
// ===========================================================================
//
// 【纯前端存储】加/删都只改 store（localStorage），不发请求。
// 【缩略图走批量 zip】与图片网格一致，用 /thumbnails/batch 一次取回全部，
//   而不是每张缩略图一个 <img src> 请求（穿透链路上会非常慢）。
// 【响应式】cartMd5s 是 store 里的 ref，卡片上点了购物车，
//   这里的 cartCount 和面板列表会立刻更新，无需重新打开面板。

const cartCount = computed(() => globalStore.cartCount)
const cartMd5s = computed(() => globalStore.cartMd5s)

// md5 -> 缩略图 blob URL（批量取回后填充）
const cartThumbs = ref<Record<string, string>>({})
const cartThumbLoading = ref(false)

/** 批量加载购物车里的缩略图（走 /thumbnails/batch，一次 zip 取回） */
async function loadCartThumbs() {
  const missing = cartMd5s.value.filter((m) => !cartThumbs.value[m])
  if (missing.length === 0) return

  cartThumbLoading.value = true
  try {
    // 与图片网格共用同一份 blob 缓存：已加载过的直接命中，不会重复请求
    await preloadThumbnails(missing)
    const next = { ...cartThumbs.value }
    for (const md5 of missing) {
      const url = getThumbBlobUrl(md5)
      if (url) next[md5] = url
    }
    cartThumbs.value = next
  } catch (e) {
    console.warn('[Cart] 缩略图批量加载失败', e)
  } finally {
    cartThumbLoading.value = false
  }
}

/** 购物车变化时增量补图（只请求新增的 md5） */
watch(
  () => cartMd5s.value.join(','),
  () => {
    if (showCartPanel.value) void loadCartThumbs()
  }
)

/** 单独移出（纯本地操作） */
function removeFromCart(md5: string) {
  globalStore.removeCartMd5(md5)
}

/** 清空（纯本地操作） */
function clearCart() {
  globalStore.clearCartState()
  toast.info('购物车已清空')
}

/** 把购物车 md5 列表一次性提交给后端，供 bot 取回 */
async function sendCartToQQ() {
  if (cartCount.value === 0) {
    toast.info('购物车是空的')
    return
  }
  if (!isLoggedIn.value) {
    toast.warning('请先登录 QQ（点击企鹅按钮）')
    return
  }

  const r = await cartApi.send(globalStore.clientId, cartMd5s.value)
  if (r.success && r.data?.success) {
    toast.success(r.data.message || '已加入待取回队列')
  } else {
    toast.error(r.data?.error || r.error || '发送失败')
  }
}

function toggleCartPanel() {
  const next = !showCartPanel.value
  closeAllPanels()
  showCartPanel.value = next
  if (next) {
    // 打开时批量补图。已加载过的会命中 blob 缓存，不会重复请求。
    void loadCartThumbs()
  }
}

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

// -------------------------------------------------------------------------
//  临时标签：props <-> 本地状态双向同步
// -------------------------------------------------------------------------
//
// 【为什么需要 syncing 标志】下面两个 watch 天然会形成无限循环：
//   props.tempTags 变 -> 写 localTempTags -> watch(local) emit
//     -> 父组件 tempTags.value = tags（新数组）-> props 变 -> ...
//
// 每次 emit 父组件都赋一个新数组，引用永远不同，deep watch 也无法跳过，
// 最终把主线程彻底占满（表现为界面卡死，连输入框都点不动）。
//
// 解法：emit 前置位 syncing，等 props 回流时发现是「自己刚发出去的」
// 就只更新本地副本、不再二次 emit，从而打断循环。

let syncingFromLocal = false

watch(
  () => props.tempTags,
  (tags) => {
    const next = tags || []
    // 内容相同就直接返回，避免无意义地重建数组
    if (
      next.length === localTempTags.value.length &&
      next.every((t, i) => t === localTempTags.value[i])
    ) {
      return
    }
    syncingFromLocal = true
    localTempTags.value = [...next]
    // 等 watch(localTempTags) 这一轮 flush 完再复位
    nextTick(() => {
      syncingFromLocal = false
    })
  },
  { immediate: true }
)

watch(
  localTempTags,
  (tags) => {
    // 来源于 props 的回流，不要再次 emit（否则死循环）
    if (syncingFromLocal) return
    emit('updateTempTags', [...tags])
  },
  { deep: true }
)

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
  showLoginPanel.value = false
  showCartPanel.value = false
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

  // 查询登录态（购物车是 localStorage 里的，无需从后端拉）
  authApi.checkMe(globalStore.clientId).then((r) => {
    globalStore.setAuthGranted(r.success && !!r.data?.granted)
  })
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
  stopLoginTimers()
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

    <!-- 登录面板
         定位同购物车面板：始终 right-36，跟随 FAB 网格左侧。 -->
    <div
      id="login-panel"
      :class="[
        'fixed top-24 right-36 bg-white rounded-xl shadow-2xl border border-slate-200 p-3 z-40 origin-top-right flex-col gap-2',
        'w-[calc(100vw-9.5rem)] max-w-64',
        showLoginPanel ? 'flex' : 'hidden'
      ]"
      title="QQ 登录"
      @click.stop
    >
      <div class="flex items-center justify-between gap-1 mb-1">
        <span class="text-xs font-bold text-slate-600 flex-1">QQ 登录</span>
        <span
          id="login-panel-close"
          class="cursor-pointer text-slate-400 hover:text-red-500 text-base ml-1"
          title="关闭"
          @click="showLoginPanel = false"
        >&times;</span>
      </div>

      <!-- 已登录 -->
      <template v-if="isLoggedIn">
        <div class="text-xs text-cyan-600 font-medium">已登录 ✅</div>
        <div class="text-[11px] text-slate-400 font-mono break-all">
          {{ globalStore.clientId }}
        </div>
        <button
          id="login-logout-btn"
          class="mt-1 px-2 py-1 text-xs bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition"
          @click="logout"
        >退出登录</button>
      </template>

      <!-- 未登录 -->
      <template v-else>
        <div class="text-xs text-slate-500">请私聊机器人发送：</div>
        <div class="text-center py-2 bg-slate-50 rounded border border-slate-200">
          <span class="text-base font-bold tracking-wide text-cyan-600 font-mono">
            bqbq登录 {{ loginCode || '----' }}
          </span>
        </div>
        <div class="text-[11px] text-slate-400">
          <span v-if="loginRemaining > 0">{{ loginRemaining }} 秒后过期</span>
          <span v-else class="text-amber-600">验证码已过期</span>
        </div>
        <button
          id="login-refresh-btn"
          class="mt-1 px-2 py-1 text-xs bg-cyan-500 text-white rounded hover:bg-cyan-600 transition"
          @click="startLogin"
        >{{ loginCode ? '换一个验证码' : '获取验证码' }}</button>
      </template>
    </div>

    <!-- 购物车面板
         始终跟随 FAB：定位在按钮组左侧。
         FAB 网格右边距 right-4(16px) + 两列 56px + gap 12px = 140px，
         这里取 right-36（144px）= 140 + 4px 间隔，紧贴网格左缘。
         手机端同样 right-36，宽度自适应剩余空间：
           calc(100vw - 9rem - 0.5rem) = 屏宽 - 144px - 8px 左边距
         多减 8px 是为了让面板左边缘留一点呼吸位，
         否则 360px 屏上会正好顶到屏幕左边，看起来像被裁掉。 -->
    <div
      id="cart-panel"
      :class="[
        'fixed top-24 right-36 bg-white rounded-xl shadow-2xl border border-slate-200 p-3 z-40 origin-top-right flex-col gap-2',
        'w-[calc(100vw-9.5rem)] max-w-72',
        showCartPanel ? 'flex' : 'hidden'
      ]"
      title="购物车"
      @click.stop
    >
      <div class="flex items-center justify-between gap-1 mb-1">
        <span class="text-xs font-bold text-slate-600 flex-1">购物车（{{ cartCount }}）</span>
        <span
          id="cart-panel-close"
          class="cursor-pointer text-slate-400 hover:text-red-500 text-base ml-1"
          title="关闭"
          @click="showCartPanel = false"
        >&times;</span>
      </div>

      <template v-if="!isLoggedIn">
        <div class="text-xs text-slate-500 py-2">请先完成 QQ 登录</div>
        <button
          class="px-2 py-1 text-xs bg-cyan-500 text-white rounded hover:bg-cyan-600"
          @click="toggleLoginPanel"
        >去登录</button>
      </template>

      <template v-else-if="cartCount === 0">
        <div class="text-xs text-slate-400 py-3 text-center">
          购物车是空的<br />
          <span class="text-[11px]">点图片上的购物车图标即可加入</span>
        </div>
      </template>

      <template v-else>
        <!-- 购物车缩略图列表
             每张右上角有一个明确的 ✕ 按钮单独移出。
             【为什么不用「点图片移出」】原实现把整个缩略图当删除按钮，
             触屏上没有 hover 提示，用户以为点图是查看大图，实际是删除；
             桌面端也容易误点。改成显式 ✕ 更安全直观。
             【缩略图来源】走 /thumbnails/batch 批量 zip 取回的 blob URL，
             与图片网格共用同一份缓存，不会逐张发请求。 -->
        <!-- 窄屏 3 列、sm 及以上 4 列：
             360px 屏上面板仅约 208px 宽，4 列时单格只有 41px，
             16px 的 × 按钮会遮掉近一半；3 列时单格 57px，好点也好按。 -->
        <div class="grid grid-cols-3 sm:grid-cols-4 gap-1.5 max-h-52 overflow-auto pr-0.5">
          <div
            v-for="md5 in cartMd5s"
            :key="md5"
            class="relative"
          >
            <img
              v-if="cartThumbs[md5]"
              :src="cartThumbs[md5]"
              class="w-full aspect-square object-cover rounded border border-slate-200"
              :title="md5.slice(0, 8)"
            />
            <!-- 缩略图还没取回时的占位 -->
            <div
              v-else
              class="w-full aspect-square rounded border border-slate-200 bg-slate-100 flex items-center justify-center"
              :title="md5.slice(0, 8)"
            >
              <Loader2 class="w-3 h-3 text-slate-400 animate-spin" />
            </div>
            <!-- 单独移出按钮 -->
            <button
              class="cart-remove-btn absolute -top-1 -right-1 w-4 h-4 rounded-full
                     bg-red-500 text-white text-[10px] leading-none
                     flex items-center justify-center
                     shadow-md ring-1 ring-white
                     hover:bg-red-600 active:scale-90 transition-transform"
              :title="'移出：' + md5.slice(0, 8)"
              @click.stop="removeFromCart(md5)"
            >&times;</button>
          </div>
        </div>

        <div class="text-[11px] text-slate-500 leading-relaxed">
          点按钮后私聊机器人发送 <b>bqbq取回</b>
        </div>

        <button
          id="cart-send-btn"
          class="px-2 py-1 text-xs bg-amber-500 text-white rounded hover:bg-amber-600"
          @click="sendCartToQQ"
        >发送到 QQ（{{ cartCount }} 张）</button>

        <button
          id="cart-clear-btn"
          class="px-2 py-1 text-xs bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
          @click="clearCart"
        >清空</button>
      </template>
    </div>

    <!-- FAB 展开状态：2×5 网格布局（旧项目） -->
    <div
      id="fab-container"
      :class="[
        'fixed right-4 grid grid-cols-2 gap-3 z-50 top-[7rem] transition-all duration-300',
        isCollapsed ? 'hidden' : ''
      ]"
    >
        <!-- 购物车（替换原「导出 JSON」按钮）
             导出接口已停用（JSON 导出在 45 万条下太慢，改用备份 db）。
             购物车数据存后端，bot 要按 openid 取。 -->
        <button
          id="fab-cart"
          class="w-14 h-14 bg-white hover:bg-amber-50 text-amber-600 border border-amber-200 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center relative group"
          :title="`购物车（${cartCount} 张）`"
          @click.stop="toggleCartPanel"
        >
          <ShoppingCart class="w-6 h-6" />
          <span
            id="cart-badge"
            :class="[
              'absolute -top-1 -right-1 bg-amber-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full',
              cartCount > 0 ? '' : 'hidden'
            ]"
          >
            {{ cartCount }}
          </span>
          <span class="absolute right-full mr-3 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap pointer-events-none">购物车</span>
        </button>

        <!-- QQ 登录（替换原「导入 JSON」按钮）
             导入接口已停用。
             图标用 lucide Bird（lucide 无企鹅/鸽子）。
             登录态只用颜色区分：未登录灰 / 已登录青。 -->
        <button
          id="fab-login"
          :class="[
            'w-14 h-14 bg-white rounded-2xl shadow-lg hover:shadow-xl hover:scale-105',
            'transition-all flex items-center justify-center relative group border',
            isLoggedIn
              ? 'border-cyan-200 text-cyan-600 hover:bg-cyan-50'
              : 'border-slate-200 text-slate-400 hover:bg-slate-50'
          ]"
          :title="isLoggedIn ? 'QQ 已登录' : 'QQ 未登录，点击登录'"
          @click.stop="toggleLoginPanel"
        >
          <Bird class="w-6 h-6" />
          <span class="absolute right-full mr-3 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap pointer-events-none">
            {{ isLoggedIn ? '已登录' : 'QQ 登录' }}
          </span>
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
