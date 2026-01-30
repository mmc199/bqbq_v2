<script setup lang="ts">
/**
 * TagInput 组件 - 标签胶囊输入
 * 支持：空格/回车添加标签、排除标签(-)、同义词组(,)、点击编辑、删除、标签建议
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

// 标签类型
interface Tag {
  text: string
  exclude: boolean
  synonym: boolean
  synonymWords: string[] | null
}

// 扩展名建议列表
const EXTENSION_SUGGESTIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.ico']

// Props
const props = withDefaults(defineProps<{
  modelValue: Tag[]
  placeholder?: string
  theme?: 'blue' | 'purple' | 'mixed'
  enableExcludes?: boolean
  autoFocus?: boolean
  suggestions?: string[]
}>(), {
  placeholder: '添加标签...',
  theme: 'blue',
  enableExcludes: false,
  autoFocus: false,
  suggestions: () => [],
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [tags: Tag[]]
  'submit': [tags: Tag[]]
  'inputUpdate': [value: string]
}>()

// 内部状态
const inputRef = ref<HTMLInputElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const inputValue = ref('')
const tags = ref<Tag[]>([...props.modelValue])

// 建议列表状态
const showSuggestions = ref(false)
const selectedSuggestionIndex = ref(-1)

// 过滤后的建议列表
const filteredSuggestions = computed(() => {
  const rawQuery = inputValue.value.replace(/^-/, '').trim()
  const query = rawQuery.toLowerCase()
  if (!query) return []

  // 扩展名建议：当输入以 . 开头时
  if (query.startsWith('.')) {
    const existingTags = new Set(tags.value.map(t => t.text.toLowerCase()))
    return EXTENSION_SUGGESTIONS
      .filter(ext => ext.startsWith(query) && !existingTags.has(ext))
      .slice(0, 8)
  }

  // 普通标签建议
  if (!props.suggestions.length) return []

  // 获取已有标签文本
  const existingTags = new Set(tags.value.map(t => t.text.toLowerCase()))

  // 过滤并排序建议
  return props.suggestions
    .filter(s => {
      const lower = s.toLowerCase()
      return lower.includes(query) && !existingTags.has(lower)
    })
    .slice(0, 8) // 最多显示8个建议
})

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  tags.value = [...newVal]
}, { deep: true })

// 监听输入变化，显示/隐藏建议
watch(inputValue, (val) => {
  const query = val.replace(/^-/, '').trim()
  showSuggestions.value = query.length > 0 && filteredSuggestions.value.length > 0
  selectedSuggestionIndex.value = -1
})

// 获取标签样式
function getTagStyle(tag: Tag): string {
  const { exclude, synonym } = tag
  if (exclude && synonym) return 'bg-orange-100 text-orange-700 border-orange-300 hover:bg-orange-200'
  if (exclude) return 'bg-red-100 text-red-600 border-red-200 hover:bg-red-200'
  if (synonym) return 'bg-green-100 text-green-600 border-green-200 hover:bg-green-200'
  if (props.theme === 'purple') return 'bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200'
  return 'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-200'
}

// 获取标签提示文本
function getTagTitle(tag: Tag): string {
  if (!tag.synonym || !tag.synonymWords) return ''
  if (tag.exclude) {
    return `交集排除: 同时包含 [${tag.synonymWords.join(' 且 ')}] 的图片才会被排除`
  }
  return `同义词组: ${tag.synonymWords.join(' | ')}`
}

// 添加标签
function addTag(text: string) {
  let isExclude = false
  let isSynonym = false
  let synonymWords: string[] = []

  // 检查排除标签
  if (props.enableExcludes && text.startsWith('-') && text.length > 1) {
    isExclude = true
    text = text.substring(1)
  }

  // 检查同义词组（逗号分隔）
  if (text.includes(',') || text.includes('，')) {
    synonymWords = text.split(/[,，]/).map(w => w.trim()).filter(w => w.length > 0)

    if (isExclude && synonymWords.length > 0) {
      synonymWords = synonymWords.map(w => w.startsWith('-') ? w.substring(1) : w).filter(w => w.length > 0)
    }

    if (synonymWords.length > 1) {
      isSynonym = true
      text = synonymWords.join(', ')
    } else if (synonymWords.length === 1 && synonymWords[0]) {
      text = synonymWords[0]
    }
  }

  // 检查重复
  const exists = tags.value.some(t =>
    t.text === text && t.exclude === isExclude && t.synonym === isSynonym
  )

  if (!exists && text) {
    const newTag: Tag = {
      text,
      exclude: isExclude,
      synonym: isSynonym,
      synonymWords: isSynonym ? synonymWords : null,
    }
    tags.value.push(newTag)
    emit('update:modelValue', tags.value)
  }
}

// 移除标签
function removeTag(index: number) {
  tags.value.splice(index, 1)
  emit('update:modelValue', tags.value)
}

// 编辑标签
function editTag(index: number) {
  // 先保存当前输入
  const currentInput = inputValue.value.trim()
  if (currentInput) {
    addTag(currentInput)
  }

  // 获取要编辑的标签
  const tag = tags.value[index]
  if (!tag) return

  let text = (tag.exclude ? '-' : '') + tag.text
  text = text.replace(/, /g, ',') // 紧凑格式避免触发空格分割

  // 移除标签
  tags.value.splice(index, 1)
  emit('update:modelValue', tags.value)

  // 放入输入框
  inputValue.value = text
  inputRef.value?.focus()
}

// 处理输入
function handleInput() {
  const val = inputValue.value
  const spaceIndex = val.search(/[ 　]/) // 半角或全角空格

  if (spaceIndex !== -1) {
    const textBefore = val.substring(0, spaceIndex).trim()
    const textAfter = val.substring(spaceIndex).trim()

    if (textBefore) {
      addTag(textBefore)
    }
    inputValue.value = textAfter
  }

  emit('inputUpdate', inputValue.value)
}

// 处理键盘事件
function handleKeydown(e: KeyboardEvent) {
  // 建议列表导航
  if (showSuggestions.value && filteredSuggestions.value.length > 0) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedSuggestionIndex.value = Math.min(
        selectedSuggestionIndex.value + 1,
        filteredSuggestions.value.length - 1
      )
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedSuggestionIndex.value = Math.max(selectedSuggestionIndex.value - 1, -1)
      return
    }
    if (e.key === 'Tab' && selectedSuggestionIndex.value >= 0) {
      e.preventDefault()
      const suggestion = filteredSuggestions.value[selectedSuggestionIndex.value]
      if (suggestion) {
        selectSuggestion(suggestion)
      }
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      showSuggestions.value = false
      return
    }
  }

  if (e.key === 'Enter') {
    // 如果有选中的建议，使用建议
    if (showSuggestions.value && selectedSuggestionIndex.value >= 0) {
      e.preventDefault()
      const suggestion = filteredSuggestions.value[selectedSuggestionIndex.value]
      if (suggestion) {
        selectSuggestion(suggestion)
      }
      return
    }

    const val = inputValue.value.trim()
    if (val) {
      e.preventDefault()
      addTag(val)
      inputValue.value = ''
    } else {
      e.preventDefault()
      emit('submit', tags.value)
    }
  } else if (e.key === 'Backspace' && !inputValue.value && tags.value.length > 0) {
    e.preventDefault()
    editTag(tags.value.length - 1)
  }
}

// 选择建议
function selectSuggestion(suggestion: string) {
  const prefix = inputValue.value.startsWith('-') ? '-' : ''
  addTag(prefix + suggestion)
  inputValue.value = ''
  showSuggestions.value = false
  selectedSuggestionIndex.value = -1
}

// 点击容器聚焦输入框
function focusInput() {
  inputRef.value?.focus()
}

// 点击外部关闭建议列表
function handleClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    showSuggestions.value = false
  }
}

// 计算 placeholder
const computedPlaceholder = computed(() =>
  tags.value.length > 0 ? '' : props.placeholder
)

// 自动聚焦
onMounted(() => {
  if (props.autoFocus) {
    requestAnimationFrame(() => inputRef.value?.focus())
  }
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// 暴露方法
defineExpose({
  focus: () => inputRef.value?.focus(),
  clear: () => {
    tags.value = []
    inputValue.value = ''
    emit('update:modelValue', [])
  },
})
</script>

<template>
  <div
    ref="containerRef"
    class="search-input-wrapper relative flex flex-wrap items-center gap-2 bg-slate-100 rounded-xl px-3 py-2 min-h-[50px] max-h-[120px] overflow-y-auto cursor-text transition-all duration-200 border border-transparent hover:bg-slate-50 focus-within:bg-white focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100"
    @click="focusInput"
  >
    <!-- 标签胶囊 -->
    <div
      v-for="(tag, index) in tags"
      :key="`${tag.text}-${index}`"
      :class="[
        'tag-capsule inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold cursor-pointer select-none transition-transform active:scale-95 border max-w-full break-all',
        getTagStyle(tag)
      ]"
      :title="getTagTitle(tag)"
    >
      <span @click.stop="editTag(index)">
        {{ tag.exclude ? '-' : '' }}{{ tag.text }}
      </span>
      <span
        class="ml-1 hover:text-black/50 text-lg leading-none px-1 rounded-full hover:bg-black/5 transition-colors cursor-pointer"
        @click.stop="removeTag(index)"
      >&times;</span>
    </div>

    <!-- 输入框 -->
    <input
      ref="inputRef"
      v-model="inputValue"
      type="text"
      :placeholder="computedPlaceholder"
      class="search-input flex-grow min-w-[60px] bg-transparent outline-none text-slate-700 placeholder-slate-400 font-medium h-8 text-sm"
      autocomplete="off"
      @input="handleInput"
      @keydown="handleKeydown"
      @focus="showSuggestions = filteredSuggestions.length > 0"
    />

    <!-- 建议下拉列表 -->
    <div
      v-if="showSuggestions && filteredSuggestions.length > 0"
      class="absolute left-0 right-0 top-full mt-1 bg-white rounded-xl shadow-xl border border-slate-200 py-1 z-50 max-h-64 overflow-y-auto"
    >
      <button
        v-for="(suggestion, index) in filteredSuggestions"
        :key="suggestion"
        type="button"
        :class="[
          'w-full px-4 py-2 text-left text-sm transition-colors',
          index === selectedSuggestionIndex
            ? 'bg-blue-50 text-blue-700'
            : 'text-slate-700 hover:bg-slate-50'
        ]"
        @click.stop="selectSuggestion(suggestion)"
        @mouseenter="selectedSuggestionIndex = index"
      >
        <span class="font-medium">{{ suggestion }}</span>
      </button>
    </div>
  </div>
</template>
