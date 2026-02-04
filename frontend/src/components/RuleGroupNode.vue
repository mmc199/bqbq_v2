<script setup lang="ts">
/**
 * RuleGroupNode 组件 - 规则组节点（递归）
 * 结构/类名对齐旧项目 DOM
 */
import { ref, computed, nextTick } from 'vue'
import { Folder, FolderX, AlertTriangle, ChevronDown, FolderPlus, Plus, Trash2, Eye, EyeOff } from 'lucide-vue-next'
import type { RuleGroup, RuleKeyword } from '@/types'
import { useToast } from '@/composables/useToast'

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
  dragOverGapKey?: string | null
  dropTargetGroupId?: number | null
}>()

const emit = defineEmits<{
  'toggleExpand': [id: number]
  'startAddGroup': [parentId: number]
  'startAddKeyword': [groupId: number]
  'deleteGroup': [group: RuleGroup]
  'deleteKeyword': [keyword: RuleKeyword]
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
  'dropOnGap': [event: DragEvent, parentId: number]
  'gapDragOver': [event: DragEvent, gapKey: string]
  'gapDragLeave': [event: DragEvent]
  'groupDragOver': [groupId: number]
  'groupDragLeave': [groupId: number]
  'renameGroup': [groupId: number, name: string]
}>()

const toast = useToast()

const groupNodeRef = ref<HTMLElement | null>(null)
const isEditingName = ref(false)
const editingName = ref('')
const editInputRef = ref<HTMLInputElement | null>(null)
const ignoreBlur = ref(false)

const isExpanded = computed(() => props.expandedIds.has(props.group.id))
const isDragging = computed(() => {
  if (!props.draggingId) return false
  if (props.draggingId === props.group.id) return true
  if (props.batchEditMode && props.selectedGroupIds?.has(props.draggingId) && props.selectedGroupIds.has(props.group.id)) {
    return true
  }
  return false
})
const isValidDropTarget = computed(() => {
  return !!props.draggingId
})
const isDropTarget = computed(() => props.dropTargetGroupId === props.group.id)
const isSelected = computed(() => props.selectedGroupIds?.has(props.group.id) ?? false)
const isDisabled = computed(() => !props.group.enabled)
const isMatch = computed(() => props.group.isMatch ?? false)
const isConflict = computed(() => props.group.isConflict ?? false)
const isEmptyNameGroup = computed(() => !props.group.name || props.group.name.trim() === '')

const emptyNameLabel = computed(() => {
  if (typeof props.group.id === 'number') return `[空名组 #${props.group.id}]`
  return '[空名组]'
})

const displayNameHtml = computed(() => {
  if (isConflict.value) {
    const reason = props.group.conflictReason || '循环依赖'
    return `<span class="text-red-600">${props.group.name || '[空名组]'}</span><span class="text-xs text-red-500 bg-red-100 px-1 rounded ml-1" title="${reason}">⚠️冲突</span>`
  }
  if (isEmptyNameGroup.value) {
    return `<span class="text-red-500 bg-red-50 px-1 rounded">${emptyNameLabel.value}</span>`
  }
  const color = isMatch.value ? 'text-blue-700' : 'text-slate-700'
  return `<span class="group-name-text ${color}">${props.group.name}</span>`
})

const folderIcon = computed(() => {
  if (isConflict.value || isEmptyNameGroup.value) return AlertTriangle
  if (isDisabled.value) return FolderX
  return Folder
})

const folderIconClass = computed(() => {
  if (isConflict.value || isEmptyNameGroup.value) return 'text-red-500'
  if (isMatch.value) return 'text-blue-600'
  return 'text-slate-500'
})

const childCount = computed(() => {
  return Array.isArray(props.group.children) ? props.group.children.length : 0
})

function isKeywordMatch(keyword: string): boolean {
  const search = props.searchText?.trim().toLowerCase()
  if (!search) return false
  return keyword.toLowerCase().includes(search)
}

function startEditName(e: MouseEvent) {
  e.stopPropagation()
  if (props.batchEditMode) return
  isEditingName.value = true
  editingName.value = props.group.name || ''
  ignoreBlur.value = false
  nextTick(() => editInputRef.value?.focus())
}

function confirmEditName() {
  if (!isEditingName.value) return
  const name = editingName.value.trim()
  if (!name) {
    toast.error('组名不能为空！')
    return
  }
  if (name === (props.group.name || '')) {
    cancelEditName()
    return
  }
  isEditingName.value = false
  emit('renameGroup', props.group.id, name)
}

function cancelEditName() {
  isEditingName.value = false
  editingName.value = props.group.name || ''
}

function markIgnoreBlur() {
  ignoreBlur.value = true
}


function handleDragStart(e: DragEvent) {
  e.stopPropagation()
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    const dragIds = (props.batchEditMode && props.selectedGroupIds?.has(props.group.id))
      ? Array.from(props.selectedGroupIds ?? [])
      : [props.group.id]
    e.dataTransfer.setData('text/plain', JSON.stringify(dragIds))
    const dragImage = groupNodeRef.value
    if (dragImage) {
      const rect = dragImage.getBoundingClientRect()
      const offsetX = Math.min(28, rect.width / 2)
      const offsetY = Math.min(16, rect.height / 2)
      e.dataTransfer.setDragImage(dragImage, offsetX, offsetY)
    }
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
  emit('groupDragOver', props.group.id)
}

function handleDragLeave(e: DragEvent) {
  e.stopPropagation()
  const current = e.currentTarget as HTMLElement | null
  const related = e.relatedTarget as Node | null
  if (current && related && current.contains(related)) {
    return
  }
  emit('groupDragLeave', props.group.id)
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  if (isValidDropTarget.value) {
    emit('dropOnGroup', props.group.id)
  }
}

function handleCheckboxClick(e: Event) {
  e.stopPropagation()
  emit('toggleSelection', props.group.id)
}

function handleGapDragOver(e: DragEvent, gapKey: string) {
  if (!props.draggingId) return
  emit('gapDragOver', e, gapKey)
}

function handleGapDragLeave(e: DragEvent) {
  emit('gapDragLeave', e)
}

function handleGapDrop(e: DragEvent) {
  emit('dropOnGap', e, props.group.id)
}

</script>

<template>
  <div
    ref="groupNodeRef"
    class="group-node group relative"
    :class="[
      isDragging ? 'dragging' : '',
      isValidDropTarget && isDropTarget ? 'drop-target-child' : '',
      isConflict ? 'border-2 border-red-400 bg-red-50' : '',
      batchEditMode && isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : '',
      isMatch ? 'bg-blue-50 border-blue-400' : '',
      isDisabled ? 'opacity-50 italic' : ''
    ]"
    :data-id="group.id"
    :data-name="group.name || ''"
    :data-match="isMatch || undefined"
    draggable="true"
    @dragstart="handleDragStart"
    @dragend="handleDragEnd"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <div
      class="group-header flex items-center p-2 rounded cursor-pointer whitespace-nowrap"
      :class="[
        batchEditMode ? 'batch-mode' : '',
        isMatch ? 'hover:bg-blue-100' : (isConflict ? 'hover:bg-red-100' : 'hover:bg-slate-100')
      ]"
      @click="emit('toggleExpand', group.id)"
      @dblclick="startEditName"
    >
      <div class="flex items-center gap-1 font-bold text-sm">
        <label v-if="batchEditMode" class="batch-checkbox-wrapper flex items-center justify-center w-7 h-7 -ml-1 mr-1 cursor-pointer">
          <input
            type="checkbox"
            class="batch-checkbox w-5 h-5 accent-blue-600 cursor-pointer"
            :checked="isSelected"
            @click.stop="handleCheckboxClick"
          />
        </label>

        <template v-if="!isEditingName">
          <span class="group-name-wrapper inline-flex items-center gap-1">
            <span class="relative inline-flex items-center justify-center" draggable="true" @dragstart="handleDragStart" @dragend="handleDragEnd">
              <component :is="folderIcon" class="w-5 h-5" :class="folderIconClass" :size="20" />
              <span
                class="absolute inset-0 flex items-center justify-center text-[9px] leading-none font-bold text-blue-600 pointer-events-none"
              >{{ childCount }}</span>
            </span>
            <span v-html="displayNameHtml" draggable="true" @dragstart="handleDragStart" @dragend="handleDragEnd" />
          </span>
        </template>

        <div v-else class="group-editor-wrapper p-2 bg-white rounded shadow-md flex flex-col gap-2" @click.stop>
          <input
            ref="editInputRef"
            v-model="editingName"
            type="text"
            :placeholder="isEmptyNameGroup ? '请输入组名以修复空名组...' : '输入组名...'"
            :class="[
              'w-full p-1 border rounded text-sm font-medium focus:outline-none focus:ring-1',
              isEmptyNameGroup ? 'border-red-400 focus:ring-red-500 bg-red-50' : 'border-blue-400 focus:ring-blue-500'
            ]"
            @click.stop
            @keydown.enter.prevent="confirmEditName"
            @keydown.escape.prevent="cancelEditName"
          />
          <div class="flex justify-between items-center text-xs">
            <button
              class="px-3 py-1 bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition"
              @mousedown.prevent="markIgnoreBlur"
              @click.stop="cancelEditName"
            >取消</button>
            <button
              class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
              @mousedown.prevent="markIgnoreBlur"
              @click.stop="confirmEditName"
            >保存</button>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-1 flex-shrink-0 ml-2">
        <div v-if="!batchEditMode" class="flex items-center gap-1">
          <button class="rule-action-btn p-1 text-blue-500 hover:text-blue-700 opacity-0 group-hover:opacity-100 transition-opacity" title="添加子组" @click.stop="emit('startAddGroup', group.id)">
            <FolderPlus class="w-4 h-4" :size="16" />
          </button>
          <button class="rule-action-btn p-1 text-green-500 hover:text-green-700 opacity-0 group-hover:opacity-100 transition-opacity" title="添加同义词" @click.stop="emit('startAddKeyword', group.id)">
            <Plus class="w-4 h-4" :size="16" />
          </button>
          <button
            :class="[
              'rule-action-btn p-1 opacity-0 group-hover:opacity-100 transition-opacity',
              isDisabled ? 'text-yellow-500 hover:text-yellow-700' : 'text-emerald-500 hover:text-emerald-700'
            ]"
            :title="isDisabled ? '启用组' : '禁用组'"
            @click.stop="emit('toggleEnabled', group)"
          >
            <component :is="isDisabled ? EyeOff : Eye" class="w-4 h-4" :size="16" />
          </button>
          <button class="rule-action-btn p-1 text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity" title="彻底删除组" @click.stop="emit('deleteGroup', group)">
            <Trash2 class="w-4 h-4" :size="16" />
          </button>
        </div>
        <ChevronDown
          class="w-4 h-4 text-slate-400 transition transform"
          :class="isExpanded ? 'rotate-180' : ''"
          :size="16"
        />
      </div>
    </div>

    <div :class="['flex flex-wrap gap-1 pl-6 pt-1 pb-2 border-l border-slate-200 ml-2', (isExpanded && !isEditingName && addingGroupParentId !== group.id) ? '' : 'hidden']">
      <span
        v-for="kw in group.keywords"
        :key="kw.id"
        :class="[
          'keyword-capsule flex items-center gap-1 px-2 py-0.5 text-xs rounded-full cursor-pointer transition-colors',
          kw.enabled
            ? (isKeywordMatch(kw.keyword) ? 'bg-purple-500 text-white hover:bg-purple-600' : 'bg-blue-500 text-white hover:bg-blue-600')
            : 'bg-slate-300 text-slate-600 hover:bg-slate-400'
        ]"
        @click.stop="emit('toggleKeywordEnabled', kw)"
      >
        <span>{{ kw.keyword }}</span>
        <button
          class="ml-1 text-lg leading-none rounded-full hover:opacity-70 text-white/80 transition-opacity"
          @click.stop="emit('deleteKeyword', kw)"
        >
          &times;
        </button>
      </span>

      <div v-if="addingKeywordGroupId === group.id" class="keyword-add-input-wrapper flex items-center gap-1 w-full bg-white rounded p-1 shadow-inner">
        <input
          :value="newKeyword"
          type="text"
          placeholder="输入关键词 (Enter)..."
          class="flex-1 p-0.5 text-xs focus:outline-none"
          list="tag-suggestions"
          autofocus
          @input="emit('update:newKeyword', ($event.target as HTMLInputElement).value)"
          @keydown.enter="emit('confirmAddKeyword')"
          @keydown.escape="emit('cancelAdd')"
          @blur="emit('confirmAddKeyword')"
        />
      </div>
    </div>

    <div :class="['ml-4 border-l border-slate-200', (isExpanded && !isEditingName) ? '' : 'hidden']">
      <div v-if="addingGroupParentId === group.id" class="child-group-add-wrapper p-2 bg-white rounded shadow-md flex flex-col gap-2 mb-2">
        <input
          :value="newGroupName"
          type="text"
          placeholder="输入新子组名称..."
          class="w-full p-1 border border-blue-400 rounded text-sm font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
          autofocus
          @input="emit('update:newGroupName', ($event.target as HTMLInputElement).value)"
          @keydown.enter="emit('confirmAddGroup')"
          @keydown.escape="emit('cancelAdd')"
          @blur="emit('confirmAddGroup')"
        />
        <div class="flex justify-between items-center text-xs">
          <button class="px-3 py-1 bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition" @click="emit('cancelAdd')">取消</button>
          <button class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition" @click="emit('confirmAddGroup')">创建</button>
        </div>
      </div>
      <template v-for="child in group.children" :key="child.id">
        <div
          :class="['drop-gap', dragOverGapKey === `gap-${group.id}-${child.id}` ? 'drag-over' : '']"
          :data-gap-key="`gap-${group.id}-${child.id}`"
          :data-gap-parent="group.id"
          @dragover="handleGapDragOver($event, `gap-${group.id}-${child.id}`)"
          @dragleave="handleGapDragLeave"
          @drop="handleGapDrop"
        ></div>
        <RuleGroupNode
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
          :drag-over-gap-key="dragOverGapKey"
          :drop-target-group-id="dropTargetGroupId"
          @toggle-expand="emit('toggleExpand', $event)"
          @start-add-group="emit('startAddGroup', $event)"
          @start-add-keyword="emit('startAddKeyword', $event)"
          @delete-group="emit('deleteGroup', $event)"
          @delete-keyword="emit('deleteKeyword', $event)"
          @toggle-keyword-enabled="emit('toggleKeywordEnabled', $event)"
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
          @drop-on-gap="(e, parentId) => emit('dropOnGap', e, parentId)"
          @gap-drag-over="(e, gapKey) => emit('gapDragOver', e, gapKey)"
          @gap-drag-leave="(e) => emit('gapDragLeave', e)"
          @group-drag-over="(groupId) => emit('groupDragOver', groupId)"
          @group-drag-leave="(groupId) => emit('groupDragLeave', groupId)"
          @rename-group="(groupId, name) => emit('renameGroup', groupId, name)"
        />
      </template>
      <div
        v-if="group.children.length > 0"
        :class="['drop-gap', dragOverGapKey === `gap-${group.id}-end` ? 'drag-over' : '']"
        :data-gap-key="`gap-${group.id}-end`"
        :data-gap-parent="group.id"
        @dragover="handleGapDragOver($event, `gap-${group.id}-end`)"
        @dragleave="handleGapDragLeave"
        @drop="handleGapDrop"
      ></div>
    </div>
  </div>
</template>
