/**
 * BQBQ 类型定义
 */

// 图片相关类型
export interface MemeImage {
  id: number
  filename: string
  md5: string
  tags: string
  created_at: string
  file_size?: number
  width?: number
  height?: number
}

export interface ImageUploadRequest {
  filename: string
  md5: string
  tags: string[]
  base64_data: string
}

export interface ImageUpdateRequest {
  id: number
  tags: string[]
  client_id: string
  base_version: number
}

// 搜索相关类型
export interface SearchRequest {
  include_tags: string[]
  exclude_tags: string[]
  page?: number
  page_size?: number
}

export interface SearchResponse {
  images: MemeImage[]
  total: number
  page: number
  page_size: number
  expanded_tags?: string[]
}

// 规则树相关类型
export interface RuleKeyword {
  id: number
  keyword: string
  group_id: number
}

export interface RuleGroup {
  id: number
  name: string
  keywords: RuleKeyword[]
  children: RuleGroup[]
}

export interface RulesTree {
  version: number
  groups: RuleGroup[]
}

// CAS 相关类型
export interface CASRequest {
  client_id: string
  base_version: number
}

export interface CASResponse {
  success: boolean
  new_version: number
  conflicts: number
  message?: string
}

// API 响应类型
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// 全局状态类型
export interface GlobalState {
  clientId: string
  rulesVersion: number
  rulesTree: RulesTree | null
  isLoading: boolean
}

// 标签输入组件配置
export interface TagInputConfig {
  placeholder?: string
  theme?: 'blue' | 'purple' | 'mixed'
  enableExcludes?: boolean
  autoFocus?: boolean
}

// 标签类型
export interface Tag {
  value: string
  isExclude: boolean
}
