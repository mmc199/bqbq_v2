/**
 * 乐观更新和冲突重试机制
 * 支持 CAS (Compare-And-Swap) 操作的自动重试
 */
import { ref } from 'vue'
import { useGlobalStore } from '@/stores/useGlobalStore'
import { useToast } from './useToast'

// 最大重试次数
const MAX_RETRIES = 3
// 重试延迟（毫秒）
const RETRY_DELAY = 500

interface OptimisticUpdateOptions<R> {
  // 乐观更新函数：立即更新本地状态
  optimisticUpdate: () => void
  // 实际 API 调用
  apiCall: (clientId: string, baseVersion: number) => Promise<{ success: boolean; data?: R; error?: string }>
  // 成功回调
  onSuccess?: (data: R) => void
  // 失败回调：回滚本地状态
  onError?: (error: string) => void
  // 冲突回调：获取最新数据后重试
  onConflict?: () => Promise<void>
  // 是否显示 toast 提示
  showToast?: boolean
}

export function useOptimisticUpdate() {
  const globalStore = useGlobalStore()
  const toast = useToast()
  const isUpdating = ref(false)

  /**
   * 执行乐观更新操作
   */
  async function execute<R>(options: OptimisticUpdateOptions<R>): Promise<boolean> {
    const {
      optimisticUpdate,
      apiCall,
      onSuccess,
      onError,
      onConflict,
      showToast = true,
    } = options

    isUpdating.value = true

    // 1. 先执行乐观更新
    optimisticUpdate()

    // 2. 尝试 API 调用（带重试）
    let retries = 0
    let lastError = ''

    while (retries < MAX_RETRIES) {
      const result = await apiCall(globalStore.clientId, globalStore.rulesVersion)

      if (result.success && result.data) {
        // 成功：更新版本号
        if ((result.data as any).new_version) {
          globalStore.updateRulesVersion((result.data as any).new_version)
        }
        onSuccess?.(result.data)
        isUpdating.value = false
        return true
      }

      // 检查是否是版本冲突（409）
      if (result.error?.includes('409') || result.error?.includes('conflict') || result.error?.includes('版本')) {
        retries++
        if (retries < MAX_RETRIES) {
          // 冲突：获取最新数据后重试
          if (onConflict) {
            await onConflict()
          }
          // 等待一段时间后重试
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
          continue
        }
      }

      lastError = result.error || '操作失败'
      break
    }

    // 3. 失败：回滚
    onError?.(lastError)
    if (showToast) {
      if (retries >= MAX_RETRIES) {
        toast.error('版本冲突，请刷新后重试')
      } else {
        toast.error(lastError)
      }
    }

    isUpdating.value = false
    return false
  }

  /**
   * 简化版：直接执行 API 调用（无乐观更新）
   */
  async function executeWithRetry<R>(
    apiCall: (clientId: string, baseVersion: number) => Promise<{ success: boolean; data?: R; error?: string }>,
    onConflict?: () => Promise<void>
  ): Promise<{ success: boolean; data?: R; error?: string }> {
    let retries = 0

    while (retries < MAX_RETRIES) {
      const result = await apiCall(globalStore.clientId, globalStore.rulesVersion)

      if (result.success && result.data) {
        if ((result.data as any).new_version) {
          globalStore.updateRulesVersion((result.data as any).new_version)
        }
        return result
      }

      // 检查是否是版本冲突
      if (result.error?.includes('409') || result.error?.includes('conflict')) {
        retries++
        if (retries < MAX_RETRIES && onConflict) {
          await onConflict()
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
          continue
        }
      }

      return result
    }

    return { success: false, error: '版本冲突，请刷新后重试' }
  }

  return {
    isUpdating,
    execute,
    executeWithRetry,
  }
}
