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
  // 新增参数 - 与旧项目一致
  min_tags?: number | null
  max_tags?: number | null
  sort_by?: string
  extensions?: string[]
  exclude_extensions?: string[]
  expand?: boolean  // 是否启用关键词膨胀
}

// 高级搜索请求（兼容旧项目二维数组格式）
export interface AdvancedSearchRequest {
  // 二维数组：每个子数组是一个标签膨胀后的关键词列表（子数组内OR，子数组间AND）
  keywords: string[][]
  // 二维数组：每个子数组是一个排除标签膨胀后的关键词列表
  excludes: string[][]
  // 三维数组：交集排除
  excludes_and: string[][][]
  // 包含的扩展名列表
  extensions: string[]
  // 排除的扩展名列表
  exclude_extensions: string[]
  // 分页
  offset: number
  limit: number
  // 排序
  sort_by: string
  // 标签数量筛选
  min_tags: number
  max_tags: number
}

export interface AdvancedSearchResponse {
  total: number
  results: {
    id: number
    md5: string
    filename: string
    tags: string[]
    width: number
    height: number
    file_size: number
    is_trash: boolean
  }[]
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
  enabled: boolean
}

export interface RuleGroup {
  id: number
  name: string
  enabled: boolean
  keywords: RuleKeyword[]
  children: RuleGroup[]
  // 前端扩展字段（用于搜索和冲突检测）
  isMatch?: boolean
  isConflict?: boolean
  conflictReason?: string
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
