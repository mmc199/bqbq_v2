<script setup lang="ts">
/**
 * FloatingButtons 组件 - FAB 悬浮按钮组
 * 一比一复刻旧项目的按钮顺序和样式
 */
import { ref, computed, onMounted } from 'vue'
import {
  Search, RefreshCw, X, Download, Upload, Trash2,
  TreeDeciduous, ImagePlus, ChevronsRight, ChevronsLeft,
  SlidersHorizontal, ArrowUpDown, Zap, Tag, Plus, Check, CheckSquare
} from 'lucide-vue-next'
import { useGlobalStore } from '@/stores/useGlobalStore'

// Props
const props = defineProps<{
  isTrashMode?: boolean
  isExpansionEnabled?: boolean
  isHQMode?: boolean
  isBatchMode?: boolean
  sortBy?: string
  minTags?: number
  maxTags?: number
  tempTags?: string[]
}>()

// Emits
const emit = defineEmits<{
  'upload': []
  'openRules': []
  'export': []
  'import': []
  'toggleTrash': [isTrash: boolean]
  'toggleExpansion': [enabled: boolean]
  'toggleHQ': [enabled: boolean]
  'toggleBatch': []
  'search': []
  'refresh': []
  'clear': []
  'updateSort': [sortBy: string]
  'updateTagRange': [min: number | null, max: number | null]
  'updateTempTags': [tags: string[]]
  'applyTempTags': []
}>()

// Store
const globalStore = useGlobalStore()

// 状态（折叠状态持久化）
const isCollapsed = computed({
  get: () => globalStore.preferences.fabCollapsed,
  set: (val) => globalStore.updatePreference('fabCollapsed', val)
})
const showSortMenu = ref(false)
const showTagCountPanel = ref(false)
const showTempTagsPanel = ref(false)

// 迷你按钮条拖拽状态
const isDragging = ref(false)
const dragStartY = ref(0)
const dragStartTop = ref(0)
const miniStripRef = ref<HTMLElement | null>(null)

// 迷你按钮条位置（从 localStorage 读取）
const miniStripTop = ref(112) // 默认 7rem = 112px
const STORAGE_KEY = 'bqbq_fab_mini_position'

// 初始化位置
onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    const pos = parseInt(saved, 10)
    if (!isNaN(pos) && pos >= 64 && pos <= window.innerHeight - 200) {
      miniStripTop.value = pos
    }
  }
})

// 拖拽开始
function handlePointerDown(e: PointerEvent) {
  if ((e.target as HTMLElement).closest('button')) return // 不拦截按钮点击

  isDragging.value = true
  dragStartY.value = e.clientY
  dragStartTop.value = miniStripTop.value

  // 捕获指针
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  e.preventDefault()
}

// 拖拽移动
function handlePointerMove(e: PointerEvent) {
  if (!isDragging.value) return

  const deltaY = e.clientY - dragStartY.value
  let newTop = dragStartTop.value + deltaY

  // 限制范围
  const minTop = 64 // 顶部导航栏高度
  const maxTop = window.innerHeight - 250 // 底部留空
  newTop = Math.max(minTop, Math.min(maxTop, newTop))

  miniStripTop.value = newTop
}

// 拖拽结束
function handlePointerUp(e: PointerEvent) {
  if (!isDragging.value) return

  isDragging.value = false

  // 保存位置
  localStorage.setItem(STORAGE_KEY, miniStripTop.value.toString())

  // 释放指针
  ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
}

// 标签数量范围
const localMinTags = ref(props.minTags ?? 0)
const localMaxTags = ref(props.maxTags ?? 50)

// 临时标签
const tempTagInput = ref('')
const localTempTags = ref<string[]>([...(props.tempTags || [])])

// 排序选项 - 与旧项目一致
const sortOptions = [
  { value: 'time_desc', label: '📅 最新添加', icon: '📅' },
  { value: 'time_asc', label: '📅 最早添加', icon: '📅' },
  { value: 'size_desc', label: '💾 文件很大', icon: '💾' },
  { value: 'size_asc', label: '💾 文件很小', icon: '💾' },
  { value: 'resolution_desc', label: '📐 高分辨率', icon: '📐' },
  { value: 'resolution_asc', label: '📐 低分辨率', icon: '📐' },
]

// 切换折叠
function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

// 切换回收站模式
function toggleTrashMode() {
  emit('toggleTrash', !props.isTrashMode)
}

// 切换关键词膨胀
function toggleExpansion() {
  emit('toggleExpansion', !props.isExpansionEnabled)
}

// 切换 HQ 模式
function toggleHQMode() {
  emit('toggleHQ', !props.isHQMode)
}

// 选择排序
function selectSort(value: string) {
  emit('updateSort', value)
  showSortMenu.value = false
}

// 应用标签数量范围
function applyTagRange() {
  emit('updateTagRange',
    localMinTags.value > 0 ? localMinTags.value : null,
    localMaxTags.value < 50 ? localMaxTags.value : null
  )
  showTagCountPanel.value = false
}

// 重置标签数量范围
function resetTagRange() {
  localMinTags.value = 0
  localMaxTags.value = 50
  emit('updateTagRange', null, null)
  showTagCountPanel.value = false
}

// 添加临时标签
function addTempTag() {
  const tag = tempTagInput.value.trim()
  if (tag && !localTempTags.value.includes(tag)) {
    localTempTags.value.push(tag)
    emit('updateTempTags', localTempTags.value)
  }
  tempTagInput.value = ''
}

// 移除临时标签
function removeTempTag(index: number) {
  localTempTags.value.splice(index, 1)
  emit('updateTempTags', localTempTags.value)
}

// 应用临时标签
function applyTempTags() {
  emit('applyTempTags')
}

// 清空临时标签
function clearTempTags() {
  localTempTags.value = []
  emit('updateTempTags', [])
}

// 点击外部关闭面板
function closeAllPanels() {
  showSortMenu.value = false
  showTagCountPanel.value = false
  showTempTagsPanel.value = false
}
</script>

<template>
  <!-- 点击遮罩关闭面板 -->
  <div
    v-if="showSortMenu || showTagCountPanel || showTempTagsPanel"
    class="fixed inset-0 z-40"
    @click="closeAllPanels"
  />

  <!-- FAB 主容器 - 右上角 2列网格，按旧项目顺序排列 -->
  <Transition name="fab-main">
    <div
      v-show="!isCollapsed"
      class="fixed right-4 grid grid-cols-2 gap-3 z-50 top-[7rem] transition-all duration-300"
    >
    <!-- 第1行：导出、导入 -->
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

    <!-- 第2行：HQ模式（青色）、排序（橙色） -->
    <button
      :class="[
        'fab-btn border',
        isHQMode
          ? 'bg-cyan-50 text-cyan-600 border-cyan-300'
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

    <div class="relative">
      <button
        class="fab-btn bg-white hover:bg-orange-50 text-orange-600 border border-orange-200"
        title="排序方式"
        @click.stop="showSortMenu = !showSortMenu"
      >
        <ArrowUpDown class="w-6 h-6" />
      </button>
      <!-- 排序下拉菜单 -->
      <div
        v-if="showSortMenu"
        class="absolute right-full mr-3 top-0 bg-white rounded-xl shadow-xl border py-2 w-40 z-50"
        @click.stop
      >
        <button
          v-for="opt in sortOptions"
          :key="opt.value"
          :class="[
            'w-full px-4 py-2 text-left text-sm hover:bg-slate-50 transition',
            sortBy === opt.value ? 'text-blue-600 font-bold bg-blue-50' : 'text-slate-600'
          ]"
          @click="selectSort(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- 第3行：回收站、上传 -->
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

    <!-- 第4行：批量编辑、搜索（带卫星按钮） -->
    <button
      :class="[
        'fab-btn border',
        isBatchMode
          ? 'bg-indigo-100 text-indigo-600 border-indigo-300'
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

    <div class="relative group">
      <button
        class="fab-btn bg-blue-600 hover:bg-blue-700 text-white z-20 relative"
        title="执行搜索"
        @click="emit('search')"
      >
        <Search class="w-7 h-7" />
      </button>

      <!-- 折叠按钮 (卫星 左上) -->
      <button
        class="fab-satellite -top-2 -left-2 hover:bg-slate-100 hover:text-blue-600"
        title="折叠悬浮按钮组"
        @click="toggleCollapse"
      >
        <ChevronsRight class="w-4 h-4" />
      </button>

      <!-- 清空按钮 (卫星 右上) -->
      <button
        class="fab-satellite -top-2 -right-2 hover:bg-red-50 hover:text-red-500"
        title="清空标签"
        @click="emit('clear')"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- 膨胀开关 (卫星 右下) - 旧项目位置 -->
      <button
        :class="[
          'fab-satellite -bottom-2 -right-2',
          isExpansionEnabled
            ? 'bg-purple-100 text-purple-600 border-purple-300 hover:bg-purple-200'
            : 'hover:bg-purple-50 hover:text-purple-600'
        ]"
        :title="isExpansionEnabled ? '同义词膨胀：已开启' : '同义词膨胀：已关闭'"
        @click="toggleExpansion"
      >
        <TreeDeciduous class="w-4 h-4" />
        <!-- 关闭状态斜杠 -->
        <div v-if="!isExpansionEnabled" class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="w-5 h-0.5 bg-red-500 rotate-45 rounded-full" />
        </div>
      </button>
    </div>

    <div class="relative">
      <button
        :class="[
          'fab-btn border',
          (minTags && minTags > 0) || (maxTags && maxTags < 50)
            ? 'bg-cyan-50 text-cyan-600 border-cyan-300'
            : 'bg-white hover:bg-cyan-50 text-cyan-600 border-cyan-200'
        ]"
        title="标签数量筛选"
        @click.stop="showTagCountPanel = !showTagCountPanel"
      >
        <SlidersHorizontal class="w-6 h-6" />
      </button>
      <!-- 标签数量面板 -->
      <div
        v-if="showTagCountPanel"
        class="absolute right-full mr-3 top-0 bg-white rounded-xl shadow-xl border p-4 w-64 z-50"
        @click.stop
      >
        <div class="text-sm font-bold text-slate-700 mb-3">标签数量筛选</div>
        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-500 w-8">最少</span>
            <input
              v-model.number="localMinTags"
              type="range"
              min="0"
              max="50"
              class="flex-1"
            />
            <span class="text-xs text-slate-600 w-6">{{ localMinTags }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-500 w-8">最多</span>
            <input
              v-model.number="localMaxTags"
              type="range"
              min="0"
              max="50"
              class="flex-1"
            />
            <span class="text-xs text-slate-600 w-6">{{ localMaxTags }}</span>
          </div>
        </div>
        <div class="flex gap-2 mt-4">
          <button
            class="flex-1 px-3 py-1.5 text-xs bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200"
            @click="resetTagRange"
          >
            重置
          </button>
          <button
            class="flex-1 px-3 py-1.5 text-xs bg-cyan-500 text-white rounded-lg hover:bg-cyan-600"
            @click="applyTagRange"
          >
            应用
          </button>
        </div>
      </div>
    </div>

    <!-- 第5行：临时标签、规则树（绿色） -->
    <div class="relative">
      <button
        :class="[
          'fab-btn border',
          localTempTags.length > 0
            ? 'bg-purple-50 text-purple-600 border-purple-300'
            : 'bg-white hover:bg-purple-50 text-purple-600 border-purple-100'
        ]"
        title="临时标签/批量打标"
        @click.stop="showTempTagsPanel = !showTempTagsPanel"
      >
        <Tag class="w-6 h-6" />
        <span
          v-if="localTempTags.length > 0"
          class="fab-badge bg-purple-500 text-white"
        >
          {{ localTempTags.length }}
        </span>
      </button>
      <!-- 临时标签面板 -->
      <div
        v-if="showTempTagsPanel"
        class="absolute right-full mr-3 top-0 bg-white rounded-xl shadow-xl border p-4 w-64 z-50"
        @click.stop
      >
        <div class="text-sm font-bold text-slate-700 mb-3">临时标签（批量打标）</div>
        <div class="flex gap-2 mb-3">
          <input
            v-model="tempTagInput"
            type="text"
            placeholder="输入标签..."
            class="flex-1 px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-300"
            @keydown.enter="addTempTag"
          />
          <button
            class="px-3 py-1.5 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
            @click="addTempTag"
          >
            <Plus class="w-4 h-4" />
          </button>
        </div>
        <div class="flex flex-wrap gap-1.5 mb-3 max-h-32 overflow-y-auto">
          <span
            v-for="(tag, index) in localTempTags"
            :key="tag"
            class="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full flex items-center gap-1"
          >
            {{ tag }}
            <button class="hover:text-purple-900" @click="removeTempTag(index)">
              <X class="w-3 h-3" />
            </button>
          </span>
          <span v-if="localTempTags.length === 0" class="text-xs text-slate-400 italic">
            暂无临时标签
          </span>
        </div>
        <div class="flex gap-2">
          <button
            class="flex-1 px-3 py-1.5 text-xs bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200"
            @click="clearTempTags"
          >
            清空
          </button>
          <button
            class="flex-1 px-3 py-1.5 text-xs bg-purple-500 text-white rounded-lg hover:bg-purple-600 flex items-center justify-center gap-1"
            :disabled="localTempTags.length === 0"
            @click="applyTempTags"
          >
            <Check class="w-3 h-3" />
            应用
          </button>
        </div>
      </div>
    </div>

    <button
      class="fab-btn bg-white hover:bg-green-50 text-green-600 border border-green-200"
      title="同义词规则树"
      @click="emit('openRules')"
    >
      <TreeDeciduous class="w-6 h-6" />
    </button>
  </div>
  </Transition>

  <!-- 折叠后的迷你按钮条 -->
  <Transition name="fab-mini">
    <div
      v-show="isCollapsed"
      ref="miniStripRef"
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
          <!-- 展开按钮 -->
          <button
            class="fab-mini-btn bg-white hover:bg-blue-50 text-slate-500 hover:text-blue-600 border border-slate-200"
            title="展开"
            @click="toggleCollapse"
          >
            <ChevronsLeft class="w-4 h-4" />
          </button>

          <!-- 搜索按钮 -->
          <button
            class="fab-mini-btn bg-blue-600 hover:bg-blue-700 text-white"
            title="搜索"
            @click="emit('search')"
          >
            <Search class="w-4 h-4" />
          </button>

          <!-- 清空按钮 -->
          <button
            class="fab-mini-btn bg-white hover:bg-red-50 text-slate-500 hover:text-red-500 border border-slate-200"
            title="清空标签"
            @click="emit('clear')"
          >
            <X class="w-4 h-4" />
          </button>

          <!-- 刷新按钮 -->
          <button
            class="fab-mini-btn bg-white hover:bg-slate-100 text-slate-500 hover:text-blue-600 border border-slate-200"
            title="刷新"
            @click="emit('refresh')"
          >
            <RefreshCw class="w-4 h-4" />
          </button>

          <!-- 膨胀开关 -->
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
            <TreeDeciduous class="w-4 h-4" />
            <div v-if="!isExpansionEnabled" class="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div class="w-4 h-0.5 bg-red-500 rotate-45 rounded-full" />
            </div>
          </button>

          <!-- 上传按钮 -->
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
</template>
