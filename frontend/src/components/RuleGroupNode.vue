<script setup lang="ts">
/**
 * RuleGroupNode 组件 - 规则组节点（递归）
 * 支持拖拽排序、批量编辑、启用/禁用、搜索高亮
 */
import { ref, computed } from 'vue'
import {
  Folder, Tag, ChevronDown, ChevronRight,
  FolderPlus, Plus, Trash2, GripVertical,
  Power, PowerOff, CheckSquare, Square, X
} from 'lucide-vue-next'
import type { RuleGroup, RuleKeyword } from '@/types'

// Props
const props = defineProps<{
  group: RuleGroup
  expandedIds: Set<number>
  addingGroupParentId: number | null
  addingKeywordGroupId: number | null
  newGroupName: string
  newKeyword: string
  depth?: number
  draggingId?: number | null
  batchEditMode?: boolean
  selectedGroupIds?: Set<number>
  searchText?: string
}>()

// Emits
const emit = defineEmits<{
  'toggleExpand': [id: number]
  'startAddGroup': [parentId: number]
  'startAddKeyword': [groupId: number]
  'deleteGroup': [group: RuleGroup]
  'deleteKeyword': [keywordId: number]
  'toggleEnabled': [group: RuleGroup]
  'toggleKeywordEnabled': [keyword: RuleKeyword]
  'toggleSelection': [groupId: number]
  'confirmAddGroup': []
  'confirmAddKeyword': []
  'cancelAdd': []
  'update:newGroupName': [value: string]
  'update:newKeyword': [value: string]
  'dragStart': [groupId: number]
  'dragEnd': []
  'dropOnGroup': [targetGroupId: number]
}>()

// 拖拽状态
const isDragOver = ref(false)

// 计算属性
const isExpanded = computed(() => props.expandedIds.has(props.group.id))
const hasContent = computed(() =>
  props.group.children.length > 0 || props.group.keywords.length > 0
)
const isDragging = computed(() => props.draggingId === props.group.id)
const isValidDropTarget = computed(() =>
  props.draggingId !== null && props.draggingId !== props.group.id
)
const isSelected = computed(() => props.selectedGroupIds?.has(props.group.id) ?? false)
const isDisabled = computed(() => !props.group.enabled)
const isMatch = computed(() => props.group.isMatch ?? false)
const isConflict = computed(() => props.group.isConflict ?? false)

// 高亮搜索文本
function highlightText(text: string): string {
  const search = props.searchText?.trim().toLowerCase()
  if (!search) return text
  const regex = new RegExp(`(${search})`, 'gi')
  return text.replace(regex, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>')
}

// 检查关键词是否匹配搜索
function isKeywordMatch(keyword: string): boolean {
  const search = props.searchText?.trim().toLowerCase()
  if (!search) return false
  return keyword.toLowerCase().includes(search)
}

// 拖拽事件处理
function handleDragStart(e: DragEvent) {
  e.stopPropagation()
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', props.group.id.toString())
  }
  emit('dragStart', props.group.id)
}

function handleDragEnd(e: DragEvent) {
  e.stopPropagation()
  emit('dragEnd')
}

function handleDragOver(e: DragEvent) {
  if (!isValidDropTarget.value) return
  e.preventDefault()
  e.stopPropagation()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  isDragOver.value = true
}

function handleDragLeave(e: DragEvent) {
  e.stopPropagation()
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false
  if (isValidDropTarget.value) {
    emit('dropOnGroup', props.group.id)
  }
}

// 点击复选框
function handleCheckboxClick(e: Event) {
  e.stopPropagation()
  emit('toggleSelection', props.group.id)
}

// 点击启用/禁用按钮
function handleToggleEnabled(e: Event) {
  e.stopPropagation()
  emit('toggleEnabled', props.group)
}
</script>

<template>
  <div
    class="rule-group mb-2"
    :class="{
      'opacity-50': isDragging,
      'ring-2 ring-red-400': isConflict
    }"
    :data-match="isMatch || undefined"
  >
    <!-- 组头部 - 一比一复刻旧项目样式 -->
    <div
      :class="[
        'rule-group-header flex items-center justify-between py-2.5 px-3 rounded-[10px] cursor-pointer group transition-all duration-150',
        isDragOver && isValidDropTarget ? 'bg-blue-100 ring-2 ring-blue-400' : 'bg-slate-50',
        isMatch ? 'bg-yellow-50 hover:bg-yellow-100' : '',
        isConflict ? 'bg-red-50 hover:bg-red-100' : '',
        isDisabled ? 'opacity-50' : '',
        !isDragOver && !isMatch && !isConflict ? 'hover:bg-slate-100' : ''
      ]"
      draggable="true"
      @click="emit('toggleExpand', group.id)"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <div class="flex items-center gap-2 min-w-0">
        <!-- 批量编辑复选框 -->
        <button
          v-if="batchEditMode"
          class="flex-shrink-0 p-0.5 text-purple-500 hover:text-purple-700"
          @click="handleCheckboxClick"
        >
          <component :is="isSelected ? CheckSquare : Square" class="w-4 h-4" />
        </button>

        <!-- 拖拽手柄 -->
        <GripVertical
          v-if="!batchEditMode"
          class="w-4 h-4 text-slate-300 flex-shrink-0 cursor-grab active:cursor-grabbing"
        />

        <!-- 展开/折叠图标 -->
        <component
          :is="hasContent ? (isExpanded ? ChevronDown : ChevronRight) : 'span'"
          :class="hasContent ? 'w-4 h-4 text-slate-400 flex-shrink-0' : 'w-4'"
        />

        <!-- 文件夹图标 -->
        <Folder
          :class="[
            'w-4 h-4 flex-shrink-0',
            isConflict ? 'text-red-500' : isDisabled ? 'text-slate-400' : 'text-amber-500'
          ]"
        />

        <!-- 组名 -->
        <span
          :class="[
            'text-sm font-medium truncate',
            isDisabled ? 'text-slate-400 line-through' : 'text-slate-700'
          ]"
          v-html="highlightText(group.name)"
        />

        <!-- 关键词数量 -->
        <span class="text-xs text-slate-400 flex-shrink-0">({{ group.keywords.length }})</span>

        <!-- 禁用标记 -->
        <span
          v-if="isDisabled"
          class="text-xs text-orange-500 flex-shrink-0"
        >
          [禁用]
        </span>
      </div>

      <!-- 操作按钮 -->
      <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
        <!-- 启用/禁用按钮 -->
        <button
          :class="[
            'p-1',
            isDisabled ? 'text-green-500 hover:text-green-700' : 'text-orange-500 hover:text-orange-700'
          ]"
          :title="isDisabled ? '启用' : '禁用'"
          @click="handleToggleEnabled"
        >
          <component :is="isDisabled ? Power : PowerOff" class="w-4 h-4" />
        </button>
        <button
          class="p-1 text-blue-500 hover:text-blue-700"
          title="添加子组"
          @click.stop="emit('startAddGroup', group.id)"
        >
          <FolderPlus class="w-4 h-4" />
        </button>
        <button
          class="p-1 text-green-500 hover:text-green-700"
          title="添加关键词"
          @click.stop="emit('startAddKeyword', group.id)"
        >
          <Plus class="w-4 h-4" />
        </button>
        <button
          class="p-1 text-red-500 hover:text-red-700"
          title="删除组"
          @click.stop="emit('deleteGroup', group)"
        >
          <Trash2 class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- 展开内容 - 一比一复刻旧项目子节点容器样式 -->
    <div v-if="isExpanded" class="rule-group-children ml-5 pl-3 mt-1 border-l-2 border-slate-200">
      <!-- 关键词列表 -->
      <div
        v-for="kw in group.keywords"
        :key="kw.id"
        :class="[
          'flex items-center justify-between gap-2 py-1 px-2 text-sm rounded group/kw',
          isKeywordMatch(kw.keyword) ? 'bg-yellow-50' : 'hover:bg-slate-50',
          !kw.enabled ? 'opacity-50' : ''
        ]"
      >
        <div class="flex items-center gap-2 min-w-0">
          <Tag :class="['w-3 h-3 flex-shrink-0', kw.enabled ? 'text-green-500' : 'text-slate-400']" />
          <span
            :class="['truncate', kw.enabled ? 'text-slate-600' : 'text-slate-400 line-through']"
            v-html="highlightText(kw.keyword)"
          />
        </div>
        <div class="flex items-center gap-1 opacity-0 group-hover/kw:opacity-100 transition-opacity flex-shrink-0">
          <button
            :class="['p-0.5', kw.enabled ? 'text-green-500 hover:text-green-700' : 'text-slate-400 hover:text-slate-600']"
            :title="kw.enabled ? '禁用关键词' : '启用关键词'"
            @click="emit('toggleKeywordEnabled', kw)"
          >
            <component :is="kw.enabled ? Power : PowerOff" class="w-3 h-3" />
          </button>
          <button
            class="p-0.5 text-red-400 hover:text-red-600"
            title="删除关键词"
            @click="emit('deleteKeyword', kw.id)"
          >
            <X class="w-3 h-3" />
          </button>
        </div>
      </div>

      <!-- 添加关键词输入框 -->
      <div v-if="addingKeywordGroupId === group.id" class="py-1 px-2">
        <input
          :value="newKeyword"
          type="text"
          placeholder="输入关键词，回车确认"
          class="w-full px-2 py-1 border border-green-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          autofocus
          @input="emit('update:newKeyword', ($event.target as HTMLInputElement).value)"
          @keydown.enter="emit('confirmAddKeyword')"
          @keydown.escape="emit('cancelAdd')"
          @blur="emit('confirmAddKeyword')"
        />
      </div>

      <!-- 递归渲染子组 -->
      <RuleGroupNode
        v-for="child in group.children"
        :key="child.id"
        :group="child"
        :expanded-ids="expandedIds"
        :adding-group-parent-id="addingGroupParentId"
        :adding-keyword-group-id="addingKeywordGroupId"
        :new-group-name="newGroupName"
        :new-keyword="newKeyword"
        :depth="(depth || 0) + 1"
        :dragging-id="draggingId"
        :batch-edit-mode="batchEditMode"
        :selected-group-ids="selectedGroupIds"
        :search-text="searchText"
        @toggle-expand="emit('toggleExpand', $event)"
        @start-add-group="emit('startAddGroup', $event)"
        @start-add-keyword="emit('startAddKeyword', $event)"
        @delete-group="emit('deleteGroup', $event)"
        @delete-keyword="emit('deleteKeyword', $event)"
        @toggle-enabled="emit('toggleEnabled', $event)"
        @toggle-selection="emit('toggleSelection', $event)"
        @confirm-add-group="emit('confirmAddGroup')"
        @confirm-add-keyword="emit('confirmAddKeyword')"
        @cancel-add="emit('cancelAdd')"
        @update:new-group-name="emit('update:newGroupName', $event)"
        @update:new-keyword="emit('update:newKeyword', $event)"
        @drag-start="emit('dragStart', $event)"
        @drag-end="emit('dragEnd')"
        @drop-on-group="emit('dropOnGroup', $event)"
      />

      <!-- 添加子组输入框 -->
      <div v-if="addingGroupParentId === group.id" class="py-1 px-2">
        <input
          :value="newGroupName"
          type="text"
          placeholder="输入组名，回车确认"
          class="w-full px-2 py-1 border border-blue-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          autofocus
          @input="emit('update:newGroupName', ($event.target as HTMLInputElement).value)"
          @keydown.enter="emit('confirmAddGroup')"
          @keydown.escape="emit('cancelAdd')"
          @blur="emit('confirmAddGroup')"
        />
      </div>
    </div>
  </div>
</template>
