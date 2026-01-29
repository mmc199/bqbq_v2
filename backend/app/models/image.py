"""
图片相关 Pydantic 模型
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ImageBase(BaseModel):
    """图片基础模型"""
    filename: str
    tags: str = ""


class ImageCreate(BaseModel):
    """图片创建请求"""
    filename: str
    md5: str
    tags: list[str] = Field(default_factory=list)
    base64_data: str


class ImageUpdate(BaseModel):
    """图片更新请求"""
    tags: list[str]
    client_id: str
    base_version: int


class ImageResponse(BaseModel):
    """图片响应模型"""
    id: int
    filename: str
    md5: str
    tags: str
    created_at: datetime
    file_size: int = 0
    width: int = 0
    height: int = 0

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """搜索请求"""
    include_tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    """搜索响应"""
    images: list[ImageResponse]
    total: int
    page: int
    page_size: int
    expanded_tags: list[str] = Field(default_factory=list)
