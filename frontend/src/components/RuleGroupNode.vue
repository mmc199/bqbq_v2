<script setup lang="ts">
/**
 * RuleGroupNode 组件 - 规则组节点（递归）
 */
import { computed } from 'vue'
import {
  Folder, Tag, ChevronDown, ChevronRight,
  FolderPlus, Plus, Trash2
} from 'lucide-vue-next'
import type { RuleGroup } from '@/types'

// Props
const props = defineProps<{
  group: RuleGroup
  expandedIds: Set<number>
  addingGroupParentId: number | null
  addingKeywordGroupId: number | null
  newGroupName: string
  newKeyword: string
  depth?: number
}>()

// Emits
const emit = defineEmits<{
  'toggleExpand': [id: number]
  'startAddGroup': [parentId: number]
  'startAddKeyword': [groupId: number]
  'deleteGroup': [group: RuleGroup]
  'confirmAddGroup': []
  'confirmAddKeyword': []
  'cancelAdd': []
  'update:newGroupName': [value: string]
  'update:newKeyword': [value: string]
}>()

// 计算属性
const isExpanded = computed(() => props.expandedIds.has(props.group.id))
const hasContent = computed(() =>
  props.group.children.length > 0 || props.group.keywords.length > 0
)
</script>

<template>
  <div class="group-node">
    <!-- 组头部 -->
    <div
      class="flex items-center justify-between p-2 rounded hover:bg-slate-100 cursor-pointer group"
      @click="emit('toggleExpand', group.id)"
    >
      <div class="flex items-center gap-2 min-w-0">
        <component
          :is="hasContent ? (isExpanded ? ChevronDown : ChevronRight) : 'span'"
          :class="hasContent ? 'w-4 h-4 text-slate-400 flex-shrink-0' : 'w-4'"
        />
        <Folder class="w-4 h-4 text-amber-500 flex-shrink-0" />
        <span class="text-sm font-medium text-slate-700 truncate">{{ group.name }}</span>
        <span class="text-xs text-slate-400 flex-shrink-0">({{ group.keywords.length }})</span>
      </div>
      <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
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

    <!-- 展开内容 -->
    <div v-if="isExpanded" class="ml-6 border-l border-slate-200 pl-2">
      <!-- 关键词列表 -->
      <div
        v-for="kw in group.keywords"
        :key="kw.id"
        class="flex items-center gap-2 py-1 px-2 text-sm text-slate-600 hover:bg-slate-50 rounded"
      >
        <Tag class="w-3 h-3 text-green-500 flex-shrink-0" />
        <span class="truncate">{{ kw.keyword }}</span>
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
        @toggle-expand="emit('toggleExpand', $event)"
        @start-add-group="emit('startAddGroup', $event)"
        @start-add-keyword="emit('startAddKeyword', $event)"
        @delete-group="emit('deleteGroup', $event)"
        @confirm-add-group="emit('confirmAddGroup')"
        @confirm-add-keyword="emit('confirmAddKeyword')"
        @cancel-add="emit('cancelAdd')"
        @update:new-group-name="emit('update:newGroupName', $event)"
        @update:new-keyword="emit('update:newKeyword', $event)"
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
