<script setup lang="ts">
/**
 * RuleTree 组件 - 规则树面板
 * 显示语义森林结构，支持增删改查
 */
import { ref, computed, onMounted, watch } from 'vue'
import { X, Search, FolderPlus, RefreshCw, Folder } from 'lucide-vue-next'
import RuleGroupNode from './RuleGroupNode.vue'
import { useRulesApi } from '@/composables/useApi'
import { useGlobalStore } from '@/stores/useGlobalStore'
import type { RuleGroup } from '@/types'

// Props
const props = defineProps<{
  visible: boolean
}>()

// Emits
const emit = defineEmits<{
  'close': []
  'update': []
}>()

// API & Store
const rulesApi = useRulesApi()
const globalStore = useGlobalStore()

// 状态
const isLoading = ref(false)
const searchText = ref('')
const expandedIds = ref<Set<number>>(new Set())
const groups = ref<RuleGroup[]>([])

// 新增状态
const addingGroupParentId = ref<number | null>(null)
const addingKeywordGroupId = ref<number | null>(null)
const newGroupName = ref('')
const newKeyword = ref('')
const showRootInput = ref(false)

// 计算属性：过滤后的树
const filteredGroups = computed(() => {
  if (!searchText.value.trim()) return groups.value
  return filterTree(groups.value, searchText.value.toLowerCase())
})

// 过滤树
function filterTree(nodes: RuleGroup[], search: string): RuleGroup[] {
  return nodes.reduce<RuleGroup[]>((acc, node) => {
    const nameMatch = node.name.toLowerCase().includes(search)
    const keywordMatch = node.keywords.some(k => k.keyword.toLowerCase().includes(search))
    const filteredChildren = filterTree(node.children, search)

    if (nameMatch || keywordMatch || filteredChildren.length > 0) {
      acc.push({
        ...node,
        children: filteredChildren,
      })
    }
    return acc
  }, [])
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

// 关闭面板
function close() {
  emit('close')
}

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
    <!-- 遮罩 -->
    <div
      v-if="visible"
      class="fixed inset-0 bg-black/30 z-40"
      @click="close"
    />

    <!-- 面板 -->
    <aside
      :class="[
        'fixed top-0 left-0 w-80 h-full bg-white shadow-xl z-50 flex flex-col transform transition-transform duration-300',
        visible ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <!-- 头部 -->
      <div class="flex items-center justify-between p-4 border-b flex-shrink-0">
        <h2 class="text-lg font-bold text-slate-800">规则树</h2>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-400">v{{ globalStore.rulesVersion }}</span>
          <button
            class="p-1 text-slate-400 hover:text-slate-600"
            :class="{ 'animate-spin': isLoading }"
            @click="loadRulesTree"
          >
            <RefreshCw class="w-4 h-4" />
          </button>
          <button
            class="p-1 text-slate-400 hover:text-slate-600"
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
            placeholder="搜索规则..."
            class="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <!-- 工具栏 -->
      <div class="flex items-center gap-2 p-3 border-b flex-shrink-0">
        <button
          class="flex items-center gap-1 px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition"
          @click="startAddRootGroup"
        >
          <FolderPlus class="w-4 h-4" />
          新建根组
        </button>
      </div>

      <!-- 树内容 -->
      <div class="flex-1 overflow-auto p-3">
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
          <p class="text-xs mt-1">点击"新建根组"开始创建</p>
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
            @toggle-expand="toggleExpand"
            @start-add-group="startAddGroup"
            @start-add-keyword="startAddKeyword"
            @delete-group="deleteGroup"
            @confirm-add-group="confirmAddGroup"
            @confirm-add-keyword="confirmAddKeyword"
            @cancel-add="cancelAdd"
            @update:new-group-name="newGroupName = $event"
            @update:new-keyword="newKeyword = $event"
          />
        </div>
      </div>
    </aside>
  </Teleport>
</template>
