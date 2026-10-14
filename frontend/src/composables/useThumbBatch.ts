/**
 * 缩略图批量加载（一次请求打包整页）
 *
 * 背景
 * ----
 * 生产链路是「中国服务器 → 内网穿透 → 美国服务器」，
 * 单次往返 RTT 约 200ms、带宽约 5Mbps，而一页最多 100 张缩略图。
 *
 * 逐个请求的代价：
 *     50 张 ÷ 浏览器 6 并发 = 9 轮 × 200ms = 1800ms 的纯等待开销
 * 合并成一次请求后：这部分降到 1 轮（约 200ms）。
 *
 * 为什么用 ZIP
 * ------------
 * ① 通用格式：出问题能用任何解压工具直接打开排查
 * ② 后端用 ZIP_STORED（不压缩）：缩略图是 JPEG，已高度压缩，
 *    再套 deflate 只能省 1-2%，却要多付服务端 CPU 和前端解压时间。
 *    实测 50 张仅多约 0.5% 体积（ZIP 头部开销）。
 *
 * 为什么在 store 里集中管理
 * -------------------------
 * 一个页面有几十张卡片，如果每张卡片各自请求就退化成原来的问题了。
 * 所以由这里统一「收集本页所有 md5 → 一次打包 → 解压后分发」。
 */
import JSZip from 'jszip'

/** 单个 blob 的 objectURL 需要手动释放，否则会内存泄漏 */
type Entry = { url: string; ts: number }

const cache = new Map<string, Entry>()
/** 正在进行的打包请求，避免同一页重复发起 */
const inflight = new Map<string, Promise<void>>()

/** 已创建的 objectURL 上限，超出后按创建时间淘汰最旧的 */
const MAX_CACHED = 600

// ---------------------------------------------------------------------------
// 「批量是否还在进行」的全局状态
// ---------------------------------------------------------------------------
//
// 【为什么必须有这个】
// 卡片挂载时会查缓存，如果没查到就【立刻】回退到单图 URL，
// 那么浏览器马上就会发出 N 个独立请求 —— 等 batch 返回时早已晚了，
// batch 的作用被完全抵消（实测就是这个现象：zip 还在下载，图片已逐张加载）。
//
// 所以卡片需要知道「现在是否还有批量任务在跑」：
//   pending  -> 显示占位，不发任何单图请求
//   settled  -> 仍未命中才回退到单图 URL（例如批量失败、或该图不在本批里）
let pendingCount = 0
const settledListeners = new Set<() => void>()

/** 当前是否还有批量任务在跑 */
export function isBatchPending(): boolean {
  return pendingCount > 0
}

/** 订阅「批量任务全部结束」，返回取消订阅函数 */
export function onBatchSettled(fn: () => void): () => void {
  settledListeners.add(fn)
  return () => {
    settledListeners.delete(fn)
  }
}

function bumpPending(delta: number) {
  pendingCount += delta
  if (pendingCount <= 0) {
    pendingCount = 0
    for (const fn of [...settledListeners]) {
      try {
        fn()
      } catch {
        /* 单个监听器异常不影响其它 */
      }
    }
  }
}

function evictIfNeeded() {
  if (cache.size <= MAX_CACHED) return
  const sorted = [...cache.entries()].sort((a, b) => a[1].ts - b[1].ts)
  const removeCount = cache.size - MAX_CACHED
  for (let i = 0; i < removeCount; i++) {
    const item = sorted[i]
    if (!item) continue
    const [k, v] = item
    URL.revokeObjectURL(v.url)
    cache.delete(k)
  }
}

/** 取出已解压好的缩略图 URL；没有则返回 null */
export function getThumbBlobUrl(md5: string): string | null {
  const hit = cache.get(md5.toLowerCase())
  return hit ? hit.url : null
}

/**
 * 打包拉取一批缩略图并解压进缓存。
 *
 * @param md5List 本页所有图片的 md5
 * @param batchUrl 后端批量接口地址（默认 /thumbnails/batch）
 * @returns 成功解压的张数
 */
export async function preloadThumbnails(
  md5List: string[],
  batchUrl = '/thumbnails/batch'
): Promise<number> {
  const wanted = [...new Set(md5List.map(m => (m || '').toLowerCase()).filter(Boolean))]
    .filter(m => !cache.has(m))

  if (wanted.length === 0) return 0

  // 同一批只发一次（翻页抖动/重复调用时合并）
  const key = wanted.slice().sort().join(',')
  const running = inflight.get(key)
  if (running) {
    await running
    return wanted.filter(m => cache.has(m)).length
  }

  const task = (async () => {
    // 后端最多接受 200 个，超出就分批（正常一页不会超）
    const CHUNK = 200
    for (let i = 0; i < wanted.length; i += CHUNK) {
      const chunk = wanted.slice(i, i + CHUNK)
      let resp: Response
      try {
        resp = await fetch(batchUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ md5: chunk }),
        })
      } catch {
        return
      }
      if (!resp.ok) continue

      let zip: JSZip
      try {
        zip = await JSZip.loadAsync(await resp.arrayBuffer())
      } catch {
        continue
      }

      // 并行解压：每个文件是独立的 Uint8Array
      await Promise.all(
        Object.keys(zip.files).map(async name => {
          const file = zip.files[name]
          if (!file || file.dir) return
          try {
            const data = await file.async('blob')
            const url = URL.createObjectURL(data)
            // zip 内文件名就是 md5
            cache.set(name.toLowerCase(), { url, ts: Date.now() })
          } catch {
            /* 单个失败不影响其它 */
          }
        })
      )
    }
    evictIfNeeded()
  })()

  inflight.set(key, task)
  // 标记「有批量任务在跑」，卡片在此期间显示占位而不是发单图请求
  bumpPending(+1)
  try {
    await task
  } finally {
    inflight.delete(key)
    bumpPending(-1)
  }
  return wanted.filter(m => cache.has(m)).length
}

/** 释放全部缓存（例如切换搜索条件时） */
export function clearThumbCache() {
  for (const v of cache.values()) URL.revokeObjectURL(v.url)
  cache.clear()
  inflight.clear()
}
