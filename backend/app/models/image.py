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
    # 新增参数 - 与旧项目一致
    min_tags: int = Field(default=0, ge=0, description="最小标签数量")
    max_tags: int = Field(default=-1, ge=-1, description="最大标签数量(-1 表示无限制)")
    sort_by: str = Field(default="time_desc", description="排序方式: time_desc, time_asc, tags_desc, tags_asc, size_desc, size_asc, resolution_desc, resolution_asc")
    extensions: list[str] = Field(default_factory=list, description="文件扩展名过滤")
    exclude_extensions: list[str] = Field(default_factory=list, description="排除的文件扩展名")
    expand: bool = Field(default=True, description="是否启用关键词膨胀")

    # 游标分页（可选）。填了就走 keyset 分页，完全跳过 OFFSET。
    #
    # 背景：OFFSET 越大越慢（SQLite 必须扫过并丢弃前 N 行），
    # 43 万行下翻到末尾要 600ms+。keyset 分页用「上一页最后一条的位置」
    # 直接定位，任意深度都是 O(1)。
    #
    # 由于时间排序的键是 (created_at, id) 复合键，
    # 游标必须**同时**带 cursor_ts 和 cursor_id，两个一起回传。
    # 与 page 参数二选一：填了游标就忽略 page。
    cursor_id: int | None = Field(default=None, description="游标分页：上一页最后一条的 id")
    cursor_ts: str | None = Field(default=None, description="游标分页：上一页最后一条的 created_at")


class SearchResultItem(BaseModel):
    """旧项目搜索结果条目"""
    md5: str
    filename: str
    tags: list[str]
    w: int
    h: int
    size: int
    is_trash: bool


class SearchResponse(BaseModel):
    """搜索响应（旧项目格式）"""
    total: int
    results: list[SearchResultItem]
