<script setup lang="ts">
/**
 * RuleTree 组件 - 规则树面板
 * 显示语义森林结构，支持增删改查、批量编辑、循环检测
 */
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { X, RefreshCw, ChevronRight, ChevronLeft, AlertTriangle, Trash2, Home, FolderX } from 'lucide-vue-next'
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
const conflictRelations = ref<{ parent_id: number; child_id: number; reason: string }[]>([])
const hasShownConflictWarning = ref(false)

// 新增状态
const addingGroupParentId = ref<number | null>(null)
const addingKeywordGroupId = ref<number | null>(null)
const newGroupName = ref('')
const newKeyword = ref('')
const showRootInput = ref(false)

// 拖拽状态
const draggingId = ref<number | null>(null)
const rootDropZoneActive = ref(false)
const dragOverGapKey = ref<string | null>(null)

// 自定义滚动条 refs
const scrollContentRef = ref<HTMLDivElement | null>(null)
const vScrollbarRef = ref<HTMLDivElement | null>(null)
const hScrollbarRef = ref<HTMLDivElement | null>(null)
const vThumbRef = ref<HTMLDivElement | null>(null)
const hThumbRef = ref<HTMLDivElement | null>(null)
const cornerRef = ref<HTMLDivElement | null>(null)

// 树容器 ref（用于滚动到匹配项）
const treeContainerRef = ref<HTMLElement | null>(null)

let cleanupScrollSync: (() => void) | null = null
let updateScrollbars: (() => void) | null = null

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

const treeSuggestions = computed(() => {
  const set = new Set<string>()
  const traverse = (nodes: RuleGroup[]) => {
    nodes.forEach(node => {
      if (node.name) set.add(node.name)
      node.keywords.forEach(k => set.add(k.keyword))
      if (node.children.length > 0) traverse(node.children)
    })
  }
  traverse(groups.value)
  return Array.from(set).sort()
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
function detectCycles(nodes: RuleGroup[]): { conflictNodes: RuleGroup[], conflictRelations: { parent_id: number; child_id: number; reason: string }[], hasConflict: boolean } {
  const conflicts: RuleGroup[] = []
  const relations: { parent_id: number; child_id: number; reason: string }[] = []
  const nodeMap = new Map<number, RuleGroup>()
  const conflictIds = new Set<number>()
  const parentMap = new Map<number, Set<number>>()

  const registerConflict = (node: RuleGroup, reason: string) => {
    if (!node.isConflict) {
      node.isConflict = true
      node.conflictReason = reason
    }
    conflictIds.add(node.id)
  }

  // 构建节点映射并重置状态
  const buildMap = (list: RuleGroup[]) => {
    list.forEach(node => {
      nodeMap.set(node.id, node)
      node.isConflict = false
      node.conflictReason = undefined
      buildMap(node.children)
    })
  }
  buildMap(nodes)

  const visit = (node: RuleGroup, ancestors: number[]) => {
    const parentId = ancestors.length > 0 ? ancestors[ancestors.length - 1] : null

    if (parentId !== null) {
      const parents = parentMap.get(node.id) ?? new Set<number>()
      if (parents.size > 0 && !parents.has(parentId)) {
        registerConflict(node, `多父关系（${[...parents, parentId].join(',')}）`)
        relations.push({ parent_id: parentId, child_id: node.id, reason: '多父关系' })
      }
      parents.add(parentId)
      parentMap.set(node.id, parents)
    } else if (!parentMap.has(node.id)) {
      parentMap.set(node.id, new Set<number>())
    }

    if (ancestors.includes(node.id)) {
      if (parentId !== null) {
        const parentNode = nodeMap.get(parentId)
        registerConflict(node, `循环依赖（与节点 ${parentId}）`)
        if (parentNode) {
          registerConflict(parentNode, `循环依赖（与节点 ${node.id}）`)
        }
        relations.push({ parent_id: parentId, child_id: node.id, reason: '循环依赖' })
      }
      return
    }

    ancestors.push(node.id)
    node.children.forEach(child => visit(child, ancestors))
    ancestors.pop()
  }

  nodes.forEach(node => visit(node, []))

  conflictIds.forEach(id => {
    const node = nodeMap.get(id)
    if (node) conflicts.push(node)
  })

  return { conflictNodes: conflicts, conflictRelations: relations, hasConflict: conflicts.length > 0 || relations.length > 0 }
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
    globalStore.setRulesTree(result.data)
    groups.value = result.data.groups

    // 检测循环依赖
    const { conflictNodes: conflicts, conflictRelations: relations } = detectCycles(groups.value)
    conflictNodes.value = conflicts
    conflictRelations.value = relations

    if ((conflicts.length > 0 || relations.length > 0) && !hasShownConflictWarning.value) {
      hasShownConflictWarning.value = true
      toast.error(`⚠️ 检测到 ${relations.length} 条数据冲突，请在规则树底部查看并修复`)
    } else if (conflicts.length === 0 && relations.length === 0) {
      hasShownConflictWarning.value = false
    }

    const hasSavedExpanded = sessionStorage.getItem('bqbq_tree_expanded') !== null
    if (!hasSavedExpanded) {
      expandedIds.value = getAllGroupIds(groups.value)
      globalStore.setExpandedGroupIds([...expandedIds.value])
    } else {
      expandedIds.value = new Set(globalStore.expandedGroupIds)
    }
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
  globalStore.setExpandedGroupIds([...expandedIds.value])
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
  globalStore.setExpandedGroupIds([...expandedIds.value])
}

// 折叠全部
function collapseAll() {
  expandedIds.value.clear()
  globalStore.setExpandedGroupIds([])
}

// 批量启用
async function batchEnableGroups() {
  if (selectedGroupIds.value.size === 0) return
  const selectedCount = selectedGroupIds.value.size

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
    toast.success(`已启用 ${selectedCount} 个规则组`)
    emit('update')
  }
}

// 批量禁用
async function batchDisableGroups() {
  if (selectedGroupIds.value.size === 0) return
  const selectedCount = selectedGroupIds.value.size

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
    toast.success(`已禁用 ${selectedCount} 个规则组`)
    emit('update')
  }
}

// 批量删除
async function batchDeleteGroups() {
  if (selectedGroupIds.value.size === 0) return
  const selectedCount = selectedGroupIds.value.size

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
    toast.success(`已删除 ${selectedCount} 个规则组`)
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

// 删除冲突的层级关系
async function removeConflictHierarchy(parentId: number, childId: number) {
  if (!confirm(`确定要删除这条冲突关系吗？\n(parent_id: ${parentId} → child_id: ${childId})`)) {
    return
  }

  const result = await rulesApi.removeHierarchy(
    childId,
    parentId,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  }
}

// 将冲突节点移到根目录
async function moveConflictNodeToRoot(nodeId: number) {
  if (!confirm(`确定要将节点 ${nodeId} 的所有父关系删除，使其成为根节点吗？`)) {
    return
  }

  const relationsToRemove = conflictRelations.value.filter(rel => rel.child_id === nodeId)
  if (relationsToRemove.length === 0) {
    const result = await rulesApi.moveGroup(
      nodeId,
      null,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
    return
  }

  let latestVersion = globalStore.rulesVersion
  for (const rel of relationsToRemove) {
    const result = await rulesApi.removeHierarchy(
      rel.child_id,
      rel.parent_id,
      globalStore.clientId,
      latestVersion
    )
    if (result.success && result.data) {
      latestVersion = result.data.new_version
    }
  }

  if (latestVersion !== globalStore.rulesVersion) {
    globalStore.updateRulesVersion(latestVersion)
  }
  await loadRulesTree()
  emit('update')
}

// 重命名组
async function handleRenameGroup(groupId: number, name: string) {
  const result = await rulesApi.renameGroup(
    groupId,
    name,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    emit('update')
  } else {
    toast.error('重命名失败')
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
  document.body.classList.add('is-dragging')
}

function handleDragEnd() {
  clearDragState()
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

  clearDragState()
}

async function handleDropOnRoot(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
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

  clearDragState()
}

function handleRootDragOver(e: DragEvent) {
  if (!draggingId.value) return
  e.preventDefault()
  e.stopPropagation()
  rootDropZoneActive.value = true
}

function handleRootDragLeave(e: DragEvent) {
  e.stopPropagation()
  rootDropZoneActive.value = false
}

function clearDragState() {
  draggingId.value = null
  rootDropZoneActive.value = false
  dragOverGapKey.value = null
  document.body.classList.remove('is-dragging')
}

function handleGapDragOver(e: DragEvent, gapKey: string) {
  if (!draggingId.value) return
  e.preventDefault()
  e.stopPropagation()
  dragOverGapKey.value = gapKey
}

function handleGapDragLeave(e: DragEvent) {
  e.stopPropagation()
  dragOverGapKey.value = null
}

async function handleGapDrop(e: DragEvent, parentId: number) {
  e.preventDefault()
  e.stopPropagation()
  dragOverGapKey.value = null
  if (!draggingId.value) return

  const targetParentId = parentId === 0 ? null : parentId
  let dragIds = [draggingId.value]

  if (batchEditMode.value && selectedGroupIds.value.size > 0 && selectedGroupIds.value.has(draggingId.value)) {
    dragIds = Array.from(selectedGroupIds.value)
  }

  if (targetParentId !== null) {
    dragIds = dragIds.filter(id => id !== targetParentId)
  }

  if (dragIds.length === 0) {
    clearDragState()
    return
  }

  if (dragIds.length > 1) {
    const result = await rulesApi.batchMoveHierarchy(
      dragIds,
      targetParentId,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
  } else {
    const result = await rulesApi.moveGroup(
      dragIds[0],
      targetParentId,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    }
  }

  clearDragState()
}

function initRulesTreeScrollSync() {
  const content = scrollContentRef.value
  const container = treeContainerRef.value
  const vScrollbar = vScrollbarRef.value
  const hScrollbar = hScrollbarRef.value
  const vThumb = vThumbRef.value
  const hThumb = hThumbRef.value
  const corner = cornerRef.value

  if (!wrapper || !content || !container || !vScrollbar || !hScrollbar || !vThumb || !hThumb || !corner) {
    return
  }

  const update = () => {
    const contentHeight = container.scrollHeight
    const viewportHeight = content.clientHeight

    if (contentHeight > viewportHeight) {
      vScrollbar.style.display = 'block'
      const trackHeight = vScrollbar.clientHeight
      const thumbHeight = Math.max(30, (viewportHeight / contentHeight) * trackHeight)
      const scrollRatio = content.scrollTop / (contentHeight - viewportHeight)
      const thumbTop = scrollRatio * (trackHeight - thumbHeight)

      vThumb.style.height = `${thumbHeight}px`
      vThumb.style.top = `${thumbTop}px`
    } else {
      vScrollbar.style.display = 'none'
    }

    const contentWidth = content.scrollWidth
    const viewportWidth = content.clientWidth

    if (contentWidth > viewportWidth) {
      hScrollbar.style.display = 'block'
      const trackWidth = hScrollbar.clientWidth
      const thumbWidth = Math.max(30, (viewportWidth / contentWidth) * trackWidth)
      const scrollRatio = content.scrollLeft / (contentWidth - viewportWidth)
      const thumbLeft = scrollRatio * (trackWidth - thumbWidth)

      hThumb.style.width = `${thumbWidth}px`
      hThumb.style.left = `${thumbLeft}px`
    } else {
      hScrollbar.style.display = 'none'
    }

    corner.style.display = (vScrollbar.style.display !== 'none' && hScrollbar.style.display !== 'none') ? 'block' : 'none'
  }

  updateScrollbars = update

  const onScroll = () => update()
  content.addEventListener('scroll', onScroll)

  const resizeObserver = new ResizeObserver(update)
  resizeObserver.observe(container)
  resizeObserver.observe(content)

  const timeoutId = window.setTimeout(update, 100)

  const setupDrag = (thumb: HTMLDivElement, scrollbar: HTMLDivElement, isVertical: boolean) => {
    let startPos = 0
    let startScroll = 0

    const onPointerDown = (e: PointerEvent) => {
      e.preventDefault()
      thumb.setPointerCapture(e.pointerId)
      thumb.classList.add('dragging')

      startPos = isVertical ? e.clientY : e.clientX
      startScroll = isVertical ? content.scrollTop : content.scrollLeft
    }

    const onPointerMove = (e: PointerEvent) => {
      if (!thumb.hasPointerCapture(e.pointerId)) return

      const currentPos = isVertical ? e.clientY : e.clientX
      const delta = currentPos - startPos
      const trackSize = isVertical ? scrollbar.clientHeight : scrollbar.clientWidth
      const thumbSize = isVertical ? thumb.offsetHeight : thumb.offsetWidth
      const contentSize = isVertical ? container.scrollHeight : container.scrollWidth
      const viewportSize = isVertical ? content.clientHeight : content.clientWidth

      const scrollRange = contentSize - viewportSize
      const trackRange = trackSize - thumbSize
      const scrollDelta = (delta / trackRange) * scrollRange

      if (isVertical) {
        content.scrollTop = startScroll + scrollDelta
      } else {
        content.scrollLeft = startScroll + scrollDelta
      }
    }

    const onPointerUp = (e: PointerEvent) => {
      if (thumb.hasPointerCapture(e.pointerId)) {
        thumb.releasePointerCapture(e.pointerId)
      }
      thumb.classList.remove('dragging')
    }

    const onPointerCancel = (e: PointerEvent) => {
      if (thumb.hasPointerCapture(e.pointerId)) {
        thumb.releasePointerCapture(e.pointerId)
      }
      thumb.classList.remove('dragging')
    }

    const onTrackPointerDown = (e: PointerEvent) => {
      if (e.target === thumb) return

      const rect = scrollbar.getBoundingClientRect()
      const clickPos = isVertical ? (e.clientY - rect.top) : (e.clientX - rect.left)
      const trackSize = isVertical ? scrollbar.clientHeight : scrollbar.clientWidth
      const thumbSize = isVertical ? thumb.offsetHeight : thumb.offsetWidth
      const contentSize = isVertical ? container.scrollHeight : container.scrollWidth
      const viewportSize = isVertical ? content.clientHeight : content.clientWidth

      const scrollRange = contentSize - viewportSize
      const targetScroll = ((clickPos - thumbSize / 2) / (trackSize - thumbSize)) * scrollRange

      if (isVertical) {
        content.scrollTop = Math.max(0, Math.min(scrollRange, targetScroll))
      } else {
        content.scrollLeft = Math.max(0, Math.min(scrollRange, targetScroll))
      }
    }

    thumb.addEventListener('pointerdown', onPointerDown)
    thumb.addEventListener('pointermove', onPointerMove)
    thumb.addEventListener('pointerup', onPointerUp)
    thumb.addEventListener('pointercancel', onPointerCancel)
    scrollbar.addEventListener('pointerdown', onTrackPointerDown)

    return () => {
      thumb.removeEventListener('pointerdown', onPointerDown)
      thumb.removeEventListener('pointermove', onPointerMove)
      thumb.removeEventListener('pointerup', onPointerUp)
      thumb.removeEventListener('pointercancel', onPointerCancel)
      scrollbar.removeEventListener('pointerdown', onTrackPointerDown)
    }
  }

  const cleanupV = setupDrag(vThumb, vScrollbar, true)
  const cleanupH = setupDrag(hThumb, hScrollbar, false)

  cleanupScrollSync = () => {
    content.removeEventListener('scroll', onScroll)
    resizeObserver.disconnect()
    window.clearTimeout(timeoutId)
    cleanupV()
    cleanupH()
  }
}

// 关闭面板
function close() {
  emit('close')
}

function clearTreeSearch() {
  searchText.value = ''
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
watch(() => props.visible, async (visible) => {
  if (visible) {
    await loadRulesTree()
    await nextTick()
    updateScrollbars?.()
  }
})

watch(filteredGroups, async () => {
  await nextTick()
  updateScrollbars?.()
})

// 初始化
onMounted(() => {
  if (props.visible) {
    loadRulesTree()
  }
  if (globalStore.expandedGroupIds.length > 0) {
    expandedIds.value = new Set(globalStore.expandedGroupIds)
  }
  initRulesTreeScrollSync()
})

onBeforeUnmount(() => {
  cleanupScrollSync?.()
  document.body.classList.remove('is-dragging')
})

</script>

<template>
  <Teleport to="body">
    <aside
      id="rules-tree-panel"
      :class="[
        'fixed top-16 left-0 w-72 bg-white border-r border-slate-200/50 z-40 transform transition-transform duration-300 shadow-xl overflow-hidden pl-5 pr-2 pt-2 pb-2',
        visible ? 'translate-x-0' : '-translate-x-full'
      ]"
      style="height: calc(100vh - 8rem);"
    >
      <div class="h-full flex flex-col">
        <div id="rules-panel-header" class="flex items-center justify-between pt-2 pb-3 shrink-0">
          <h3 id="rules-panel-title" class="text-lg font-bold text-slate-700">🌳 同义词规则</h3>
          <div class="flex items-center gap-2">
            <span id="rules-version-info" class="text-xs text-slate-400" title="当前本地规则版本号">v{{ globalStore.rulesVersion }}</span>
            <button
              id="refresh-rules-btn"
              class="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
              title="刷新规则树（强制从服务器重新加载）"
              :class="{ 'animate-spin': isLoading }"
              @click="loadRulesTree"
            >
              <RefreshCw class="w-4 h-4" />
            </button>
          </div>
        </div>

        <div id="rules-search-container" class="pb-3 relative shrink-0">
          <input
            id="rules-tree-search"
            v-model="searchText"
            list="tree-suggestions"
            type="text"
            placeholder="🔍 搜索组/关键词..."
            class="w-full px-3 py-2 pr-8 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-200 focus:border-green-400"
            title="在同义词规则树中搜索组名或关键词"
          />
          <button
            id="rules-tree-search-clear"
            :class="['absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 transition', searchText ? '' : 'hidden']"
            title="清空搜索"
            @click="clearTreeSearch"
          >
            <X class="w-4 h-4" />
          </button>
          <datalist id="tree-suggestions">
            <option v-for="item in treeSuggestions" :key="item" :value="item" />
          </datalist>
        </div>

        <div id="batch-edit-toolbar" class="p-2 bg-blue-50 border border-blue-200 rounded-lg flex flex-col gap-1.5 shrink-0">
          <div class="flex gap-1.5 items-center">
            <button id="batch-mode-btn" class="px-2 py-1 text-xs bg-white text-blue-600 border border-blue-300 rounded hover:bg-blue-100 transition" title="进入/退出批量编辑模式" @click="toggleBatchMode">批量</button>
            <button id="expand-all-btn" class="px-2 py-1 text-xs bg-white text-slate-600 border border-slate-300 rounded hover:bg-slate-100 transition" title="展开全部" @click="expandAll">展开</button>
            <button id="collapse-all-btn" class="px-2 py-1 text-xs bg-white text-slate-600 border border-slate-300 rounded hover:bg-slate-100 transition" title="折叠全部" @click="collapseAll">折叠</button>
            <button id="add-root-group-btn" class="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition" title="添加新组" @click="startAddRootGroup">新组</button>
          </div>
          <div
            id="batch-actions-row"
            :class="[batchEditMode ? 'flex' : 'hidden', 'flex gap-1.5 items-center']"
          >
            <button id="batch-select-all" class="px-2 py-1 text-xs bg-white text-blue-600 border border-blue-300 rounded hover:bg-blue-100 transition" title="全选/取消全选" @click="toggleSelectAll">全选</button>
            <button id="batch-enable-btn" class="px-2 py-1 text-xs bg-emerald-500 text-white rounded hover:bg-emerald-600 transition" title="批量启用" @click="batchEnableGroups">启用</button>
            <button id="batch-disable-btn" class="px-2 py-1 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600 transition" title="批量禁用" @click="batchDisableGroups">禁用</button>
            <button id="batch-delete-btn" class="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition" title="批量删除" @click="batchDeleteGroups">删除</button>
            <span id="batch-selected-info" class="text-xs text-blue-700 font-medium">已选(<span id="batch-selected-count" class="font-bold">{{ selectedGroupIds.size }}</span>)</span>
          </div>
        </div>

        <div id="rules-tree-scroll-wrapper" class="flex-1 min-h-0 -ml-5 -mr-2 -mb-2 border-t border-slate-200 bg-slate-50/30">
          <div
            id="rules-tree-content"
            ref="scrollContentRef"
            class="h-full overflow-auto"
          >
            <div id="rules-tree-container" ref="treeContainerRef" class="space-y-2 p-3">
              <div
                v-if="filteredGroups.length > 0"
                :class="['root-drop-zone', rootDropZoneActive ? 'drag-over' : '', draggingId ? '' : 'hidden']"
                @dragover="handleRootDragOver"
                @dragleave="handleRootDragLeave"
                @drop="handleDropOnRoot"
              >
                <span class="text-xs">📁 移至根目录</span>
              </div>

              <div v-if="showRootInput" class="new-group-editor mb-2 p-2 bg-white border border-blue-300 rounded-lg shadow-md flex flex-col gap-2">
                <input
                  v-model="newGroupName"
                  type="text"
                  placeholder="输入新组名..."
                  class="w-full p-2 border border-slate-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-blue-400"
                  autofocus
                  @keydown.enter="confirmAddGroup"
                  @keydown.escape="cancelAdd"
                  @blur="confirmAddGroup"
                />
                <div class="flex justify-end gap-2">
                  <button class="px-3 py-1 text-xs bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition" @click="cancelAdd">取消</button>
                  <button class="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition" @click="confirmAddGroup">创建</button>
                </div>
              </div>

              <div v-if="filteredGroups.length === 0 && !isLoading" class="text-sm text-slate-400 text-center mt-4">
                暂无规则数据。
              </div>

              <template v-for="group in filteredGroups" :key="group.id">
                <div
                  :class="['drop-gap', dragOverGapKey === `gap-0-${group.id}` ? 'drag-over' : '']"
                  @dragover="handleGapDragOver($event, `gap-0-${group.id}`)"
                  @dragleave="handleGapDragLeave"
                  @drop="handleGapDrop($event, 0)"
                ></div>
                <RuleGroupNode
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
                  :drag-over-gap-key="dragOverGapKey"
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
                  @drop-on-gap="handleGapDrop"
                  @gap-drag-over="handleGapDragOver"
                  @gap-drag-leave="handleGapDragLeave"
                  @rename-group="handleRenameGroup"
                />
              </template>
              <div
                v-if="filteredGroups.length > 0"
                :class="['drop-gap', dragOverGapKey === 'gap-0-end' ? 'drag-over' : '']"
                @dragover="handleGapDragOver($event, 'gap-0-end')"
                @dragleave="handleGapDragLeave"
                @drop="handleGapDrop($event, 0)"
              ></div>

              <div v-if="conflictNodes.length > 0 || conflictRelations.length > 0">
                <div class="my-4 border-t-2 border-red-300"></div>
                <div class="flex items-center gap-2 p-2 bg-red-100 rounded-lg mb-2">
                  <AlertTriangle class="w-5 h-5 text-red-600" />
                  <span class="font-bold text-red-700">⚠️ 检测到数据冲突 ({{ conflictNodes.length }} 个节点, {{ conflictRelations.length }} 条关系)</span>
                </div>

                <div v-if="conflictRelations.length > 0" class="mb-3 p-2 bg-red-50 rounded border border-red-200">
                  <div class="text-sm font-bold text-red-700 mb-2">冲突的层级关系：</div>
                  <div
                    v-for="rel in conflictRelations"
                    :key="`${rel.parent_id}-${rel.child_id}`"
                    class="flex items-center justify-between p-2 mb-1 bg-white rounded border border-red-200 text-sm"
                  >
                    <span class="text-red-800">
                      <span class="font-mono bg-red-100 px-1 rounded">parent_id: {{ rel.parent_id }}</span>
                      →
                      <span class="font-mono bg-red-100 px-1 rounded">child_id: {{ rel.child_id }}</span>
                      <br />
                      <span class="text-red-600 text-xs">{{ rel.reason }}</span>
                    </span>
                    <button
                      class="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition whitespace-nowrap"
                      @click="removeConflictHierarchy(rel.parent_id, rel.child_id)"
                    >
                      <Trash2 class="w-3 h-3 inline" />
                      删除此关系
                    </button>
                  </div>
                </div>

                <div v-if="conflictNodes.length > 0" class="p-2 bg-red-50 rounded border border-red-200">
                  <div class="text-sm font-bold text-red-700 mb-2">受影响的节点：</div>
                  <div
                    v-for="node in conflictNodes"
                    :key="node.id"
                    class="flex items-center justify-between p-2 mb-1 bg-white rounded border border-red-200"
                  >
                    <div class="flex items-center gap-2">
                      <FolderX class="w-4 h-4 text-red-500" />
                      <span class="font-bold text-red-800">{{ node.name || '[空名组]' }}</span>
                      <span class="text-xs text-red-500 bg-red-100 px-1 rounded">ID: {{ node.id }}</span>
                      <span class="text-xs text-red-600">{{ node.conflictReason || '' }}</span>
                    </div>
                    <div class="flex gap-1">
                      <button
                        class="px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition"
                        @click="moveConflictNodeToRoot(node.id)"
                      >
                        <Home class="w-3 h-3 inline" />
                        移到根目录
                      </button>
                      <button
                        class="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition"
                        @click="deleteGroup(node)"
                      >
                        <Trash2 class="w-3 h-3 inline" />
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div ref="vScrollbarRef" class="custom-scrollbar-v">
            <div class="scrollbar-track"></div>
            <div ref="vThumbRef" class="scrollbar-thumb"></div>
          </div>
          <div ref="hScrollbarRef" class="custom-scrollbar-h">
            <div class="scrollbar-track"></div>
            <div ref="hThumbRef" class="scrollbar-thumb"></div>
          </div>
          <div ref="cornerRef" class="scrollbar-corner"></div>
        </div>
      </div>
    </aside>

    <button
      id="rules-panel-toggle-btn"
      class="fixed top-16 z-50 w-5 hover:w-6 bg-gradient-to-r from-slate-50 to-white hover:from-slate-100 hover:to-slate-50 text-slate-400 hover:text-slate-600 border-r border-y border-slate-200 hover:border-slate-300 rounded-r-md shadow-md hover:shadow-lg transition-all duration-300 flex items-center justify-center group"
      :style="{ left: visible ? '288px' : '0px', height: 'calc(100vh - 4rem - 4rem)' }"
      :title="visible ? '关闭同义词规则侧边栏' : '打开同义词规则侧边栏'"
      @click="emit('toggle')"
    >
      <ChevronLeft v-if="visible" class="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
      <ChevronRight v-else class="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
    </button>
  </Teleport>
</template>
