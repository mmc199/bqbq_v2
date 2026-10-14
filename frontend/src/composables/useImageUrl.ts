/**
 * 图片资源地址解析
 *
 * 背景
 * ----
 * 图片按 md5 分片存放（`ab/cd/<md5>.<ext>`），
 * 数据库 `filename` 存的就是这个相对路径，例如 `7f/5d/7f5d....gif`。
 *
 * 默认（本地 / 自建服务器）：直接请求后端
 *     /images/7f/5d/7f5d....gif
 *     /thumbnails/7f/5d/7f5d....gif
 *
 * 配了 CDN（例如 Cloudflare R2 + 自定义域名）后改成请求 CDN：
 *     https://img.example.com/meme_images/7f/5d/7f5d....gif
 *     https://img.example.com/meme_images_thumbnail/7f/5d/7f5d...._thumbnail.jpg
 *
 * 用法：在项目根目录建 `.env.local`：
 *     VITE_CDN_BASE_URL=https://img.example.com
 * 不设置时保持原有本地行为，因此**本地开发与线上 CDN 可以共存**。
 */

const CDN_BASE = (import.meta.env.VITE_CDN_BASE_URL as string | undefined)?.replace(/\/+$/, '') || ''

/**
 * 缩略图 CDN 基地址（可选，独立于原图）。
 *
 * 之所以分开配置：原图和缩略图可以分批上传。
 * 例如本项目目前只把原图传到了 R2，缩略图仍在本地，
 * 那就只设 VITE_CDN_BASE_URL，缩略图继续走后端。
 */
const CDN_THUMB_BASE =
  (import.meta.env.VITE_CDN_THUMB_BASE_URL as string | undefined)?.replace(/\/+$/, '') || ''

export const cdnEnabled = CDN_BASE.length > 0

/** 原图地址（可能指向 CDN） */
export function imageUrl(filename: string): string {
  if (!CDN_BASE) return `/images/${filename}`
  return `${CDN_BASE}/meme_images/${filename}`
}

/** 缩略图地址（可能指向 CDN） */
export function thumbnailUrl(filename: string): string {
  // 缩略图没配 CDN 时，一律走本地后端（避免 404）
  if (!CDN_THUMB_BASE) return `/thumbnails/${filename}`
  // 缩略图命名规则：<md5>_thumbnail.jpg，分片目录保持一致
  const base = filename.replace(/\.[^./]+$/, '')
  return `${CDN_THUMB_BASE}/meme_images_thumbnail/${base}_thumbnail.jpg`
}

// ---------------------------------------------------------------------------
// 本地回退地址
// ---------------------------------------------------------------------------
//
// 【为什么需要】CDN 背后的 R2 需要后端同步才有新图。同步是异步的，
// 会有短暂的「已入库但 R2 还没有」窗口；同步失败时窗口更长。
// 此时 CDN 返回 404 —— 图片加载失败后应自动回退到本地后端接口。

/** 本地原图地址（始终走本后端，不经过 CDN） */
export function localImageUrl(filename: string): string {
  return `/images/${filename}`
}

/** 本地缩略图地址（始终走本后端） */
export function localThumbnailUrl(filename: string): string {
  return `/thumbnails/${filename}`
}

/** 该地址是否已经指向 CDN（用于判断还有没有回退空间） */
export function isCdnUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://')
}

/** 下载文件名：只取纯文件名，避免带出 `ab/cd/` 目录前缀 */
export function downloadName(filename: string): string {
  return filename.split('/').pop() || filename
}
