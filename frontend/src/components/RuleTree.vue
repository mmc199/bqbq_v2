<script setup lang="ts">
/**
 * RuleTree 组件 - 规则树面板
 * 显示语义森林结构，支持增删改查、批量编辑、循环检测
 */
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { X, Search, FolderPlus, RefreshCw, Folder, ChevronRight, CheckSquare, Square, Trash2, Power, PowerOff, ChevronsUpDown, ChevronsDownUp } from 'lucide-vue-next'
import RuleGroupNode from './RuleGroupNode.vue'
import { useRulesApi } from '@/composables/useApi'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useToast } from '@/composables/useToast'
import type { RuleGroup, RuleKeyword } from '@/types'

// Props
const props = defineProps<{
  visible: boolean
}>()

// Emits
const emit = defineEmits<{
  'close': []
  'update': []
  'toggle': []
}>()

// API & Store
const rulesApi = useRulesApi()
const globalStore = useGlobalStore()
const toast = useToast()

// 状态
const isLoading = ref(false)
const searchText = ref('')
const expandedIds = ref<Set<number>>(new Set())
const groups = ref<RuleGroup[]>([])

// 批量编辑状态
const batchEditMode = ref(false)
const selectedGroupIds = ref<Set<number>>(new Set())

// 冲突检测状态
const conflictNodes = ref<RuleGroup[]>([])

// 新增状态
const addingGroupParentId = ref<number | null>(null)
const addingKeywordGroupId = ref<number | null>(null)
const newGroupName = ref('')
const newKeyword = ref('')
const showRootInput = ref(false)

// 拖拽状态
const draggingId = ref<number | null>(null)
const rootDropZoneActive = ref(false)

// 树容器 ref（用于滚动到匹配项）
const treeContainerRef = ref<HTMLElement | null>(null)

// 计算属性：过滤后的树（带搜索高亮）
const filteredGroups = computed(() => {
  const search = searchText.value.trim().toLowerCase()
  if (!search) {
    // 清除所有 isMatch 标记
    clearMatchFlags(groups.value)
    return groups.value
  }
  return filterTree(groups.value, search)
})

// 清除匹配标记
function clearMatchFlags(nodes: RuleGroup[]) {
  nodes.forEach(node => {
    node.isMatch = false
    clearMatchFlags(node.children)
  })
}

// 过滤树并标记匹配
function filterTree(nodes: RuleGroup[], search: string): RuleGroup[] {
  return nodes.reduce<RuleGroup[]>((acc, node) => {
    const nameMatch = node.name.toLowerCase().includes(search)
    const keywordMatch = node.keywords.some(k => k.keyword.toLowerCase().includes(search))
    const filteredChildren = filterTree(node.children, search)

    if (nameMatch || keywordMatch || filteredChildren.length > 0) {
      acc.push({
        ...node,
        isMatch: nameMatch || keywordMatch,
        children: filteredChildren,
      })
    }
    return acc
  }, [])
}

// 循环依赖检测
function detectCycles(nodes: RuleGroup[]): { conflictNodes: RuleGroup[], hasConflict: boolean } {
  const conflicts: RuleGroup[] = []
  const nodeMap = new Map<number, RuleGroup>()

  // 构建节点映射
  function buildMap(list: RuleGroup[]) {
    list.forEach(node => {
      nodeMap.set(node.id, node)
      buildMap(node.children)
    })
  }
  buildMap(nodes)

  // 检测从 startId 开始是否能到达 targetId（检测循环）


  // 标记冲突节点
  nodeMap.forEach(node => {
    node.isConflict = false
    node.conflictReason = undefined
  })

  return { conflictNodes: conflicts, hasConflict: conflicts.length > 0 }
}

// 加载规则树
async function loadRulesTree() {
  isLoading.value = true
  const result = await rulesApi.getRulesTree(globalStore.rulesVersion)

  if (result.notModified) {
    isLoading.value = false
    return
  }

  if (result.success && result.data) {
    groups.value = result.data.groups
    globalStore.updateRulesVersion(result.data.version)

    // 检测循环依赖
    const { conflictNodes: conflicts } = detectCycles(groups.value)
    conflictNodes.value = conflicts
  }
  isLoading.value = false
}

// 切换展开/折叠
function toggleExpand(groupId: number) {
  const newSet = new Set(expandedIds.value)
  if (newSet.has(groupId)) {
    newSet.delete(groupId)
  } else {
    newSet.add(groupId)
  }
  expandedIds.value = newSet
}

// 批量编辑模式
function toggleBatchMode() {
  batchEditMode.value = !batchEditMode.value
  if (!batchEditMode.value) {
    selectedGroupIds.value.clear()
  }
}

// 切换组选择
function toggleGroupSelection(groupId: number) {
  const newSet = new Set(selectedGroupIds.value)
  if (newSet.has(groupId)) {
    newSet.delete(groupId)
  } else {
    newSet.add(groupId)
  }
  selectedGroupIds.value = newSet
}

// 获取所有组ID
function getAllGroupIds(nodes: RuleGroup[]): Set<number> {
  const ids = new Set<number>()
  function collect(list: RuleGroup[]) {
    list.forEach(node => {
      ids.add(node.id)
      collect(node.children)
    })
  }
  collect(nodes)
  return ids
}

// 全选/取消全选
function toggleSelectAll() {
  const allIds = getAllGroupIds(groups.value)
  if (selectedGroupIds.value.size === allIds.size) {
    selectedGroupIds.value.clear()
  } else {
    selectedGroupIds.value = allIds
  }
}

// 展开全部
function expandAll() {
  expandedIds.value = getAllGroupIds(groups.value)
}

// 折叠全部
function collapseAll() {
  expandedIds.value.clear()
}

// 批量启用
async function batchEnableGroups() {
  if (selectedGroupIds.value.size === 0) return

  const result = await rulesApi.batchGroups(
    Array.from(selectedGroupIds.value),
    'enable',
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    selectedGroupIds.value.clear()
    toast.success(`已启用 ${selectedGroupIds.value.size} 个规则组`)
    emit('update')
  }
}

// 批量禁用
async function batchDisableGroups() {
  if (selectedGroupIds.value.size === 0) return

  const result = await rulesApi.batchGroups(
    Array.from(selectedGroupIds.value),
    'disable',
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    selectedGroupIds.value.clear()
    toast.success(`已禁用 ${selectedGroupIds.value.size} 个规则组`)
    emit('update')
  }
}

// 批量删除
async function batchDeleteGroups() {
  if (selectedGroupIds.value.size === 0) return

  if (!confirm(`确定要删除选中的 ${selectedGroupIds.value.size} 个规则组吗？\n这将同时删除所有子组和关键词。`)) {
    return
  }

  const result = await rulesApi.batchGroups(
    Array.from(selectedGroupIds.value),
    'delete',
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    selectedGroupIds.value.clear()
    toast.success(`已删除 ${selectedGroupIds.value.size} 个规则组`)
    emit('update')
  }
}

// 切换组启用状态
async function toggleGroupEnabled(group: RuleGroup) {
  const result = await rulesApi.toggleGroup(
    group.id,
    !group.enabled,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }
}

// 开始添加根组
function startAddRootGroup() {
  showRootInput.value = true
  newGroupName.value = ''
}

// 开始添加子组
function startAddGroup(parentId: number) {
  addingGroupParentId.value = parentId
  newGroupName.value = ''
  const newSet = new Set(expandedIds.value)
  newSet.add(parentId)
  expandedIds.value = newSet
}

// 开始添加关键词
function startAddKeyword(groupId: number) {
  addingKeywordGroupId.value = groupId
  newKeyword.value = ''
  const newSet = new Set(expandedIds.value)
  newSet.add(groupId)
  expandedIds.value = newSet
}

// 确认添加组
async function confirmAddGroup() {
  const name = newGroupName.value.trim()
  if (!name) {
    cancelAdd()
    return
  }

  const parentId = showRootInput.value ? null : addingGroupParentId.value

  const result = await rulesApi.createGroup(
    name,
    parentId,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }

  cancelAdd()
}

// 确认添加关键词
async function confirmAddKeyword() {
  const keyword = newKeyword.value.trim()
  if (!keyword || addingKeywordGroupId.value === null) {
    cancelAdd()
    return
  }

  const result = await rulesApi.addKeyword(
    addingKeywordGroupId.value,
    keyword,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }

  cancelAdd()
}

// 取消添加
function cancelAdd() {
  showRootInput.value = false
  addingGroupParentId.value = null
  addingKeywordGroupId.value = null
  newGroupName.value = ''
  newKeyword.value = ''
}

// 删除组
async function deleteGroup(group: RuleGroup) {
  if (!confirm(`确定要删除规则组 "${group.name}" 吗？\n这将同时删除所有子组和关键词。`)) {
    return
  }

  const result = await rulesApi.deleteGroup(
    group.id,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }
}

// 删除关键词
async function deleteKeyword(keywordId: number) {
  const result = await rulesApi.deleteKeyword(
    keywordId,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }
}

// 切换关键词启用状态
async function toggleKeywordEnabled(keyword: RuleKeyword) {
  const result = await rulesApi.toggleKeyword(
    keyword.id,
    !keyword.enabled,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }
}

// 拖拽事件处理
function handleDragStart(groupId: number) {
  draggingId.value = groupId
}

function handleDragEnd() {
  draggingId.value = null
  rootDropZoneActive.value = false
}

async function handleDropOnGroup(targetGroupId: number) {
  if (!draggingId.value || draggingId.value === targetGroupId) return

  // 批量拖拽支持
  let dragIds = [draggingId.value]
  if (batchEditMode.value && selectedGroupIds.value.size > 0 && selectedGroupIds.value.has(draggingId.value)) {
    dragIds = Array.from(selectedGroupIds.value)
  }

  if (dragIds.length > 1) {
    // 批量移动
    const result = await rulesApi.batchMoveHierarchy(
      dragIds,
      targetGroupId,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
  } else {
    // 单个移动
    const result = await rulesApi.moveGroup(
      draggingId.value,
      targetGroupId,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
  }

  draggingId.value = null
}

async function handleDropOnRoot(e: DragEvent) {
  e.preventDefault()
  if (!draggingId.value) return

  // 批量拖拽支持
  let dragIds = [draggingId.value]
  if (batchEditMode.value && selectedGroupIds.value.size > 0 && selectedGroupIds.value.has(draggingId.value)) {
    dragIds = Array.from(selectedGroupIds.value)
  }

  if (dragIds.length > 1) {
    // 批量移动到根
    const result = await rulesApi.batchMoveHierarchy(
      dragIds,
      null,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
  } else {
    // 单个移动到根
    const result = await rulesApi.moveGroup(
      draggingId.value,
      null,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
  }

  draggingId.value = null
  rootDropZoneActive.value = false
}

function handleRootDragOver(e: DragEvent) {
  if (!draggingId.value) return
  e.preventDefault()
  rootDropZoneActive.value = true
}

function handleRootDragLeave() {
  rootDropZoneActive.value = false
}

// 关闭面板
function close() {
  emit('close')
}

// 监听搜索文本变化，滚动到第一个匹配项
watch(searchText, async (newVal) => {
  if (!newVal.trim()) return

  // 等待 DOM 更新
  await nextTick()

  // 查找第一个匹配项并滚动
  const firstMatch = treeContainerRef.value?.querySelector('[data-match="true"]')
  if (firstMatch) {
    firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
})

// 监听可见性
watch(() => props.visible, (visible) => {
  if (visible) {
    loadRulesTree()
  }
})

// 初始化
onMounted(() => {
  if (props.visible) {
    loadRulesTree()
  }
})
</script>

<template>
  <Teleport to="body">
    <!-- 左侧切换条 - 面板关闭时显示（一比一复刻旧项目绿色渐变） -->
    <button
      v-show="!visible"
      class="rules-toggle-bar fixed left-0 top-1/2 -translate-y-1/2 z-50 w-5 h-20 flex items-center justify-center rounded-r-lg cursor-pointer transition-all duration-200 hover:w-6"
      style="background: linear-gradient(to right, #f0fdf4, #dcfce7);"
      title="打开规则树"
      @click="emit('toggle')"

    >
      <ChevronRight class="w-3 h-3 text-green-600" />
    </button>

    <!-- 遮罩 -->
    <div
      v-if="visible"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 transition-opacity"
      @click="close"
    />

    <!-- 面板 - 320px 宽度 -->
    <aside
      :class="[
        'rules-panel fixed top-0 left-0 w-80 h-full bg-white z-50 flex flex-col transform transition-transform duration-300',
        visible ? 'translate-x-0' : '-translate-x-full'
      ]"
      style="box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);"
    >
      <!-- 头部 -->
      <div class="rules-panel-header flex items-center justify-between p-5 border-b border-slate-200 flex-shrink-0">
        <h2 class="text-lg font-semibold text-slate-800">规则树</h2>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-400">v{{ globalStore.rulesVersion }}</span>
          <button
            class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all"
            :class="{ 'animate-spin': isLoading }"
            @click="loadRulesTree"
          >
            <RefreshCw class="w-4 h-4" />
          </button>
          <button
            class="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700 transition-all"
            @click="close"
          >
            <X class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- 搜索框 -->
      <div class="p-3 border-b flex-shrink-0">
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索组名或关键词..."
            class="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <!-- 工具栏 -->
      <div class="flex items-center justify-between gap-2 p-3 border-b flex-shrink-0">
        <div class="flex items-center gap-2">
          <button
            class="flex items-center gap-1 px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition"
            @click="startAddRootGroup"
          >
            <FolderPlus class="w-4 h-4" />
            新建
          </button>
          <button
            :class="[
              'flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg transition',
              batchEditMode ? 'bg-purple-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            ]"
            @click="toggleBatchMode"
          >
            <CheckSquare class="w-4 h-4" />
            批量
          </button>
        </div>
        <!-- 展开/折叠全部按钮 -->
        <div class="flex items-center gap-1">
          <button
            class="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded transition"
            title="展开全部"
            @click="expandAll"
          >
            <ChevronsDownUp class="w-4 h-4" />
          </button>
          <button
            class="p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded transition"
            title="折叠全部"
            @click="collapseAll"
          >
            <ChevronsUpDown class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- 批量编辑工具栏 -->
      <div
        v-if="batchEditMode"
        class="flex items-center justify-between gap-2 p-3 bg-purple-50 border-b flex-shrink-0"
      >
        <div class="flex items-center gap-2">
          <button
            class="flex items-center gap-1 px-2 py-1 text-xs bg-white border border-slate-200 rounded hover:bg-slate-50"
            @click="toggleSelectAll"
          >
            <component :is="selectedGroupIds.size === getAllGroupIds(groups).size ? CheckSquare : Square" class="w-3 h-3" />
            全选
          </button>
          <span class="text-xs text-purple-600">
            已选 {{ selectedGroupIds.size }} 项
          </span>
        </div>
        <div class="flex items-center gap-1">
          <button
            class="p-1.5 text-green-600 hover:bg-green-100 rounded"
            title="批量启用"
            :disabled="selectedGroupIds.size === 0"
            @click="batchEnableGroups"
          >
            <Power class="w-4 h-4" />
          </button>
          <button
            class="p-1.5 text-orange-600 hover:bg-orange-100 rounded"
            title="批量禁用"
            :disabled="selectedGroupIds.size === 0"
            @click="batchDisableGroups"
          >
            <PowerOff class="w-4 h-4" />
          </button>
          <button
            class="p-1.5 text-red-600 hover:bg-red-100 rounded"
            title="批量删除"
            :disabled="selectedGroupIds.size === 0"
            @click="batchDeleteGroups"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- 冲突警告 -->
      <div
        v-if="conflictNodes.length > 0"
        class="p-3 bg-red-50 border-b border-red-200 flex-shrink-0"
      >
        <div class="flex items-center gap-2 text-red-700 text-sm">
          <span class="font-bold">⚠️ 检测到数据冲突 ({{ conflictNodes.length }} 个节点)</span>
        </div>
      </div>

      <!-- 树内容 -->
      <div
        ref="treeContainerRef"
        class="flex-1 overflow-auto p-3 custom-scrollbar"
        @dragover="handleRootDragOver"
        @dragleave="handleRootDragLeave"
        @drop="handleDropOnRoot"
      >
        <!-- 根级别放置提示 -->
        <div
          v-if="draggingId && rootDropZoneActive"
          class="mb-2 p-3 border-2 border-dashed border-blue-400 bg-blue-50 rounded-lg text-center text-sm text-blue-600"
        >
          放置到根级别
        </div>

        <!-- 根级别新增输入框 -->
        <div v-if="showRootInput" class="mb-2">
          <input
            v-model="newGroupName"
            type="text"
            placeholder="输入组名，回车确认"
            class="w-full px-3 py-2 border border-blue-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            autofocus
            @keydown.enter="confirmAddGroup"
            @keydown.escape="cancelAdd"
            @blur="confirmAddGroup"
          />
        </div>

        <!-- 空状态 -->
        <div
          v-if="filteredGroups.length === 0 && !isLoading && !showRootInput"
          class="text-center text-slate-400 py-8"
        >
          <Folder class="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>暂无规则数据</p>
          <p class="text-xs mt-1">点击"新建"开始创建</p>
        </div>

        <!-- 递归渲染树 -->
        <div class="space-y-1">
          <RuleGroupNode
            v-for="group in filteredGroups"
            :key="group.id"
            :group="group"
            :expanded-ids="expandedIds"
            :adding-group-parent-id="addingGroupParentId"
            :adding-keyword-group-id="addingKeywordGroupId"
            :new-group-name="newGroupName"
            :new-keyword="newKeyword"
            :dragging-id="draggingId"
            :batch-edit-mode="batchEditMode"
            :selected-group-ids="selectedGroupIds"
            :search-text="searchText"
            @toggle-expand="toggleExpand"
            @start-add-group="startAddGroup"
            @start-add-keyword="startAddKeyword"
            @delete-group="deleteGroup"
            @delete-keyword="deleteKeyword"
            @toggle-keyword-enabled="toggleKeywordEnabled"
            @toggle-enabled="toggleGroupEnabled"
            @toggle-selection="toggleGroupSelection"
            @confirm-add-group="confirmAddGroup"
            @confirm-add-keyword="confirmAddKeyword"
            @cancel-add="cancelAdd"
            @update:new-group-name="newGroupName = $event"
            @update:new-keyword="newKeyword = $event"
            @drag-start="handleDragStart"
            @drag-end="handleDragEnd"
            @drop-on-group="handleDropOnGroup"
          />
        </div>
      </div>
    </aside>
  </Teleport>
</template>
