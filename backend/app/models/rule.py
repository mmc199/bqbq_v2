"""
规则树相关 Pydantic 模型
"""
from pydantic import BaseModel, Field


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: int
    keyword: str
    group_id: int
    enabled: bool = True


class GroupBase(BaseModel):
    """规则组基础模型"""
    name: str


class GroupCreate(BaseModel):
    """创建规则组请求"""
    name: str
    parent_id: int | None = None
    client_id: str
    base_version: int


class GroupResponse(BaseModel):
    """规则组响应（含子节点）"""
    id: int
    name: str
    enabled: bool = True
    keywords: list[KeywordResponse] = Field(default_factory=list)
    children: list["GroupResponse"] = Field(default_factory=list)


class RulesTreeResponse(BaseModel):
    """规则树响应"""
    version: int
    groups: list[GroupResponse]


class KeywordCreate(BaseModel):
    """添加关键词请求"""
    keyword: str
    client_id: str
    base_version: int


class CASRequest(BaseModel):
    """CAS 请求基类"""
    client_id: str
    base_version: int


class CASResponse(BaseModel):
    """CAS 响应"""
    success: bool
    new_version: int
    conflicts: int = 0
    message: str = ""


class GroupUpdate(BaseModel):
    """更新规则组请求"""
    name: str | None = None
    parent_id: int | None = None
    enabled: bool | None = None
    client_id: str
    base_version: int


class GroupToggle(BaseModel):
    """切换规则组启用状态"""
    enabled: bool
    client_id: str
    base_version: int


class GroupBatchRequest(BaseModel):
    """批量操作规则组请求"""
    group_ids: list[int]
    action: str  # "delete", "enable", "disable", "move"
    target_parent_id: int | None = None  # 用于 move 操作
    client_id: str
    base_version: int


class HierarchyAddRequest(BaseModel):
    """添加层级关系请求"""
    child_id: int
    parent_id: int
    client_id: str
    base_version: int


class HierarchyRemoveRequest(BaseModel):
    """删除层级关系请求"""
    child_id: int
    parent_id: int
    client_id: str
    base_version: int


class HierarchyBatchMoveRequest(BaseModel):
    """批量移动层级请求"""
    group_ids: list[int] | None = None
    child_ids: list[int] | None = None  # 旧项目字段
    new_parent_id: int | None = None
    parent_id: int | None = None  # 旧项目字段
    client_id: str
    base_version: int


class KeywordToggle(BaseModel):
    """切换关键词启用状态"""
    enabled: bool
    client_id: str
    base_version: int
