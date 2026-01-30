/**
 * API 调用封装
 */
import type { ApiResponse, SearchRequest, SearchResponse, MemeImage, RulesTree, AdvancedSearchRequest, AdvancedSearchResponse } from '@/types'

const API_BASE = '/api'

// 通用请求函数
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()
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
    return request<AdvancedSearchResponse>('/search/advanced', {
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
    return { success: true, data }
  }

  // 创建规则组
  async function createGroup(
    name: string,
    parentId: number | null,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ id: number; new_version: number }>> {
    return request<{ id: number; new_version: number }>('/rules/groups', {
      method: 'POST',
      body: JSON.stringify({
        name,
        parent_id: parentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 添加关键词
  async function addKeyword(
    groupId: number,
    keyword: string,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ id: number; new_version: number }>> {
    return request<{ id: number; new_version: number }>(`/rules/groups/${groupId}/keywords`, {
      method: 'POST',
      body: JSON.stringify({
        keyword,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 删除规则组
  async function deleteGroup(
    groupId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>(`/rules/groups/${groupId}`, {
      method: 'DELETE',
      body: JSON.stringify({
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 移动规则组到新父节点
  async function moveGroup(
    groupId: number,
    newParentId: number | null,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>(`/rules/groups/${groupId}`, {
      method: 'PUT',
      body: JSON.stringify({
        parent_id: newParentId === null ? 0 : newParentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 添加层级关系
  async function addHierarchy(
    childId: number,
    parentId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>('/rules/hierarchy/add', {
      method: 'POST',
      body: JSON.stringify({
        child_id: childId,
        parent_id: parentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 移除层级关系（移动到根级别）
  async function removeHierarchy(
    childId: number,
    parentId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>('/rules/hierarchy/remove', {
      method: 'POST',
      body: JSON.stringify({
        child_id: childId,
        parent_id: parentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 删除关键词
  async function deleteKeyword(
    keywordId: number,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>(`/rules/keywords/${keywordId}`, {
      method: 'DELETE',
      body: JSON.stringify({
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 切换关键词启用状态
  async function toggleKeyword(
    keywordId: number,
    enabled: boolean,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>(`/rules/keywords/${keywordId}/toggle`, {
      method: 'POST',
      body: JSON.stringify({
        enabled,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 切换规则组启用状态
  async function toggleGroup(
    groupId: number,
    enabled: boolean,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>(`/rules/groups/${groupId}/toggle`, {
      method: 'POST',
      body: JSON.stringify({
        enabled,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 批量操作规则组
  async function batchGroups(
    groupIds: number[],
    action: 'delete' | 'enable' | 'disable' | 'move',
    clientId: string,
    baseVersion: number,
    targetParentId?: number | null
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>('/rules/groups/batch', {
      method: 'POST',
      body: JSON.stringify({
        group_ids: groupIds,
        action,
        target_parent_id: targetParentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  // 批量移动层级
  async function batchMoveHierarchy(
    groupIds: number[],
    newParentId: number | null,
    clientId: string,
    baseVersion: number
  ): Promise<ApiResponse<{ new_version: number }>> {
    return request<{ new_version: number }>('/rules/hierarchy/batch_move', {
      method: 'POST',
      body: JSON.stringify({
        group_ids: groupIds,
        new_parent_id: newParentId,
        client_id: clientId,
        base_version: baseVersion,
      }),
    })
  }

  return {
    getRulesTree,
    createGroup,
    addKeyword,
    deleteGroup,
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
  async function exportData(): Promise<ApiResponse<Blob>> {
    const response = await fetch(`${API_BASE}/export`)
    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }
    const blob = await response.blob()
    return { success: true, data: blob }
  }

  // 导入数据
  async function importData(file: File): Promise<ApiResponse<{ imported: number }>> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE}/import`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` }
    }

    return await response.json()
  }

  return {
    getAllTags,
    getTagSuggestions,
    exportData,
    importData,
  }
}
