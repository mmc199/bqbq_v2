<script setup lang="ts">
/**
 * MemeCard 组件 - 图片卡片
 * 复刻旧项目：覆盖层标签编辑、复制标签、回收站软删除、原图加载
 */
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { Download, Trash2, RefreshCw, Check, Loader2, ShoppingCart } from 'lucide-vue-next'
import TagInput from '@/components/TagInput.vue'
import { imageUrl, thumbnailUrl, downloadName, localImageUrl, localThumbnailUrl, isCdnUrl } from '@/composables/useImageUrl'
import { getThumbBlobUrl, isBatchPending, onBatchSettled } from '@/composables/useThumbBatch'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useCartApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import type { MemeImage } from '@/types'

const props = defineProps<{
  image: MemeImage
  preferHQ?: boolean
  isTrash?: boolean
  index?: number
  tempMode?: boolean
}>()

const emit = defineEmits<{
  'delete': [image: MemeImage]
  'applyTempTags': [image: MemeImage]
  'updateTags': [image: MemeImage, tags: string[]]
}>()

// ===========================================================================
//  购物车
// ===========================================================================
//
// 数据存在后端（bot 要按 openid 取），store 只是内存缓存。
// 卡片上的按钮只负责调用接口 + 同步 store，FAB 的角标会自动更新。
const globalStore = useGlobalStore()
const cartApi = useCartApi()
const toast = useToast()

const inCart = computed(() => globalStore.isInCart(props.image.md5))
const cartBusy = ref(false)

async function toggleCart() {
  if (cartBusy.value) return
  if (!globalStore.authGranted) {
    toast.warning('请先登录 QQ 再使用购物车（点击右侧企鹅按钮）')
    return
  }

  cartBusy.value = true
  const md5 = props.image.md5
  try {
    if (inCart.value) {
      const r = await cartApi.remove(globalStore.clientId, md5)
      if (r.success) {
        globalStore.removeCartMd5(md5)
        toast.info('已移出购物车')
      } else {
        toast.error(r.error || '移出失败')
      }
    } else {
      const r = await cartApi.add(globalStore.clientId, md5)
      if (r.success) {
        globalStore.addCartMd5(md5)
        toast.success('已加入购物车')
      } else {
        toast.error(r.error || '加入失败')
      }
    }
  } finally {
    cartBusy.value = false
  }
}

const isOriginalLoading = ref(false)
const imageError = ref(false)
const currentSrcType = ref<'thumbnail' | 'original'>(props.preferHQ ? 'original' : 'thumbnail')

const isEditingTags = ref(false)
const editTags = ref<string[]>([])
const editInputValue = ref('')
const tagInputRef = ref<InstanceType<typeof TagInput> | null>(null)
const editorRef = ref<HTMLElement | null>(null)
const copySuccess = ref(false)
let copyResetTimer: number | null = null

/**
 * 顶部工具栏显隐。
 *
 * 【为什么不能只用 group-hover】触屏没有 hover：CSS :hover 在手机上要么不成立，
 * 要么要等 touchend 之后才"粘"一下，工具栏于是完全点不出来，下载/复制/删除
 * 三个功能在移动端等于不存在。
 *
 * 【为什么由点击切换而不是长按】长按要用户等，且各家触屏浏览器的长按规则
 * 并不统一（部分会被文本选择菜单抢走）。点击是零等待、且已经在用的手势。
 *
 * 【为什么不会和"看图"冲突】卡片上原本单击 img 就是 loadOriginalImage()，
 * 现在只是"顺带"把工具栏切出来，不新增手势、不改变原有语义。
 */
const toolbarVisible = ref(false)

const EAGER_LOAD_COUNT = 4

const imageSrc = computed(() => imageUrl(props.image.filename))
const thumbnailSrc = computed(() => thumbnailUrl(props.image.filename))

/**
 * CDN 失败后回退到本地后端。
 *
 * 【为什么需要】CDN 背后是 R2，而后端同步新图是**异步**的：
 *   · 正常情况有 1-2 秒的「已入库但 R2 还没有」窗口
 *   · 同步失败时这个窗口会一直存在
 * 此时 CDN 返回 404。若不做回退，用户看到的是空白卡片。
 *
 * 【行为】CDN 地址加载失败 -> 自动换成后端 /images 或 /thumbnails 再试一次。
 * 本地也失败才真正标记为错误（显示重试图标）。
 */
const cdnFailedImage = ref(false)
const cdnFailedThumb = ref(false)

/**
 * 缩略图地址。
 *
 * 【关键】不能一查不到 blob 就回退到单图 URL。
 * 批量请求需要时间（真实链路约 2-3 秒），如果卡片在等待期间就渲染了
 * 单图 URL，浏览器会立刻并发发出 N 个请求 —— 等 batch 返回时早已晚了，
 * batch 的意义被完全抵消。
 *
 * 正确行为：
 *   · batch 进行中（isBatchPending）  -> src 留空，只显示占位，不发任何请求
 *   · batch 已结束且命中 blob        -> 用 blob URL
 *   · batch 已结束但没命中（失败/不在本批）-> 才回退到单图 URL
 */
const batchedThumbUrl = ref<string | null>(getThumbBlobUrl(props.image.md5))
/** 批量是否已结束（结束后才允许回退到单图 URL） */
const batchSettled = ref(!isBatchPending())

/** 原图地址：CDN 失败后回退本地 */
const imageSrcFinal = computed(() =>
  cdnFailedImage.value ? localImageUrl(props.image.filename) : imageSrc.value
)

/** 缩略图地址：CDN 失败后回退本地 */
const thumbnailSrcFinal = computed(() =>
  cdnFailedThumb.value ? localThumbnailUrl(props.image.filename) : thumbnailSrc.value
)

/** 最终用于 <img src> 的值；批量等待期间为 null，表示「先不加载」 */
const resolvedThumbSrc = computed(() => {
  if (batchedThumbUrl.value) return batchedThumbUrl.value
  // 批量还在跑：先占位，避免发出单图请求
  if (!batchSettled.value) return null
  // 批量已结束仍未命中 -> 回退
  return thumbnailSrcFinal.value
})

// 卡片挂载后：订阅批量事件，而不是轮询。
// 轮询在「批量整整 2-3 秒」的场景下既浪费又可能错过时机。
let unsubscribeSettled: (() => void) | null = null

function refreshFromBatch() {
  const u = getThumbBlobUrl(props.image.md5)
  if (u && u !== batchedThumbUrl.value) batchedThumbUrl.value = u
  const settled = !isBatchPending()
  if (settled !== batchSettled.value) batchSettled.value = settled
}

onMounted(() => {
  refreshFromBatch()
  // 批量全部结束时通知一次（此时决定是命中还是回退）
  unsubscribeSettled = onBatchSettled(refreshFromBatch)
})

onBeforeUnmount(() => {
  if (unsubscribeSettled) {
    unsubscribeSettled()
    unsubscribeSettled = null
  }
})


/** 最终 src；为 null 时表示「暂不加载」（批量等待中） */
const currentSrc = computed(() => {
  return currentSrcType.value === 'original' ? imageSrcFinal.value : resolvedThumbSrc.value
})

/**
 * 原图 <img> 的 crossorigin 属性 —— 让预览和下载共用同一份浏览器缓存。
 *
 * 【为什么需要】
 * 默认 <img> 请求**不带 Origin 头**，CDN 因此返回"无 CORS 头"的响应；
 * 而下载用的 fetch 带 Origin、必须看到 CORS 头。两者在浏览器缓存里是
 * 不同条目，导致同一张图被下载两遍（预览一遍 + 下载一遍）。
 *
 * 给 <img> 加上 crossorigin="anonymous" 后，图片请求也进入 CORS 模式：
 *   · 请求带 Origin 头 -> CDN 返回带 CORS 头的响应
 *   · 缓存条目与 fetch 的一致 -> 下载直接命中缓存，0 额外网络传输
 * 实测：首次加载 2774ms（网络），随后 fetch 仅 7ms（纯缓存）→ 快 427 倍。
 *
 * 【为什么条件性设置，而不是写死】
 * CDN 拿不到图时会回退到同源 /images/...（见 imageSrcFinal）。同源地址
 * 若还带 crossorigin，浏览器会按 CORS 规则校验，而后端静态挂载**不返回**
 * CORS 头 —— 那会让图片直接加载失败。
 * 所以只在跨源（CDN）地址上启用，同源回退时保持普通 <img> 行为。
 */
const imgCrossOrigin = computed(() => {
  const src = currentSrc.value
  return src && isCdnUrl(src) ? 'anonymous' : undefined
})

const loadingStrategy = computed(() => {
  return (props.index ?? 0) < EAGER_LOAD_COUNT ? 'eager' : 'lazy'
})

const tags = computed(() => {
  if (!props.image.tags) return []
  return props.image.tags.split(' ').filter(t => t.trim())
})

const isTempMode = computed(() => !!props.tempMode)

const isTrashImage = computed(() => tags.value.includes('trash_bin'))

const extLabel = computed(() => {
  // filename 现在是分片相对路径（如 "00/be/00be....jpg"），
  // 所以先取文件名部分再取扩展名。
  const baseName = props.image.filename.split('/').pop() || ''
  const parts = baseName.split('.')
  const ext = parts.length > 1 ? parts[parts.length - 1] : ''
  return ext ? ext.toUpperCase() : ''
})

const sizeLabel = computed(() => {
  if (props.image.file_size === undefined || props.image.file_size === null) return ''
  return (props.image.file_size / (1024 * 1024)).toFixed(3) + 'MB'
})

const dimensionLabel = computed(() => {
  if (props.image.width === undefined || props.image.height === undefined) return ''
  return `${props.image.width}x${props.image.height}`
})

watch(() => props.preferHQ, (newVal) => {
  if (newVal && currentSrcType.value === 'thumbnail') {
    loadOriginalImage()
  }
})

function handleImageClick() {
  // 每次点击图片都切换工具栏：触屏靠它唤出，电脑端语义不变（本来就有 hover）
  toolbarVisible.value = !toolbarVisible.value

  if (isTempMode.value) {
    emit('applyTempTags', props.image)
    return
  }
  loadOriginalImage()
}

function copyText(text: string) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text)
  }
  return new Promise<void>((resolve, reject) => {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-9999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    try {
      document.execCommand('copy')
      document.body.removeChild(textArea)
      resolve()
    } catch (err) {
      document.body.removeChild(textArea)
      reject(err)
    }
  })
}

function handleCopy() {
  const tagsText = (props.image.tags || '').trim()
  copyText(tagsText)
    .then(() => {
      if (copyResetTimer !== null) {
        window.clearTimeout(copyResetTimer)
      }
      copySuccess.value = true
      copyResetTimer = window.setTimeout(() => {
        copySuccess.value = false
        copyResetTimer = null
      }, 1500)
    })
    .catch((err) => {
      console.error('Failed to copy', err)
    })
}

function handleDelete() {
  emit('delete', props.image)
}

/**
 * 下载原图。
 *
 * 【为什么不能直接用 <a download>】
 * `download` 属性只对**同源** URL 生效。本项目配了 CDN 后
 * imageSrc 指向 https://bqbq-img.mmc199.com/...，属于跨源，
 * 浏览器会直接忽略 download 属性并导航到该地址 —— 表现为
 * 「点下载跳进了图片页面」而不是保存文件。
 *
 * 【核心：与预览共用同一份缓存，全流程只走一遍网络】
 * 原图 <img> 带 crossorigin="anonymous"（见 imgCrossOrigin），
 * 预览时就把「带 CORS 头」的响应写进了浏览器缓存。
 * 下载这里用 mode:'cors' 发同样的请求，即可**直接命中缓存**。
 *
 *   · 预览：<img crossorigin>  → 网络下载一次（并写入缓存）
 *   · 下载：fetch mode:'cors'  → 命中缓存，0 额外网络传输
 *
 * 实测（cors-cache-test.html）：首次 2774ms，fetch 仅 7ms，快 427 倍。
 * 流量全部由 Cloudflare/R2 承担，不占用后端带宽。
 *
 * 【同源兜底】
 * CDN 拿不到图时（R2 尚未同步）回退 /images/<filename>，保证下载
 * 始终可用。同源地址不需要也不应带 mode:'cors'。
 *
 * 【顺带修掉的两个问题】
 *   1. 原来 href 用的是 imageSrc（CDN 直链），没有走 imageSrcFinal
 *      的「CDN 404 -> 本地后端」回退，R2 尚未同步时会下到 404。
 *   2. 原来 :download="downloadName" 传的是函数本身（漏了调用），
 *      这里改为 downloadName(props.image.filename) 取真正的文件名。
 */
const isDownloading = ref(false)

async function handleDownload() {
  if (isDownloading.value) return
  isDownloading.value = true

  const filename = downloadName(props.image.filename)
  // CDN 优先（与 <img crossorigin> 同缓存），同源兜底
  const candidates = [imageSrcFinal.value, localImageUrl(props.image.filename)]

  try {
    let blob: Blob | null = null
    let lastErr: unknown = null
    for (const url of candidates) {
      const isCdn = isCdnUrl(url)
      try {
        /**
         * mode: 'cors' —— 关键。
         *
         * 原图 <img> 已带 crossorigin="anonymous"（见 imgCrossOrigin），
         * 预览时就把「带 CORS 头」的响应存进了浏览器缓存。
         * 这里用同样的 CORS 模式 fetch，就能**直接命中那份缓存**，
         * 不再产生第二次网络传输 —— 预览和下载合计只走一遍。
         *
         * 实测：首次网络加载 2774ms，fetch 命中缓存仅 7ms。
         *
         * 同源兜底地址（/images/...）不需要 CORS，用默认模式即可；
         * 对同源也带 mode:'cors' 是合法的，但没必要，保持简单。
         */
        const res = await fetch(url, isCdn
          ? { mode: 'cors', credentials: 'omit' }
          : { credentials: 'same-origin' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        blob = await res.blob()
        break
      } catch (err) {
        lastErr = err
      }
    }
    if (!blob) throw lastErr ?? new Error('download failed')

    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    // 交给浏览器读完再释放，立即 revoke 会导致部分浏览器下载中断
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
  } catch (err) {
    console.error('下载失败，回退为直接打开链接', err)
    // 兜底：仍然让用户能拿到图（新标签打开，至少不是静默失败）
    window.open(candidates[0], '_blank', 'noopener')
  } finally {
    isDownloading.value = false
  }
}

function handleImageError() {
  // ---- 第一层回退：CDN -> 本地后端 ----
  // CDN 背后的 R2 由后端异步同步，新图会有短暂 404 窗口。
  // 这里换成后端直连地址再试一次，用户完全无感。
  if (currentSrcType.value === 'thumbnail') {
    if (!cdnFailedThumb.value && isCdnUrl(thumbnailSrc.value)) {
      cdnFailedThumb.value = true
      return // src 变化会触发浏览器重新加载
    }
    // 缩略图本地也失败时不自动切换，等待点击加载原图
    return
  }

  if (!cdnFailedImage.value && isCdnUrl(imageSrc.value)) {
    cdnFailedImage.value = true
    return // src 变化会触发重新加载
  }

  // ---- 两层都失败：真正标记为错误 ----
  imageError.value = true
  isOriginalLoading.value = false
}

function handleImageLoad() {
  if (currentSrcType.value === 'original') {
    isOriginalLoading.value = false
    imageError.value = false
  }
}

function loadOriginalImage() {
  if (currentSrcType.value === 'original' && !imageError.value) return
  imageError.value = false
  isOriginalLoading.value = true

  // 预加载原图；若 CDN 拿不到（R2 尚未同步），自动改用本地后端地址
  const tryLoad = (url: string, isFallback: boolean) => {
    const tempImg = new Image()

    /**
     * 【关键】这个预加载器也必须带 crossOrigin，且规则与模板里的 <img> 完全一致
     * （见 imgCrossOrigin）。
     *
     * 它加载的 URL 会被浏览器写进缓存。如果这里不带 crossOrigin：
     *   · 请求不带 Origin 头 -> CDN 返回"无 CORS 头"的响应
     *   · 缓存里存下的是这份"无 CORS"条目
     *   · 之后点下载用 fetch(mode:'cors') 时匹配不到该条目 -> 报 CORS 错并重下一次
     * 即：从缩略图点开原图这一步会把缓存"污染"成 fetch 不可用的形态。
     *
     * 带上 crossOrigin 后，预加载写下的就是带 CORS 头的条目，下载可直接复用。
     */
    if (isCdnUrl(url)) {
      tempImg.crossOrigin = 'anonymous'
    }

    tempImg.onload = () => {
      if (isFallback) cdnFailedImage.value = true
      currentSrcType.value = 'original'
      isOriginalLoading.value = false
      imageError.value = false
    }
    tempImg.onerror = () => {
      if (!isFallback && isCdnUrl(url)) {
        tryLoad(localImageUrl(props.image.filename), true)
        return
      }
      isOriginalLoading.value = false
      imageError.value = true
    }
    tempImg.src = url
  }

  tryLoad(imageSrcFinal.value, cdnFailedImage.value)
}

function openEditor() {
  if (isEditingTags.value) return
  editTags.value = [...tags.value]
  editInputValue.value = ''
  isEditingTags.value = true
  nextTick(() => {
    setTimeout(() => {
      document.addEventListener('click', handleOutsideClick)
    }, 0)
  })
}

function handleOutsideClick(e: MouseEvent) {
  const editorEl = editorRef.value
  if (editorEl && editorEl.contains(e.target as Node)) return
  finishEdit()
}

function finishEdit() {
  document.removeEventListener('click', handleOutsideClick)

  const pending = editInputValue.value.trim()
  if (pending) {
    tagInputRef.value?.addTag(pending)
  }

  const nextTags = [...editTags.value]
  const current = [...tags.value]
  const changed = nextTags.join(' ') !== current.join(' ')

  isEditingTags.value = false

  if (changed) {
    emit('updateTags', props.image, nextTags)
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
  if (copyResetTimer !== null) {
    window.clearTimeout(copyResetTimer)
  }
})
</script>

<template>
  <div
    :class="[
      'meme-card group relative rounded-xl overflow-hidden aspect-square bg-slate-200 shadow-sm hover:shadow-lg',
      isTrashImage ? 'is-trash' : '',
      imageError ? 'load-failed' : '',
      isTempMode ? 'temp-mode-card' : ''
    ]"
  >
    <img
      v-if="currentSrc"
      class="image-element w-full h-full object-contain"
      :src="currentSrc"
      :crossorigin="imgCrossOrigin"
      alt=""
      :loading="loadingStrategy"
      @click="handleImageClick"
      @load="handleImageLoad"
      @error="handleImageError"
    />

    <!-- 批量打包等待中：显示占位，不发任何单图请求 -->
    <div
      v-else
      class="absolute inset-0 flex items-center justify-center text-gray-300"
    >
      <Loader2 class="w-6 h-6 animate-spin" />
    </div>

    <!-- Loader for original load -->
    <div
      v-if="isOriginalLoading"
      class="loader-element absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white drop-shadow-md z-10"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="w-8 h-8 animate-spin-fast"
      >
        <path d="M5 22h14" />
        <path d="M5 2h14" />
        <path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22" />
        <path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2" />
      </svg>
    </div>

    <!-- Error Overlay -->
    <div
      v-if="imageError"
      class="error-overlay absolute inset-0 text-red-500 flex flex-col items-center justify-center text-center p-4 z-20 cursor-pointer rounded-xl transition-opacity hover:opacity-90"
      @click.stop="loadOriginalImage"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="w-10 h-10"
      >
        <path d="m21.73 18-9-15-9 15z" />
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
      </svg>
    </div>

    <!-- 顶部工具栏 -->
    <!--
      显隐：电脑端靠 group-hover（原有行为），触屏靠点击图片切换 toolbarVisible。
      保留 hidden 作为默认，flex 由两种途径之一命中。
    -->
    <div
      :class="[
        'top-toolbar absolute top-0 left-0 right-0 p-2 justify-between items-start z-30',
        toolbarVisible ? 'flex' : 'hidden group-hover:flex'
      ]"
      @click.stop
    >
      <button
        type="button"
        class="download-btn p-2 bg-black/40 text-white rounded-lg hover:bg-black/60 transition disabled:opacity-60"
        :disabled="isDownloading"
        :title="isDownloading ? '下载中…' : '下载原图'"
        @click.stop="handleDownload"
      >
        <Loader2 v-if="isDownloading" class="w-5 h-5 animate-spin" />
        <Download v-else class="w-5 h-5" />
      </button>
      <div class="flex gap-2">
        <!-- 购物车切换（放在复制按钮左边） -->
        <button
          :class="[
            'cart-btn p-2 rounded-lg transition',
            inCart ? 'bg-amber-500 text-white' : 'bg-black/40 text-white hover:bg-black/60'
          ]"
          :title="inCart ? '移出购物车' : '加入购物车'"
          :disabled="cartBusy"
          @click.stop="toggleCart"
        >
          <Loader2 v-if="cartBusy" class="w-5 h-5 animate-spin" />
          <ShoppingCart v-else class="w-5 h-5" />
        </button>
        <button
          :class="[
            'copy-btn p-2 rounded-lg transition',
            copySuccess ? 'bg-green-500 text-white' : 'bg-black/40 text-white hover:bg-black/60'
          ]"
          @click.stop="handleCopy"
        >
          <Check v-if="copySuccess" class="w-5 h-5" />
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="w-5 h-5"
          >
            <rect width="8" height="14" x="4" y="8" rx="2" />
            <path d="M15 4h-2a2 2 0 0 0-2 2v2" />
            <rect width="8" height="14" x="12" y="2" rx="2" ry="2" />
          </svg>
        </button>
        <button
          :class="[
            'delete-btn p-2 rounded-lg hover:bg-black/60 transition',
            isTrashImage ? 'bg-red-500 text-white' : 'bg-black/40 text-white'
          ]"
          @click.stop="handleDelete"
        >
          <RefreshCw v-if="isTrashImage" class="w-5 h-5" />
          <Trash2 v-else class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- 底部覆盖层 -->
    <div class="image-overlay absolute bottom-0 left-0 right-0 p-3 pt-8 flex flex-col justify-end text-white transition-opacity duration-300">
      <div class="image-info text-[12px] font-mono opacity-80 mb-1 leading-tight">
        <span v-if="extLabel">{{ extLabel }}</span>
        <br v-if="extLabel && (dimensionLabel || sizeLabel)" />
        <span v-if="dimensionLabel">{{ dimensionLabel }}</span>
        <br v-if="dimensionLabel && sizeLabel" />
        <span v-if="sizeLabel">{{ sizeLabel }}</span>
      </div>

      <div
        v-if="!isEditingTags"
        class="tags-container-element flex flex-wrap gap-1 cursor-pointer"
        @click.stop="openEditor"
      >
        <template v-if="tags.length > 0">
          <span
            v-for="tag in tags"
            :key="tag"
            class="overlay-tag px-2 py-1 rounded text-sm font-medium shadow-sm"
          >
            {{ tag }}
          </span>
        </template>
        <span v-else class="text-sm opacity-60 italic">&nbsp;</span>
      </div>

      <div v-else ref="editorRef">
        <TagInput
          ref="tagInputRef"
          v-model="editTags"
          suggestions-id="tag-suggestions"
          placeholder="添加标签..."
          theme="blue"
          :enable-excludes="false"
          :auto-focus="true"
          container-class="tag-editor-container w-full bg-white/95 rounded p-1 flex flex-wrap gap-1 items-center animate-in fade-in slide-in-from-bottom-2 border border-blue-300 shadow-lg text-slate-800"
          @submit="finishEdit"
          @input-update="editInputValue = $event"
        />
      </div>
    </div>
  </div>
</template>
