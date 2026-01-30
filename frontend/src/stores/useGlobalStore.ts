/**
 * 全局状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { RulesTree } from '@/types'

const CLIENT_ID_KEY = 'bqbq_client_id'
const RULES_VERSION_KEY = 'bqbq_rules_version'
const RULES_TREE_KEY = 'bqbq_rules_tree'
const RULES_TREE_TIMESTAMP_KEY = 'bqbq_rules_tree_timestamp'
const PREFERENCES_KEY = 'bqbq_preferences'
const TAG_CACHE_KEY = 'bqbq_tag_cache'
const TAG_TIMESTAMP_KEY = 'bqbq_tag_timestamp'
const TAG_CACHE_TTL = 10 * 60 * 1000 // 10 分钟缓存有效期
const RULES_TREE_CACHE_TTL = 10 * 60 * 1000 // 规则树缓存 10 分钟

// 用户偏好设置类型
interface UserPreferences {
  isExpansionEnabled: boolean
  isHQMode: boolean
  sortBy: string
  fabCollapsed: boolean
}

// 默认偏好设置
const defaultPreferences: UserPreferences = {
  isExpansionEnabled: true,
  isHQMode: false,
  sortBy: 'time_desc',
  fabCollapsed: false,
}

// 从 localStorage 加载偏好设置
function loadPreferences(): UserPreferences {
  try {
    const saved = localStorage.getItem(PREFERENCES_KEY)
    if (saved) {
      return { ...defaultPreferences, ...JSON.parse(saved) }
    }
  } catch (e) {
    console.warn('加载偏好设置失败:', e)
  }
  return { ...defaultPreferences }
}

// 生成客户端唯一 ID
function generateClientId(): string {
  return 'client_' + Math.random().toString(36).substring(2, 15)
}

export const useGlobalStore = defineStore('global', () => {
  // 客户端 ID（持久化）
  const clientId = ref<string>(
    localStorage.getItem(CLIENT_ID_KEY) || generateClientId()
  )

  // 规则树版本号
  const rulesVersion = ref<number>(
    parseInt(localStorage.getItem(RULES_VERSION_KEY) || '0', 10)
  )

  // 规则树数据
  const rulesTree = ref<RulesTree | null>(null)

  // 全局加载状态
  const isLoading = ref(false)

  // 用户偏好设置（持久化）
  const preferences = ref<UserPreferences>(loadPreferences())

  // 标签缓存
  const tagCache = ref<string[]>([])
  const tagCacheTimestamp = ref<number>(0)

  // 保存偏好设置
  function savePreferences() {
    try {
      localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences.value))
    } catch (e) {
      console.warn('保存偏好设置失败:', e)
    }
  }

  // 监听偏好设置变化，自动保存
  watch(preferences, savePreferences, { deep: true })

  // 更新单个偏好设置
  function updatePreference<K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) {
    preferences.value[key] = value
  }

  // 保存客户端 ID
  function saveClientId() {
    localStorage.setItem(CLIENT_ID_KEY, clientId.value)
  }

  // 更新规则版本
  function updateRulesVersion(version: number) {
    rulesVersion.value = version
    localStorage.setItem(RULES_VERSION_KEY, version.toString())
  }

  // 设置规则树（同时保存到 LocalStorage）
  function setRulesTree(tree: RulesTree) {
    rulesTree.value = tree
    updateRulesVersion(tree.version)
    saveRulesTreeCache(tree)
  }

  // 规则树缓存相关方法（与旧项目保持一致）
  function loadRulesTreeCache(): RulesTree | null {
    try {
      const cached = localStorage.getItem(RULES_TREE_KEY)
      const timestamp = localStorage.getItem(RULES_TREE_TIMESTAMP_KEY)

      if (cached && timestamp) {
        const ts = parseInt(timestamp, 10)
        if (Date.now() - ts < RULES_TREE_CACHE_TTL) {
          const tree = JSON.parse(cached) as RulesTree
          rulesTree.value = tree
          return tree
        }
      }
    } catch (e) {
      console.warn('加载规则树缓存失败:', e)
    }
    return null
  }

  function saveRulesTreeCache(tree: RulesTree) {
    try {
      const now = Date.now()
      localStorage.setItem(RULES_TREE_KEY, JSON.stringify(tree))
      localStorage.setItem(RULES_TREE_TIMESTAMP_KEY, now.toString())
    } catch (e) {
      console.warn('保存规则树缓存失败:', e)
    }
  }

  function clearRulesTreeCache() {
    localStorage.removeItem(RULES_TREE_KEY)
    localStorage.removeItem(RULES_TREE_TIMESTAMP_KEY)
  }

  function isRulesTreeCacheValid(): boolean {
    const timestamp = localStorage.getItem(RULES_TREE_TIMESTAMP_KEY)
    if (!timestamp) return false
    return Date.now() - parseInt(timestamp, 10) < RULES_TREE_CACHE_TTL
  }

  // 标签缓存相关方法
  function loadTagCache(): string[] | null {
    try {
      const cached = localStorage.getItem(TAG_CACHE_KEY)
      const timestamp = localStorage.getItem(TAG_TIMESTAMP_KEY)

      if (cached && timestamp) {
        const ts = parseInt(timestamp, 10)
        if (Date.now() - ts < TAG_CACHE_TTL) {
          tagCache.value = JSON.parse(cached)
          tagCacheTimestamp.value = ts
          return tagCache.value
        }
      }
    } catch (e) {
      console.warn('加载标签缓存失败:', e)
    }
    return null
  }

  function saveTagCache(tags: string[]) {
    try {
      const now = Date.now()
      localStorage.setItem(TAG_CACHE_KEY, JSON.stringify(tags))
      localStorage.setItem(TAG_TIMESTAMP_KEY, now.toString())
      tagCache.value = tags
      tagCacheTimestamp.value = now
    } catch (e) {
      console.warn('保存标签缓存失败:', e)
    }
  }

  function clearTagCache() {
    localStorage.removeItem(TAG_CACHE_KEY)
    localStorage.removeItem(TAG_TIMESTAMP_KEY)
    tagCache.value = []
    tagCacheTimestamp.value = 0
  }

  function isTagCacheValid(): boolean {
    return tagCacheTimestamp.value > 0 && Date.now() - tagCacheTimestamp.value < TAG_CACHE_TTL
  }

  // 初始化
  function init() {
    saveClientId()
    loadTagCache()
    loadRulesTreeCache()
  }

  // 计算属性：是否有规则树
  const hasRulesTree = computed(() => rulesTree.value !== null)

  return {
    clientId,
    rulesVersion,
    rulesTree,
    isLoading,
    hasRulesTree,
    preferences,
    tagCache,
    saveClientId,
    updateRulesVersion,
    setRulesTree,
    updatePreference,
    loadTagCache,
    saveTagCache,
    clearTagCache,
    isTagCacheValid,
    loadRulesTreeCache,
    saveRulesTreeCache,
    clearRulesTreeCache,
    isRulesTreeCacheValid,
    init,
  }
})
