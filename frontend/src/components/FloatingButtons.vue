<script setup lang="ts">
/**
 * FloatingButtons 组件 - FAB 悬浮按钮组
 */
import { ref } from 'vue'
import {
  Upload, Settings, Download, FileUp, ChevronUp, ChevronDown,
  Trash2, RotateCcw, Sparkles
} from 'lucide-vue-next'

// Emits
const emit = defineEmits<{
  'upload': []
  'openRules': []
  'export': []
  'import': []
  'toggleTrash': [isTrash: boolean]
  'toggleExpansion': [enabled: boolean]
}>()

// 状态
const isExpanded = ref(true)
const isTrashMode = ref(false)
const isExpansionEnabled = ref(true)

// 切换展开
function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

// 切换回收站模式
function toggleTrashMode() {
  isTrashMode.value = !isTrashMode.value
  emit('toggleTrash', isTrashMode.value)
}

// 切换关键词膨胀
function toggleExpansion() {
  isExpansionEnabled.value = !isExpansionEnabled.value
  emit('toggleExpansion', isExpansionEnabled.value)
}

// 文件导入
const fileInputRef = ref<HTMLInputElement | null>(null)

function triggerImport() {
  fileInputRef.value?.click()
}

function handleImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    // 这里可以触发导入事件
    emit('import')
  }
  input.value = ''
}
</script>

<template>
  <div class="fixed bottom-6 right-6 z-30 flex flex-col items-end gap-3">
    <!-- 展开的按钮组 -->
    <Transition name="fab-group">
      <div v-if="isExpanded" class="flex flex-col items-end gap-3">
        <!-- 关键词膨胀开关 -->
        <button
          :class="[
            'group flex items-center gap-2 p-3 rounded-full shadow-lg transition-all hover:scale-110',
            isExpansionEnabled
              ? 'bg-emerald-500 text-white hover:bg-emerald-600'
              : 'bg-slate-200 text-slate-500 hover:bg-slate-300'
          ]"
          :title="isExpansionEnabled ? '关键词膨胀: 开启' : '关键词膨胀: 关闭'"
          @click="toggleExpansion"
        >
          <Sparkles class="w-5 h-5" />
          <span class="text-sm font-medium hidden group-hover:inline whitespace-nowrap pr-1">
            {{ isExpansionEnabled ? '膨胀开' : '膨胀关' }}
          </span>
        </button>

        <!-- 回收站模式 -->
        <button
          :class="[
            'group flex items-center gap-2 p-3 rounded-full shadow-lg transition-all hover:scale-110',
            isTrashMode
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-slate-200 text-slate-500 hover:bg-slate-300'
          ]"
          :title="isTrashMode ? '退出回收站' : '进入回收站'"
          @click="toggleTrashMode"
        >
          <component :is="isTrashMode ? RotateCcw : Trash2" class="w-5 h-5" />
          <span class="text-sm font-medium hidden group-hover:inline whitespace-nowrap pr-1">
            {{ isTrashMode ? '退出回收站' : '回收站' }}
          </span>
        </button>

        <!-- 导出 -->
        <button
          class="group flex items-center gap-2 p-3 bg-amber-500 text-white rounded-full shadow-lg hover:bg-amber-600 transition-all hover:scale-110"
          title="导出数据"
          @click="emit('export')"
        >
          <Download class="w-5 h-5" />
          <span class="text-sm font-medium hidden group-hover:inline whitespace-nowrap pr-1">
            导出
          </span>
        </button>

        <!-- 导入 -->
        <button
          class="group flex items-center gap-2 p-3 bg-cyan-500 text-white rounded-full shadow-lg hover:bg-cyan-600 transition-all hover:scale-110"
          title="导入数据"
          @click="triggerImport"
        >
          <FileUp class="w-5 h-5" />
          <span class="text-sm font-medium hidden group-hover:inline whitespace-nowrap pr-1">
            导入
          </span>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".json"
          class="hidden"
          @change="handleImportFile"
        />

        <!-- 规则树 -->
        <button
          class="group flex items-center gap-2 p-3 bg-purple-500 text-white rounded-full shadow-lg hover:bg-purple-600 transition-all hover:scale-110"
          title="规则树"
          @click="emit('openRules')"
        >
          <Settings class="w-5 h-5" />
          <span class="text-sm font-medium hidden group-hover:inline whitespace-nowrap pr-1">
            规则树
          </span>
        </button>

        <!-- 上传 -->
        <button
          class="group flex items-center gap-2 p-4 bg-blue-500 text-white rounded-full shadow-lg hover:bg-blue-600 transition-all hover:scale-110"
          title="上传图片"
          @click="emit('upload')"
        >
          <Upload class="w-6 h-6" />
          <span class="text-sm font-medium hidden group-hover:inline whitespace-nowrap pr-1">
            上传
          </span>
        </button>
      </div>
    </Transition>

    <!-- 折叠/展开按钮 -->
    <button
      class="p-3 bg-slate-700 text-white rounded-full shadow-lg hover:bg-slate-800 transition-all"
      :title="isExpanded ? '收起' : '展开'"
      @click="toggleExpand"
    >
      <component :is="isExpanded ? ChevronDown : ChevronUp" class="w-5 h-5" />
    </button>
  </div>
</template>

<style scoped>
.fab-group-enter-active,
.fab-group-leave-active {
  transition: all 0.3s ease;
}

.fab-group-enter-from,
.fab-group-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
