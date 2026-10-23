"""购物车相关的请求 / 响应模型。"""
from pydantic import BaseModel


class CartAddRequest(BaseModel):
    """加入 / 移出购物车。"""
    client_id: str
    md5: str


class CartSendRequest(BaseModel):
    """把购物车推入待取回队列。"""
    client_id: str
    md5s: list[str] | None = None   # 不传 = 整个购物车


class CartItem(BaseModel):
    md5: str
    filename: str
    tags: list[str] = []
    thumb_url: str = ""
    added_at: str | None = None


class CartListResponse(BaseModel):
    items: list[CartItem]
    total: int


class CartOutboxItem(BaseModel):
    """bot 取回的一张图。"""
    md5: str
    filename: str
    url: str


class CartOutboxResponse(BaseModel):
    items: list[CartOutboxItem]
    remaining: int = 0
    message: str | None = None
