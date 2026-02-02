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

// 批量编辑状态（旧版支持）
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
const isHandlingHierarchyChange = ref(false)
const touchDropTargetId = ref<number | null>(null)
const touchDragPointerId = ref<number | null>(null)
const touchDragActive = ref(false)
const touchDragMoved = ref(false)
const touchDragStartX = ref(0)
const touchDragStartY = ref(0)
const touchDragTimer = ref<number | null>(null)
const touchDragJustEnded = ref(false)
const touchDragSourceEl = ref<HTMLElement | null>(null)
let touchListenersAttached = false

// 自定义滚动条 refs
const scrollContentRef = ref<HTMLDivElement | null>(null)
const vScrollbarRef = ref<HTMLDivElement | null>(null)
const hScrollbarRef = ref<HTMLDivElement | null>(null)
const vThumbRef = ref<HTMLDivElement | null>(null)
const hThumbRef = ref<HTMLDivElement | null>(null)
const cornerRef = ref<HTMLDivElement | null>(null)

// 树容器 ref（用于滚动到匹配项）
const treeContainerRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

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

function applyRulesTree(tree: RuleGroup[] | null, hierarchy?: { parent_id: number; child_id: number }[]) {
  if (!tree) return
  groups.value = tree

  // 检测冲突/循环（优先使用旧项目层级关系）
  const legacyHierarchy = hierarchy
  const conflictResult = Array.isArray(legacyHierarchy)
    ? detectLegacyConflicts(groups.value, legacyHierarchy)
    : detectCycles(groups.value)
  const { conflictNodes: conflicts, conflictRelations: relations } = conflictResult
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

// 清除匹配标记
function clearMatchFlags(nodes: RuleGroup[]) {
  nodes.forEach(node => {
    node.isMatch = false
    clearMatchFlags(node.children)
  })
}

// 过滤树并标记匹配（包含空名组匹配逻辑）
function filterTree(nodes: RuleGroup[], search: string): RuleGroup[] {
  const emptyKeywords = ['空', '无名', 'empty', '空组', '无名组']
  return nodes.reduce<RuleGroup[]>((acc, node) => {
    const nodeName = node.name || ''
    const isEmptyNameGroup = !nodeName || nodeName.trim() === ''
    const emptyGroupMatch = isEmptyNameGroup
      ? emptyKeywords.some(keyword => keyword.includes(search) || search.includes(keyword))
      : false
    const nameMatch = nodeName.toLowerCase().includes(search)
    const keywordMatch = node.keywords.some(k => k.keyword.toLowerCase().includes(search))
    const filteredChildren = filterTree(node.children, search)

    if (nameMatch || keywordMatch || emptyGroupMatch || filteredChildren.length > 0) {
      acc.push({
        ...node,
        isMatch: nameMatch || keywordMatch || emptyGroupMatch,
        children: filteredChildren,
      })
    }
    return acc
  }, [])
}

function expandMatches(nodes: RuleGroup[], search: string, expanded: Set<number>, ancestors: number[] = []) {
  const emptyKeywords = ['空', '无名', 'empty', '空组', '无名组']
  nodes.forEach(node => {
    const nodeName = node.name || ''
    const isEmptyNameGroup = !nodeName || nodeName.trim() === ''
    const emptyGroupMatch = isEmptyNameGroup
      ? emptyKeywords.some(keyword => keyword.includes(search) || search.includes(keyword))
      : false
    const nameMatch = nodeName.toLowerCase().includes(search)
    const keywordMatch = node.keywords.some(k => k.keyword.toLowerCase().includes(search))
    const nextAncestors = [...ancestors, node.id]

    if (nameMatch || keywordMatch || emptyGroupMatch) {
      expanded.add(node.id)
      ancestors.forEach(id => expanded.add(id))
    }

    if (node.children.length > 0) {
      expandMatches(node.children, search, expanded, nextAncestors)
    }
  })
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
    const parentId = ancestors.length > 0 ? ancestors[ancestors.length - 1]! : null

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

function detectLegacyConflicts(
  nodes: RuleGroup[],
  hierarchy: { parent_id: number; child_id: number }[]
): { conflictNodes: RuleGroup[], conflictRelations: { parent_id: number; child_id: number; reason: string }[], hasConflict: boolean } {
  const conflicts: RuleGroup[] = []
  const relations: { parent_id: number; child_id: number; reason: string }[] = []
  const nodeMap = new Map<number, RuleGroup>()

  const buildMap = (list: RuleGroup[]) => {
    list.forEach(node => {
      nodeMap.set(node.id, node)
      node.isConflict = false
      node.conflictReason = undefined
      buildMap(node.children)
    })
  }
  buildMap(nodes)

  const adjacency = new Map<number, number[]>()

  const detectCycle = (startId: number, targetId: number, visited = new Set<number>()) => {
    if (startId === targetId) return true
    if (visited.has(startId)) return false
    visited.add(startId)
    const children = adjacency.get(startId) ?? []
    for (const childId of children) {
      if (detectCycle(childId, targetId, visited)) return true
    }
    return false
  }

  hierarchy.forEach(rel => {
    if (!rel) return
    const parentId = rel.parent_id
    const childId = rel.child_id
    const parent = nodeMap.get(parentId)
    const child = nodeMap.get(childId)

    if (!parent || !child) {
      const reason = `节点不存在: ${!parent ? 'parent_id=' + parentId : ''} ${!child ? 'child_id=' + childId : ''}`
      relations.push({ parent_id: parentId, child_id: childId, reason })
      return
    }

    if (parentId === childId) {
      relations.push({
        parent_id: parentId,
        child_id: childId,
        reason: `自引用: 节点 ${parentId} 不能作为自己的父节点`,
      })
      child.isConflict = true
      child.conflictReason = '自引用'
      return
    }

    if (detectCycle(childId, parentId, new Set<number>())) {
      relations.push({
        parent_id: parentId,
        child_id: childId,
        reason: `循环依赖: ${childId} → ${parentId} 会形成环路`,
      })
      parent.isConflict = true
      parent.conflictReason = `循环依赖（与节点 ${childId}）`
      child.isConflict = true
      child.conflictReason = `循环依赖（与节点 ${parentId}）`
      return
    }

    const children = adjacency.get(parentId) ?? []
    children.push(childId)
    adjacency.set(parentId, children)
  })

  nodeMap.forEach((node) => {
    if (node.isConflict) conflicts.push(node)
  })

  return { conflictNodes: conflicts, conflictRelations: relations, hasConflict: conflicts.length > 0 || relations.length > 0 }
}

async function loadRulesTree() {
  isLoading.value = true
  const result = await rulesApi.getRulesTree(globalStore.rulesVersion)

  if (result.notModified) {
    const cached = globalStore.rulesTree || globalStore.loadRulesTreeCache()
    if (cached) {
      applyRulesTree(cached.groups, cached.hierarchy)
      isLoading.value = false
      return
    }
    const fresh = await rulesApi.getRulesTree()
    if (fresh.success && fresh.data) {
      globalStore.setRulesTree(fresh.data)
      applyRulesTree(fresh.data.groups, fresh.data.hierarchy)
    }
    isLoading.value = false
    return
  }

  if (result.success && result.data) {
    globalStore.setRulesTree(result.data)
    applyRulesTree(result.data.groups, result.data.hierarchy)
  }
  isLoading.value = false
}

// 刷新规则树（旧版：提示+强制拉取最新数据）
async function refreshRulesTree() {
  isLoading.value = true
  toast.info('正在刷新规则树...')
  globalStore.updateRulesVersion(0)
  globalStore.clearRulesTreeCache()
  hasShownConflictWarning.value = false

  try {
    const result = await rulesApi.getRulesTree()
    if (result.success && result.data) {
      globalStore.setRulesTree(result.data)
      applyRulesTree(result.data.groups, result.data.hierarchy)
      toast.success('规则树已刷新')
    } else {
      toast.error('刷新失败，请重试')
    }
  } catch (error) {
    console.error('刷新规则树失败:', error)
    toast.error('刷新失败，请重试')
  } finally {
    isLoading.value = false
  }
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

// 切换组选中
function toggleGroupSelection(groupId: number) {
  const newSet = new Set(selectedGroupIds.value)
  if (newSet.has(groupId)) {
    newSet.delete(groupId)
  } else {
    newSet.add(groupId)
  }
  selectedGroupIds.value = newSet
}

// 批量编辑模式
// 切换组选择
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

// 全选/取消全选
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
  if (selectedGroupIds.value.size === 0) {
    toast.error('请先选择要操作的组')
    return
  }
  const selectedCount = selectedGroupIds.value.size

  if (!confirm(`确定要启用选中的 ${selectedCount} 个组吗？`)) return

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
    const affected = result.data.affected_count ?? selectedCount
    toast.success(`已启用 ${affected} 个组`)
    emit('update')
  }
}

// 批量禁用
async function batchDisableGroups() {
  if (selectedGroupIds.value.size === 0) {
    toast.error('请先选择要操作的组')
    return
  }
  const selectedCount = selectedGroupIds.value.size

  if (!confirm(`确定要禁用选中的 ${selectedCount} 个组吗？`)) return

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
    const affected = result.data.affected_count ?? selectedCount
    toast.success(`已禁用 ${affected} 个组`)
    emit('update')
  }
}

// 批量删除
async function batchDeleteGroups() {
  if (selectedGroupIds.value.size === 0) {
    toast.error('请先选择要删除的组')
    return
  }
  const selectedCount = selectedGroupIds.value.size

  if (!confirm(`确定要彻底删除选中的 ${selectedCount} 个组吗？\n\n⚠️ 此操作将递归删除所有子组和关键词，无法撤销！`)) return

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
    const affected = result.data.affected_count ?? selectedCount
    toast.success(`已删除 ${affected} 个组`)
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
    const displayName = group.name || '[无名组]'
    const actionText = group.enabled ? '禁用' : '启用'
    toast.success(`组「${displayName}」已${actionText}`)
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
    toast.error('组名不能为空！')
    cancelAdd()
    return
  }

  const parentId = showRootInput.value ? null : addingGroupParentId.value

  const result = await rulesApi.createGroup(
    name,
    null,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    if (parentId !== null) {
      const hierarchyResult = await rulesApi.addHierarchy(
        result.data.id,
        parentId,
        globalStore.clientId,
        globalStore.rulesVersion
      )
      if (hierarchyResult.success && hierarchyResult.data) {
        globalStore.updateRulesVersion(hierarchyResult.data.new_version)
        await loadRulesTree()
        toast.success(`子组「${name}」已创建`)
        emit('update')
      } else {
        await loadRulesTree()
        toast.error('建立关系失败')
        emit('update')
      }
    } else {
      await loadRulesTree()
      toast.success(`已创建组: ${name}`)
      emit('update')
    }
  } else {
    toast.error('创建组失败')
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
  const target = findGroupById(groups.value, group.id)
  if (!target) {
    toast.error('组不存在')
    return
  }

  const descendantCount = countDescendants(target)
  const displayName = target.name || '[无名组]'
  const confirmMsg = descendantCount > 0
    ? `确定要彻底删除组「${displayName}」吗？\n\n这将同时删除其 ${descendantCount} 个子组及所有关键词。\n此操作无法撤销！`
    : `确定要彻底删除组「${displayName}」吗？\n\n此操作无法撤销！`

  if (!confirm(confirmMsg)) return

  const result = await rulesApi.deleteGroup(
    group.id,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.new_version)
    await loadRulesTree()
    const deletedCount = result.data.deleted_count ?? 1
    toast.success(`已删除 ${deletedCount} 个组`)
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
    toast.success('冲突关系已删除')
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
    toast.info('未找到需要删除的父关系')
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
  toast.success(`已删除 ${relationsToRemove.length} 条父关系，节点已移到根目录`)
  emit('update')
}

function findGroupById(nodes: RuleGroup[], id: number): RuleGroup | null {
  for (const node of nodes) {
    if (node.id === id) return node
    const found = findGroupById(node.children, id)
    if (found) return found
  }
  return null
}

function countDescendants(node: RuleGroup): number {
  let count = 0
  if (node.children && node.children.length > 0) {
    count = node.children.length
    node.children.forEach(child => {
      count += countDescendants(child)
    })
  }
  return count
}

// 重命名组
async function handleRenameGroup(groupId: number, name: string) {
  const target = findGroupById(groups.value, groupId)
  const enabled = target ? target.enabled : true
  const result = await rulesApi.renameGroup(
    groupId,
    name,
    enabled,
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
async function deleteKeyword(keyword: RuleKeyword) {
  if (!confirm(`确定要从该组移除关键词 "${keyword.keyword}" 吗?`)) {
    return
  }
  const result = await rulesApi.deleteKeyword(
    keyword.group_id,
    keyword.keyword,
    globalStore.clientId,
    globalStore.rulesVersion
  )

  if (result.success && result.data) {
    globalStore.updateRulesVersion(result.data.version_id)
    await loadRulesTree()
    toast.success(`关键词 "${keyword.keyword}" 已移除。`)
    emit('update')
  }
}

// 切换关键词启用状态（旧项目不支持）
async function toggleKeywordEnabled() {
  return
}

// 拖拽事件处理
function handleDragStart(groupId: number) {
  draggingId.value = groupId
  document.body.classList.add('is-dragging')
}

function handleDragEnd() {
  clearDragState()
}

function buildParentMap(nodes: RuleGroup[]) {
  const parentMap = new Map<number, number[]>()
  const visited = new Set<number>()

  const walk = (list: RuleGroup[], parent: RuleGroup | null) => {
    list.forEach(node => {
      if (parent) {
        const parents = parentMap.get(node.id) ?? []
        parents.push(parent.id)
        parentMap.set(node.id, parents)
      }
      if (visited.has(node.id)) return
      visited.add(node.id)
      if (node.children.length > 0) {
        walk(node.children, node)
      }
    })
  }

  walk(nodes, null)
  return parentMap
}

function wouldCreateCycle(parentId: number | null, childId: number) {
  if (!parentId || parentId === 0) return false
  if (parentId === childId) return true

  const parentMap = buildParentMap(groups.value)
  const visited = new Set<number>()
  const stack = [parentId]

  while (stack.length > 0) {
    const current = stack.pop()!
    if (current === childId) return true
    if (visited.has(current)) continue
    visited.add(current)
    const parents = parentMap.get(current) ?? []
    parents.forEach(pid => stack.push(pid))
  }
  return false
}

function getDragIds(): number[] {
  if (!draggingId.value) return []
  if (batchEditMode.value && selectedGroupIds.value.size > 0 && selectedGroupIds.value.has(draggingId.value)) {
    return Array.from(selectedGroupIds.value)
  }
  return [draggingId.value]
}

async function handleHierarchyMove(targetParentId: number | null, dragIds: number[]) {
  if (isHandlingHierarchyChange.value) return
  if (dragIds.length === 0) return

  const normalizedParentId = targetParentId ?? 0
  let ids = Array.from(new Set(dragIds)).filter(id => id)
  if (normalizedParentId !== 0) {
    ids = ids.filter(id => id !== normalizedParentId)
  }
  if (ids.length === 0) {
    if (normalizedParentId !== 0 && dragIds.includes(normalizedParentId)) {
      toast.error('无法将组拖拽到自身。')
    }
    clearDragState()
    return
  }

  const cycleErrors = ids.filter(id => wouldCreateCycle(normalizedParentId, id))
  if (cycleErrors.length > 0) {
    toast.error(`❌ 无法移动：${cycleErrors.length} 个组会形成循环依赖！`)
    console.error('[handleBatchHierarchyChange] 循环检测失败的节点:', cycleErrors)
    clearDragState()
    return
  }

  isHandlingHierarchyChange.value = true

  let previousSelected: Set<number> | null = null
  if (batchEditMode.value && selectedGroupIds.value.size > 0) {
    previousSelected = new Set(selectedGroupIds.value)
    selectedGroupIds.value.clear()
  }

  toast.info(`正在移动 ${ids.length} 个组...`)

  try {
    const result = await rulesApi.batchMoveHierarchy(
      ids,
      normalizedParentId === 0 ? null : normalizedParentId,
      globalStore.clientId,
      globalStore.rulesVersion
    )

    if (result.data) {
      const moved = result.data.moved ?? ids.length
      const errors = Array.isArray(result.data.errors) ? result.data.errors : []

      if (result.success) {
        if (errors.length === 0) {
          toast.success(`已移动 ${moved} 个组`)
        } else {
          toast.warning(`移动完成：${moved} 成功，${errors.length} 失败`)
          console.log('[handleBatchHierarchyChange] 部分失败:', errors)
        }
      } else if (errors.length > 0) {
        const allCycle = errors.every((err: any) => err?.error === 'Would create cycle')
        toast.error(allCycle ? '❌ 移动失败：会形成循环依赖' : `❌ 移动失败：${errors.length} 个错误`)
        console.error('[handleBatchHierarchyChange] 全部失败:', errors)
      }
    }

    if (result.success && result.data) {
      globalStore.updateRulesVersion(result.data.new_version)
      await loadRulesTree()
      emit('update')
    } else if (!result.success && previousSelected) {
      selectedGroupIds.value = new Set(previousSelected)
    }
  } catch (error) {
    console.error('[handleBatchHierarchyChange] 请求失败:', error)
    toast.error('网络错误，请重试')
    if (previousSelected) {
      selectedGroupIds.value = new Set(previousSelected)
    }
  } finally {
    isHandlingHierarchyChange.value = false
    clearDragState()
  }
}

async function handleDropOnGroup(targetGroupId: number) {
  if (!draggingId.value) return
  const dragIds = getDragIds()
  await handleHierarchyMove(targetGroupId, dragIds)
}

async function handleDropOnRoot(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  if (!draggingId.value) return
  const dragIds = getDragIds()
  await handleHierarchyMove(null, dragIds)
}

function handleRootDragOver(e: DragEvent) {
  if (!draggingId.value) return
  e.preventDefault()
  e.stopPropagation()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  applyDropHighlight({ type: 'root' })
}

function handleRootDragLeave(e: DragEvent) {
  e.stopPropagation()
  applyDropHighlight({ type: 'none' })
}

function clearDragState() {
  draggingId.value = null
  applyDropHighlight({ type: 'none' })
  document.body.classList.remove('is-dragging')
}

function handleGapDragOver(e: DragEvent, gapKey: string) {
  if (!draggingId.value) return
  e.preventDefault()
  e.stopPropagation()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  applyDropHighlight({ type: 'gap', parentId: 0, gapKey })
}

function handleGapDragLeave(e: DragEvent) {
  e.stopPropagation()
  applyDropHighlight({ type: 'none' })
}

async function handleGapDrop(e: DragEvent, parentId: number) {
  e.preventDefault()
  e.stopPropagation()
  dragOverGapKey.value = null
  if (!draggingId.value) return

  const targetParentId = parentId === 0 ? null : parentId
  const dragIds = getDragIds()
  await handleHierarchyMove(targetParentId, dragIds)
}

type TouchDropTarget =
  | { type: 'root' }
  | { type: 'gap'; parentId: number; gapKey: string }
  | { type: 'group'; groupId: number }
  | { type: 'none' }

const TOUCH_LONG_PRESS_MS = 220
const TOUCH_MOVE_THRESHOLD = 6

function clearTouchDragTimer() {
  if (touchDragTimer.value) {
    window.clearTimeout(touchDragTimer.value)
    touchDragTimer.value = null
  }
}

function resetTouchDragState(clearDrag = false) {
  clearTouchDragTimer()
  touchDragPointerId.value = null
  touchDragActive.value = false
  touchDragMoved.value = false
  touchDragSourceEl.value = null
  touchDropTargetId.value = null
  if (clearDrag) {
    applyDropHighlight({ type: 'none' })
  }
}

function shouldIgnoreTouchTarget(target: HTMLElement) {
  if (target.closest('button, input, textarea, select, [contenteditable="true"]')) return true
  if (target.closest('.rule-action-btn, .batch-checkbox-wrapper, .batch-checkbox, .group-editor-wrapper, .keyword-add-input-wrapper')) {
    return true
  }
  return false
}

function resolveTouchDropTarget(x: number, y: number): TouchDropTarget {
  const el = document.elementFromPoint(x, y) as HTMLElement | null
  if (!el) return { type: 'none' }

  const rootEl = el.closest('.root-drop-zone') as HTMLElement | null
  if (rootEl) {
    return { type: 'root' }
  }

  const gapEl = el.closest('.drop-gap') as HTMLElement | null
  if (gapEl && gapEl.dataset.gapKey) {
    const parentId = Number(gapEl.dataset.gapParent ?? '')
    if (!Number.isNaN(parentId)) {
      return { type: 'gap', parentId, gapKey: gapEl.dataset.gapKey }
    }
  }

  const groupEl = el.closest('.group-node') as HTMLElement | null
  if (groupEl) {
    const groupId = Number(groupEl.dataset.id ?? '')
    if (!Number.isNaN(groupId)) {
      return { type: 'group', groupId }
    }
  }

  return { type: 'none' }
}

function applyDropHighlight(target: TouchDropTarget) {
  if (target.type === 'root') {
    rootDropZoneActive.value = true
    dragOverGapKey.value = null
    touchDropTargetId.value = null
    return
  }
  if (target.type === 'gap') {
    rootDropZoneActive.value = false
    dragOverGapKey.value = target.gapKey
    touchDropTargetId.value = null
    return
  }
  if (target.type === 'group') {
    rootDropZoneActive.value = false
    dragOverGapKey.value = null
    touchDropTargetId.value = target.groupId
    return
  }
  rootDropZoneActive.value = false
  dragOverGapKey.value = null
  touchDropTargetId.value = null
}

function startTouchDrag(groupId: number, pointerId: number, sourceEl: HTMLElement) {
  touchDragActive.value = true
  touchDragPointerId.value = pointerId
  touchDragMoved.value = false
  draggingId.value = groupId
  document.body.classList.add('is-dragging')
  try {
    sourceEl.setPointerCapture(pointerId)
  } catch {
    // ignore pointer capture failures
  }
}

function attachTouchListeners() {
  if (touchListenersAttached) return
  touchListenersAttached = true
  document.addEventListener('pointermove', handleTouchPointerMove, { passive: false })
  document.addEventListener('pointerup', handleTouchPointerUp, { passive: false })
  document.addEventListener('pointercancel', handleTouchPointerCancel, { passive: false })
}

function detachTouchListeners() {
  if (!touchListenersAttached) return
  touchListenersAttached = false
  document.removeEventListener('pointermove', handleTouchPointerMove)
  document.removeEventListener('pointerup', handleTouchPointerUp)
  document.removeEventListener('pointercancel', handleTouchPointerCancel)
}

function handleTouchPointerDown(e: PointerEvent) {
  if (e.pointerType !== 'touch') return
  if (draggingId.value) return
  if (touchDragPointerId.value !== null) return
  const target = e.target as HTMLElement | null
  if (!target) return
  if (shouldIgnoreTouchTarget(target)) return

  const groupEl = target.closest('.group-node') as HTMLElement | null
  if (!groupEl) return
  const groupId = Number(groupEl.dataset.id ?? '')
  if (!groupId) return

  touchDragSourceEl.value = groupEl
  touchDragPointerId.value = e.pointerId
  touchDragStartX.value = e.clientX
  touchDragStartY.value = e.clientY

  touchDragTimer.value = window.setTimeout(() => {
    startTouchDrag(groupId, e.pointerId, groupEl)
    applyDropHighlight(resolveTouchDropTarget(e.clientX, e.clientY))
  }, TOUCH_LONG_PRESS_MS)

  attachTouchListeners()
}

function handleTouchPointerMove(e: PointerEvent) {
  if (e.pointerType !== 'touch') return
  if (touchDragPointerId.value !== null && e.pointerId !== touchDragPointerId.value) return

  const dx = e.clientX - touchDragStartX.value
  const dy = e.clientY - touchDragStartY.value
  const moved = Math.hypot(dx, dy)

  if (!touchDragActive.value) {
    if (moved > TOUCH_MOVE_THRESHOLD) {
      resetTouchDragState()
      detachTouchListeners()
    }
    return
  }

  e.preventDefault()
  if (moved > 1) {
    touchDragMoved.value = true
  }
  applyDropHighlight(resolveTouchDropTarget(e.clientX, e.clientY))
}

async function handleTouchPointerUp(e: PointerEvent) {
  if (e.pointerType !== 'touch') return
  if (touchDragPointerId.value !== null && e.pointerId !== touchDragPointerId.value) return

  if (!touchDragActive.value) {
    resetTouchDragState()
    detachTouchListeners()
    return
  }

  e.preventDefault()
  try {
    touchDragSourceEl.value?.releasePointerCapture(e.pointerId)
  } catch {
    // ignore pointer capture failures
  }

  const target = resolveTouchDropTarget(e.clientX, e.clientY)
  const dragIds = getDragIds()
  const currentDragId = draggingId.value

  if (!touchDragMoved.value && target.type === 'group' && currentDragId && target.groupId === currentDragId) {
    resetTouchDragState(true)
    clearDragState()
    touchDragJustEnded.value = true
    window.setTimeout(() => {
      touchDragJustEnded.value = false
    }, 300)
    detachTouchListeners()
    return
  }

  if (target.type === 'root') {
    await handleHierarchyMove(null, dragIds)
  } else if (target.type === 'gap') {
    const parentId = target.parentId === 0 ? null : target.parentId
    await handleHierarchyMove(parentId, dragIds)
  } else if (target.type === 'group') {
    await handleHierarchyMove(target.groupId, dragIds)
  }

  resetTouchDragState(true)
  clearDragState()
  touchDragJustEnded.value = true
  window.setTimeout(() => {
    touchDragJustEnded.value = false
  }, 300)
  detachTouchListeners()
}

function handleTouchPointerCancel(e: PointerEvent) {
  if (e.pointerType !== 'touch') return
  if (touchDragPointerId.value !== null && e.pointerId !== touchDragPointerId.value) return
  try {
    touchDragSourceEl.value?.releasePointerCapture(e.pointerId)
  } catch {
    // ignore pointer capture failures
  }
  resetTouchDragState(true)
  clearDragState()
  detachTouchListeners()
}

function handleTouchClickCapture(e: MouseEvent) {
  if (!touchDragJustEnded.value) return
  e.preventDefault()
  e.stopPropagation()
  touchDragJustEnded.value = false
}

function initRulesTreeScrollSync() {
  const wrapper = document.getElementById('rules-tree-scroll-wrapper')
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

function clearTreeSearch() {
  searchText.value = ''
  searchInputRef.value?.focus()
}

// 监听搜索文本变化，滚动到第一个匹配项
watch(searchText, async (newVal) => {
  const trimmed = newVal.trim()
  if (!trimmed) return

  const search = trimmed.toLowerCase()
  const newSet = new Set(expandedIds.value)
  expandMatches(groups.value, search, newSet)
  expandedIds.value = newSet
  globalStore.setExpandedGroupIds([...expandedIds.value])

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
onMounted(async () => {
  if (props.visible) {
    loadRulesTree()
  }
  if (globalStore.expandedGroupIds.length > 0) {
    expandedIds.value = new Set(globalStore.expandedGroupIds)
  }
  initRulesTreeScrollSync()
  await nextTick()
  const container = treeContainerRef.value
  if (container) {
    container.addEventListener('pointerdown', handleTouchPointerDown, { passive: true })
    container.addEventListener('click', handleTouchClickCapture, true)
  }
})

onBeforeUnmount(() => {
  cleanupScrollSync?.()
  const container = treeContainerRef.value
  if (container) {
    container.removeEventListener('pointerdown', handleTouchPointerDown)
    container.removeEventListener('click', handleTouchClickCapture, true)
  }
  detachTouchListeners()
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
              @click="refreshRulesTree"
            >
              <RefreshCw :class="['w-4 h-4', isLoading ? 'animate-spin' : '']" />
            </button>
          </div>
        </div>

        <div id="rules-search-container" class="pb-3 relative shrink-0">
          <input
            id="rules-tree-search"
            ref="searchInputRef"
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
            <button
              id="batch-mode-btn"
              :class="[
                'px-2 py-1 text-xs rounded transition border hover:bg-blue-100',
                batchEditMode
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-blue-600 border-blue-300'
              ]"
              title="进入/退出批量编辑模式"
              @click="toggleBatchMode"
            >批量</button>
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
            <span
              id="batch-selected-info"
              :class="['text-xs text-blue-700 font-medium', batchEditMode ? '' : 'hidden']"
            >已选(<span id="batch-selected-count" class="font-bold">{{ selectedGroupIds.size }}</span>)</span>
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
                data-drop-root="1"
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

              <p v-if="isLoading && filteredGroups.length === 0" class="text-sm text-slate-400">
                加载中...
              </p>

              <p v-if="filteredGroups.length === 0 && !isLoading" class="text-sm text-slate-400 text-center mt-4">
                暂无规则数据。
              </p>

              <template v-for="group in filteredGroups" :key="group.id">
                <div
                  :class="['drop-gap', dragOverGapKey === `gap-0-${group.id}` ? 'drag-over' : '']"
                  :data-gap-key="`gap-0-${group.id}`"
                  data-gap-parent="0"
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
                  :touch-drop-target-id="touchDropTargetId"
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
                data-gap-key="gap-0-end"
                data-gap-parent="0"
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
