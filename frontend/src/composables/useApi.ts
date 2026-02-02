/**
 * API 调用封装
 */
import type {
  ApiResponse,
  SearchRequest,
  SearchResponse,
  MemeImage,
  RulesTree,
  AdvancedSearchRequest,
  AdvancedSearchResponse,
  LegacyRulesData,
  RuleGroup,
  RuleKeyword,
} from '@/types'

const API_BASE = '/api'

// 冲突响应类型（与旧项目保持一致）
export interface ConflictResponse {
  success: false
  error: 'conflict'
  status: number
  latest_data: LegacyRulesData
  unique_modifiers: number
}

// 通用请求函数
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T> & { conflict?: ConflictResponse }> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    const data = await response.json()

    // 处理 409 冲突响应（与旧项目保持一致）
    if (response.status === 409) {
      const message = data?.error === 'conflict'
        ? '版本冲突'
        : (data?.detail || data?.error || '版本冲突')
      return {
        success: false,
        error: `HTTP 409: ${message}`,
        conflict: data as ConflictResponse,
      }
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${data.detail || response.statusText}`)
    }

    // 后端直接返回数据，包装成 ApiResponse 格式
    return { success: true, data }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : '未知错误',
    }
  }
}

// 图片相关 API
export function useImageApi() {
  // 搜索图片
  async function searchImages(params: SearchRequest): Promise<ApiResponse<SearchResponse>> {
    return request<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  // 高级搜索（兼容旧项目二维数组格式）
  async function advancedSearch(params: AdvancedSearchRequest): Promise<ApiResponse<AdvancedSearchResponse>> {
    return request<AdvancedSearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  // 获取单张图片
  async function getImage(id: number): Promise<ApiResponse<MemeImage>> {
    return request<MemeImage>(`/images/${id}`)
  }

  // 上传图片
  async function uploadImage(data: {
    filename: string
    md5: string
    tags: string[]
    base64_data: string
  }): Promise<ApiResponse<MemeImage>> {
    return request<MemeImage>('/images', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // 检查 MD5 是否存在
  async function checkMD5(md5: string, refreshTime: boolean = false): Promise<ApiResponse<{ exists: boolean; filename?: string; time_refreshed?: boolean }>> {
    return request<{ exists: boolean; filename?: string; time_refreshed?: boolean }>(`/images/check-md5/${md5}?refresh_time=${refreshTime}`)
  }

  // 更新图片标签
  async function updateImageTags(
    id: number,
    tags: string[],
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>(`/images/${id}/tags`, {
      method: 'PUT',
      body: JSON.stringify({
        tags,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 删除图片
  async function deleteImage(id: number): Promise<ApiResponse<void>> {
    return request<void>(`/images/${id}`, {
      method: 'DELETE',
    })
  }

  return {
    searchImages,
    advancedSearch,
    getImage,
    uploadImage,
    checkMD5,
    updateImageTags,
    deleteImage,
  }
}

// 规则树相关 API
export function useRulesApi() {
  function buildRulesTreeFromLegacy(data: LegacyRulesData | null | undefined): RulesTree {
    const safeData = data ?? { version_id: 0, groups: [], keywords: [], hierarchy: [] }
    const groupMap = new Map<number, RuleGroup>()
    const groups = Array.isArray(safeData.groups) ? safeData.groups : []
    const keywords = Array.isArray(safeData.keywords) ? safeData.keywords : []
    const hierarchy = Array.isArray(safeData.hierarchy) ? safeData.hierarchy : []

    groups.forEach((group) => {
      const rawId = (group as { group_id?: unknown; id?: unknown }).group_id
        ?? (group as { id?: unknown }).id
      const id = typeof rawId === 'number' ? rawId : Number(rawId)
      if (!Number.isFinite(id)) return
      groupMap.set(id, {
        id,
        name: (group as { group_name?: string; name?: string }).group_name
          ?? (group as { name?: string }).name
          ?? '',
        enabled: !!((group as { is_enabled?: unknown; enabled?: unknown }).is_enabled
          ?? (group as { enabled?: unknown }).enabled),
        keywords: [],
        children: [],
      })
    })

    let keywordId = 1
    keywords.forEach((kw) => {
      const rawGroupId = (kw as { group_id?: unknown; groupId?: unknown }).group_id
        ?? (kw as { groupId?: unknown }).groupId
      const groupId = typeof rawGroupId === 'number' ? rawGroupId : Number(rawGroupId)
      if (!Number.isFinite(groupId)) return
      const target = groupMap.get(groupId)
      if (!target) return
      const keywordText = (kw as { keyword?: string; text?: string }).keyword
        ?? (kw as { text?: string }).text
        ?? ''
      const keyword: RuleKeyword = {
        id: keywordId++,
        keyword: keywordText,
        group_id: groupId,
        enabled: !!((kw as { is_enabled?: unknown; enabled?: unknown }).is_enabled
          ?? (kw as { enabled?: unknown }).enabled),
      }
      target.keywords.push(keyword)
    })

    const hasParent = new Set<number>()
    hierarchy.forEach((rel) => {
      if (!rel) return
      const rawParentId = (rel as { parent_id?: unknown; parentId?: unknown }).parent_id
        ?? (rel as { parentId?: unknown }).parentId
      const rawChildId = (rel as { child_id?: unknown; childId?: unknown }).child_id
        ?? (rel as { childId?: unknown }).childId
      const parentId = typeof rawParentId === 'number' ? rawParentId : Number(rawParentId)
      const childId = typeof rawChildId === 'number' ? rawChildId : Number(rawChildId)
      if (!Number.isFinite(childId)) return
      if (parentId === 0 || Number.isNaN(parentId)) return
      const parent = groupMap.get(parentId)
      const child = groupMap.get(childId)
      if (parent && child) {
        parent.children.push(child)
        hasParent.add(child.id)
      }
    })

    const roots: RuleGroup[] = []
    groupMap.forEach((group, id) => {
      if (!hasParent.has(id)) {
        roots.push(group)
      }
    })

    return {
      version: typeof safeData.version_id === 'number' ? safeData.version_id : 0,
      groups: roots,
      hierarchy,
    }
  }

  // 获取规则树
  async function getRulesTree(currentVersion?: number): Promise<ApiResponse<RulesTree> & { notModified?: boolean }> {
    const headers: Record<string, string> = {}
    if (currentVersion !== undefined) {
      headers['If-None-Match'] = currentVersion.toString()
    }

    const response = await fetch(`${API_BASE}/rules`, { headers })

    if (response.status === 304) {
      return { success: true, notModified: true }
    }

    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }

    const data = await response.json()
    const legacyData = (data?.latest_data ?? data?.data ?? data) as LegacyRulesData
    return { success: true, data: buildRulesTreeFromLegacy(legacyData) }
  }

  // 创建规则组
  async function createGroup(
    name: string,
    parentId: number | null,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ id: number; new_version: number }>> {
    const result = await request<{ version_id: number; new_id: number }>('/rules/group/add', {
      method: 'POST',
      body: JSON.stringify({
        group_name: name,
        is_enabled: 1,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ id: number; new_version: number }>
    }

    let newVersion = result.data.version_id
    if (parentId !== null) {
      const moveResult = await request<{ version_id: number }>('/rules/hierarchy/add', {
        method: 'POST',
        body: JSON.stringify({
          child_id: result.data.new_id,
          parent_id: parentId,
          client_id: clientId,
          base_version: newVersion,
        }),
      })

      if (moveResult.success && moveResult.data?.version_id) {
        newVersion = moveResult.data.version_id
      } else if (!moveResult.success) {
        return moveResult as ApiResponse<{ id: number; new_version: number }>
      }
    }

    return {
      success: true,
      data: {
        id: result.data.new_id,
        new_version: newVersion,
      },
    }
  }

  // 添加关键词
  async function addKeyword(
    groupId: number,
    keyword: string,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ id: number; new_version: number }>> {
    const result = await request<{ version_id: number }>('/rules/keyword/add', {
      method: 'POST',
      body: JSON.stringify({
        group_id: groupId,
        keyword,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ id: number; new_version: number }>
    }

    return {
      success: true,
      data: {
        id: -1,
        new_version: result.data.version_id,
      },
    }
  }

  // 删除规则组
  async function deleteGroup(
    groupId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number; deleted_count?: number }>> {
    const result = await request<{ version_id: number; deleted_count?: number }>('/rules/group/delete', {
      method: 'POST',
      body: JSON.stringify({
        group_id: groupId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number; deleted_count?: number }>
    }

    return {
      success: true,
      data: {
        new_version: result.data.version_id,
        deleted_count: result.data.deleted_count,
      },
    }
  }

  // 重命名规则组
  async function renameGroup(
    groupId: number,
    name: string,
    enabled: boolean,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    const result = await request<{ version_id: number }>('/rules/group/update', {
      method: 'POST',
      body: JSON.stringify({
        group_id: groupId,
        group_name: name,
        is_enabled: enabled ? 1 : 0,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number }>
    }

    return {
      success: true,
      data: {
        new_version: result.data.version_id,
      },
    }
  }

  // 移动规则组到新父节点
  async function moveGroup(
    groupId: number,
    newParentId: number | null,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    const result = await request<{ version_id: number }>('/rules/hierarchy/add', {
      method: 'POST',
      body: JSON.stringify({
        child_id: groupId,
        parent_id: newParentId === null ? 0 : newParentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number }>
    }

    return {
      success: true,
      data: { new_version: result.data.version_id },
    }
  }

  // 添加层级关系
  async function addHierarchy(
    childId: number,
    parentId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    const result = await request<{ version_id: number }>('/rules/hierarchy/add', {
      method: 'POST',
      body: JSON.stringify({
        child_id: childId,
        parent_id: parentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number }>
    }

    return {
      success: true,
      data: { new_version: result.data.version_id },
    }
  }

  // 移除层级关系（移动到根级别）
  async function removeHierarchy(
    childId: number,
    parentId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    const result = await request<{ version_id: number }>('/rules/hierarchy/remove', {
      method: 'POST',
      body: JSON.stringify({
        child_id: childId,
        parent_id: parentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number }>
    }

    return {
      success: true,
      data: { new_version: result.data.version_id },
    }
  }

  // 删除关键词
  async function deleteKeyword(
    groupId: number,
    keyword: string,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ version_id: number }>> {
    return request<{ version_id: number }>('/rules/keyword/remove', {
      method: 'POST',
      body: JSON.stringify({
        group_id: groupId,
        keyword,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 切换关键词启用状态
  async function toggleKeyword() {
    return { success: false, error: 'Keyword toggle not supported' }
  }

  // 切换规则组启用状态
  async function toggleGroup(
    groupId: number,
    enabled: boolean,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    const result = await request<{ version_id: number }>('/rules/group/toggle', {
      method: 'POST',
      body: JSON.stringify({
        group_id: groupId,
        is_enabled: enabled ? 1 : 0,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number }>
    }

    return {
      success: true,
      data: {
        new_version: result.data.version_id,
      },
    }
  }

  // 批量操作规则组
  async function batchGroups(
    groupIds: number[],
    action: 'delete' | 'enable' | 'disable' | 'move',
    clientId: string,
    baseVersion: number,
    targetParentId?: number | null
  ): Promise<ApiResponse<{ new_version: number; affected_count?: number }>> {
    if (action === 'move') {
      const result = await request<{ version_id: number; success?: boolean; moved?: number; errors?: unknown[] }>('/rules/hierarchy/batch_move', {
        method: 'POST',
        body: JSON.stringify({
          group_ids: groupIds,
          new_parent_id: targetParentId ?? 0,
          client_id: clientId,
          base_version: baseVersion,
        }),
      })
      if (!result.success || !result.data) {
        return result as ApiResponse<{ new_version: number; affected_count?: number }>
      }

      return {
        success: true,
        data: { new_version: result.data.version_id },
      }
    }

    const result = await request<{ version_id: number; affected_count?: number }>('/rules/group/batch', {
      method: 'POST',
      body: JSON.stringify({
        group_ids: groupIds,
        action,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })

    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number; affected_count?: number }>
    }

    return {
      success: true,
      data: {
        new_version: result.data.version_id,
        affected_count: result.data.affected_count,
      },
    }
  }

  // 批量移动层级
  async function batchMoveHierarchy(
    groupIds: number[],
    newParentId: number | null,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number; moved?: number; errors?: unknown[] }>> {
    const result = await request<{ version_id: number; success?: boolean; moved?: number; errors?: unknown[] }>('/rules/hierarchy/batch_move', {
      method: 'POST',
      body: JSON.stringify({
        group_ids: groupIds,
        new_parent_id: newParentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
    if (!result.success || !result.data) {
      return result as ApiResponse<{ new_version: number; moved?: number; errors?: unknown[] }>
    }

    const apiSuccess = result.data.success !== undefined ? result.data.success : true
    const moved = result.data.moved ?? groupIds.length
    const errors = result.data.errors ?? []

    return {
      success: apiSuccess,
      data: { new_version: result.data.version_id, moved, errors },
    }
  }

  return {
    getRulesTree,
    createGroup,
    addKeyword,
    deleteGroup,
    renameGroup,
    deleteKeyword,
    toggleKeyword,
    moveGroup,
    toggleGroup,
    batchGroups,
    addHierarchy,
    removeHierarchy,
    batchMoveHierarchy,
  }
}

// 系统相关 API
export function useSystemApi() {
  // 获取所有标签
  async function getAllTags(): Promise<ApiResponse<{ tags: string[] }>> {
    return request<{ tags: string[] }>('/tags')
  }

  // 获取标签建议（按使用次数排序，兼容旧项目）
  async function getTagSuggestions(): Promise<ApiResponse<string[]>> {
    return request<string[]>('/meta/tags')
  }

  // 导出数据
  async function exportData(): Promise<ApiResponse<Record<string, unknown>>> {
    return request<Record<string, unknown>>('/export/all')
  }

  // 导入数据
  async function importData(file: File): Promise<ApiResponse<{ imported_images?: number; skipped_images?: number; message?: string; success?: boolean; error?: string }>> {
    let payload: Record<string, unknown>
    try {
      const content = await file.text()
      payload = JSON.parse(content) as Record<string, unknown>
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '无效的 JSON 文件',
      }
    }

    return request<{ imported_images?: number; skipped_images?: number; message?: string; success?: boolean; error?: string }>(
      '/import/all',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    )
  }

  // 更新图片标签（旧项目兼容）
  async function updateTags(md5: string, tags: string[]): Promise<ApiResponse<{ success: boolean }>> {
    return request<{ success: boolean }>('/update_tags', {
      method: 'POST',
      body: JSON.stringify({ md5, tags }),
    })
  }

  return {
    getAllTags,
    getTagSuggestions,
    exportData,
    importData,
    updateTags,
  }
}
