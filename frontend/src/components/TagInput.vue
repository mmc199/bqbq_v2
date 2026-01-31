<script setup lang="ts">
/**
 * TagInput 组件 - 标签胶囊输入
 * 复刻旧项目交互：空格/回车添加、排除标签(-)、同义词组(,)、datalist 建议
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

// 标签类型
interface Tag {
  text: string
  exclude: boolean
  synonym: boolean
  synonymWords: string[] | null
}

type TagEntry = Tag | string

const props = withDefaults(defineProps<{
  modelValue: TagEntry[]
  placeholder?: string
  theme?: 'blue' | 'purple' | 'mixed'
  enableExcludes?: boolean
  autoFocus?: boolean
  suggestions?: string[]
  suggestionsId?: string
  containerClass?: string
}>(), {
  placeholder: '输入关键词 (空格生成胶囊)...',
  theme: 'blue',
  enableExcludes: false,
  autoFocus: false,
  suggestions: () => [],
  suggestionsId: 'tag-suggestions',
  containerClass:
    'flex-1 flex flex-wrap items-center gap-2 bg-slate-100 rounded-xl px-3 py-2 min-h-[50px] max-h-[120px] overflow-y-auto cursor-text transition-colors hover:bg-slate-50 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-100 border border-transparent focus-within:border-blue-300 custom-scrollbar'
})

const emit = defineEmits<{
  'update:modelValue': [tags: TagEntry[]]
  'submit': [tags: TagEntry[]]
  'inputUpdate': [value: string]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const inputValue = ref('')
const tags = ref<TagEntry[]>([...props.modelValue])

watch(() => props.modelValue, (newVal) => {
  tags.value = [...newVal]
}, { deep: true })

function isTagObject(tag: TagEntry): tag is Tag {
  return typeof tag === 'object'
}

// 获取标签样式
function getTagStyle(tag: TagEntry): string {
  if (!isTagObject(tag)) {
    if (props.theme === 'purple') return 'bg-purple-100 text-purple-700 border border-purple-200 hover:bg-purple-200'
    return 'bg-blue-100 text-blue-600 border border-blue-200 hover:bg-blue-200'
  }
  const { exclude, synonym } = tag
  if (exclude && synonym) return 'bg-orange-100 text-orange-700 border border-orange-300 hover:bg-orange-200'
  if (exclude) return 'bg-red-100 text-red-600 border border-red-200 hover:bg-red-200'
  if (synonym) return 'bg-green-100 text-green-600 border border-green-200 hover:bg-green-200'
  if (props.theme === 'purple') return 'bg-purple-100 text-purple-700 border border-purple-200 hover:bg-purple-200'
  return 'bg-blue-100 text-blue-600 border border-blue-200 hover:bg-blue-200'
}

// 获取标签提示文本
function getTagTitle(tag: TagEntry): string {
  if (!isTagObject(tag)) return ''
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

  if (props.enableExcludes && text.startsWith('-') && text.length > 1) {
    isExclude = true
    text = text.substring(1)
  }

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

  const exists = tags.value.some(t => {
    if (isTagObject(t)) {
      return t.text === text && t.exclude === isExclude && t.synonym === isSynonym
    }
    return t === text
  })

  if (!exists && text) {
    if (props.enableExcludes) {
      const newTag: Tag = {
        text,
        exclude: isExclude,
        synonym: isSynonym,
        synonymWords: isSynonym ? synonymWords : null,
      }
      tags.value.push(newTag)
    } else {
      tags.value.push(text)
    }
    emit('update:modelValue', tags.value)
  }

  inputRef.value?.focus()
}

// 移除标签
function removeTag(index: number) {
  tags.value.splice(index, 1)
  emit('update:modelValue', tags.value)
}

// 编辑标签
function editTag(index: number) {
  const currentInput = inputValue.value.trim()
  if (currentInput) {
    addTag(currentInput)
  }

  const tag = tags.value[index]
  if (!tag) return

  let text = isTagObject(tag) ? (tag.exclude ? '-' : '') + tag.text : tag
  text = text.replace(/, /g, ',')

  tags.value.splice(index, 1)
  emit('update:modelValue', tags.value)

  inputValue.value = text
  inputRef.value?.focus()
}

function handleInput() {
  const val = inputValue.value
  const spaceIndex = val.search(/[ 　]/)

  if (spaceIndex !== -1) {
    const textBefore = val.substring(0, spaceIndex).trim()
    const textAfter = val.substring(spaceIndex).trim()

    if (textBefore) {
      addTag(textBefore)
    }
    inputValue.value = textAfter
    inputRef.value?.focus()
  }

  emit('inputUpdate', inputValue.value)
}

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

function focusInput() {
  inputRef.value?.focus()
}

function handleClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    // no-op: datalist is native; nothing to close
  }
}

const computedPlaceholder = computed(() =>
  tags.value.length > 0 ? '' : props.placeholder
)

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
  addTag,
  removeTag
})
</script>

<template>
  <div
    ref="containerRef"
    :class="containerClass"
    @click="focusInput"
  >
    <!-- 标签胶囊 -->
    <div
      v-for="(tag, index) in tags"
      :key="`${typeof tag === 'string' ? tag : tag.text}-${index}`"
      :class="[
        'tag-capsule flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold cursor-pointer select-none whitespace-nowrap transition-transform active:scale-95 max-w-full break-all border',
        getTagStyle(tag)
      ]"
      :title="getTagTitle(tag)"
    >
      <span @click.stop="editTag(index)">
        {{ typeof tag === 'string' ? tag : `${tag.exclude ? '-' : ''}${tag.text}` }}
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
      :list="suggestionsId"
      class="flex-grow min-w-[60px] bg-transparent outline-none text-slate-700 placeholder-slate-400 font-medium h-8 text-sm"
      autocomplete="off"
      @input="handleInput"
      @keydown="handleKeydown"
    />
  </div>
</template>
