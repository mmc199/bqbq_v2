/**
 * 全局状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { RulesTree } from '@/types'

const CLIENT_ID_KEY = 'bqbq_client_id'
const RULES_VERSION_KEY = 'bqbq_rules_version'
const RULES_CACHE_KEY = 'bqbq_rules_cache'
const TAG_CACHE_KEY = 'bqbq_tag_cache'
const TAG_TIMESTAMP_KEY = 'bqbq_tag_timestamp'
const PREFER_HQ_KEY = 'bqbq_prefer_hq'
const EXPANSION_KEY = 'bqbq_expansion_enabled'
const FAB_COLLAPSED_KEY = 'bqbq_fab_collapsed'
const FAB_MINI_POSITION_KEY = 'bqbq_fab_mini_position'
const TREE_EXPANDED_KEY = 'bqbq_tree_expanded'

const TAG_CACHE_TTL = 10 * 60 * 1000 // 10 分钟缓存有效期

// 生成客户端唯一 ID
function generateClientId(): string {
  return 'client_' + Math.random().toString(36).substring(2, 15)
}

function loadBooleanFromStorage(storage: Storage, key: string, defaultValue: boolean) {
  try {
    const saved = storage.getItem(key)
    if (saved !== null) {
      return saved === 'true'
    }
  } catch (e) {
    console.warn(`读取 ${key} 失败:`, e)
  }
  return defaultValue
}

function saveBooleanToStorage(storage: Storage, key: string, value: boolean) {
  try {
    storage.setItem(key, value.toString())
  } catch (e) {
    console.warn(`写入 ${key} 失败:`, e)
  }
}

function loadNumberFromStorage(storage: Storage, key: string): number | null {
  try {
    const saved = storage.getItem(key)
    if (saved !== null) {
      const parsed = parseInt(saved, 10)
      if (!Number.isNaN(parsed)) {
        return parsed
      }
    }
  } catch (e) {
    console.warn(`读取 ${key} 失败:`, e)
  }
  return null
}

function loadJsonFromStorage<T>(storage: Storage, key: string, fallback: T): T {
  try {
    const saved = storage.getItem(key)
    if (saved) {
      return JSON.parse(saved) as T
    }
  } catch (e) {
    console.warn(`读取 ${key} 失败:`, e)
  }
  return fallback
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

  // 旧项目一致的偏好存储
  const preferHQ = ref(loadBooleanFromStorage(localStorage, PREFER_HQ_KEY, false))
  const isExpansionEnabled = ref(loadBooleanFromStorage(sessionStorage, EXPANSION_KEY, true))
  const fabCollapsed = ref(loadBooleanFromStorage(sessionStorage, FAB_COLLAPSED_KEY, true))
  const fabMiniPosition = ref<number | null>(loadNumberFromStorage(sessionStorage, FAB_MINI_POSITION_KEY))
  const expandedGroupIds = ref<number[]>(loadJsonFromStorage<number[]>(sessionStorage, TREE_EXPANDED_KEY, []))

  // 标签缓存
  const tagCache = ref<string[]>([])
  const tagCacheTimestamp = ref<number>(0)

  watch(preferHQ, (val) => saveBooleanToStorage(localStorage, PREFER_HQ_KEY, val))
  watch(isExpansionEnabled, (val) => saveBooleanToStorage(sessionStorage, EXPANSION_KEY, val))
  watch(fabCollapsed, (val) => saveBooleanToStorage(sessionStorage, FAB_COLLAPSED_KEY, val))
  watch(fabMiniPosition, (val) => {
    try {
      if (val === null) {
        sessionStorage.removeItem(FAB_MINI_POSITION_KEY)
      } else {
        sessionStorage.setItem(FAB_MINI_POSITION_KEY, val.toString())
      }
    } catch (e) {
      console.warn('保存 FAB 迷你位置失败:', e)
    }
  })
  watch(expandedGroupIds, (val) => {
    try {
      sessionStorage.setItem(TREE_EXPANDED_KEY, JSON.stringify(val))
    } catch (e) {
      console.warn('保存规则树展开状态失败:', e)
    }
  }, { deep: true })

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

  // 规则树缓存（旧项目 key）
  function loadRulesTreeCache(): RulesTree | null {
    try {
      const cached = localStorage.getItem(RULES_CACHE_KEY)
      if (cached) {
        const tree = JSON.parse(cached) as RulesTree
        rulesTree.value = tree
        return tree
      }
    } catch (e) {
      console.warn('加载规则树缓存失败:', e)
    }
    return null
  }

  function saveRulesTreeCache(tree: RulesTree) {
    try {
      localStorage.setItem(RULES_CACHE_KEY, JSON.stringify(tree))
    } catch (e) {
      console.warn('保存规则树缓存失败:', e)
    }
  }

  function clearRulesTreeCache() {
    localStorage.removeItem(RULES_CACHE_KEY)
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

  // 公开的状态更新方法
  function setPreferHQ(value: boolean) {
    preferHQ.value = value
  }

  function setExpansionEnabled(value: boolean) {
    isExpansionEnabled.value = value
  }

  function setFabCollapsed(value: boolean) {
    fabCollapsed.value = value
  }

  function setFabMiniPosition(value: number | null) {
    fabMiniPosition.value = value
  }

  function setExpandedGroupIds(ids: number[]) {
    expandedGroupIds.value = ids
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
    preferHQ,
    isExpansionEnabled,
    fabCollapsed,
    fabMiniPosition,
    expandedGroupIds,
    tagCache,
    saveClientId,
    updateRulesVersion,
    setRulesTree,
    loadRulesTreeCache,
    saveRulesTreeCache,
    clearRulesTreeCache,
    loadTagCache,
    saveTagCache,
    clearTagCache,
    isTagCacheValid,
    setPreferHQ,
    setExpansionEnabled,
    setFabCollapsed,
    setFabMiniPosition,
    setExpandedGroupIds,
    init,
  }
})
