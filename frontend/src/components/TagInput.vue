<script setup lang="ts">
/**
 * TagInput 组件 - 标签胶囊输入
 * 支持：空格/回车添加标签、排除标签(-)、同义词组(,)、点击编辑、删除
 */
import { ref, computed, watch, onMounted } from 'vue'
import { X } from 'lucide-vue-next'

// 标签类型
interface Tag {
  text: string
  exclude: boolean
  synonym: boolean
  synonymWords: string[] | null
}

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
const inputValue = ref('')
const tags = ref<Tag[]>([...props.modelValue])

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  tags.value = [...newVal]
}, { deep: true })

// 获取标签样式
function getTagStyle(tag: Tag): string {
  const { exclude, synonym } = tag
  if (exclude && synonym) return 'bg-orange-100 text-orange-700 border-orange-300 hover:bg-orange-200'
  if (exclude) return 'bg-red-100 text-red-600 border-red-200 hover:bg-red-200'
  if (synonym) return 'bg-green-100 text-green-600 border-green-200 hover:bg-green-200'
  if (props.theme === 'purple') return 'bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200'
  return 'bg-blue-100 text-blue-600 border-blue-200 hover:bg-blue-200'
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
  if (e.key === 'Enter') {
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

// 点击容器聚焦输入框
function focusInput() {
  inputRef.value?.focus()
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
    class="flex flex-wrap items-center gap-2 p-2 bg-white border border-slate-200 rounded-lg min-h-[44px] cursor-text focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500"
    @click="focusInput"
  >
    <!-- 标签胶囊 -->
    <div
      v-for="(tag, index) in tags"
      :key="`${tag.text}-${index}`"
      :class="[
        'flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold cursor-pointer select-none transition-transform active:scale-95 border',
        getTagStyle(tag)
      ]"
      :title="getTagTitle(tag)"
    >
      <span @click.stop="editTag(index)">
        {{ tag.exclude ? '-' : '' }}{{ tag.text }}
      </span>
      <button
        type="button"
        class="ml-1 hover:text-black/50 rounded-full hover:bg-black/5 transition-colors p-0.5"
        @click.stop="removeTag(index)"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- 输入框 -->
    <input
      ref="inputRef"
      v-model="inputValue"
      type="text"
      :list="suggestions.length ? 'tag-suggestions' : undefined"
      :placeholder="computedPlaceholder"
      class="flex-grow min-w-[60px] bg-transparent outline-none text-slate-700 placeholder-slate-400 font-medium h-8 text-sm"
      @input="handleInput"
      @keydown="handleKeydown"
    />

    <!-- Datalist 建议 -->
    <datalist v-if="suggestions.length" id="tag-suggestions">
      <option v-for="s in suggestions" :key="s" :value="s" />
    </datalist>
  </div>
</template>
