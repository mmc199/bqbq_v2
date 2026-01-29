/**
 * 全局状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RulesTree } from '@/types'

const CLIENT_ID_KEY = 'bqbq_client_id'
const RULES_VERSION_KEY = 'bqbq_rules_version'

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

  // 保存客户端 ID
  function saveClientId() {
    localStorage.setItem(CLIENT_ID_KEY, clientId.value)
  }

  // 更新规则版本
  function updateRulesVersion(version: number) {
    rulesVersion.value = version
    localStorage.setItem(RULES_VERSION_KEY, version.toString())
  }

  // 设置规则树
  function setRulesTree(tree: RulesTree) {
    rulesTree.value = tree
    updateRulesVersion(tree.version)
  }

  // 初始化
  function init() {
    saveClientId()
  }

  // 计算属性：是否有规则树
  const hasRulesTree = computed(() => rulesTree.value !== null)

  return {
    clientId,
    rulesVersion,
    rulesTree,
    isLoading,
    hasRulesTree,
    saveClientId,
    updateRulesVersion,
    setRulesTree,
    init,
  }
})
