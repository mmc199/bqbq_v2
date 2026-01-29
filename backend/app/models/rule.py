"""
规则树相关 Pydantic 模型
"""
from pydantic import BaseModel, Field


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: int
    keyword: str
    group_id: int


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
